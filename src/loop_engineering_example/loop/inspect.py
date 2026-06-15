"""Print a structured snapshot of the readable mock systems."""

import argparse
import json
from pathlib import Path

from loop_engineering_example.loop.adapters import (
    CIAdapter,
    MonitoringAdapter,
    PullRequestAdapter,
    StateAdapter,
    TicketAdapter,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("mock-systems"))
    return parser


def main() -> int:
    root = build_parser().parse_args().root
    monitoring = MonitoringAdapter(root)
    snapshot = {
        "monitoring": monitoring.list_events(),
        "acknowledgments": monitoring.list_acknowledgments(),
        "tickets": TicketAdapter(root).list_tickets(),
        "ci_runs": CIAdapter(root).list_runs(),
        "pull_requests": PullRequestAdapter(root).list_pull_requests(),
        "state": StateAdapter(root / "state.json").load(),
    }
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
