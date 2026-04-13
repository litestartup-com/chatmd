"""Confirmation window — explicit user confirmation for commands in Markdown files.

The confirmation flow:
1. Agent detects a command that is in the ``commands`` list.
2. Instead of executing, Agent writes a confirmation prompt to the file.
3. The command stays pending until the user explicitly types ``/confirm``.
4. If the user **deletes** the confirmation line → cancel.
5. Commands NOT in the ``commands`` list execute immediately (no confirmation).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
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
    args: dict = field(default_factory=dict)


class ConfirmationWindow:
    """Manages explicit user confirmation for commands.

    When a command requires confirmation:
    1. A confirmation marker is written to the file.
    2. The user must type ``/confirm`` to execute the command.
    3. If the user removes the marker line → cancel.
    4. No timer — commands never auto-execute.
    """

    def __init__(
        self,
        enabled: bool = False,
        commands: list[str] | None = None,
    ) -> None:
        self._enabled = enabled
        self._commands: set[str] = set(commands or [])
        self._pending: dict[str, PendingConfirmation] = {}
        self._lock = threading.Lock()
        self._counter = 0

    @property
    def enabled(self) -> bool:
        """Whether confirmation is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def commands(self) -> set[str]:
        """Set of command names that require confirmation."""
        return self._commands

    def needs_confirmation(self, command_name: str) -> bool:
        """Check if a command requires confirmation.

        Returns ``True`` only if confirmation is enabled AND the command
        is in the ``commands`` list.
        """
        if not self._enabled:
            return False
        return command_name in self._commands

    def request_confirmation(
        self,
        command_text: str,
        source_file: Path,
        source_line: int,
        callback: Any,
        args: dict | None = None,
    ) -> PendingConfirmation:
        """Create a pending confirmation (no timer — waits for /confirm).

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
            args=args or {},
        )

        with self._lock:
            self._pending[confirm_id] = pending

        logger.debug("Confirmation requested: %s for %s", confirm_id, command_text)
        return pending

    def confirm(self, confirm_id: str | None = None) -> PendingConfirmation | None:
        """Execute a pending confirmation.

        If *confirm_id* is ``None``, confirm the most recent pending command.
        Returns the confirmed ``PendingConfirmation``, or ``None`` if not found.
        """
        with self._lock:
            if confirm_id:
                pending = self._pending.pop(confirm_id, None)
            elif self._pending:
                # Confirm the most recent (last added)
                confirm_id = list(self._pending.keys())[-1]
                pending = self._pending.pop(confirm_id)
            else:
                pending = None

        if pending is None:
            return None

        logger.info("Confirmation confirmed by user: %s", pending.confirm_id)
        try:
            pending.callback()
        except Exception:
            logger.exception(
                "Error executing confirmed command: %s", pending.confirm_id,
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

        logger.info("Confirmation cancelled: %s", confirm_id)
        return True

    def cancel_all(self) -> int:
        """Cancel all pending confirmations. Returns count cancelled."""
        with self._lock:
            items = list(self._pending.values())
            self._pending.clear()

        return len(items)

    def get_pending(self, confirm_id: str) -> PendingConfirmation | None:
        """Look up a pending confirmation by ID."""
        with self._lock:
            return self._pending.get(confirm_id)

    def list_pending(self) -> list[PendingConfirmation]:
        """Return all pending confirmations."""
        with self._lock:
            return list(self._pending.values())

    def confirmation_marker(self, confirm_id: str, command_text: str) -> str:
        """Generate the Markdown confirmation marker line."""
        return t(
            "confirm.prompt",
            command=command_text,
            confirm_id=confirm_id,
        )
