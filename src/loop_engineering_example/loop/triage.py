"""Read-only explorer runtime and deterministic triage validation."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Protocol

from loop_engineering_example.loop.storage import (
    Record,
    StorageError,
    atomic_write_json,
    atomic_write_text,
    require_fields,
)

TRIAGE_FIELDS: dict[str, type | tuple[type, ...]] = {
    "decision": str,
    "summary": str,
    "relevant_files": list,
    "constraints": list,
    "risks": list,
    "ambiguities": list,
    "success_predicate": (str, type(None)),
    "recommended_tests": list,
    "confidence": (int, float),
}


class ExplorerError(RuntimeError):
    """Raised when the explorer cannot produce a usable result."""


class ExplorerRuntime(Protocol):
    def explore(self, prompt: str, output_directory: Path) -> Record: ...


def parse_token_usage(stderr: str) -> int | None:
    matches = re.findall(r"tokens used\s+([\d,]+)", stderr)
    if not matches:
        return None
    return int(matches[-1].replace(",", ""))


def validate_triage_result(result: Record) -> Record:
    require_fields(result, TRIAGE_FIELDS)
    if result["decision"] not in {"ready", "escalate"}:
        raise StorageError(f"invalid triage decision: {result['decision']}")
    for field in (
        "relevant_files",
        "constraints",
        "risks",
        "ambiguities",
        "recommended_tests",
    ):
        if not all(isinstance(item, str) and item.strip() for item in result[field]):
            raise StorageError(f"{field} must contain non-empty strings")
    if not result["summary"].strip():
        raise StorageError("summary must not be empty")
    if not result["relevant_files"]:
        raise StorageError("relevant_files must not be empty")
    if not 0 <= result["confidence"] <= 1:
        raise StorageError("confidence must be between 0 and 1")
    if result["decision"] == "ready":
        predicate = result["success_predicate"]
        if not isinstance(predicate, str) or not predicate.strip():
            raise StorageError("ready triage requires a success predicate")
        if result["ambiguities"]:
            raise StorageError("ready triage must not contain ambiguities")
    else:
        if not result["ambiguities"]:
            raise StorageError("escalated triage requires ambiguities")
        if result["success_predicate"] is not None:
            raise StorageError("escalated triage must not invent a success predicate")
    return result


def repository_fingerprint(repository: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


class CodexExplorer:
    def __init__(
        self,
        repository: Path,
        schema_path: Path,
        executable: str = "codex",
        timeout_seconds: int = 180,
    ) -> None:
        self.repository = repository
        self.schema_path = schema_path
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def command(self, output_path: Path) -> list[str]:
        return [
            self.executable,
            "exec",
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--ignore-user-config",
            "--color",
            "never",
            "--output-schema",
            str(self.schema_path),
            "--output-last-message",
            str(output_path),
            "-C",
            str(self.repository),
            "-",
        ]

    def explore(self, prompt: str, output_directory: Path) -> Record:
        output_directory.mkdir(parents=True, exist_ok=True)
        prompt_path = output_directory / "prompt.txt"
        result_path = output_directory / "result.json"
        stderr_path = output_directory / "stderr.txt"
        atomic_write_text(prompt_path, prompt)
        before = repository_fingerprint(self.repository)
        started = time.monotonic()
        process = subprocess.run(
            self.command(result_path),
            input=prompt,
            cwd=self.repository,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        duration = time.monotonic() - started
        atomic_write_text(stderr_path, process.stderr)
        after = repository_fingerprint(self.repository)
        if after != before:
            raise ExplorerError("explorer changed the repository")
        if process.returncode != 0:
            raise ExplorerError(
                f"explorer exited with status {process.returncode}; see {stderr_path}"
            )
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ExplorerError("explorer did not return valid JSON") from error
        if not isinstance(result, dict):
            raise ExplorerError("explorer result must be a JSON object")
        runtime: Record = {
            "name": "codex",
            "duration_seconds": round(duration, 3),
        }
        token_usage = parse_token_usage(process.stderr)
        if token_usage is not None:
            runtime["tokens_used"] = token_usage
        result["_runtime"] = runtime
        return result


def build_triage_prompt(
    instructions: str,
    event: Record,
    ticket: Record,
    ticket_text: str,
) -> str:
    return (
        f"{instructions.strip()}\n\n"
        "## Monitoring event\n\n"
        f"```json\n{json.dumps(event, indent=2, sort_keys=True)}\n```\n\n"
        "## Ticket record\n\n"
        f"```json\n{json.dumps(ticket, indent=2, sort_keys=True)}\n```\n\n"
        "## Ticket body\n\n"
        f"{ticket_text}\n"
    )


def save_validated_result(output_directory: Path, result: Record) -> Record:
    runtime = result.pop("_runtime", None)
    validated = validate_triage_result(result)
    artifact = dict(validated)
    if runtime is not None:
        artifact["runtime"] = runtime
    atomic_write_json(output_directory / "validated-result.json", artifact)
    return validated
