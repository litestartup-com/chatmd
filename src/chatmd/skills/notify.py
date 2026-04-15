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

    # Valid channel short names (used for input validation)
    _VALID_CHANNELS = frozenset({"file", "system", "desktop", "email", "bot"})

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        """Send a notification with the given text.

        Supports ``channel`` arg to target specific channels::

            /notify(channel=email) Deployment done
            /notify(channel=bot) Server alert
            /notify All channels
        """
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

        # Parse channel filter from args.
        # Supports: /notify(email) msg, /notify(email,bot) msg, /notify(channel=email) msg
        channel_filter: list[str] | None = None
        raw_channel = args.get("channel", "").strip()
        if not raw_channel:
            # Try positional arg as channel shorthand: /notify(email) msg
            positional = args.get("_positional", "").strip()
            if positional:
                parts = [p.strip().lower() for p in positional.split(",") if p.strip()]
                if parts and all(p in self._VALID_CHANNELS for p in parts):
                    raw_channel = positional
        if raw_channel:
            channel_filter = [c.strip().lower() for c in raw_channel.split(",") if c.strip()]
            invalid = [c for c in channel_filter if c not in self._VALID_CHANNELS]
            if invalid:
                return SkillResult(
                    success=False, output="",
                    error=t(
                        "error.notify_invalid_channel",
                        channels=", ".join(invalid),
                        valid=", ".join(sorted(self._VALID_CHANNELS)),
                    ),
                )

        title = t("output.notify.title")
        self._notification_mgr.notify(
            title=title,
            body=message,
            level="info",
            source="user",
            channels=channel_filter,
        )

        if channel_filter:
            channel_str = ", ".join(channel_filter)
        else:
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
