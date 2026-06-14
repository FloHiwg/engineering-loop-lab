"""Small validated storage helpers shared by the adapters."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

type Record = dict[str, Any]


class StorageError(ValueError):
    """Raised when persisted data does not satisfy its contract."""


def find_record(
    records: list[Record],
    field: str,
    value: str,
) -> Record | None:
    return next((record for record in records if record.get(field) == value), None)


def require_fields(record: Record, fields: dict[str, type | tuple[type, ...]]) -> None:
    for field, expected_type in fields.items():
        if field not in record:
            raise StorageError(f"missing required field: {field}")
        if not isinstance(record[field], expected_type):
            raise StorageError(f"{field} has invalid type")


def read_json(path: Path, default: Record | None = None) -> Record:
    if not path.exists():
        if default is None:
            raise StorageError(f"missing storage file: {path}")
        return deepcopy(default)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(f"invalid JSON in {path}") from error
    if not isinstance(value, dict):
        raise StorageError(f"expected JSON object in {path}")
    return value


def atomic_write_json(path: Path, value: Record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(value, file, indent=2, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(value)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_jsonl(path: Path) -> list[Record]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            value: Any = json.loads(line)
        except json.JSONDecodeError as error:
            raise StorageError(f"invalid JSON in {path}:{line_number}") from error
        if not isinstance(value, dict):
            raise StorageError(f"expected JSON object in {path}:{line_number}")
        records.append(value)
    return records


def append_jsonl(path: Path, record: Record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
