"""File-backed pull-request operations."""

from pathlib import Path

from loop_engineering_example.storage import (
    Record,
    StorageError,
    atomic_write_json,
    read_json,
    require_fields,
)

INDEX_DEFAULT: Record = {
    "next_number": 1,
    "by_ticket_id": {},
    "pull_requests": {},
}


class PullRequestAdapter:
    def __init__(self, root: Path) -> None:
        self.directory = root / "pull-requests"
        self.index_path = self.directory / "index.json"

    def _index(self) -> Record:
        index = read_json(self.index_path, INDEX_DEFAULT)
        require_fields(
            index,
            {"next_number": int, "by_ticket_id": dict, "pull_requests": dict},
        )
        return index

    def open(self, ticket: Record, diff: str, ci_run_id: str) -> Record:
        require_fields(ticket, {"ticket_id": str, "title": str})
        index = self._index()
        ticket_id = ticket["ticket_id"]
        existing_id = index["by_ticket_id"].get(ticket_id)
        if existing_id is not None:
            return {
                "created": False,
                "pull_request": dict(index["pull_requests"][existing_id]),
            }

        pull_request_id = f"PR-{index['next_number']:03d}"
        pull_request = {
            "pull_request_id": pull_request_id,
            "ticket_id": ticket_id,
            "title": ticket["title"],
            "status": "open",
            "ci_run_id": ci_run_id,
            "diff": diff,
            "review": None,
        }
        atomic_write_json(self.directory / f"{pull_request_id}.json", pull_request)
        index["next_number"] += 1
        index["by_ticket_id"][ticket_id] = pull_request_id
        index["pull_requests"][pull_request_id] = pull_request
        atomic_write_json(self.index_path, index)
        return {"created": True, "pull_request": dict(pull_request)}

    def list_pull_requests(self) -> list[Record]:
        return [
            dict(pull_request)
            for pull_request in self._index()["pull_requests"].values()
        ]

    def review(self, pull_request_id: str, verdict: str, evidence: str) -> Record:
        if verdict not in {"approved", "rejected", "escalated"}:
            raise StorageError(f"invalid review verdict: {verdict}")
        index = self._index()
        try:
            pull_request = index["pull_requests"][pull_request_id]
        except KeyError as error:
            raise StorageError(f"unknown pull request: {pull_request_id}") from error
        review = {"verdict": verdict, "evidence": evidence}
        changed = pull_request["review"] != review
        pull_request["review"] = review
        atomic_write_json(self.directory / f"{pull_request_id}.json", pull_request)
        atomic_write_json(self.index_path, index)
        return {"changed": changed, "pull_request": dict(pull_request)}
