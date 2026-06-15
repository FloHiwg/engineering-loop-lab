"""File-backed monitoring operations."""

from pathlib import Path

from loop_engineering_example.loop.storage import (
    Record,
    StorageError,
    append_jsonl,
    find_record,
    read_jsonl,
    require_fields,
)

EVENT_FIELDS: dict[str, type | tuple[type, ...]] = {
    "event_id": str,
    "deduplication_key": str,
    "status": str,
    "service": str,
    "error_type": str,
    "message": str,
    "request": dict,
    "source": dict,
    "reproduce": str,
}


class MonitoringAdapter:
    def __init__(self, root: Path) -> None:
        self.path = root / "monitoring" / "events.jsonl"

    def emit(self, event: Record) -> Record:
        require_fields(event, EVENT_FIELDS)
        existing = find_record(self.list_events(), "event_id", event["event_id"])
        if existing is not None:
            if existing != event:
                raise StorageError(f"event ID already exists: {event['event_id']}")
            return {"created": False, "event": dict(existing)}
        append_jsonl(self.path, event)
        return {"created": True, "event": dict(event)}

    def list_events(self) -> list[Record]:
        events = []
        for record in read_jsonl(self.path):
            if record.get("record_type") == "acknowledgment":
                continue
            require_fields(record, EVENT_FIELDS)
            events.append(record)
        return events

    def list_acknowledgments(self) -> list[Record]:
        return [
            record
            for record in read_jsonl(self.path)
            if record.get("record_type") == "acknowledgment"
        ]

    def acknowledge(self, event_id: str) -> Record:
        if find_record(self.list_events(), "event_id", event_id) is None:
            raise StorageError(f"unknown event: {event_id}")
        acknowledgments = self.list_acknowledgments()
        existing = find_record(acknowledgments, "event_id", event_id)
        if existing is not None:
            return {"created": False, "acknowledgment": dict(existing)}
        acknowledgment = {
            "record_type": "acknowledgment",
            "acknowledgment_id": f"ack-{event_id}",
            "event_id": event_id,
        }
        append_jsonl(self.path, acknowledgment)
        return {"created": True, "acknowledgment": acknowledgment}

    def correlate(self, deduplication_key: str) -> Record:
        event_ids = [
            event["event_id"]
            for event in self.list_events()
            if event["deduplication_key"] == deduplication_key
        ]
        return {
            "deduplication_key": deduplication_key,
            "event_ids": event_ids,
            "count": len(event_ids),
        }
