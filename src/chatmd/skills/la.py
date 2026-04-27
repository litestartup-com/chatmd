"""/la skill — passthrough to LiteStartup /ai/chat + destructive Phase-2 confirm.

Reuses the shared ``LiteStartupProvider`` (loaded from ``ai.providers[]`` in
``agent.yaml``) for ``api_base`` / ``api_key`` / ``timeout`` / auth headers —
same pattern as :class:`BindSkill`, :class:`UploadSkill`, :class:`NotifySkill`.
No separate ``.env`` or env-var lookup; if users configure LiteStartup via
``agent.yaml`` they get ``/la`` for free.

Three invocation forms — two hit ``/ai/chat``, one hits ``/ai/plans/confirm``:

  * ``/la newsletter.list {}``           — hardcoded smoke backdoor (no LA needed)
  * ``/la 给我看最新 newsletter``          — natural-language (LA LLM maps to tool)
  * ``/la confirm cft_<32 hex>``         — Phase-2 confirmation of a destructive
                                           plan issued in a previous ``/la`` turn
                                           (T-MVP03-M2 · LAD RULE §R2.2 / §R4)

Renders ``data.rendered`` (set by LS ``ToolExecutionService``) as the skill
body plus an optional debug footnote with ``tool`` / ``plan_id``. For
``destructive`` tools, LS Phase-1 returns ``confirm_required: true`` + a
``cft_`` token + a pre-rendered confirmation card instead of executing;
ChatMD surfaces that envelope to the user and waits for ``/la confirm ...``.

Technical debt: Q-LAD-4 resolution_note (plan C') calls for ChatMD Phase 2 to
extend YAMLSkill with a declarative HTTP handler. When that lands, this
Python plugin can be deleted and replaced by ``skills/la.yaml`` (~15 min).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import httpx

from chatmd.i18n import t
from chatmd.providers.litestartup import _mask_token
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.providers.litestartup import LiteStartupProvider

logger = logging.getLogger(__name__)

# Valid confirm_token shape per LAD RULE §R7: ``cft_`` + 32 lowercase hex.
_CONFIRM_TOKEN_RE = re.compile(r"^cft_[0-9a-f]{32}$")

# ``confirm <anything>`` dispatch — grab any non-whitespace as candidate
# token, then validate against _CONFIRM_TOKEN_RE to give a precise error
# when the format is wrong (short-circuit before any network call).
_CONFIRM_DISPATCH_RE = re.compile(r"^\s*confirm\s+(\S+)\s*$", re.IGNORECASE)

# LS confirm-plan error code -> i18n key. Codes not listed fall through to
# ``la.confirm.generic``. See LAD RULE §R8 + LS AiApiController::confirmPlan.
_CONFIRM_ERROR_I18N: dict[int, str] = {
    400: "la.confirm.bad_token",
    403: "la.confirm.forbidden",
    404: "la.confirm.not_found",
    409: "la.confirm.consumed",
    410: "la.confirm.expired",
}


class LaSkill(Skill):
    """Invoke a LiteStartup-exposed tool via the LAP ``/ai/chat`` endpoint.

    The skill is deliberately dumb — it does not parse tool names, schemas,
    or OpenAPI spec. ChatMD stays a pure passthrough UI layer; tool mapping
    happens in LS + LA. See
    ``app/liteadapter/docs/mvp/ARCHITECTURE_RATIONALE.md`` §2.

    The one exception is the ``confirm <cft_token>`` sub-command introduced in
    T-MVP03-M2 to support the destructive two-phase flow (LAD RULE §R2.2):

      * First user turn  · ``/la 删除客户 #42``           → LS returns
        ``confirm_required:true`` + ``cft_xxx`` + pre-rendered card.
      * Second user turn · ``/la confirm cft_xxx``        → LS consumes the
        token from ``os_tool_plans`` (single-use) and executes the plan.

    The dispatch here is intentionally minimal: a regex matches the
    ``confirm <token>`` prefix before any network call, and token format
    validation (``cft_`` + 32 hex, total length 36) short-circuits invalid
    input without touching LS.
    """

    name = "la"
    description = "Call a LiteStartup AI tool via LAP (passthrough to /ai/chat)"
    category = "integration"
    requires_network = True
    aliases: list[str] = []

    def __init__(self, provider: LiteStartupProvider | None = None) -> None:
        self._provider = provider

    def set_provider(self, provider: LiteStartupProvider) -> None:
        """Inject the LiteStartup provider after construction."""
        self._provider = provider

    def execute(
        self, input_text: str, args: dict, context: SkillContext,
    ) -> SkillResult:
        provider = self._provider
        if provider is None or not provider.api_base or not provider.api_key:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "LiteStartup provider is not configured. Add an "
                    "`ai.providers[]` entry with `type: litestartup` + "
                    "`api_url` + `api_key` to `.chatmd/agent.yaml`."
                ),
                informational=True,
            )

        raw = input_text.strip()

        # Branch A · Phase-2 confirmation: ``confirm cft_<token>``.
        confirm_match = _CONFIRM_DISPATCH_RE.match(raw)
        if confirm_match:
            return self._execute_confirm(provider, confirm_match.group(1))

        # Branch B · Phase-1 tool invoke (passthrough to /ai/chat).
        return self._execute_phase1(provider, raw)

    # ------------------------------------------------------------------
    # Phase-1 ("/la <tool>" or "/la <NL>") — unchanged behavior plus new
    # detection of the ``confirm_required`` envelope emitted by LS
    # ToolExecutionService when a destructive plan needs user review.
    # ------------------------------------------------------------------

    def _execute_phase1(
        self, provider: LiteStartupProvider, raw: str,
    ) -> SkillResult:
        # Preserve the "/la " prefix so LS segment a (AiApiController) routes
        # to the tool_invoke branch instead of plain chat.
        prompt = f"/la {raw}" if raw else "/la"

        endpoint = provider.endpoint("chat")
        try:
            resp = httpx.post(
                endpoint,
                headers=provider.auth_headers(),
                json={"prompt": prompt},
                timeout=provider.timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("/la HTTP error calling %s: %s", endpoint, exc)
            return SkillResult(
                success=False,
                output="",
                error=f"HTTP error calling LiteStartup: {exc}",
            )

        try:
            payload: dict[str, Any] = resp.json() or {}
        except ValueError:
            return SkillResult(
                success=False,
                output="",
                error=(
                    f"LiteStartup returned non-JSON "
                    f"(status={resp.status_code}): {resp.text[:200]}"
                ),
            )

        data: dict[str, Any] = payload.get("data") or {}
        rendered = str(data.get("rendered") or "").strip()
        typ = data.get("type")

        # Error path: non-200 HTTP or server-reported error type.
        if resp.status_code != 200 or typ == "error":
            msg = (
                payload.get("message")
                or data.get("message")
                or "unknown error"
            )
            err_code = (
                data.get("code") or payload.get("code") or resp.status_code
            )
            return SkillResult(
                success=False,
                output="",
                error=f"LiteStartup error [{err_code}]: {msg}",
            )

        # T-MVP03-M2 · destructive two-phase confirm detection. LS sets
        # both ``confirm_required:true`` and ``type:"confirm_required"`` in
        # the envelope; check either for robustness against future field
        # renames (runtime wins per LAD RULE R1).
        if data.get("confirm_required") is True or typ == "confirm_required":
            return self._render_confirm_card(data, rendered)

        # Success path: body is data.rendered + optional debug footnote.
        output = rendered or "_(empty response from /la)_"

        debug_bits: list[str] = []
        tool = data.get("tool")
        plan_id = data.get("plan_id")
        if tool:
            debug_bits.append(f"tool: `{tool}`")
        if plan_id:
            debug_bits.append(f"plan: `{plan_id}`")
        if debug_bits:
            output = output + "\n\n> " + " · ".join(debug_bits)

        return SkillResult(
            success=True,
            output=output,
            metadata={
                "tool": tool,
                "plan_id": plan_id,
                "type": typ,
                "adapter_version": data.get("adapter_version"),
            },
        )

    # ------------------------------------------------------------------
    # Phase-2 confirmation (``/la confirm cft_<token>``) — hits the
    # dedicated ``/ai/plans/confirm`` endpoint via provider.confirm_plan().
    # ------------------------------------------------------------------

    def _execute_confirm(
        self, provider: LiteStartupProvider, token_input: str,
    ) -> SkillResult:
        token = token_input.strip()

        # Fast path: reject malformed tokens locally so we don't leak user
        # input or hammer LS with obviously invalid requests.
        if not _CONFIRM_TOKEN_RE.match(token):
            logger.info(
                "/la confirm: rejected malformed token (len=%d, starts=%r)",
                len(token),
                token[:4],
            )
            return SkillResult(
                success=False,
                output="",
                error=t("la.confirm.bad_token"),
                informational=True,
            )

        logger.info("/la confirm: token=%s", _mask_token(token))
        result = provider.confirm_plan(token)

        if result.get("success"):
            rendered = str(result.get("rendered") or "").strip()
            tool = str(result.get("tool") or "")
            output = rendered or "_(empty response from /la confirm)_"

            debug_bits: list[str] = []
            if tool:
                debug_bits.append(f"tool: `{tool}`")
            debug_bits.append(f"confirm: `{_mask_token(token)}`")
            output = output + "\n\n> " + " · ".join(debug_bits)

            logger.info(
                "/la confirm succeeded: tool=%s token=%s",
                tool or "<unknown>",
                _mask_token(token),
            )
            return SkillResult(
                success=True,
                output=output,
                metadata={
                    "tool": tool,
                    "confirm_token_masked": _mask_token(token),
                },
            )

        # Failure · map LS numeric code to an i18n key; ``la.confirm.generic``
        # is the catch-all and receives ``{message}`` placeholder.
        code = int(result.get("code") or 0)
        key = _CONFIRM_ERROR_I18N.get(code, "la.confirm.generic")
        raw_err = str(result.get("error") or "")
        localized = (
            t(key, message=raw_err) if key == "la.confirm.generic" else t(key)
        )
        logger.warning(
            "/la confirm failed: code=%s token=%s",
            code,
            _mask_token(token),
        )
        return SkillResult(
            success=False,
            output="",
            error=localized,
            informational=True,
        )

    # ------------------------------------------------------------------
    # Destructive confirmation card (Phase-1 response renderer). Shown to
    # the user when LS returns ``confirm_required:true``; the card must
    # surface (a) WHAT will happen (``rendered``), (b) the exact token to
    # copy back, and (c) the TTL so the user knows the window.
    # ------------------------------------------------------------------

    def _render_confirm_card(
        self, data: dict[str, Any], rendered: str,
    ) -> SkillResult:
        token = str(data.get("confirm_token") or "")
        tool = str(data.get("tool") or "")
        expires_at = str(data.get("expires_at") or "")

        header = t("la.confirm.card_header")
        hint = t("la.confirm.card_hint", token=token)

        body_lines: list[str] = [f"⚠️ **{header}**", ""]
        if rendered:
            body_lines.append(rendered)
            body_lines.append("")
        if tool:
            body_lines.append(f"- tool: `{tool}`")
        body_lines.append(f"- confirm_token: `{token}`")
        if expires_at:
            body_lines.append(f"- expires_at: {expires_at}")
        body_lines.append("")
        body_lines.append(hint)

        logger.info(
            "/la phase-1 confirm_required: tool=%s token=%s",
            tool or "<unknown>",
            _mask_token(token),
        )
        return SkillResult(
            success=True,
            output="\n".join(body_lines),
            metadata={
                "tool": tool,
                "type": "confirm_required",
                "confirm_required": True,
                "confirm_token_masked": _mask_token(token),
                "expires_at": expires_at or None,
            },
        )
