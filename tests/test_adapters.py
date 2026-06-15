import json
from collections.abc import Callable
from pathlib import Path

import pytest

from loop_engineering_example.loop.adapters import (
    CIAdapter,
    MonitoringAdapter,
    PullRequestAdapter,
    StateAdapter,
    TicketAdapter,
)
from loop_engineering_example.loop.storage import StorageError


@pytest.fixture
def event() -> dict[str, object]:
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
        "acceptance_criteria": [
            'A divide request with right=0 returns {"error":"division by zero"}.',
            "No raw ZeroDivisionError escapes the API boundary.",
        ],
    }


def test_monitoring_contract_is_idempotent(
    tmp_path: Path,
    event: dict[str, object],
) -> None:
    adapter = MonitoringAdapter(tmp_path)

    assert adapter.emit(event)["created"] is True
    assert adapter.emit(event)["created"] is False
    assert adapter.acknowledge("evt-001")["created"] is True
    assert adapter.acknowledge("evt-001")["created"] is False
    assert len(adapter.list_acknowledgments()) == 1

    records = (tmp_path / "monitoring" / "events.jsonl").read_text().splitlines()
    assert len(records) == 2
    assert adapter.correlate(event["deduplication_key"]) == {
        "deduplication_key": event["deduplication_key"],
        "event_ids": ["evt-001"],
        "count": 1,
    }


def test_monitoring_correlates_distinct_events(
    tmp_path: Path,
    event: dict[str, object],
) -> None:
    adapter = MonitoringAdapter(tmp_path)
    adapter.emit(event)
    duplicate = dict(event, event_id="evt-002")
    adapter.emit(duplicate)

    assert adapter.correlate(event["deduplication_key"])["event_ids"] == [
        "evt-001",
        "evt-002",
    ]


def test_monitoring_rejects_invalid_and_conflicting_events(
    tmp_path: Path,
    event: dict[str, object],
) -> None:
    adapter = MonitoringAdapter(tmp_path)
    with pytest.raises(StorageError, match="missing required field: event_id"):
        adapter.emit({"message": "incomplete"})

    adapter.emit(event)
    with pytest.raises(StorageError, match="event ID already exists"):
        adapter.emit(dict(event, message="different"))


def test_ticket_contract_creates_one_readable_ticket(
    tmp_path: Path,
    event: dict[str, object],
) -> None:
    adapter = TicketAdapter(tmp_path)

    first = adapter.create_or_get(event)
    second = adapter.create_or_get(event)
    ticket_id = first["ticket"]["ticket_id"]

    assert first["created"] is True
    assert second["created"] is False
    assert len(adapter.list_tickets()) == 1
    assert adapter.transition(ticket_id, "triaged")["changed"] is True
    assert adapter.transition(ticket_id, "triaged")["changed"] is False
    assert adapter.comment(ticket_id, "Reproduced locally.")["created"] is True
    assert adapter.comment(ticket_id, "Reproduced locally.")["created"] is False

    ticket_text = (tmp_path / "tickets" / f"{ticket_id}.md").read_text()
    assert "- Status: triaged" in ticket_text
    assert "make reproduce-division-by-zero" in ticket_text
    assert "## Acceptance Criteria" in ticket_text
    assert "No raw ZeroDivisionError" in ticket_text
    assert ticket_text.count("Reproduced locally.") == 1


def test_ticket_defaults_are_isolated_between_roots(
    tmp_path: Path,
    event: dict[str, object],
) -> None:
    first = TicketAdapter(tmp_path / "first")
    second = TicketAdapter(tmp_path / "second")

    assert first.create_or_get(event)["ticket"]["ticket_id"] == "TICKET-001"
    assert second.create_or_get(event)["ticket"]["ticket_id"] == "TICKET-001"


def test_ci_contract_deduplicates_runs(tmp_path: Path) -> None:
    adapter = CIAdapter(tmp_path)
    run = {
        "run_id": "ci-001",
        "ticket_id": "TICKET-001",
        "status": "passed",
        "command": "make check",
        "output": "10 passed",
    }

    assert adapter.record(run)["created"] is True
    assert adapter.record(run)["created"] is False
    assert adapter.get("ci-001") == run
    assert adapter.list_runs() == [run]

    with pytest.raises(StorageError, match="CI run ID already exists"):
        adapter.record(dict(run, status="failed"))


def test_pull_request_contract_deduplicates_and_reviews(tmp_path: Path) -> None:
    adapter = PullRequestAdapter(tmp_path)
    ticket = {"ticket_id": "TICKET-001", "title": "Handle division by zero"}

    first = adapter.open(ticket, "diff --git", "ci-001")
    second = adapter.open(ticket, "different diff", "ci-002")
    pull_request_id = first["pull_request"]["pull_request_id"]

    assert first["created"] is True
    assert second["created"] is False
    assert len(adapter.list_pull_requests()) == 1
    assert adapter.review(pull_request_id, "approved", "All checks pass")["changed"]
    assert not adapter.review(pull_request_id, "approved", "All checks pass")["changed"]
    assert adapter.merge(pull_request_id)["changed"] is True
    assert adapter.merge(pull_request_id)["changed"] is False
    assert adapter.list_pull_requests()[0]["status"] == "merged"


def test_pull_request_must_be_approved_before_merge(tmp_path: Path) -> None:
    adapter = PullRequestAdapter(tmp_path)
    ticket = {"ticket_id": "TICKET-001", "title": "Handle division by zero"}
    pull_request_id = adapter.open(ticket, "diff --git", "ci-001")["pull_request"][
        "pull_request_id"
    ]

    with pytest.raises(StorageError, match="reviewed"):
        adapter.merge(pull_request_id)

    adapter.review(pull_request_id, "rejected", "Missing a regression test")
    with pytest.raises(StorageError, match="approved"):
        adapter.merge(pull_request_id)


def test_state_contract_replaces_json_atomically(tmp_path: Path) -> None:
    adapter = StateAdapter(tmp_path / "state.json")
    state = {"version": 1, "current": {"ticket_id": "TICKET-001"}}

    assert adapter.load() == {"version": 1, "current": None}
    assert adapter.save(state) == {"saved": True, "state": state}
    assert adapter.load() == state
    assert list(tmp_path.glob(".state.json.*")) == []


@pytest.mark.parametrize(
    ("relative_path", "contents", "operation"),
    [
        (
            "monitoring/events.jsonl",
            "not json\n",
            lambda root: MonitoringAdapter(root).list_events(),
        ),
        (
            "tickets/index.json",
            json.dumps({"next_number": "one"}),
            lambda root: TicketAdapter(root).list_tickets(),
        ),
        (
            "ci/runs.jsonl",
            json.dumps({"run_id": "missing fields"}) + "\n",
            lambda root: CIAdapter(root).list_runs(),
        ),
        (
            "pull-requests/index.json",
            "[]",
            lambda root: PullRequestAdapter(root).list_pull_requests(),
        ),
        (
            "state.json",
            json.dumps({"version": "one"}),
            lambda root: StateAdapter(root / "state.json").load(),
        ),
    ],
)
def test_adapters_reject_malformed_storage(
    tmp_path: Path,
    relative_path: str,
    contents: str,
    operation: Callable[[Path], object],
) -> None:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(StorageError):
        operation(tmp_path)
