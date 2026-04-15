"""Inbox skill — /inbox shows today's inbox summary.

Usage::

    /inbox          # Show today's inbox summary
    /inbox 2026-04-13  # Show inbox for a specific date

Reads ``chatmd/inbox/YYYY-MM-DD.md`` and displays a summary including
message count, time range, and a brief preview of each entry.
"""

from __future__ import annotations

import re
from datetime import date

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

# Pattern to match ## HH:MM:SS headings in inbox files
_TIME_HEADING_RE = re.compile(r"^##\s+(\d{2}:\d{2}(?::\d{2})?)$")
# Max characters for each entry preview
_PREVIEW_MAX_LEN = 60


class InboxSkill(Skill):
    """Show today's inbox summary."""

    name = "inbox"
    description = "inbox"
    category = "builtin"
    aliases = []

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        # Determine target date
        target_date = input_text.strip() if input_text.strip() else ""
        if target_date:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", target_date):
                return SkillResult(
                    success=False, output="",
                    error=t("error.inbox_invalid_date", date=target_date),
                )
        else:
            target_date = date.today().isoformat()

        # Locate inbox file
        workspace = context.interaction_root or context.workspace
        inbox_file = workspace / "chatmd" / "inbox" / f"{target_date}.md"

        if not inbox_file.exists():
            return SkillResult(
                success=True,
                output=t("output.inbox.empty", date=target_date),
            )

        content = inbox_file.read_text(encoding="utf-8")
        entries = self._parse_entries(content)

        if not entries:
            return SkillResult(
                success=True,
                output=t("output.inbox.empty", date=target_date),
            )

        # Build summary
        lines: list[str] = []
        lines.append(t("output.inbox.header", date=target_date, count=len(entries)))

        lines.append(t("output.inbox.table_header"))
        lines.append("|------|------|")

        for entry in entries:
            preview = entry["preview"]
            if len(preview) > _PREVIEW_MAX_LEN:
                preview = preview[:_PREVIEW_MAX_LEN] + "..."
            lines.append(f"| {entry['time']} | {preview} |")

        # Time range
        first_time = entries[0]["time"]
        last_time = entries[-1]["time"]
        lines.append("")
        lines.append(
            t(
                "output.inbox.summary",
                count=len(entries),
                first=first_time,
                last=last_time,
            ),
        )

        return SkillResult(success=True, output="\n".join(lines))

    @staticmethod
    def _parse_entries(content: str) -> list[dict[str, str]]:
        """Parse inbox Markdown into a list of entries.

        Each entry has ``time`` and ``preview`` (first non-empty line of body).
        """
        entries: list[dict[str, str]] = []
        current_time: str | None = None
        current_lines: list[str] = []

        for line in content.splitlines():
            match = _TIME_HEADING_RE.match(line.strip())
            if match:
                # Save previous entry
                if current_time is not None:
                    preview = _first_meaningful_line(current_lines)
                    entries.append({"time": current_time, "preview": preview})
                current_time = match.group(1)
                current_lines = []
            elif current_time is not None:
                stripped = line.strip()
                if stripped and stripped != "---":
                    current_lines.append(stripped)

        # Save last entry
        if current_time is not None:
            preview = _first_meaningful_line(current_lines)
            entries.append({"time": current_time, "preview": preview})

        return entries


def _first_meaningful_line(lines: list[str]) -> str:
    """Return the first non-empty line, or a placeholder."""
    for line in lines:
        if line.strip():
            return line.strip()
    return "(empty)"
