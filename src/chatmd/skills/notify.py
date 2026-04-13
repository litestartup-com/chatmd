"""Notify skill — /notify sends a notification through all configured channels."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillResult

if TYPE_CHECKING:
    from chatmd.infra.notification import NotificationManager
    from chatmd.skills.base import SkillContext

logger = logging.getLogger(__name__)


class NotifySkill(Skill):
    """Send a notification through all configured channels (file, desktop, email).

    Usage::

        /notify Remember to eat dinner
        /notify Server deployment completed

    When used with cron::

        ```cron
        0 18 * * * /notify Time for dinner!
        ```
    """

    name = "notify"
    description = "notify"
    category = "general"
    requires_network = False  # FileChannel works offline; email degrades gracefully
    aliases = ["ntf"]

    @property
    def help_text(self) -> str:
        """Rich help text for /help notify."""
        return t("skill.notify.help_text")

    def __init__(
        self,
        notification_mgr: NotificationManager | None = None,
    ) -> None:
        self._notification_mgr = notification_mgr

    def set_notification_manager(self, mgr: NotificationManager) -> None:
        """Inject the notification manager after construction."""
        self._notification_mgr = mgr

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        """Send a notification with the given text."""
        message = input_text.strip()
        if not message:
            positional = args.get("_positional", "").strip()
            message = positional

        if not message:
            return SkillResult(
                success=False, output="",
                error=t("error.notify_empty"),
            )

        if not self._notification_mgr:
            return SkillResult(
                success=False, output="",
                error=t("error.notify_not_configured"),
            )

        if not self._notification_mgr.enabled:
            return SkillResult(
                success=False, output="",
                error=t("error.notify_disabled"),
            )

        title = t("output.notify.title")
        self._notification_mgr.notify(
            title=title,
            body=message,
            level="info",
            source="user",
        )

        channels = self._notification_mgr.channel_names
        channel_str = ", ".join(channels) if channels else "none"

        return SkillResult(
            success=True,
            output=t(
                "output.notify.success",
                message=message,
                channels=channel_str,
            ),
        )
