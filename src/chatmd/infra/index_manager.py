"""Index manager — auto-maintain chat/_index.md for session navigation."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from chatmd.i18n import t

logger = logging.getLogger(__name__)


def _build_index_header() -> str:
    """Build the index header using i18n strings."""
    return (
        "# Chat Sessions\n\n"
        f"{t('index.header_note')}\n\n"
        f"{t('index.table_header')}\n"
        "|------|---------|------|\n"
    )


class IndexManager:
    """Maintains ``chat/_index.md`` with a table of all session files.

    Scans ``chat/`` directory for ``.md`` files (excluding ``_index.md``)
    and regenerates the index table.
    """

    def __init__(self, workspace: Path, *, interaction_root: Path | None = None) -> None:
        self._workspace = workspace
        root = interaction_root if interaction_root is not None else workspace
        self._chat_dir = root / "chat"
        self._index_file = self._chat_dir / "_index.md"

    @property
    def index_file(self) -> Path:
        return self._index_file

    def update(self) -> bool:
        """Regenerate the index file. Returns True if the file was updated."""
        if not self._chat_dir.is_dir():
            return False

        entries = self._scan_sessions()
        content = self._render(entries)

        # Only write if content changed
        if self._index_file.exists():
            existing = self._index_file.read_text(encoding="utf-8")
            if existing == content:
                return False

        self._index_file.write_text(content, encoding="utf-8")
        logger.info("Updated index: %s (%d entries)", self._index_file, len(entries))
        return True

    def _scan_sessions(self) -> list[dict]:
        """Scan chat/ directory for .md files."""
        entries = []
        for path in sorted(self._chat_dir.glob("*.md")):
            if path.name == "_index.md":
                continue
            stat = path.stat()
            entries.append({
                "name": path.name,
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
                "size": self._human_size(stat.st_size),
            })
        return entries

    def _render(self, entries: list[dict]) -> str:
        """Render the index Markdown content."""
        lines = [_build_index_header()]
        for e in entries:
            lines.append(f"| [{e['name']}]({e['name']}) | {e['created']} | {e['size']} |")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable size."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / (1024 * 1024):.1f} MB"
