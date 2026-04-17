"""KernelGate — output filtering and audit for all Skill results."""

from __future__ import annotations

import logging
import re

from chatmd.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)

# Pattern to detect slash commands in AI output (injection prevention)
# Matches /command at start of line OR after whitespace (not inside words like "http://")
_SLASH_CMD_RE = re.compile(r"(?:^|(?<=\s))/[a-zA-Z_][\w-]*", re.MULTILINE)


class KernelGate:
    """Filters and audits all Skill output before it reaches the user.

    Core responsibilities:
    1. Prevent AI command injection — ``/command`` in AI output must not be parsed.
    2. Audit logging — every Skill execution is recorded.
    """

    def __init__(self, *, audit_enabled: bool = True) -> None:
        self._audit_entries: list[dict] = []
        self._audit_enabled = audit_enabled

    def process_output(self, skill: Skill, result: SkillResult) -> SkillResult:
        """Filter and audit a Skill result before writing back."""
        # 1. Filter: escape slash commands in AI output
        if skill.category in ("ai", "remote") and result.success:
            result = self._escape_commands(result)

        # 2. Audit log (only when enabled via logging.audit config)
        if self._audit_enabled:
            self._audit(skill, result)

        return result

    def get_recent_audit(self, count: int = 20) -> list[dict]:
        """Return the most recent audit entries."""
        return self._audit_entries[-count:]

    @staticmethod
    def _escape_commands(result: SkillResult) -> SkillResult:
        """Escape slash commands in output to prevent re-parsing.

        Converts ``/command`` to ``\\/command`` in AI-generated text so the
        Parser will not treat them as real commands.
        """
        if not result.output:
            return result

        def _escape_match(m: re.Match) -> str:
            return "\\" + m.group(0)

        escaped = _SLASH_CMD_RE.sub(_escape_match, result.output)
        if escaped != result.output:
            logger.debug("KernelGate escaped %d command(s) in AI output",
                         len(_SLASH_CMD_RE.findall(result.output)))
            return SkillResult(
                success=result.success,
                output=escaped,
                error=result.error,
                metadata=result.metadata,
            )
        return result

    def _audit(self, skill: Skill, result: SkillResult) -> None:
        """Record an audit entry."""
        entry = {
            "skill": skill.name,
            "category": skill.category,
            "success": result.success,
            "error": result.error,
        }
        self._audit_entries.append(entry)
        if len(self._audit_entries) > 1000:
            self._audit_entries = self._audit_entries[-500:]

        if result.success:
            logger.info(
                "AUDIT skill=%s category=%s status=ok",
                skill.name, skill.category,
            )
        elif result.informational:
            logger.info(
                "AUDIT skill=%s category=%s status=info",
                skill.name, skill.category,
            )
        else:
            logger.warning(
                "AUDIT skill=%s category=%s status=fail error=%s",
                skill.name, skill.category, result.error,
            )
