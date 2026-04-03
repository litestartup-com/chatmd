"""Safe file writer — atomic writes with task ID anchoring and agent write lock."""

from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Matches placeholder lines like: > ⏳ Translating... `#task-a1b2`
_TASK_ID_RE = re.compile(r"`#(task-[a-z0-9]+)`")


class FileWriter:
    """Serialised, safe file writer for Agent output.

    All writes go through this singleton to avoid concurrent corruption.
    Maintains a set of paths currently being written so the FileWatcher
    can ignore Agent-originated changes.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._agent_writes: set[str] = set()

    def is_agent_write(self, filepath: Path) -> bool:
        """Check whether *filepath* is currently flagged as an Agent write."""
        return str(filepath) in self._agent_writes

    def write_result(
        self,
        filepath: Path,
        line_num: int,
        old_text: str,
        new_text: str,
    ) -> bool:
        """Replace *old_text* with *new_text* atomically.

        When *line_num* > 0, the replacement is anchored to that specific
        line (1-indexed) so that identical text elsewhere in the file is
        never accidentally matched.  Falls back to a plain string search
        when *line_num* is 0.

        Returns ``True`` on success, ``False`` if the anchor was not found.
        """
        with self._lock:
            return self._do_replace(filepath, old_text, new_text, line_num)

    def replace_by_task_id(
        self,
        filepath: Path,
        task_id: str,
        new_text: str,
    ) -> bool:
        """Find the line containing ``#task_id`` and replace it with *new_text*."""
        with self._lock:
            self._mark_agent_write(filepath)
            try:
                content = filepath.read_text(encoding="utf-8")
                marker = f"`#{task_id}`"
                if marker not in content:
                    logger.warning("Task anchor '%s' not found in %s", marker, filepath)
                    return False

                # Replace the whole line containing the marker
                lines = content.splitlines(keepends=True)
                new_lines: list[str] = []
                replaced = False
                for line in lines:
                    if marker in line and not replaced:
                        new_lines.append(new_text if new_text.endswith("\n") else new_text + "\n")
                        replaced = True
                    else:
                        new_lines.append(line)

                if replaced:
                    self._atomic_write(filepath, "".join(new_lines))
                return replaced
            finally:
                self._unmark_agent_write(filepath)

    def write_result_range(
        self,
        filepath: Path,
        start_line: int,
        end_line: int,
        new_text: str,
    ) -> bool:
        """Replace lines *start_line* through *end_line* (1-indexed, inclusive).

        Used for fenced commands (``/cmd`` + ``:::`` block) where the
        replacement spans multiple lines.  Returns ``True`` on success.
        """
        with self._lock:
            self._mark_agent_write(filepath)
            try:
                content = filepath.read_text(encoding="utf-8")
                lines = content.splitlines(keepends=True)

                if start_line < 1 or end_line > len(lines):
                    logger.warning(
                        "Range %d-%d out of bounds (%d lines) in %s",
                        start_line, end_line, len(lines), filepath,
                    )
                    return False

                # Replace the line range with new_text
                suffix = "\n" if not new_text.endswith("\n") else ""
                new_lines = (
                    lines[:start_line - 1]
                    + [new_text + suffix]
                    + lines[end_line:]
                )
                new_content = "".join(new_lines).rstrip("\n") + "\n\n"
                self._atomic_write(filepath, new_content)
                return True
            finally:
                self._unmark_agent_write(filepath)

    def append_line(self, filepath: Path, text: str) -> None:
        """Append a line to the end of *filepath*."""
        with self._lock:
            self._mark_agent_write(filepath)
            try:
                content = filepath.read_text(encoding="utf-8") if filepath.exists() else ""
                if content and not content.endswith("\n"):
                    content += "\n"
                content += text if text.endswith("\n") else text + "\n"
                self._atomic_write(filepath, content)
            finally:
                self._unmark_agent_write(filepath)

    def _do_replace(
        self, filepath: Path, old_text: str, new_text: str, line_num: int = 0,
    ) -> bool:
        """Core replacement logic.

        When *line_num* > 0, locate the exact line (1-indexed) and replace
        it.  This avoids the bug where ``content.replace`` matches the
        first occurrence of ``old_text`` which may live inside a previous
        command's output rather than the user's actual input line.
        """
        self._mark_agent_write(filepath)
        try:
            content = filepath.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            if line_num > 0 and line_num <= len(lines):
                # Precise line-based replacement
                target_line = lines[line_num - 1]
                if old_text.rstrip() in target_line.rstrip():
                    # Replace old_text within the target line (not the whole line)
                    replaced_line = target_line.replace(old_text, new_text, 1)
                    # If old_text was the entire line content, replaced_line
                    # already has the newline from target_line.
                    if not replaced_line.endswith("\n"):
                        replaced_line += "\n"
                    lines[line_num - 1] = replaced_line
                    new_content = "".join(lines)
                else:
                    logger.warning(
                        "Line %d does not contain '%s' in %s, falling back",
                        line_num, old_text[:40], filepath,
                    )
                    return self._do_replace_by_text(content, filepath, old_text, new_text)
            else:
                return self._do_replace_by_text(content, filepath, old_text, new_text)

            # Ensure the file ends with a blank line for cursor landing.
            new_content = new_content.rstrip("\n") + "\n\n"
            self._atomic_write(filepath, new_content)
            return True
        finally:
            self._unmark_agent_write(filepath)

    def _do_replace_by_text(
        self, content: str, filepath: Path, old_text: str, new_text: str,
    ) -> bool:
        """Fallback: plain string replacement (when line_num is unavailable)."""
        if old_text not in content:
            logger.warning("Old text not found in %s for replacement", filepath)
            return False
        new_content = content.replace(old_text, new_text, 1)
        new_content = new_content.rstrip("\n") + "\n\n"
        self._atomic_write(filepath, new_content)
        return True

    _ATOMIC_RETRIES = 5
    _ATOMIC_RETRY_DELAY = 0.1  # seconds, doubles each retry

    def _atomic_write(self, filepath: Path, content: str) -> None:
        """Write *content* to a temp file then rename (atomic on most OS).

        On Windows, ``os.replace`` may raise ``PermissionError`` when
        another process (e.g. the file watcher or antivirus) still holds
        the target file.  Retry with exponential back-off, then fall back
        to a direct (non-atomic) write so the user always sees the result.
        """
        self._mark_agent_write(filepath)
        tmp_path: Path | None = None
        try:
            parent = filepath.parent
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=parent,
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            delay = self._ATOMIC_RETRY_DELAY
            for attempt in range(self._ATOMIC_RETRIES):
                try:
                    tmp_path.replace(filepath)
                    logger.debug("Atomic write to %s", filepath)
                    tmp_path = None  # rename succeeded, nothing to clean up
                    return
                except PermissionError:
                    if attempt < self._ATOMIC_RETRIES - 1:
                        logger.debug(
                            "Atomic rename attempt %d failed for %s, retrying in %.2fs",
                            attempt + 1, filepath, delay,
                        )
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.warning(
                            "Atomic rename failed after %d attempts for %s, "
                            "falling back to direct write",
                            self._ATOMIC_RETRIES, filepath,
                        )

            # Fallback: direct write (non-atomic but better than silent failure)
            filepath.write_text(content, encoding="utf-8")
            logger.debug("Direct (non-atomic) write to %s", filepath)
        finally:
            # Clean up leftover temp file if rename never succeeded
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            self._unmark_agent_write(filepath)

    def _mark_agent_write(self, filepath: Path) -> None:
        self._agent_writes.add(str(filepath.resolve()))

    def _unmark_agent_write(self, filepath: Path) -> None:
        self._agent_writes.discard(str(filepath.resolve()))
