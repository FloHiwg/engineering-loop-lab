"""CLI and deterministic orchestration for the scripted loop."""

from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Callable
from pathlib import Path

from loop_engineering_example.loop.adapters import (
    CIAdapter,
    MonitoringAdapter,
    PullRequestAdapter,
    StateAdapter,
    TicketAdapter,
)
from loop_engineering_example.loop.state_machine import (
    TERMINAL_STATES,
    LoopState,
    transition,
    validate_loop_state,
)
from loop_engineering_example.loop.storage import Record, StorageError
from loop_engineering_example.loop.triage import (
    CodexExplorer,
    ExplorerRuntime,
    build_triage_prompt,
    save_validated_result,
)

DEFAULT_ROOT = Path("runs/demo")
DEFAULT_FIXTURES = Path("mock-systems")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TransitionObserver = Callable[[Record, Record], None]


class ScriptedLoop:
    def __init__(
        self,
        root: Path,
        fixtures: Path = DEFAULT_FIXTURES,
        explorer: ExplorerRuntime | None = None,
        repository: Path = REPOSITORY_ROOT,
    ) -> None:
        self.root = root
        self.fixtures = fixtures
        self.explorer = explorer
        self.repository = repository
        self.monitoring = MonitoringAdapter(root)
        self.tickets = TicketAdapter(root)
        self.ci = CIAdapter(root)
        self.pull_requests = PullRequestAdapter(root)
        self.state = StateAdapter(root / "state.json", validate_loop_state)

    def reset(self) -> Record:
        if self.root.exists():
            shutil.rmtree(self.root)
        event_path = self.fixtures / "monitoring" / "events.jsonl"
        seed_event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[0])
        self.monitoring.emit(seed_event)
        return self.state.save({"version": 1, "current": None})["state"]

    def status(self) -> Record:
        return self.state.load()

    def advance(self) -> Record:
        state = self.state.load()
        if state.get("current") is None:
            return self._discover()

        current = validate_loop_state(state)
        actions = {
            LoopState.DISCOVERED: self._triage,
            LoopState.TRIAGED: self._explore if self.explorer else self._ready,
            LoopState.READY: self._implement,
            LoopState.IMPLEMENTING: self._verify,
            LoopState.VERIFYING: self._open_pull_request,
            LoopState.PR_OPEN: self._complete,
        }
        if current in TERMINAL_STATES:
            return state
        try:
            action = actions[current]
        except KeyError as error:
            raise StorageError(f"no scripted action for state: {current}") from error
        return action(state)

    def run(self, observer: TransitionObserver | None = None) -> Record:
        state = self.status()
        while state.get("current") is None or LoopState(state["current"]) not in (
            TERMINAL_STATES
        ):
            previous = state
            state = self.advance()
            if observer is not None:
                observer(previous, state)
        return state

    def _discover(self) -> Record:
        events = self.monitoring.list_events()
        if not events:
            raise StorageError("no monitoring event available")
        event = events[0]
        state: Record = {
            "version": 1,
            "current": LoopState.DISCOVERED.value,
            "event_id": event["event_id"],
            "ticket_id": None,
            "worktree": None,
            "branch": None,
            "agent": None,
            "attempt_count": 0,
            "evidence": [
                {
                    "kind": "monitoring_event",
                    "id": event["event_id"],
                    "reproduce": event["reproduce"],
                }
            ],
            "token_cost_estimate": 0.0,
            "last_error": None,
            "next_action": "triage event",
        }
        validate_loop_state(state)
        return self.state.save(state)["state"]

    def _event(self, state: Record) -> Record:
        for event in self.monitoring.list_events():
            if event["event_id"] == state["event_id"]:
                return event
        raise StorageError(f"unknown event: {state['event_id']}")

    def _triage(self, state: Record) -> Record:
        ticket_result = self.tickets.create_or_get(self._event(state))
        ticket = ticket_result["ticket"]
        self.tickets.transition(ticket["ticket_id"], "triaged")
        updated = transition(
            state,
            LoopState.TRIAGED,
            ticket_id=ticket["ticket_id"],
            next_action="establish scripted readiness",
        )
        return self.state.save(updated)["state"]

    def _ready(self, state: Record) -> Record:
        ticket_id = state["ticket_id"]
        self.tickets.transition(ticket_id, "ready")
        evidence = [
            *state["evidence"],
            {
                "kind": "success_predicate",
                "value": "division by zero returns a controlled application error",
            },
        ]
        updated = transition(
            state,
            LoopState.READY,
            evidence=evidence,
            next_action="run scripted implementation",
        )
        return self.state.save(updated)["state"]

    def _explore(self, state: Record) -> Record:
        ticket_id = state["ticket_id"]
        ticket = next(
            ticket
            for ticket in self.tickets.list_tickets()
            if ticket["ticket_id"] == ticket_id
        )
        ticket_text = (self.root / "tickets" / ticket["file"]).read_text(
            encoding="utf-8"
        )
        instructions = (self.repository / "agents" / "explorer.md").read_text(
            encoding="utf-8"
        )
        prompt = build_triage_prompt(
            instructions,
            self._event(state),
            ticket,
            ticket_text,
        )
        output_directory = self.root / "agent" / "triage"
        raw_result = self.explorer.explore(prompt, output_directory)
        result = save_validated_result(output_directory, dict(raw_result))
        evidence = [
            *state["evidence"],
            {
                "kind": "triage_report",
                "decision": result["decision"],
                "path": "agent/triage/validated-result.json",
            },
        ]
        if result["decision"] == "escalate":
            self.tickets.transition(ticket_id, "escalated")
            updated = transition(
                state,
                LoopState.ESCALATED,
                agent="explorer",
                evidence=evidence,
                last_error="; ".join(result["ambiguities"]),
                next_action=None,
            )
            return self.state.save(updated)["state"]

        self.tickets.transition(ticket_id, "ready")
        evidence.append(
            {
                "kind": "success_predicate",
                "value": result["success_predicate"],
            }
        )
        updated = transition(
            state,
            LoopState.READY,
            agent="explorer",
            evidence=evidence,
            next_action="run implementation in an isolated worktree",
        )
        return self.state.save(updated)["state"]

    def _implement(self, state: Record) -> Record:
        ticket_id = state["ticket_id"]
        self.tickets.transition(ticket_id, "implementing")
        branch = f"loop/{ticket_id.lower()}"
        updated = transition(
            state,
            LoopState.IMPLEMENTING,
            branch=branch,
            worktree=f"worktrees/{ticket_id.lower()}",
            agent="scripted-implementer",
            attempt_count=state["attempt_count"] + 1,
            next_action="verify scripted implementation evidence",
        )
        return self.state.save(updated)["state"]

    def _verify(self, state: Record) -> Record:
        ticket_id = state["ticket_id"]
        run = {
            "run_id": f"ci-{ticket_id.lower()}-attempt-{state['attempt_count']}",
            "ticket_id": ticket_id,
            "status": "passed",
            "command": "scripted verification",
            "output": "orchestration checkpoint; no source change executed",
        }
        ci_result = self.ci.record(run)
        self.tickets.transition(ticket_id, "verifying")
        evidence = [
            *state["evidence"],
            {"kind": "ci_run", "id": ci_result["run"]["run_id"], "status": "passed"},
        ]
        updated = transition(
            state,
            LoopState.VERIFYING,
            evidence=evidence,
            agent="scripted-verifier",
            next_action="open mock pull request",
        )
        return self.state.save(updated)["state"]

    def _open_pull_request(self, state: Record) -> Record:
        ticket_id = state["ticket_id"]
        ticket = next(
            ticket
            for ticket in self.tickets.list_tickets()
            if ticket["ticket_id"] == ticket_id
        )
        ci_run_id = next(
            evidence["id"]
            for evidence in state["evidence"]
            if evidence["kind"] == "ci_run"
        )
        result = self.pull_requests.open(
            ticket,
            "Scripted checkpoint: no source diff.",
            ci_run_id,
        )
        pull_request_id = result["pull_request"]["pull_request_id"]
        self.pull_requests.review(
            pull_request_id,
            "approved",
            "Scripted verifier accepted orchestration evidence.",
        )
        self.tickets.transition(ticket_id, "pr_open")
        evidence = [
            *state["evidence"],
            {"kind": "pull_request", "id": pull_request_id, "verdict": "approved"},
        ]
        updated = transition(
            state,
            LoopState.PR_OPEN,
            evidence=evidence,
            next_action="complete scripted lifecycle",
        )
        return self.state.save(updated)["state"]

    def _complete(self, state: Record) -> Record:
        pull_request_id = next(
            evidence["id"]
            for evidence in state["evidence"]
            if evidence["kind"] == "pull_request"
        )
        self.pull_requests.merge(pull_request_id)
        self.tickets.transition(state["ticket_id"], "done")
        self.monitoring.acknowledge(state["event_id"])
        updated = transition(
            state,
            LoopState.DONE,
            agent=None,
            next_action=None,
        )
        return self.state.save(updated)["state"]


def describe_transition(previous: Record, current: Record) -> list[str]:
    state = LoopState(current["current"])
    match state:
        case LoopState.DISCOVERED:
            description = (
                f"Read monitoring event {current['event_id']} and selected it for work."
            )
        case LoopState.TRIAGED:
            description = (
                f"Created or reused ticket {current['ticket_id']} "
                "and marked it triaged."
            )
        case LoopState.READY:
            description = (
                "Added a scripted success predicate and marked the ticket ready."
            )
        case LoopState.IMPLEMENTING:
            description = (
                f"Assigned {current['agent']} on {current['branch']} "
                f"(attempt {current['attempt_count']})."
            )
        case LoopState.VERIFYING:
            description = "Recorded a passing scripted CI run."
        case LoopState.PR_OPEN:
            description = "Opened and approved a mock pull request."
        case LoopState.DONE:
            description = (
                "Merged the pull request, completed the ticket, "
                "and acknowledged the event."
            )
        case _:
            raise StorageError(f"no demo description for state: {state}")
    previous_evidence = previous.get("evidence", [])
    new_evidence = current["evidence"][len(previous_evidence) :]
    lines = [f"{state.value}: {description}"]
    for evidence in new_evidence:
        identifier = evidence.get("id") or evidence.get("value")
        lines.append(f"  evidence + {evidence['kind']}: {identifier}")
    if current["next_action"] is not None:
        lines.append(f"  next: {current['next_action']}")
    return lines


def run_demo(loop: ScriptedLoop) -> Record:
    loop.reset()
    print("Scripted loop demo")
    print(f"Runtime files: {loop.root}")
    print("Note: implementation, CI, and review are simulated in this checkpoint.")
    step = 0

    def observe(previous: Record, current: Record) -> None:
        nonlocal step
        step += 1
        lines = describe_transition(previous, current)
        print(f"\n[{step}/7] {lines[0]}")
        for line in lines[1:]:
            print(line)

    result = loop.run(observer=observe)
    print("\nCompleted: DONE")
    print("Inspect artifacts with: make inspect-demo")
    print("Confirm the bug remains with: make reproduce-division-by-zero")
    return result


def run_agent_demo(loop: ScriptedLoop) -> Record:
    loop.reset()
    print("Read-only explorer demo")
    print(f"Runtime files: {loop.root}")
    states = []
    while not states or states[-1] not in {LoopState.READY, LoopState.ESCALATED}:
        previous = loop.status()
        current = loop.advance()
        state = LoopState(current["current"])
        states.append(state)
        if state in {LoopState.DISCOVERED, LoopState.TRIAGED}:
            lines = describe_transition(previous, current)
            print(f"\n[{len(states)}/3] {lines[0]}")
            for line in lines[1:]:
                print(line)
        elif state is LoopState.READY:
            print("\n[3/3] READY: Explorer produced a validated success predicate.")
            print(f"  report: {loop.root / 'agent/triage/validated-result.json'}")
        else:
            print("\n[3/3] ESCALATED: Explorer found unresolved ambiguity.")
            print(f"  reason: {current['last_error']}")
            print(f"  report: {loop.root / 'agent/triage/validated-result.json'}")
    print(f"\nCompleted triage: {states[-1].value}")
    return current


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("agent-demo", "demo", "reset", "step", "run", "status"),
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "agent-demo":
        repository = REPOSITORY_ROOT
        explorer = CodexExplorer(
            repository=repository,
            schema_path=repository / "agents" / "explorer.schema.json",
        )
        loop = ScriptedLoop(
            arguments.root,
            fixtures=arguments.fixtures,
            explorer=explorer,
            repository=repository,
        )
        run_agent_demo(loop)
        return 0
    loop = ScriptedLoop(arguments.root, fixtures=arguments.fixtures)
    if arguments.command == "demo":
        run_demo(loop)
        return 0
    actions = {
        "reset": loop.reset,
        "step": loop.advance,
        "run": loop.run,
        "status": loop.status,
    }
    result = actions[arguments.command]()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
