import json
from pathlib import Path

import pytest

from loop_engineering_example.loop.runner import ScriptedLoop
from loop_engineering_example.loop.state_machine import LoopState
from loop_engineering_example.loop.storage import Record, StorageError
from loop_engineering_example.loop.triage import (
    CodexExplorer,
    build_triage_prompt,
    parse_token_usage,
    validate_triage_result,
)


class FakeExplorer:
    def __init__(self, result: Record) -> None:
        self.result = result
        self.prompt = ""

    def explore(self, prompt: str, output_directory: Path) -> Record:
        self.prompt = prompt
        output_directory.mkdir(parents=True, exist_ok=True)
        return dict(self.result)


def event() -> Record:
    return {
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


def write_fixtures(root: Path) -> None:
    path = root / "monitoring" / "events.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(event()) + "\n", encoding="utf-8")


def ready_result() -> Record:
    return {
        "decision": "ready",
        "summary": "Division by zero escapes the API boundary.",
        "relevant_files": [
            "src/loop_engineering_example/app/calculator.py",
            "src/loop_engineering_example/app/api.py",
        ],
        "constraints": ["Preserve existing operations."],
        "risks": ["Changing the response contract could break callers."],
        "ambiguities": [],
        "success_predicate": (
            "A divide request with right=0 returns a controlled application error."
        ),
        "recommended_tests": ["make check", "make reproduce-division-by-zero"],
        "confidence": 0.95,
    }


def prepare_triaged_loop(
    tmp_path: Path,
    explorer: FakeExplorer,
) -> ScriptedLoop:
    fixtures = tmp_path / "fixtures"
    write_fixtures(fixtures)
    loop = ScriptedLoop(
        tmp_path / "run",
        fixtures=fixtures,
        explorer=explorer,
        repository=Path.cwd(),
    )
    loop.reset()
    loop.advance()
    assert loop.advance()["current"] == LoopState.TRIAGED
    return loop


def test_valid_explorer_output_advances_ticket_to_ready(tmp_path: Path) -> None:
    explorer = FakeExplorer(ready_result())
    loop = prepare_triaged_loop(tmp_path, explorer)

    result = loop.advance()

    assert result["current"] == LoopState.READY
    assert result["agent"] == "explorer"
    assert result["evidence"][-1]["kind"] == "success_predicate"
    assert loop.tickets.list_tickets()[0]["status"] == "ready"
    assert "## Monitoring event" in explorer.prompt
    assert "## Ticket body" in explorer.prompt
    assert (tmp_path / "run/agent/triage/validated-result.json").exists()


def test_ambiguous_output_escalates_instead_of_guessing(tmp_path: Path) -> None:
    result = ready_result()
    result.update(
        {
            "decision": "escalate",
            "ambiguities": ["Expected decimal precision is not specified."],
            "success_predicate": None,
            "confidence": 0.8,
        }
    )
    loop = prepare_triaged_loop(tmp_path, FakeExplorer(result))

    state = loop.advance()

    assert state["current"] == LoopState.ESCALATED
    assert "decimal precision" in state["last_error"]
    assert loop.tickets.list_tickets()[0]["status"] == "escalated"


@pytest.mark.parametrize(
    "invalid",
    [
        {"decision": "ready"},
        dict(ready_result(), success_predicate=None),
        dict(ready_result(), ambiguities=["Still unclear."]),
        dict(
            ready_result(),
            decision="escalate",
            ambiguities=[],
            success_predicate=None,
        ),
    ],
)
def test_invalid_output_cannot_advance_state(
    tmp_path: Path,
    invalid: Record,
) -> None:
    loop = prepare_triaged_loop(tmp_path, FakeExplorer(invalid))

    with pytest.raises(StorageError):
        loop.advance()

    assert loop.status()["current"] == LoopState.TRIAGED
    assert loop.tickets.list_tickets()[0]["status"] == "triaged"


def test_codex_runtime_is_ephemeral_read_only_and_schema_bound(tmp_path: Path) -> None:
    explorer = CodexExplorer(
        repository=tmp_path,
        schema_path=tmp_path / "schema.json",
    )

    command = explorer.command(tmp_path / "result.json")

    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in command
    assert "--ignore-user-config" in command
    assert "--output-schema" in command
    assert "--output-last-message" in command


def test_prompt_contains_supplied_evidence() -> None:
    prompt = build_triage_prompt(
        "Read only.",
        event(),
        {"ticket_id": "TICKET-001"},
        "# Ticket body",
    )

    assert "evt-001" in prompt
    assert "TICKET-001" in prompt
    assert "# Ticket body" in prompt


def test_token_usage_uses_last_reported_total() -> None:
    stderr = "tokens used\n18,128\nretry\ntokens used\n21,243\n"

    assert parse_token_usage(stderr) == 21243


def test_missing_token_usage_is_unknown() -> None:
    assert parse_token_usage("no usage report") is None


def test_validation_rejects_confidence_outside_range() -> None:
    result = ready_result()
    result["confidence"] = 2

    with pytest.raises(StorageError, match="confidence"):
        validate_triage_result(result)
