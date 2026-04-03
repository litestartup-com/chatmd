"""State manager — multi-session state with AI conversation context."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """Represents one chat session (one .md file) with AI conversation history."""

    file_path: Path
    messages: list[dict] = field(default_factory=list)
    created_at: str = ""
    last_active: str = ""

    def __post_init__(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        if not self.created_at:
            self.created_at = now
        if not self.last_active:
            self.last_active = now

    def add_user_message(self, text: str) -> None:
        """Append a user message to the conversation history."""
        self.messages.append({"role": "user", "content": text})
        self.last_active = datetime.now().isoformat(timespec="seconds")

    def add_assistant_message(self, text: str) -> None:
        """Append an assistant response to the conversation history."""
        self.messages.append({"role": "assistant", "content": text})
        self.last_active = datetime.now().isoformat(timespec="seconds")

    def get_context_messages(self, max_turns: int = 20) -> list[dict]:
        """Return recent conversation messages for AI context."""
        return self.messages[-max_turns * 2 :]

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "file_path": str(self.file_path),
            "messages": self.messages,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ChatSession:
        """Deserialize from a dict."""
        return cls(
            file_path=Path(data["file_path"]),
            messages=data.get("messages", []),
            created_at=data.get("created_at", ""),
            last_active=data.get("last_active", ""),
        )


class StateManager:
    """Manages multiple chat sessions and persists state to disk."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace
        self._state_file = workspace / ".chatmd" / "state.json"
        self._sessions: dict[str, ChatSession] = {}
        self._online = True
        self.load_state()

    def get_session(self, file_path: Path) -> ChatSession:
        """Get or create a session for the given file."""
        key = str(file_path.resolve())
        if key not in self._sessions:
            self._sessions[key] = ChatSession(file_path=file_path)
            logger.debug("Created new session for %s", file_path)
        return self._sessions[key]

    def list_sessions(self) -> list[ChatSession]:
        """Return all active sessions."""
        return list(self._sessions.values())

    def remove_session(self, file_path: Path) -> bool:
        """Remove a session."""
        key = str(file_path.resolve())
        if key in self._sessions:
            del self._sessions[key]
            return True
        return False

    @property
    def is_online(self) -> bool:
        return self._online

    @is_online.setter
    def is_online(self, value: bool) -> None:
        self._online = value

    def save_state(self) -> None:
        """Persist all sessions to state.json."""
        data = {
            "sessions": {k: v.to_dict() for k, v in self._sessions.items()},
            "online": self._online,
        }
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("State saved to %s", self._state_file)
        except OSError as exc:
            logger.error("Failed to save state: %s", exc)

    def load_state(self) -> None:
        """Restore sessions from state.json."""
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, encoding="utf-8") as f:
                data = json.load(f)
            sessions_data = data.get("sessions", {})
            for key, sess_dict in sessions_data.items():
                self._sessions[key] = ChatSession.from_dict(sess_dict)
            self._online = data.get("online", True)
            logger.debug("State loaded: %d sessions", len(self._sessions))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load state: %s", exc)
