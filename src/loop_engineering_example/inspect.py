"""Print a structured snapshot of the readable mock systems."""

import json
from pathlib import Path

from loop_engineering_example.adapters import (
    CIAdapter,
    MonitoringAdapter,
    PullRequestAdapter,
    StateAdapter,
    TicketAdapter,
)


def main() -> int:
    root = Path("mock-systems")
    snapshot = {
        "monitoring": MonitoringAdapter(root).list_events(),
        "tickets": TicketAdapter(root).list_tickets(),
        "ci_runs": CIAdapter(root).list_runs(),
        "pull_requests": PullRequestAdapter(root).list_pull_requests(),
        "state": StateAdapter(root / "state.json").load(),
    }
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
