"""Small application boundary for calculator requests."""

from typing import Any

from loop_engineering_example.app.calculator import Number, calculate


def handle_calculation(request: dict[str, Any]) -> dict[str, Number | str]:
    operation = request.get("operation")
    left = request.get("left")
    right = request.get("right")

    if not isinstance(operation, str):
        raise ValueError("operation must be a string")
    if not isinstance(left, int | float) or isinstance(left, bool):
        raise ValueError("left must be a number")
    if not isinstance(right, int | float) or isinstance(right, bool):
        raise ValueError("right must be a number")

    if operation == "modulo" and right == 0:
        return {"error": "division by zero"}

    return {"result": calculate(operation, left, right)}
