"""Bind skill — /bind connects the user's Git repo to a Telegram Bot.

Usage::

    /bind ghp_xxxxxxxxxxxxxxxxxxxx

The skill automatically reads ``git remote get-url origin``, converts SSH
URLs to HTTPS, calls the LiteStartup bind API, and displays a 6-digit
bind code for the user to send to the Telegram Bot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.infra.git_utils import (
    detect_git_platform,
    get_git_remote_url,
    get_token_help_url,
    mask_repo_url,
    ssh_to_https,
    strip_url_credentials,
)
from chatmd.skills.base import Skill, SkillResult

if TYPE_CHECKING:
    from chatmd.providers.litestartup import LiteStartupProvider
    from chatmd.skills.base import SkillContext

logger = logging.getLogger(__name__)


class BindSkill(Skill):
    """Bind the user's Git repository to a Telegram Bot.

    Reads ``git remote origin`` automatically, calls LiteStartup bind API,
    and displays a 6-digit bind code.
    """

    name = "bind"
    description = "bind"
    category = "general"
    requires_network = True
    aliases: list[str] = []

    def __init__(
        self,
        provider: LiteStartupProvider | None = None,
    ) -> None:
        self._provider = provider

    def set_provider(self, provider: LiteStartupProvider) -> None:
        """Inject the LiteStartup provider after construction."""
        self._provider = provider

    @property
    def help_text(self) -> str:
        """Rich help text for /help bind."""
        return t("skill.bind.help_text")

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        """Execute the bind flow.

        ``input_text`` is expected to contain the Git platform access token.
        """
        git_token = input_text.strip()

        # -- Validate prerequisites ------------------------------------------

        if not self._provider:
            return SkillResult(
                success=False, output="",
                error=t("error.bind_no_provider"),
            )

        if not git_token:
            return self._missing_token_help(context)

        # -- Read git remote -------------------------------------------------

        raw_url = get_git_remote_url(context.workspace)
        if not raw_url:
            return SkillResult(
                success=False, output="",
                error=t("error.bind_no_remote"),
            )

        repo_url = strip_url_credentials(ssh_to_https(raw_url))

        # -- Check current binding status ------------------------------------

        status_result = self._provider.bind_status()
        if status_result.get("success") and status_result.get("status") == "active":
            return self._already_bound(status_result)

        # -- Call bind/initiate ----------------------------------------------

        result = self._provider.bind_initiate(
            repo_url=repo_url,
            git_token=git_token,
            platform="telegram",
            timezone=self._detect_timezone(),
        )

        if not result.get("success"):
            return self._bind_error(result)

        # -- Format success output -------------------------------------------

        return self._bind_success(result, repo_url)

    # -- Output formatters ---------------------------------------------------

    def _missing_token_help(self, context: SkillContext) -> SkillResult:
        """Return help output when no token is provided."""
        raw_url = get_git_remote_url(context.workspace) or ""
        repo_url = ssh_to_https(raw_url) if raw_url else ""
        platform = detect_git_platform(repo_url) if repo_url else "unknown"
        help_url = get_token_help_url(platform)

        lines = [t("error.bind_missing_token")]
        if repo_url:
            lines.append("")
            lines.append(t("output.bind.detected_repo", repo_url=repo_url))
            lines.append(
                t("output.bind.platform_detected", platform=platform),
            )
        if help_url:
            lines.append("")
            lines.append(t("output.bind.token_help_link", url=help_url))

        lines.append("")
        lines.append(t("output.bind.usage_hint"))

        return SkillResult(success=False, output="\n".join(lines))

    def _already_bound(self, status: dict) -> SkillResult:
        """Return output when user already has an active binding."""
        lines = [
            t("output.bind.already_active"),
            "",
            t(
                "output.bind.current_binding",
                platform=status.get("platform", "?"),
                repo=status.get("repo_url_masked", "?"),
                bound_at=status.get("bound_at", "?"),
            ),
        ]
        return SkillResult(success=False, output="\n".join(lines))

    def _bind_error(self, result: dict) -> SkillResult:
        """Return output for a failed bind attempt."""
        error_code = result.get("code")
        error_msg = result.get("error", "")

        # Map known error codes to user-friendly messages
        code_map = {
            1001: t("error.bind_invalid_repo"),
            1002: t("error.bind_invalid_platform"),
            1003: t("error.bind_already_active"),
            2001: t("error.bind_unauthorized"),
            3001: t("error.bind_rate_limited"),
        }

        if error_code and error_code in code_map:
            user_msg = code_map[error_code]
        elif error_msg:
            # Show server error detail (e.g. Network error, HTTP 404, timeout)
            user_msg = t("error.bind_server_error", detail=error_msg)
        else:
            user_msg = t("error.bind_unknown")

        return SkillResult(success=False, output="", error=user_msg)

    @staticmethod
    def _detect_timezone() -> str:
        """Detect the local IANA timezone name.

        Falls back to UTC offset string (e.g. ``Etc/GMT-8``) when the
        system timezone name cannot be determined.
        """
        import datetime
        import time

        # Try tzname first (e.g. 'Asia/Shanghai' on well-configured systems)
        try:
            local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
            tz_name = getattr(local_tz, "key", None)  # Python 3.9+ ZoneInfo
            if tz_name:
                return tz_name
        except Exception:  # noqa: BLE001
            pass

        # Fallback: compute UTC offset → Etc/GMT±N
        utc_offset_sec = -time.timezone if time.daylight == 0 else -time.altzone
        hours = utc_offset_sec // 3600
        # Etc/GMT sign is inverted: UTC+8 → Etc/GMT-8
        if hours >= 0:
            return f"Etc/GMT-{hours}" if hours != 0 else "UTC"
        return f"Etc/GMT+{abs(hours)}"

    def _bind_success(self, result: dict, repo_url: str) -> SkillResult:
        """Return output for a successful bind initiation."""
        bind_code = result.get("bind_code", "")
        expires_in = result.get("expires_in", 300)
        bot_username = result.get("bot_username", "")
        bot_deep_link = result.get("bot_deep_link", "")
        expire_min = expires_in // 60

        lines = [
            t("output.bind.title"),
            "",
            t("output.bind.repo_line", repo_url=mask_repo_url(repo_url)),
            t("output.bind.platform_line", platform="Telegram"),
            "",
            t("output.bind.code_line", code=bind_code, minutes=expire_min),
            "",
        ]

        if bot_deep_link:
            lines.append(
                t("output.bind.bot_link", link=bot_deep_link, name=bot_username),
            )
        else:
            lines.append(
                t("output.bind.bot_name", name=bot_username),
            )

        lines.append("")
        lines.append(t("output.bind.waiting"))

        return SkillResult(
            success=True,
            output="\n".join(lines),
            metadata={
                "bind_code": bind_code,
                "expires_in": expires_in,
                "bot_deep_link": bot_deep_link,
            },
        )
