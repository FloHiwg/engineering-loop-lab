"""File-backed external-system adapters."""

from loop_engineering_example.loop.adapters.ci import CIAdapter
from loop_engineering_example.loop.adapters.monitoring import MonitoringAdapter
from loop_engineering_example.loop.adapters.pull_requests import PullRequestAdapter
from loop_engineering_example.loop.adapters.state import StateAdapter
from loop_engineering_example.loop.adapters.tickets import TicketAdapter

__all__ = [
    "CIAdapter",
    "MonitoringAdapter",
    "PullRequestAdapter",
    "StateAdapter",
    "TicketAdapter",
]
