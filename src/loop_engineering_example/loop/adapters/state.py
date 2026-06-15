"""File-backed durable-state operations."""

from collections.abc import Callable
from pathlib import Path

from loop_engineering_example.loop.storage import (
    Record,
    atomic_write_json,
    read_json,
    require_fields,
)


class StateAdapter:
    def __init__(
        self,
        path: Path,
        validator: Callable[[Record], object] | None = None,
    ) -> None:
        self.path = path
        self.validator = validator

    def load(self) -> Record:
        state = read_json(self.path, {"version": 1, "current": None})
        require_fields(state, {"version": int})
        if self.validator is not None and state.get("current") is not None:
            self.validator(state)
        return state

    def save(self, state: Record) -> Record:
        require_fields(state, {"version": int})
        if self.validator is not None and state.get("current") is not None:
            self.validator(state)
        atomic_write_json(self.path, state)
        return {"saved": True, "state": dict(state)}
