import pytest

from loop_engineering_example.api import handle_calculation


def test_handle_calculation_returns_result() -> None:
    assert handle_calculation({"operation": "multiply", "left": 6, "right": 7}) == {
        "result": 42
    }


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"left": 1, "right": 2}, "operation must be a string"),
        ({"operation": "add", "left": "1", "right": 2}, "left must be a number"),
        ({"operation": "add", "left": 1, "right": None}, "right must be a number"),
    ],
)
def test_handle_calculation_validates_request(
    payload: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        handle_calculation(payload)
