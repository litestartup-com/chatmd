"""Confirm skill — /confirm to execute pending commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.engine.confirm import ConfirmationWindow


class ConfirmSkill(Skill):
    """Execute the most recent pending confirmation, or a specific one by ID."""

    name = "confirm"
    description = "confirm"
    category = "builtin"
    aliases = ["y", "yes"]

    def __init__(self, confirmation_window: ConfirmationWindow | None = None) -> None:
        self._cw = confirmation_window

    def set_confirmation_window(self, cw: ConfirmationWindow) -> None:
        self._cw = cw

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        if not self._cw:
            return SkillResult(
                success=False, output="", error=t("confirm.nothing_pending"),
            )

        # /confirm → confirm latest; /confirm #confirm-3 → confirm by ID
        confirm_id: str | None = None
        text = input_text.strip()
        if text:
            # Strip leading # if present
            confirm_id = text.lstrip("#").strip() or None

        # List pending if user typed /confirm list
        if text == "list":
            return self._list_pending()

        pending = self._cw.confirm(confirm_id)
        if pending is None:
            return SkillResult(
                success=True,
                output=t("confirm.nothing_pending"),
            )

        return SkillResult(
            success=True,
            output=t("confirm.accepted_placeholder"),
        )

    def _list_pending(self) -> SkillResult:
        """List all pending confirmations."""
        items = self._cw.list_pending() if self._cw else []
        if not items:
            return SkillResult(
                success=True, output=t("confirm.nothing_pending"),
            )
        lines = [t("confirm.list_header")]
        for p in items:
            lines.append(t("confirm.list_item", confirm_id=p.confirm_id, command=p.command_text))
        return SkillResult(success=True, output="\n".join(lines))
