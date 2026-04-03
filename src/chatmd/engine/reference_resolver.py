"""Reference resolver — resolves @above, @section, @all, @file, @clip markers.

These markers allow users to reference existing text as command input
without copy-pasting. Resolved text is passed as ``input_text`` to skills.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_REF_RE = re.compile(
    r"^@(?P<kind>above|section|all|file|clip)"
    r"(?:\((?P<arg>[^)]*)\))?$"
)

_BLOCKQUOTE_RE = re.compile(r"^>")
_HEADING2_RE = re.compile(r"^##\s")


def _get_clipboard_text() -> str:
    """Read text from system clipboard (best-effort, no hard dependency)."""
    try:
        import subprocess
        import sys

        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
        elif sys.platform == "darwin":
            result = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
        else:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
    except Exception as exc:
        logger.warning("Failed to read clipboard: %s", exc)
        return ""


def _extract_paragraphs(lines: list[str], stop_before: int) -> list[str]:
    """Extract paragraphs from lines above *stop_before* (1-indexed).

    A paragraph is a group of consecutive non-empty, non-blockquote lines
    separated by empty lines. Returns paragraphs in order (first = earliest).
    """
    paragraphs: list[str] = []
    current: list[str] = []

    for i in range(min(stop_before - 1, len(lines))):
        line = lines[i]
        stripped = line.rstrip()

        # Skip blockquote lines (agent output)
        if _BLOCKQUOTE_RE.match(stripped):
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue

        if stripped == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
        else:
            current.append(stripped)

    if current:
        paragraphs.append("\n".join(current))

    return paragraphs


def _resolve_above(lines: list[str], cmd_line: int, n: int = 1) -> str:
    """Resolve @above or @above(N) — Nth paragraph above the command line."""
    paragraphs = _extract_paragraphs(lines, cmd_line)
    if not paragraphs or n < 1:
        return ""
    idx = len(paragraphs) - n
    if idx < 0:
        return ""
    return paragraphs[idx]


def _resolve_section(lines: list[str], cmd_line: int) -> str:
    """Resolve @section — content of the current ## section above cmd_line."""
    section_start = 0
    for i in range(min(cmd_line - 1, len(lines)) - 1, -1, -1):
        if _HEADING2_RE.match(lines[i].rstrip()):
            section_start = i + 1  # Exclude the heading itself
            break

    content_lines: list[str] = []
    for i in range(section_start, min(cmd_line - 1, len(lines))):
        content_lines.append(lines[i].rstrip())

    return "\n".join(content_lines).strip()


def _resolve_all(lines: list[str], cmd_line: int) -> str:
    """Resolve @all — all file content excluding the command line."""
    result: list[str] = []
    for i, line in enumerate(lines, start=1):
        if i == cmd_line:
            continue
        result.append(line.rstrip())
    return "\n".join(result).strip()


def _resolve_file(arg: str, source_file: Path | None) -> str:
    """Resolve @file(path) — read content from another file."""
    if not arg:
        return ""

    file_path = Path(arg)

    # Try absolute first
    if file_path.is_absolute() and file_path.exists():
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed to read %s: %s", file_path, exc)
            return ""

    # Try relative to source file's directory
    if source_file is not None:
        resolved = source_file.parent / file_path
        if resolved.exists():
            try:
                return resolved.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Failed to read %s: %s", resolved, exc)
                return ""

    logger.warning("Referenced file not found: %s", arg)
    return ""


class ReferenceResolver:
    """Resolves @ reference markers in command input text."""

    def __init__(
        self,
        lines: list[str],
        cmd_line: int,
        source_file: Path | None = None,
    ) -> None:
        self._lines = lines
        self._cmd_line = cmd_line
        self._source_file = source_file

    def resolve(self, text: str) -> str:
        """Resolve any @ reference in *text*, returning the referenced content.

        If *text* is not a reference, returns it unchanged.
        """
        stripped = text.strip()
        m = _REF_RE.match(stripped)
        if not m:
            return text

        kind = m.group("kind")
        arg = m.group("arg") or ""

        if kind == "above":
            n = int(arg) if arg.isdigit() else 1
            return _resolve_above(self._lines, self._cmd_line, n)
        elif kind == "section":
            return _resolve_section(self._lines, self._cmd_line)
        elif kind == "all":
            return _resolve_all(self._lines, self._cmd_line)
        elif kind == "file":
            return _resolve_file(arg, self._source_file)
        elif kind == "clip":
            return _get_clipboard_text()

        return text

    @staticmethod
    def is_reference(text: str) -> bool:
        """Check whether *text* is a valid @ reference marker."""
        return _REF_RE.match(text.strip()) is not None


def resolve_references(
    text: str,
    lines: list[str],
    cmd_line: int,
    source_file: Path | None = None,
) -> str:
    """Convenience function — resolve @ references in *text*."""
    resolver = ReferenceResolver(lines, cmd_line, source_file)
    return resolver.resolve(text)
