"""Deterministic states and transitions for the engineering loop."""

from copy import deepcopy
from enum import StrEnum
from typing import Any

from loop_engineering_example.loop.storage import Record, StorageError, require_fields


class LoopState(StrEnum):
    DISCOVERED = "DISCOVERED"
    TRIAGED = "TRIAGED"
    READY = "READY"
    IMPLEMENTING = "IMPLEMENTING"
    VERIFYING = "VERIFYING"
    PR_OPEN = "PR_OPEN"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    ESCALATED = "ESCALATED"


TRANSITIONS: dict[LoopState, frozenset[LoopState]] = {
    LoopState.DISCOVERED: frozenset(
        {LoopState.TRIAGED, LoopState.BLOCKED, LoopState.ESCALATED}
    ),
    LoopState.TRIAGED: frozenset(
        {LoopState.READY, LoopState.BLOCKED, LoopState.ESCALATED}
    ),
    LoopState.READY: frozenset(
        {LoopState.IMPLEMENTING, LoopState.BLOCKED, LoopState.ESCALATED}
    ),
    LoopState.IMPLEMENTING: frozenset(
        {
            LoopState.VERIFYING,
            LoopState.FAILED_RETRYABLE,
            LoopState.ESCALATED,
        }
    ),
    LoopState.FAILED_RETRYABLE: frozenset(
        {LoopState.IMPLEMENTING, LoopState.ESCALATED}
    ),
    LoopState.VERIFYING: frozenset(
        {LoopState.PR_OPEN, LoopState.FAILED_RETRYABLE, LoopState.ESCALATED}
    ),
    LoopState.PR_OPEN: frozenset({LoopState.DONE, LoopState.ESCALATED}),
    LoopState.DONE: frozenset(),
    LoopState.BLOCKED: frozenset(),
    LoopState.ESCALATED: frozenset(),
}

TERMINAL_STATES = frozenset({LoopState.DONE, LoopState.BLOCKED, LoopState.ESCALATED})

STATE_FIELDS: dict[str, type | tuple[type, ...]] = {
    "version": int,
    "current": str,
    "event_id": str,
    "ticket_id": (str, type(None)),
    "worktree": (str, type(None)),
    "branch": (str, type(None)),
    "agent": (str, type(None)),
    "attempt_count": int,
    "evidence": list,
    "token_cost_estimate": (int, float),
    "last_error": (str, type(None)),
    "next_action": (str, type(None)),
}


class TransitionError(ValueError):
    """Raised when a state transition is not permitted."""


def validate_loop_state(state: Record) -> LoopState:
    require_fields(state, STATE_FIELDS)
    try:
        current = LoopState(state["current"])
    except ValueError as error:
        raise StorageError(f"unknown loop state: {state['current']}") from error
    if state["attempt_count"] < 0:
        raise StorageError("attempt_count must not be negative")
    if state["token_cost_estimate"] < 0:
        raise StorageError("token_cost_estimate must not be negative")
    return current


def transition(
    state: Record,
    target: LoopState,
    **updates: Any,
) -> Record:
    current = validate_loop_state(state)
    if target not in TRANSITIONS[current]:
        raise TransitionError(f"illegal transition: {current} -> {target}")
    updated = deepcopy(state)
    updated.update(updates)
    updated["current"] = target.value
    validate_loop_state(updated)
    return updated
