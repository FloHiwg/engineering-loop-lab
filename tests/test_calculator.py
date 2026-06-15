import pytest

from loop_engineering_example.app.calculator import calculate


@pytest.mark.parametrize(
    ("operation", "left", "right", "expected"),
    [
        ("add", 7, 3, 10),
        ("subtract", 7, 3, 4),
        ("multiply", 7, 3, 21),
        ("divide", 7, 2, 3.5),
        ("power", 2, 8, 256),
    ],
)
def test_calculate_supported_operations(
    operation: str,
    left: int,
    right: int,
    expected: int | float,
) -> None:
    assert calculate(operation, left, right) == expected


def test_calculate_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="unsupported operation: modulo"):
        calculate("modulo", 2, 3)
