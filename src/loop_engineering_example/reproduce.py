"""Reproduce and verify the intentional division-by-zero defect."""

from loop_engineering_example.api import handle_calculation


def main() -> int:
    request = {"operation": "divide", "left": 10, "right": 0}
    print(f"Request: {request}")

    try:
        handle_calculation(request)
    except ZeroDivisionError as error:
        print(f"Observed intentional defect: {type(error).__name__}: {error}")
        print("Matching event: mock-systems/monitoring/events.jsonl")
        return 0

    print("Defect not reproduced: division by zero did not escape the API.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
