"""Bind skill — /bind connects the user's Git repo to a Telegram Bot.

Usage::

    /bind ghp_xxxxxxxxxxxxxxxxxxxx     # primary: initiate a binding
    /bind status                       # T-R083 / T-126: list all bindings

The skill automatically reads ``git remote get-url origin``, converts SSH
URLs to HTTPS, calls the LiteStartup bind API, and displays a 6-digit
bind code for the user to send to the Telegram Bot. The ``status``
sub-command surfaces every binding visible to the LS user (multi-repo
support landed in T-R083) and marks the current workspace with ``▶``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.infra.git_utils import (
    derive_repo_alias,
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

        ``input_text`` is expected to contain the Git platform access token,
        or the literal sub-command ``status`` (T-R083 / T-126) to list every
        binding visible to the current LS user.
        """
        raw = input_text.strip()

        # -- Validate prerequisites ------------------------------------------

        if not self._provider:
            return SkillResult(
                success=False, output="",
                error=t("error.bind_no_provider"),
            )

        # -- T-126 sub-command: `/bind status` -> multi-repo listing ---------
        #
        # Recognise the literal `status` token BEFORE the no-token branch
        # below so that `/bind status` doesn't fall through to the
        # missing-token help. We accept extra trailing args (they're
        # currently ignored) so a future `/bind status --all` etc. can
        # extend without breaking the command surface.
        first_word = raw.split(maxsplit=1)[0] if raw else ""
        if first_word == "status":
            return self._handle_status(context)

        git_token = raw
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

        # -- Derive a friendly alias from the local workspace ----------------
        #
        # T-125 option B: pass `repo_alias` so the server can persist a
        # human-readable handle that survives /repos and powers
        # `/use <alias>` from Telegram. We prefer the local Git root name
        # because that's the directory the user actually `cd`s into and
        # therefore intuitively types. Falls back to URL basename when
        # Git is unavailable; empty string is acceptable (server then
        # synthesises an effective_alias from the URL).
        repo_alias = derive_repo_alias(context.workspace, repo_url)

        # -- Call bind/initiate ----------------------------------------------
        #
        # Note (T-R083 / T-123.2 hotfix): we used to short-circuit here when
        # bind_status() returned status="active", but that is incorrect under
        # the multi-repo binding model — a user may legitimately bind multiple
        # distinct repos under the same account. The server is the only
        # authority on duplicate detection (UserBindingService::findByUserAndRepo
        # returns code 1003 for the exact-same repo_url on the same user +
        # platform). Removing the client-side guard avoids false negatives
        # across different repos sharing one git_token.

        result = self._provider.bind_initiate(
            repo_url=repo_url,
            git_token=git_token,
            platform="telegram",
            timezone=self._detect_timezone(),
            repo_alias=repo_alias,
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

        return SkillResult(success=False, output="\n".join(lines), informational=True)

    # -- T-126 · /bind status sub-command -----------------------------------

    def _handle_status(self, context: SkillContext) -> SkillResult:
        """Render the multi-repo binding listing.

        Calls ``provider.bind_list()`` and emits a markdown listing where:

        - ``✅`` marks the active binding (server-side ``is_active`` flag).
        - ``▶`` marks the binding whose repo URL matches the current
          workspace, so the user immediately sees "where am I right now"
          without having to copy-compare URLs.
        - ``·`` is the catch-all bullet for inactive non-current rows.

        Empty list emits a friendly hint pointing back at ``/bind <token>``
        rather than a confusing blank result. Network / auth / rate-limit
        errors are surfaced via :meth:`_list_error` with the same i18n
        coding pattern used by the bind initiate flow.
        """
        # _provider non-null already guaranteed by execute() guard.
        assert self._provider is not None
        result = self._provider.bind_list(platform="telegram")
        if not result.get("success"):
            return self._list_error(result)

        repos = result.get("repos", [])
        count = result.get("count", 0)

        if count == 0 or not repos:
            return SkillResult(
                success=True,
                output=t("output.bind.list_empty"),
                informational=True,
            )

        # Compute the masked URL for the current workspace so we can mark
        # the row that corresponds to "where the user is right now". We
        # mirror the LS server-side maskRepoUrl rule (strip credentials,
        # scheme, .git suffix) -- the two implementations are kept in
        # lockstep on purpose; see the docstring on git_utils.mask_repo_url.
        current_masked = ""
        raw_url = get_git_remote_url(context.workspace) or ""
        if raw_url:
            try:
                current_masked = mask_repo_url(
                    strip_url_credentials(ssh_to_https(raw_url)),
                )
            except Exception:  # noqa: BLE001
                # Best-effort -- a degraded mask just means we won't put
                # ▶ next to any row. The list itself is still useful.
                current_masked = ""

        lines = [t("output.bind.list_header", count=count), ""]
        for repo in repos:
            # `effective_alias` is guaranteed non-empty by the server
            # (T-125 synthesises it from repo_url basename for legacy
            # NULL rows). Fall back to literals in case an older server
            # responds without the new field.
            alias = (
                repo.get("effective_alias")
                or repo.get("repo_alias")
                or t("output.bind.list_unnamed_alias")
            )
            masked = repo.get("repo_url_masked") or ""
            is_active = bool(repo.get("is_active"))
            is_current = bool(current_masked) and masked == current_masked

            markers: list[str] = []
            if is_active:
                markers.append("✅")
            if is_current:
                markers.append("▶")
            if not markers:
                markers.append("·")
            marker_str = " ".join(markers)

            lines.append(t(
                "output.bind.list_row",
                marker=marker_str,
                alias=alias,
                url=masked,
            ))

        lines.append("")
        lines.append(t("output.bind.list_footer"))

        return SkillResult(
            success=True,
            output="\n".join(lines),
            informational=True,
        )

    def _list_error(self, result: dict) -> SkillResult:
        """Render an error envelope from ``provider.bind_list``."""
        error_code = result.get("code")
        error_msg = result.get("error", "")

        # Reuse bind_initiate's auth/rate-limit messages so the user sees
        # the same friendly text regardless of which call leaked the error.
        code_map = {
            2001: t("error.bind_unauthorized"),
            3001: t("error.bind_rate_limited"),
        }
        if error_code and error_code in code_map:
            user_msg = code_map[error_code]
        elif error_msg:
            code_suffix = f" [code={error_code}]" if error_code else ""
            user_msg = t("error.bind_list_failed", detail=error_msg) + code_suffix
        else:
            user_msg = t("error.bind_list_failed", detail="(no detail)")

        return SkillResult(success=False, output="", error=user_msg)

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
            code_suffix = f" [code={error_code}]" if error_code else ""
            user_msg = t("error.bind_server_error", detail=error_msg) + code_suffix
        else:
            # Neither a known code nor a message — expose whatever we have
            # so the user can diagnose instead of seeing "Unknown error".
            user_msg = t(
                "error.bind_unknown",
                code=error_code if error_code is not None else "n/a",
                raw=str(result) if result else "n/a",
            )
            logger.warning("Bind failed with unmapped response: %r", result)

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
