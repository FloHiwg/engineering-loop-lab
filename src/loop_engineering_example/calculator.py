"""Core calculator operations."""

from collections.abc import Callable

type Number = int | float
type Operation = Callable[[Number, Number], Number]


def add(left: Number, right: Number) -> Number:
    return left + right


def subtract(left: Number, right: Number) -> Number:
    return left - right


def multiply(left: Number, right: Number) -> Number:
    return left * right


def divide(left: Number, right: Number) -> Number:
    # Intentional defect for step-01: zero is not handled at the API boundary.
    return left / right


OPERATIONS: dict[str, Operation] = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
}


def calculate(operation: str, left: Number, right: Number) -> Number:
    try:
        function = OPERATIONS[operation]
    except KeyError as error:
        raise ValueError(f"unsupported operation: {operation}") from error
    return function(left, right)
