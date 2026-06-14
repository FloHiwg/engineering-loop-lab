"""File-backed continuous-integration operations."""

from pathlib import Path

from loop_engineering_example.storage import (
    Record,
    StorageError,
    append_jsonl,
    find_record,
    read_jsonl,
    require_fields,
)

RUN_FIELDS: dict[str, type | tuple[type, ...]] = {
    "run_id": str,
    "ticket_id": str,
    "status": str,
    "command": str,
    "output": str,
}


class CIAdapter:
    def __init__(self, root: Path) -> None:
        self.path = root / "ci" / "runs.jsonl"

    def _runs(self) -> list[Record]:
        runs = read_jsonl(self.path)
        for run in runs:
            require_fields(run, RUN_FIELDS)
        return runs

    def list_runs(self) -> list[Record]:
        return [dict(run) for run in self._runs()]

    def record(self, run: Record) -> Record:
        require_fields(run, RUN_FIELDS)
        existing = find_record(self._runs(), "run_id", run["run_id"])
        if existing is not None:
            if existing != run:
                raise StorageError(f"CI run ID already exists: {run['run_id']}")
            return {"created": False, "run": dict(existing)}
        append_jsonl(self.path, run)
        return {"created": True, "run": dict(run)}

    def get(self, run_id: str) -> Record:
        run = find_record(self._runs(), "run_id", run_id)
        if run is None:
            raise StorageError(f"unknown CI run: {run_id}")
        return dict(run)
