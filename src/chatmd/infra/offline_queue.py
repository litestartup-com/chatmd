"""Offline queue — persist network-dependent tasks and replay on reconnect."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class QueuedItem:
    """A command queued while offline."""

    id: str
    skill_name: str
    input_text: str
    args: dict
    source_file: str
    source_line: int
    raw_text: str
    queued_at: str = ""

    def __post_init__(self) -> None:
        if not self.queued_at:
            self.queued_at = datetime.now().isoformat(timespec="seconds")


class OfflineQueue:
    """Persists commands that need network, replays them when online."""

    def __init__(self, workspace: Path) -> None:
        self._queue_file = workspace / ".chatmd" / "queue.json"
        self._items: list[QueuedItem] = []
        self.load()

    def enqueue(self, item: QueuedItem) -> None:
        """Add an item to the offline queue."""
        self._items.append(item)
        self.save()
        logger.info("Queued offline: %s (%s)", item.id, item.skill_name)

    def dequeue(self) -> QueuedItem | None:
        """Remove and return the oldest item, or None if empty."""
        if not self._items:
            return None
        item = self._items.pop(0)
        self.save()
        return item

    def peek(self) -> list[QueuedItem]:
        """Return all queued items without removing them."""
        return list(self._items)

    def remove(self, item_id: str) -> bool:
        """Remove a specific item by ID."""
        for i, item in enumerate(self._items):
            if item.id == item_id:
                self._items.pop(i)
                self.save()
                return True
        return False

    @property
    def size(self) -> int:
        return len(self._items)

    @property
    def is_empty(self) -> bool:
        return len(self._items) == 0

    def save(self) -> None:
        """Persist queue to disk."""
        try:
            self._queue_file.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(item) for item in self._items]
            with open(self._queue_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error("Failed to save queue: %s", exc)

    def load(self) -> None:
        """Load queue from disk."""
        if not self._queue_file.exists():
            return
        try:
            with open(self._queue_file, encoding="utf-8") as f:
                data = json.load(f)
            self._items = [
                QueuedItem(**item) for item in data if isinstance(item, dict)
            ]
            logger.debug("Queue loaded: %d items", len(self._items))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load queue: %s", exc)
