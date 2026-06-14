"""Reject common secrets and machine-specific paths in public project files."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOW_MARKER = "publication-check: allow"
IGNORED_PARTS = {".git", ".venv", "__pycache__", "runs", "worktrees"}
TEXT_SUFFIXES = {
    "",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SUSPICIOUS_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "macOS user path": re.compile(r"/Users/[^/\s]+/"),  # publication-check: allow
    "Linux home path": re.compile(r"/home/[^/\s]+/"),  # publication-check: allow
}


def candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        ROOT / name
        for name in result.stdout.splitlines()
        if name
        and not IGNORED_PARTS.intersection(Path(name).parts)
        and Path(name).suffix in TEXT_SUFFIXES
    ]


def scan_text(path: Path, text: str) -> list[str]:
    findings = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for label, pattern in SUSPICIOUS_PATTERNS.items():
            if pattern.search(line):
                findings.append(
                    f"{path.relative_to(ROOT)}:{line_number}: possible {label}"
                )
    return findings


def main() -> int:
    findings = []
    for path in candidate_files():
        try:
            findings.extend(scan_text(path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue

    if findings:
        print("Publication check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Publication check passed.")
    return 0
