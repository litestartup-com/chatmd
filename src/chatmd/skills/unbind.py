"""Unbind skill — /unbind removes a Bot repo binding (T-R083 / T-126).

Three usage modes:

- ``/unbind`` (no args) — figure out which binding belongs to THIS
  workspace (by matching the masked ``git remote origin`` against the
  server's binding list) and remove it. The most ergonomic mode for
  users who think in terms of "disconnect this notebook from the bot".
- ``/unbind <alias>`` — remove the binding addressed by alias. The alias
  can be either the user-supplied ``repo_alias`` or the server's
  synthesised ``effective_alias`` for legacy NULL rows (T-125).
- ``/unbind --all`` — wipe every binding visible to the current LS user.
  The server collapses the audit trail into a single ``EVENT_UNBIND_ALL``
  composite event so PO can grep for the wipe in one shot.

When the active binding is removed (single-alias mode), the server
atomically promotes the next survivor; we surface the new active alias
in the success output so the user immediately knows what ``/use``
defaults to from Telegram.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.infra.git_utils import (
    get_git_remote_url,
    mask_repo_url,
    ssh_to_https,
    strip_url_credentials,
)
from chatmd.skills.base import Skill, SkillResult

if TYPE_CHECKING:
    from chatmd.providers.litestartup import LiteStartupProvider
    from chatmd.skills.base import SkillContext

logger = logging.getLogger(__name__)


class UnbindSkill(Skill):
    """Remove one or all Telegram Bot repo bindings.

    Provider-backed via ``LiteStartupProvider.bind_unbind``. The skill
    layer adds the workspace-aware default routing and translates
    server error codes into i18n-keyed user-facing messages.
    """

    name = "unbind"
    description = "unbind"
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
        """Rich help text for /help unbind."""
        return t("skill.unbind.help_text")

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        """Dispatch /unbind to one of three handlers based on input.

        The dispatch order (--all → alias → workspace) is deliberate:
        we recognise the ``--all`` / ``-a`` flag first so that an alias
        named "--all" can never be created (the server-side flow
        normally rejects it on alias validation, but this guards
        defence-in-depth on the client too).
        """
        if not self._provider:
            return SkillResult(
                success=False, output="",
                error=t("error.bind_no_provider"),
            )

        arg = input_text.strip()
        if arg in ("--all", "-a"):
            return self._unbind_all()
        if arg:
            return self._unbind_by_alias(arg)
        return self._unbind_current_workspace(context)

    # -- Mode handlers -------------------------------------------------------

    def _unbind_all(self) -> SkillResult:
        """Wipe every binding for the current LS user (telegram)."""
        assert self._provider is not None
        result = self._provider.bind_unbind(all=True, platform="telegram")
        if not result.get("success"):
            return self._unbind_error(result)

        deleted_count = result.get("deleted_count", 0)
        if deleted_count == 0:
            return SkillResult(
                success=True,
                output=t("output.unbind.all_empty"),
                informational=True,
            )

        # Build a friendly summary listing the deleted aliases. Prefer
        # `effective_alias` (server-side T-125 synthesised) so legacy
        # NULL rows still render a usable name in the audit summary.
        aliases: list[str] = []
        for row in result.get("deleted", []):
            alias = (
                row.get("effective_alias")
                or row.get("repo_alias")
                or "?"
            )
            aliases.append(f"`{alias}`")

        return SkillResult(
            success=True,
            output=t(
                "output.unbind.all_success",
                count=deleted_count,
                aliases=", ".join(aliases),
            ),
            informational=True,
        )

    def _unbind_by_alias(self, alias: str) -> SkillResult:
        """Remove the binding addressed by alias."""
        assert self._provider is not None
        result = self._provider.bind_unbind(alias=alias, platform="telegram")
        if not result.get("success"):
            return self._unbind_error(result, alias=alias)
        return self._format_single_success(result, alias)

    def _unbind_current_workspace(self, context: SkillContext) -> SkillResult:
        """Default mode: derive alias from the current workspace remote.

        Steps:
        1. Read ``git remote origin`` for the workspace.
        2. Mask it with the same rule as LS server-side ``maskRepoUrl``.
        3. Fetch the binding list and find the row whose
           ``repo_url_masked`` equals the workspace masked URL.
        4. Use that row's alias (``repo_alias`` or ``effective_alias``)
           to call ``provider.bind_unbind``.

        Each step has a deliberate error path with a distinct i18n key
        so users see actionable guidance ("run /bind status first")
        rather than a generic "not found".
        """
        assert self._provider is not None
        raw_url = get_git_remote_url(context.workspace)
        if not raw_url:
            return SkillResult(
                success=False, output="",
                error=t("error.bind_no_remote"),
            )

        try:
            current_masked = mask_repo_url(
                strip_url_credentials(ssh_to_https(raw_url)),
            )
        except Exception:  # noqa: BLE001
            current_masked = ""

        if not current_masked:
            return SkillResult(
                success=False, output="",
                error=t("error.unbind_no_workspace_match", url=raw_url),
            )

        # Pre-fetch the list to translate workspace -> alias. We could
        # add a server-side `unbind by repo_url` endpoint, but reusing
        # the existing list+unbind pair keeps the API surface lean and
        # the client can also surface the matched alias in the success
        # message ("Unbound `<alias>`") without a second round-trip.
        list_result = self._provider.bind_list(platform="telegram")
        if not list_result.get("success"):
            return self._list_error(list_result)

        match: dict | None = None
        for repo in list_result.get("repos", []):
            if repo.get("repo_url_masked") == current_masked:
                match = repo
                break

        if not match:
            return SkillResult(
                success=False, output="",
                error=t("error.unbind_no_workspace_match", url=current_masked),
            )

        alias = match.get("repo_alias") or match.get("effective_alias") or ""
        if not alias:
            # Should be impossible post-T-125 (effective_alias guaranteed
            # non-empty by the server). Keep this branch as a defensive
            # fallback for older LS deployments without the T-125 fix.
            return SkillResult(
                success=False, output="",
                error=t("error.unbind_no_addressable_alias"),
            )

        result = self._provider.bind_unbind(alias=alias, platform="telegram")
        if not result.get("success"):
            return self._unbind_error(result, alias=alias)
        return self._format_single_success(result, alias)

    # -- Output formatters ---------------------------------------------------

    def _format_single_success(self, result: dict, alias: str) -> SkillResult:
        """Render a markdown body for a successful single-alias unbind."""
        remaining = result.get("remaining_count", 0)
        new_active = result.get("new_active")

        lines = [t("output.unbind.success", alias=alias, remaining=remaining)]

        if isinstance(new_active, dict):
            new_alias = (
                new_active.get("effective_alias")
                or new_active.get("repo_alias")
                or "?"
            )
            lines.append("")
            lines.append(t("output.unbind.new_active", alias=new_alias))

        return SkillResult(
            success=True,
            output="\n".join(lines),
            informational=True,
        )

    def _unbind_error(self, result: dict, alias: str = "") -> SkillResult:
        """Render an error envelope from ``provider.bind_unbind``."""
        error_code = result.get("code")
        error_msg = result.get("error", "")

        # Error code 4040 = alias not in caller's scope (T-122 contract).
        # We never leak whether someone else owns the alias, just say
        # "not found" -- the server already enforces this.
        if error_code == 4040:
            if alias:
                user_msg = t("error.unbind_alias_not_found", alias=alias)
            else:
                user_msg = t("error.unbind_alias_not_found_generic")
        elif error_code == 2001:
            user_msg = t("error.bind_unauthorized")
        elif error_code == 3001:
            user_msg = t("error.bind_rate_limited")
        elif error_msg:
            code_suffix = f" [code={error_code}]" if error_code else ""
            user_msg = t("error.unbind_failed", detail=error_msg) + code_suffix
        else:
            user_msg = t("error.unbind_failed", detail="(no detail)")

        return SkillResult(success=False, output="", error=user_msg)

    def _list_error(self, result: dict) -> SkillResult:
        """Render an error from the pre-unbind ``provider.bind_list`` call."""
        error_code = result.get("code")
        error_msg = result.get("error", "")

        if error_code == 2001:
            return SkillResult(
                success=False, output="",
                error=t("error.bind_unauthorized"),
            )
        if error_code == 3001:
            return SkillResult(
                success=False, output="",
                error=t("error.bind_rate_limited"),
            )

        code_suffix = f" [code={error_code}]" if error_code else ""
        detail = error_msg or "(no detail)"
        return SkillResult(
            success=False, output="",
            error=t("error.bind_list_failed", detail=detail) + code_suffix,
        )
