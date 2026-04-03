"""AI Provider base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for all AI service providers."""

    name: str = ""

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs: object) -> str:
        """Send messages to the AI and return the response text."""
        ...
