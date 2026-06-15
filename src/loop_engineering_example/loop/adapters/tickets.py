"""File-backed ticket operations."""

import json
from pathlib import Path

from loop_engineering_example.loop.adapters.monitoring import EVENT_FIELDS
from loop_engineering_example.loop.storage import (
    Record,
    StorageError,
    atomic_write_json,
    atomic_write_text,
    read_json,
    require_fields,
)

INDEX_DEFAULT: Record = {
    "next_number": 1,
    "by_deduplication_key": {},
    "tickets": {},
}


class TicketAdapter:
    def __init__(self, root: Path) -> None:
        self.directory = root / "tickets"
        self.index_path = self.directory / "index.json"

    def _index(self) -> Record:
        index = read_json(self.index_path, INDEX_DEFAULT)
        require_fields(
            index,
            {"next_number": int, "by_deduplication_key": dict, "tickets": dict},
        )
        return index

    def create_or_get(self, event: Record) -> Record:
        require_fields(event, EVENT_FIELDS)
        index = self._index()
        deduplication_key = event["deduplication_key"]
        existing_id = index["by_deduplication_key"].get(deduplication_key)
        if existing_id is not None:
            return {"created": False, "ticket": dict(index["tickets"][existing_id])}

        ticket_id = f"TICKET-{index['next_number']:03d}"
        filename = f"{ticket_id}.md"
        ticket = {
            "ticket_id": ticket_id,
            "status": "open",
            "title": f"{event['error_type']}: {event['message']}",
            "event_id": event["event_id"],
            "deduplication_key": deduplication_key,
            "file": filename,
        }
        formatted_request = json.dumps(event["request"], indent=2, sort_keys=True)
        body = (
            f"# {ticket_id}: {ticket['title']}\n\n"
            f"- Status: {ticket['status']}\n"
            f"- Event: {ticket['event_id']}\n"
            f"- Deduplication key: `{deduplication_key}`\n"
            f"- Reproduce: `{event['reproduce']}`\n\n"
            "## Request\n\n"
            f"```json\n{formatted_request}\n```\n\n"
            "## Comments\n"
        )
        atomic_write_text(self.directory / filename, body)
        index["next_number"] += 1
        index["by_deduplication_key"][deduplication_key] = ticket_id
        index["tickets"][ticket_id] = ticket
        atomic_write_json(self.index_path, index)
        return {"created": True, "ticket": dict(ticket)}

    def list_tickets(self) -> list[Record]:
        return [dict(ticket) for ticket in self._index()["tickets"].values()]

    def transition(self, ticket_id: str, status: str) -> Record:
        if not status:
            raise StorageError("ticket status must not be empty")
        index = self._index()
        try:
            ticket = index["tickets"][ticket_id]
        except KeyError as error:
            raise StorageError(f"unknown ticket: {ticket_id}") from error
        previous_status = ticket["status"]
        changed = previous_status != status
        ticket["status"] = status
        path = self.directory / ticket["file"]
        ticket_text = path.read_text(encoding="utf-8")
        updated_text = ticket_text.replace(
            f"- Status: {previous_status}\n",
            f"- Status: {status}\n",
            1,
        )
        atomic_write_text(path, updated_text)
        atomic_write_json(self.index_path, index)
        return {"changed": changed, "ticket": dict(ticket)}

    def comment(self, ticket_id: str, message: str) -> Record:
        if not message.strip():
            raise StorageError("ticket comment must not be empty")
        index = self._index()
        try:
            ticket = index["tickets"][ticket_id]
        except KeyError as error:
            raise StorageError(f"unknown ticket: {ticket_id}") from error
        path = self.directory / ticket["file"]
        existing_text = path.read_text(encoding="utf-8")
        marker = f"\n- {message.strip()}\n"
        if marker in existing_text:
            return {
                "created": False,
                "ticket_id": ticket_id,
                "message": message.strip(),
            }
        atomic_write_text(path, existing_text + marker)
        return {"created": True, "ticket_id": ticket_id, "message": message.strip()}
