from itertools import product

import pytest

from loop_engineering_example.loop.state_machine import (
    TRANSITIONS,
    LoopState,
    TransitionError,
    transition,
    validate_loop_state,
)
from loop_engineering_example.loop.storage import StorageError


def state(current: LoopState) -> dict[str, object]:
    return {
        "version": 1,
        "current": current.value,
        "event_id": "evt-001",
        "ticket_id": "TICKET-001",
        "worktree": None,
        "branch": None,
        "agent": None,
        "attempt_count": 0,
        "evidence": [],
        "token_cost_estimate": 0.0,
        "last_error": None,
        "next_action": "test",
    }


@pytest.mark.parametrize(
    ("source", "target"),
    [(source, target) for source, targets in TRANSITIONS.items() for target in targets],
)
def test_all_legal_transitions(source: LoopState, target: LoopState) -> None:
    updated = transition(state(source), target, next_action=None)

    assert updated["current"] == target.value
    assert validate_loop_state(updated) is target


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (source, target)
        for source, target in product(LoopState, repeat=2)
        if target not in TRANSITIONS[source]
    ],
)
def test_all_illegal_transitions(source: LoopState, target: LoopState) -> None:
    with pytest.raises(
        TransitionError,
        match=f"illegal transition: {source} -> {target}",
    ):
        transition(state(source), target)


def test_state_validation_rejects_unknown_state() -> None:
    invalid = state(LoopState.DISCOVERED)
    invalid["current"] = "UNKNOWN"

    with pytest.raises(StorageError, match="unknown loop state"):
        validate_loop_state(invalid)


def test_state_validation_rejects_negative_attempt_count() -> None:
    invalid = state(LoopState.DISCOVERED)
    invalid["attempt_count"] = -1

    with pytest.raises(StorageError, match="attempt_count"):
        validate_loop_state(invalid)
