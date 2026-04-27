"""Tests for chatmd.skills.la — /la passthrough to LS /ai/chat (T-MVP01 段 c)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from chatmd.skills.base import SkillContext
from chatmd.skills.la import LaSkill


@pytest.fixture()
def context(tmp_path: Path) -> SkillContext:
    return SkillContext(
        source_file=tmp_path / "chat.md",
        source_line=1,
        workspace=tmp_path,
    )


def _mock_provider(
    api_base: str = "https://api.litestartup.example",
    api_key: str = "sk-test-xyz",
    timeout: int = 30,
) -> MagicMock:
    """Shape-compatible mock of LiteStartupProvider."""
    provider = MagicMock()
    provider.api_base = api_base
    provider.api_key = api_key
    provider.timeout = timeout
    provider.endpoint.return_value = f"{api_base}/client/v2/ai/chat"
    provider.auth_headers.return_value = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return provider


@pytest.fixture()
def provider() -> MagicMock:
    return _mock_provider()


class TestLaSkillMetadata:
    def test_name_and_flags(self) -> None:
        skill = LaSkill()
        assert skill.name == "la"
        assert skill.category == "integration"
        assert skill.requires_network is True


class TestLaSkillConfigErrors:
    def test_missing_provider(self, context: SkillContext) -> None:
        skill = LaSkill(provider=None)
        result = skill.execute("newsletter.list {}", {}, context)
        assert result.success is False
        assert result.informational is True
        assert result.error is not None
        assert "agent.yaml" in result.error

    def test_missing_api_key(self, context: SkillContext) -> None:
        prov = _mock_provider(api_key="")
        skill = LaSkill(provider=prov)
        result = skill.execute("newsletter.list {}", {}, context)
        assert result.success is False
        assert result.informational is True

    def test_missing_api_base(self, context: SkillContext) -> None:
        prov = _mock_provider(api_base="")
        skill = LaSkill(provider=prov)
        result = skill.execute("newsletter.list {}", {}, context)
        assert result.success is False
        assert result.informational is True

    def test_set_provider_after_construction(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        skill = LaSkill(provider=None)
        # Initially unconfigured
        r1 = skill.execute("x", {}, context)
        assert r1.success is False and r1.informational is True
        # After injection it works
        skill.set_provider(provider)

        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                200,
                json={"code": 200, "data": {"type": "text", "rendered": "ok"}},
            )
        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            r2 = skill.execute("x", {}, context)
        assert r2.success is True


class TestLaSkillHappyPath:
    def test_smoke_backdoor_hardcoded(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Smoke a: `/la newsletter.list {}` — LS bypasses LA."""
        captured: dict = {}

        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            captured["timeout"] = timeout
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "message": "Success",
                    "data": {
                        "mode": "tool_invoke",
                        "type": "plan",
                        "plan_id": "pln_abc123",
                        "tool": "newsletter.list",
                        "params": {},
                        "rendered": "- N1 (published)\n- N2 (draft)",
                        "adapter_version": "v0.2",
                    },
                },
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "newsletter.list {}", {}, context,
            )

        assert result.success is True
        assert "- N1 (published)" in result.output
        assert "- N2 (draft)" in result.output
        # Debug footer shows tool + plan_id
        assert "newsletter.list" in result.output
        assert "pln_abc123" in result.output

        # URL from provider.endpoint("chat") — reuses agent.yaml config
        assert captured["url"] == (
            "https://api.litestartup.example/client/v2/ai/chat"
        )
        # Auth via provider.auth_headers() — Bearer, same as other skills
        assert captured["headers"]["Authorization"] == "Bearer sk-test-xyz"
        assert captured["headers"]["Content-Type"] == "application/json"
        # Preserves `/la` prefix in body — LS needs it to dispatch
        assert captured["json"] == {"prompt": "/la newsletter.list {}"}
        # Timeout from provider
        assert captured["timeout"] == 30
        # Metadata
        assert result.metadata is not None
        assert result.metadata["tool"] == "newsletter.list"
        assert result.metadata["plan_id"] == "pln_abc123"

        # Verified we called the provider helpers (not raw os.environ)
        provider.endpoint.assert_called_once_with("chat")
        provider.auth_headers.assert_called_once()

    def test_natural_language_prompt(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Smoke b: `/la 给我看最新 newsletter` — LA maps NL to tool."""
        captured: dict = {}

        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            captured["json"] = json
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "type": "plan",
                        "plan_id": "pln_nl_1",
                        "tool": "newsletter.list",
                        "rendered": "- 最新 newsletter · 一条",
                    },
                },
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "给我看最新 newsletter", {}, context,
            )

        assert result.success is True
        assert "最新 newsletter" in result.output
        assert captured["json"] == {"prompt": "/la 给我看最新 newsletter"}


class TestLaSkillErrorPaths:
    def test_http_non_200(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                401,
                json={"code": 401, "message": "Invalid API key"},
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "newsletter.list {}", {}, context,
            )

        assert result.success is False
        assert result.error is not None
        assert "401" in result.error
        assert "Invalid API key" in result.error

    def test_server_reported_error_type(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "type": "error",
                        "code": "tool_not_found",
                        "message": "unknown tool: bogus.x",
                    },
                },
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "bogus.x {}", {}, context,
            )

        assert result.success is False
        assert result.error is not None
        assert "tool_not_found" in result.error
        assert "bogus.x" in result.error

    def test_network_failure(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            raise httpx.ConnectError("connection refused")

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "newsletter.list {}", {}, context,
            )

        assert result.success is False
        assert result.error is not None
        assert "connection refused" in result.error

    def test_non_json_response(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            return httpx.Response(500, text="<html>502 Bad Gateway</html>")

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "newsletter.list {}", {}, context,
            )

        assert result.success is False
        assert result.error is not None
        # Either the JSON-parse branch or the non-200 branch reports it.
        assert "500" in result.error or "non-JSON" in result.error


class TestLaSkillEdgeCases:
    def test_empty_input_still_sends_la_prefix(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        captured: dict = {}

        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            captured["json"] = json
            return httpx.Response(
                200,
                json={"code": 200, "data": {"type": "text", "rendered": "help"}},
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute("", {}, context)

        assert result.success is True
        assert captured["json"] == {"prompt": "/la"}

    def test_legacy_api_url_still_works(
        self, context: SkillContext,
    ) -> None:
        """Provider built from legacy ``api_url`` form (agent.yaml pattern)."""
        # Mirrors: create_litestartup_provider({"api_url":
        # "https://api.litestartup.com/client/v2/ai/chat", "api_key": "..."})
        prov = _mock_provider(api_base="https://api.litestartup.com")
        captured: dict = {}

        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            captured["url"] = url
            return httpx.Response(
                200,
                json={"code": 200, "data": {"type": "text", "rendered": "ok"}},
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            LaSkill(provider=prov).execute("x", {}, context)

        # api_base (no trailing slash) + /client/v2/ai/chat
        assert captured["url"] == "https://api.litestartup.com/client/v2/ai/chat"


# ========== T-MVP03-M2 · destructive Phase-2 confirm UX ==========


_VALID_TOKEN = "cft_" + "a" * 32  # shape-valid per LAD §R7


class TestLaSkillConfirmRequired:
    """Phase-1 envelope with ``confirm_required:true`` renders a card."""

    def test_card_contains_token_tool_and_hint(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "message": "Success",
                    "data": {
                        "mode": "tool_invoke",
                        "type": "confirm_required",
                        "tool": "contact.delete",
                        "params": {"id": 42},
                        "plan_id": "pln_abc",
                        "rendered": "Will delete contact Alice (#42)",
                        "confirm_required": True,
                        "confirm_token": _VALID_TOKEN,
                        "expires_at": "2026-04-26T00:45:00Z",
                        "adapter_version": "v0.3",
                    },
                },
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "删除联系人 #42", {}, context,
            )

        assert result.success is True
        assert result.output.startswith("⚠️")
        # Card surfaces WHAT (rendered) + tool + token + expires_at + hint
        assert "Will delete contact Alice (#42)" in result.output
        assert "`contact.delete`" in result.output
        assert _VALID_TOKEN in result.output
        assert "2026-04-26T00:45:00Z" in result.output
        assert "/la confirm" in result.output
        # Metadata reports confirm_required + masked token
        assert result.metadata is not None
        assert result.metadata["confirm_required"] is True
        assert result.metadata["type"] == "confirm_required"
        assert result.metadata["confirm_token_masked"] == "cft_aaaa…"

    def test_confirm_required_flag_alone_also_triggers_card(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Robustness: even if ``type`` is plain ``plan``, the boolean flag
        ``confirm_required: true`` is enough to render the card (LAD R1 —
        runtime wins, so we must not depend on a single field)."""
        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "type": "plan",
                        "tool": "email.delete",
                        "rendered": "Delete email 'Subject X'",
                        "confirm_required": True,
                        "confirm_token": _VALID_TOKEN,
                        "expires_at": "2026-04-26T00:45:00Z",
                    },
                },
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "删除邮件", {}, context,
            )

        assert result.success is True
        assert "Subject X" in result.output
        assert _VALID_TOKEN in result.output


class TestLaSkillConfirmDispatch:
    """``/la confirm cft_<token>`` hits provider.confirm_plan, not /ai/chat."""

    def test_bad_token_format_short_circuits(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Malformed token must NOT reach the network or provider."""
        from chatmd.i18n import t

        with patch("chatmd.skills.la.httpx.post") as mock_post:
            result = LaSkill(provider=provider).execute(
                "confirm cft_tooshort", {}, context,
            )

        assert result.success is False
        assert result.informational is True
        assert result.error == t("la.confirm.bad_token")
        # Critical: no network call, no provider.confirm_plan call
        mock_post.assert_not_called()
        provider.confirm_plan.assert_not_called()

    def test_valid_token_calls_provider_confirm_plan(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        provider.confirm_plan.return_value = {
            "success": True,
            "tool": "contact.delete",
            "rendered": "Deleted contact Alice.",
            "data": {"id": 42},
        }

        with patch("chatmd.skills.la.httpx.post") as mock_post:
            result = LaSkill(provider=provider).execute(
                f"confirm {_VALID_TOKEN}", {}, context,
            )

        # Phase-2 does NOT go through /ai/chat
        mock_post.assert_not_called()
        # Provider receives the exact token string
        provider.confirm_plan.assert_called_once_with(_VALID_TOKEN)
        assert result.success is True
        assert "Deleted contact Alice." in result.output
        assert "`contact.delete`" in result.output
        # Metadata masks the token for audit
        assert result.metadata is not None
        assert result.metadata["confirm_token_masked"] == "cft_aaaa…"

    def test_confirm_uppercase_dispatch_word_still_matches(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Dispatch regex is case-insensitive — `Confirm <token>` also works."""
        provider.confirm_plan.return_value = {
            "success": True,
            "tool": "x",
            "rendered": "ok",
            "data": {},
        }
        with patch("chatmd.skills.la.httpx.post"):
            result = LaSkill(provider=provider).execute(
                f"Confirm {_VALID_TOKEN}", {}, context,
            )

        provider.confirm_plan.assert_called_once_with(_VALID_TOKEN)
        assert result.success is True


class TestLaSkillConfirmErrorCodes:
    """LS numeric code from confirm_plan → i18n key per LAD §R8 matrix."""

    @pytest.fixture()
    def _provider_with_error(self, provider: MagicMock):  # noqa: ANN202
        def _set(code: int, err: str = "error from LS"):
            provider.confirm_plan.return_value = {
                "success": False,
                "error": err,
                "code": code,
            }
            return provider
        return _set

    def test_code_404_uses_not_found_key(
        self, context: SkillContext, _provider_with_error,  # noqa: ANN001
    ) -> None:
        from chatmd.i18n import t

        prov = _provider_with_error(404)
        result = LaSkill(provider=prov).execute(
            f"confirm {_VALID_TOKEN}", {}, context,
        )
        assert result.success is False
        assert result.informational is True
        assert result.error == t("la.confirm.not_found")

    def test_code_403_uses_forbidden_key(
        self, context: SkillContext, _provider_with_error,  # noqa: ANN001
    ) -> None:
        from chatmd.i18n import t

        prov = _provider_with_error(403)
        result = LaSkill(provider=prov).execute(
            f"confirm {_VALID_TOKEN}", {}, context,
        )
        assert result.error == t("la.confirm.forbidden")

    def test_code_409_uses_consumed_key(
        self, context: SkillContext, _provider_with_error,  # noqa: ANN001
    ) -> None:
        from chatmd.i18n import t

        prov = _provider_with_error(409)
        result = LaSkill(provider=prov).execute(
            f"confirm {_VALID_TOKEN}", {}, context,
        )
        assert result.error == t("la.confirm.consumed")

    def test_code_410_uses_expired_key(
        self, context: SkillContext, _provider_with_error,  # noqa: ANN001
    ) -> None:
        from chatmd.i18n import t

        prov = _provider_with_error(410)
        result = LaSkill(provider=prov).execute(
            f"confirm {_VALID_TOKEN}", {}, context,
        )
        assert result.error == t("la.confirm.expired")

    def test_unknown_code_uses_generic_with_message(
        self, context: SkillContext, _provider_with_error,  # noqa: ANN001
    ) -> None:
        from chatmd.i18n import t

        prov = _provider_with_error(500, err="internal boom")
        result = LaSkill(provider=prov).execute(
            f"confirm {_VALID_TOKEN}", {}, context,
        )
        # Generic key takes a {message} placeholder
        expected = t("la.confirm.generic", message="internal boom")
        assert result.error == expected
        assert "internal boom" in result.error


class TestLaSkillTokenMasking:
    """Logs and metadata never contain the full confirm_token (§9 risk)."""

    def test_logger_does_not_leak_full_token(
        self,
        context: SkillContext,
        provider: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Phase-2 confirm log entries must be truncated."""
        import logging as _logging

        provider.confirm_plan.return_value = {
            "success": True,
            "tool": "x",
            "rendered": "ok",
            "data": {},
        }
        with caplog.at_level(_logging.INFO, logger="chatmd.skills.la"):
            LaSkill(provider=provider).execute(
                f"confirm {_VALID_TOKEN}", {}, context,
            )

        all_messages = " ".join(r.getMessage() for r in caplog.records)
        # Masked form must appear; full token must not
        assert "cft_aaaa…" in all_messages
        assert _VALID_TOKEN not in all_messages

    def test_confirm_card_metadata_has_masked_token_only(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Phase-1 card metadata must not leak full token via logs."""
        def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "type": "confirm_required",
                        "tool": "contact.delete",
                        "rendered": "x",
                        "confirm_required": True,
                        "confirm_token": _VALID_TOKEN,
                    },
                },
            )

        with patch("chatmd.skills.la.httpx.post", side_effect=fake_post):
            result = LaSkill(provider=provider).execute(
                "删除客户", {}, context,
            )

        assert result.metadata is not None
        assert result.metadata["confirm_token_masked"] == "cft_aaaa…"
        # Output still contains full token (user needs to copy it)
        # but metadata — which is logged / persisted — never has it.
        assert _VALID_TOKEN in result.output
        # No metadata key is equal to the full token
        for v in result.metadata.values():
            assert v != _VALID_TOKEN
