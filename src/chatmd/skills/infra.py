"""Infrastructure skills — /sync, /log, /new."""

from __future__ import annotations

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.infra.git_sync import GitSync
    from chatmd.infra.index_manager import IndexManager
    from chatmd.security.kernel_gate import KernelGate

logger = logging.getLogger(__name__)

# Characters unsafe in filenames
_UNSAFE_FILENAME_RE = re.compile(r'[/\:*?"<>|]')


class SyncSkill(Skill):
    """Manually trigger Git sync."""

    name = "sync"
    description = "sync"
    category = "builtin"
    requires_network = True
    aliases = []

    def __init__(self, git_sync: GitSync | None = None) -> None:
        self._git_sync = git_sync

    def set_git_sync(self, git_sync: GitSync) -> None:
        self._git_sync = git_sync

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        if not self._git_sync:
            return SkillResult(success=False, output="", error=t("error.sync_not_configured"))
        success, msg = self._git_sync.sync_now()
        return SkillResult(success=success, output=msg, error=None if success else msg)


class LogSkill(Skill):
    """Show recent audit log entries."""

    name = "log"
    description = "log"
    category = "builtin"
    aliases = []

    def __init__(self, kernel_gate: KernelGate | None = None) -> None:
        self._kernel_gate = kernel_gate

    def set_kernel_gate(self, kernel_gate: KernelGate) -> None:
        self._kernel_gate = kernel_gate

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        if not self._kernel_gate:
            return SkillResult(success=False, output="", error=t("error.audit_not_configured"))

        count = 10
        if input_text.strip().isdigit():
            count = min(int(input_text.strip()), 50)

        entries = self._kernel_gate.get_recent_audit(count)
        if not entries:
            return SkillResult(success=True, output=t("output.log.empty"))

        lines = [t("output.log.header", count=len(entries))]
        lines.append(t("output.log.table_header"))
        lines.append("|---|-------|------|------|------|")
        for i, e in enumerate(reversed(entries), 1):
            status = "✅" if e["success"] else "❌"
            error = e.get("error") or ""
            lines.append(f"| {i} | {e['skill']} | {e['category']} | {status} | {error} |")

        return SkillResult(success=True, output="\n".join(lines))


class NewSessionSkill(Skill):
    """Archive current chat.md and create a fresh session."""

    name = "new"
    description = "new"
    category = "builtin"
    aliases = ["n"]

    # Max characters for auto-extracted topic
    _TOPIC_MAX_LEN = 20
    # Fallback topic when chat.md body is empty
    _FALLBACK_TOPIC_KEY = "new.fallback_topic"

    def __init__(self, index_manager: IndexManager | None = None) -> None:
        self._index_manager = index_manager

    def set_index_manager(self, index_manager: IndexManager) -> None:
        """Inject the IndexManager after construction."""
        self._index_manager = index_manager

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        workspace = context.workspace
        chat_md = workspace / "chat.md"

        if not chat_md.exists():
            return SkillResult(
                success=False, output="",
                error=t("error.new_no_chat_md"),
            )

        content = chat_md.read_text(encoding="utf-8")
        body = self._extract_body(content)

        if not body.strip():
            return SkillResult(
                success=False, output="",
                error=t("error.new_empty_content"),
            )

        # Determine topic
        topic = input_text.strip() if input_text.strip() else self._auto_topic(body)
        topic = self._sanitize_topic(topic)

        # Build archive filename
        now = datetime.now()
        date_prefix = now.strftime("%Y-%m%d-%H%M")
        archive_name = f"{date_prefix}-{topic}.md"

        # Ensure chat/ directory exists
        chat_dir = workspace / "chat"
        chat_dir.mkdir(exist_ok=True)

        # Handle filename conflict
        archive_path = chat_dir / archive_name
        archive_path = self._resolve_conflict(archive_path)

        # Archive: copy then overwrite
        shutil.copy2(chat_md, archive_path)
        logger.info("Archived chat.md to %s", archive_path)

        # Create fresh chat.md (minimal template)
        fresh_content = self._build_fresh_chat_md()
        chat_md.write_text(fresh_content, encoding="utf-8")

        # Update _index.md
        if self._index_manager:
            self._index_manager.update()

        return SkillResult(
            success=True,
            output=t(
                "output.new.success",
                archive=archive_path.name,
            ),
        )

    @classmethod
    def _extract_body(cls, content: str) -> str:
        """Extract meaningful body from chat.md, skipping frontmatter and commands."""
        lines = content.splitlines()
        body_lines: list[str] = []
        in_frontmatter = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip YAML frontmatter
            if i == 0 and stripped == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                continue
            # Skip empty lines, commands, blockquotes, horizontal rules, headings
            if not stripped:
                continue
            if stripped.startswith("/"):
                continue
            if stripped.startswith(">"):
                continue
            if stripped == "---":
                continue
            if stripped.startswith("#"):
                continue
            # Skip code fences
            if stripped.startswith("```"):
                continue
            body_lines.append(stripped)

        return "\n".join(body_lines)

    @classmethod
    def _auto_topic(cls, body: str) -> str:
        """Extract topic from body text (first meaningful characters)."""
        # Take first line's meaningful content
        first_line = body.split("\n")[0].strip()
        if len(first_line) > cls._TOPIC_MAX_LEN:
            return first_line[:cls._TOPIC_MAX_LEN]
        if first_line:
            return first_line
        return t(cls._FALLBACK_TOPIC_KEY)

    @staticmethod
    def _sanitize_topic(topic: str) -> str:
        """Replace unsafe filename characters with hyphens."""
        sanitized = _UNSAFE_FILENAME_RE.sub("-", topic)
        # Collapse multiple hyphens
        sanitized = re.sub(r"-{2,}", "-", sanitized)
        return sanitized.strip("-") or "chat"

    @staticmethod
    def _resolve_conflict(path: Path) -> Path:
        """Append -2, -3, etc. if the file already exists."""
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 2
        while True:
            candidate = parent / f"{stem}-{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _build_fresh_chat_md() -> str:
        """Build a minimal fresh chat.md for the new session."""
        return f"{t('init.welcome_title')}\n\n---\n\n"
