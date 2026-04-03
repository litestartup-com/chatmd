"""Confirmation window — delay-based confirmation for commands in Markdown files.

The confirmation flow:
1. Agent detects a command and writes a confirmation prompt line.
2. A timer starts (default 1.5s).
3. If the user **deletes** the confirmation line before the timer fires → cancel.
4. If the timer fires and the line still exists → execute.
5. Commands in the ``skip`` list bypass confirmation entirely.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chatmd.i18n import t

logger = logging.getLogger(__name__)


@dataclass
class PendingConfirmation:
    """A command awaiting user confirmation."""

    confirm_id: str
    command_text: str
    source_file: Path
    source_line: int
    callback: Any  # Callable to execute if confirmed
    timer: threading.Timer | None = None


class ConfirmationWindow:
    """Manages delay-based confirmation for potentially dangerous commands.

    When a command requires confirmation:
    1. A confirmation marker is written to the file.
    2. After ``delay`` seconds, if the marker still exists → execute.
    3. If the user removes the marker line → cancel.
    """

    def __init__(
        self,
        delay: float = 1.5,
        skip_commands: list[str] | None = None,
    ) -> None:
        self._delay = delay
        self._skip_commands: set[str] = set(skip_commands or [])
        self._pending: dict[str, PendingConfirmation] = {}
        self._lock = threading.Lock()
        self._counter = 0

    @property
    def delay(self) -> float:
        return self._delay

    @delay.setter
    def delay(self, value: float) -> None:
        self._delay = max(0.0, value)

    def needs_confirmation(self, command_name: str) -> bool:
        """Check if a command requires confirmation (i.e. not in skip list)."""
        return command_name not in self._skip_commands

    def request_confirmation(
        self,
        command_text: str,
        source_file: Path,
        source_line: int,
        callback: Any,
    ) -> PendingConfirmation:
        """Create a pending confirmation with a delay timer.

        Returns the ``PendingConfirmation`` so the caller can write
        a confirmation marker to the file.
        """
        with self._lock:
            self._counter += 1
            confirm_id = f"confirm-{self._counter}"

        pending = PendingConfirmation(
            confirm_id=confirm_id,
            command_text=command_text,
            source_file=source_file,
            source_line=source_line,
            callback=callback,
        )

        timer = threading.Timer(self._delay, self._on_timer, args=[confirm_id])
        pending.timer = timer

        with self._lock:
            self._pending[confirm_id] = pending

        timer.start()
        logger.debug(
            "Confirmation requested: %s (%.1fs delay)", confirm_id, self._delay,
        )
        return pending

    def cancel(self, confirm_id: str) -> bool:
        """Cancel a pending confirmation (user deleted the marker line).

        Returns ``True`` if the confirmation was found and cancelled.
        """
        with self._lock:
            pending = self._pending.pop(confirm_id, None)

        if pending is None:
            return False

        if pending.timer:
            pending.timer.cancel()

        logger.info("Confirmation cancelled: %s", confirm_id)
        return True

    def cancel_all(self) -> int:
        """Cancel all pending confirmations. Returns count cancelled."""
        with self._lock:
            items = list(self._pending.values())
            self._pending.clear()

        for p in items:
            if p.timer:
                p.timer.cancel()

        return len(items)

    def get_pending(self, confirm_id: str) -> PendingConfirmation | None:
        """Look up a pending confirmation by ID."""
        with self._lock:
            return self._pending.get(confirm_id)

    def list_pending(self) -> list[PendingConfirmation]:
        """Return all pending confirmations."""
        with self._lock:
            return list(self._pending.values())

    def _on_timer(self, confirm_id: str) -> None:
        """Timer callback — execute the command if still pending."""
        with self._lock:
            pending = self._pending.pop(confirm_id, None)

        if pending is None:
            return  # Already cancelled

        logger.info("Confirmation confirmed (timer expired): %s", confirm_id)
        try:
            pending.callback()
        except Exception:
            logger.exception("Error executing confirmed command: %s", confirm_id)

    def confirmation_marker(self, confirm_id: str, command_text: str) -> str:
        """Generate the Markdown confirmation marker line."""
        return t(
            "confirm.prompt",
            command=command_text,
            delay=self._delay,
            confirm_id=confirm_id,
        )
