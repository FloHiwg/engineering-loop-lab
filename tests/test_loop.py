import json
from pathlib import Path

import pytest

from loop_engineering_example.loop.adapters import (
    CIAdapter,
    PullRequestAdapter,
    StateAdapter,
    TicketAdapter,
)
from loop_engineering_example.loop.runner import (
    ScriptedLoop,
    build_snapshot,
    describe_transition,
)
from loop_engineering_example.loop.state_machine import (
    LoopState,
    validate_loop_state,
)
from loop_engineering_example.loop.storage import atomic_write_json


@pytest.fixture
def fixtures(tmp_path: Path) -> Path:
    root = tmp_path / "fixtures"
    event_path = root / "monitoring" / "events.jsonl"
    event_path.parent.mkdir(parents=True)
    event = {
        "event_id": "evt-001",
        "deduplication_key": "calculator:ZeroDivisionError:divide",
        "status": "open",
        "service": "calculator-api",
        "error_type": "ZeroDivisionError",
        "message": "division by zero",
        "request": {"operation": "divide", "left": 10, "right": 0},
        "source": {
            "module": "loop_engineering_example.app.calculator",
            "function": "divide",
        },
        "reproduce": "make reproduce-division-by-zero",
    }
    event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return root


def side_effect_counts(root: Path) -> dict[str, int]:
    monitoring_records = (root / "monitoring" / "events.jsonl").read_text().splitlines()
    return {
        "monitoring_records": len(monitoring_records),
        "tickets": len(TicketAdapter(root).list_tickets()),
        "ci_runs": len(CIAdapter(root).list_runs()),
        "pull_requests": len(PullRequestAdapter(root).list_pull_requests()),
    }


def test_scripted_happy_path_reaches_done(
    tmp_path: Path,
    fixtures: Path,
) -> None:
    root = tmp_path / "run"
    loop = ScriptedLoop(root, fixtures)
    loop.reset()

    result = loop.run()

    assert result["current"] == LoopState.DONE
    assert result["ticket_id"] == "TICKET-001"
    assert result["attempt_count"] == 1
    assert result["next_action"] is None
    assert side_effect_counts(root) == {
        "monitoring_records": 2,
        "tickets": 1,
        "ci_runs": 1,
        "pull_requests": 1,
    }
    assert TicketAdapter(root).list_tickets()[0]["status"] == "done"
    pull_request = PullRequestAdapter(root).list_pull_requests()[0]
    assert pull_request["review"]["verdict"] == "approved"
    assert pull_request["status"] == "merged"


def test_terminal_run_is_idempotent(tmp_path: Path, fixtures: Path) -> None:
    root = tmp_path / "run"
    loop = ScriptedLoop(root, fixtures)
    loop.reset()
    first = loop.run()
    counts = side_effect_counts(root)

    second = ScriptedLoop(root, fixtures).run()

    assert second == first
    assert side_effect_counts(root) == counts


def test_snapshot_collects_readable_system_state(
    tmp_path: Path,
    fixtures: Path,
) -> None:
    root = tmp_path / "run"
    loop = ScriptedLoop(root, fixtures)
    loop.reset()
    loop.advance()

    snapshot = build_snapshot(root)

    assert snapshot["monitoring"][0]["event_id"] == "evt-001"
    assert snapshot["state"]["current"] == LoopState.DISCOVERED
    assert snapshot["tickets"] == []


def test_restart_at_every_state_does_not_duplicate_side_effects(
    tmp_path: Path,
    fixtures: Path,
) -> None:
    root = tmp_path / "run"
    loop = ScriptedLoop(root, fixtures)
    loop.reset()

    while True:
        before = loop.status()
        first_result = ScriptedLoop(root, fixtures).advance()
        first_counts = side_effect_counts(root)

        if before["current"] is not None:
            StateAdapter(root / "state.json").save(before)
            repeated_result = ScriptedLoop(root, fixtures).advance()
            assert repeated_result == first_result
            assert side_effect_counts(root) == first_counts

        if first_result["current"] == LoopState.DONE:
            break
        loop = ScriptedLoop(root, fixtures)


def test_step_exposes_each_happy_path_state(
    tmp_path: Path,
    fixtures: Path,
) -> None:
    root = tmp_path / "run"
    loop = ScriptedLoop(root, fixtures)
    loop.reset()
    observed = []

    while not observed or observed[-1] != LoopState.DONE:
        state = ScriptedLoop(root, fixtures).advance()
        observed.append(LoopState(state["current"]))

    assert observed == [
        LoopState.DISCOVERED,
        LoopState.TRIAGED,
        LoopState.READY,
        LoopState.IMPLEMENTING,
        LoopState.VERIFYING,
        LoopState.PR_OPEN,
        LoopState.DONE,
    ]


def test_transition_description_explains_action_and_next_step() -> None:
    previous = {
        "current": LoopState.DISCOVERED,
        "evidence": [{"kind": "monitoring_event", "id": "evt-001"}],
    }
    current = {
        "current": LoopState.TRIAGED,
        "ticket_id": "TICKET-001",
        "evidence": previous["evidence"],
        "next_action": "establish scripted readiness",
    }

    assert describe_transition(previous, current) == [
        "TRIAGED: Created or reused ticket TICKET-001 and marked it triaged.",
        "  next: establish scripted readiness",
    ]


def test_state_adapter_rejects_invalid_persisted_loop_state(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    atomic_write_json(path, {"version": 1, "current": "UNKNOWN"})

    with pytest.raises(ValueError, match="missing required field: event_id"):
        StateAdapter(path, validator=validate_loop_state).load()
