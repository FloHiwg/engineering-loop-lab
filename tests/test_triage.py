import pytest

from loop_engineering_example.loop.storage import StorageError
from loop_engineering_example.loop.triage import (
    parse_token_usage,
    validate_triage_result,
)


def ready_result() -> dict[str, object]:
    return {
        "decision": "ready",
        "summary": "The issue is actionable.",
        "relevant_files": ["src/example.py"],
        "constraints": ["Preserve existing behavior."],
        "risks": [],
        "ambiguities": [],
        "success_predicate": "The focused regression test passes.",
        "recommended_tests": ["make check"],
        "confidence": 0.9,
    }


def test_ready_result_is_valid() -> None:
    assert validate_triage_result(ready_result())["decision"] == "ready"


def test_escalation_requires_ambiguity() -> None:
    result = ready_result()
    result.update(
        {
            "decision": "escalate",
            "success_predicate": None,
            "ambiguities": [],
        }
    )

    with pytest.raises(StorageError, match="requires ambiguities"):
        validate_triage_result(result)


def test_ready_result_requires_success_predicate() -> None:
    result = ready_result()
    result["success_predicate"] = None

    with pytest.raises(StorageError, match="success predicate"):
        validate_triage_result(result)


def test_token_usage_uses_last_reported_total() -> None:
    assert parse_token_usage("tokens used\n1,200\ntokens used\n2,345") == 2345
