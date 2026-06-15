import pytest

from loop_engineering_example.app.calculator import calculate


@pytest.mark.parametrize(
    ("operation", "left", "right", "expected"),
    [
        ("add", 7, 3, 10),
        ("subtract", 7, 3, 4),
        ("multiply", 7, 3, 21),
        ("divide", 7, 2, 3.5),
        ("modulo", 10, 3, 1),
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
    with pytest.raises(ValueError, match="unsupported operation: power"):
        calculate("power", 2, 3)
