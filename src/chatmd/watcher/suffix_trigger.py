"""Suffix signal trigger — detect trailing markers (e.g. `;`) as command triggers."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default suffix marker
DEFAULT_SUFFIX_MARKER = ";"


@dataclass
class SuffixSignal:
    """Represents a detected suffix trigger signal."""

    line_text: str
    clean_text: str
    marker: str
    line_num: int


class SuffixTrigger:
    """Detects suffix markers at end of lines as command triggers.

    When enabled, a line ending with the configured marker (default ``;``)
    is treated as a trigger signal.  The marker is stripped before the line
    is forwarded for parsing.

    Example::

        /translate hello;   →  triggers immediately, input = "/translate hello"
        summarize this;      →  triggers as open-chat, input = "summarize this"
    """

    def __init__(
        self,
        marker: str = DEFAULT_SUFFIX_MARKER,
        enabled: bool = False,
    ) -> None:
        self._marker = marker
        self._enabled = enabled
        # Pattern: line content + marker + optional whitespace at end
        self._pattern = re.compile(
            rf"^(?P<content>.+?)\s*{re.escape(marker)}\s*$"
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def marker(self) -> str:
        return self._marker

    @marker.setter
    def marker(self, value: str) -> None:
        self._marker = value
        self._pattern = re.compile(
            rf"^(?P<content>.+?)\s*{re.escape(value)}\s*$"
        )

    def detect(self, line: str, line_num: int = 0) -> SuffixSignal | None:
        """Check if a line ends with the suffix marker.

        Returns a ``SuffixSignal`` if detected, ``None`` otherwise.
        """
        if not self._enabled:
            return None

        m = self._pattern.match(line)
        if m is None:
            return None

        clean = m.group("content").strip()
        if not clean:
            return None

        logger.debug("Suffix signal detected at line %d: '%s'", line_num, clean)
        return SuffixSignal(
            line_text=line,
            clean_text=clean,
            marker=self._marker,
            line_num=line_num,
        )
