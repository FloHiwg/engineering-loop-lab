"""File-backed durable-state operations."""

from pathlib import Path

from loop_engineering_example.storage import (
    Record,
    atomic_write_json,
    read_json,
    require_fields,
)


class StateAdapter:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Record:
        state = read_json(self.path, {"version": 1, "current": None})
        require_fields(state, {"version": int})
        return state

    def save(self, state: Record) -> Record:
        require_fields(state, {"version": int})
        atomic_write_json(self.path, state)
        return {"saved": True, "state": dict(state)}
