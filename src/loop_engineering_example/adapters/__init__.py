"""File-backed external-system adapters."""

from loop_engineering_example.adapters.ci import CIAdapter
from loop_engineering_example.adapters.monitoring import MonitoringAdapter
from loop_engineering_example.adapters.pull_requests import PullRequestAdapter
from loop_engineering_example.adapters.state import StateAdapter
from loop_engineering_example.adapters.tickets import TicketAdapter

__all__ = [
    "CIAdapter",
    "MonitoringAdapter",
    "PullRequestAdapter",
    "StateAdapter",
    "TicketAdapter",
]
