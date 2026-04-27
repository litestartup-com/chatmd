"""Tests for LiteStartupProvider — unified API abstraction for LiteStartup services."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from chatmd.providers.litestartup import LiteStartupProvider, create_litestartup_provider

# ========== Initialization ==========


class TestLiteStartupProviderInit:
    def test_defaults(self):
        p = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
        )
        assert p.api_base == "https://api.litestartup.com"
        assert p.api_key == "sk-test"
        assert p.timeout == 60

    def test_custom_timeout(self):
        p = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
            timeout=120,
        )
        assert p.timeout == 120

    def test_trailing_slash_stripped(self):
        p = LiteStartupProvider(
            api_base="https://api.litestartup.com/",
            api_key="sk-test",
        )
        assert p.api_base == "https://api.litestartup.com"


# ========== Endpoint URL building ==========


class TestEndpointUrl:
    def test_chat_endpoint(self):
        p = LiteStartupProvider("https://api.litestartup.com", "k")
        assert p.endpoint("chat") == "https://api.litestartup.com/client/v2/ai/chat"

    def test_upload_endpoint(self):
        p = LiteStartupProvider("https://api.litestartup.com", "k")
        assert p.endpoint("upload") == "https://api.litestartup.com/client/v2/storage/upload"

    def test_publish_endpoint(self):
        p = LiteStartupProvider("https://api.litestartup.com", "k")
        assert p.endpoint("publish") == "https://api.litestartup.com/client/v2/publish"

    def test_unknown_endpoint_raises(self):
        p = LiteStartupProvider("https://api.litestartup.com", "k")
        with pytest.raises(ValueError, match="Unknown endpoint"):
            p.endpoint("unknown_service")

    def test_custom_endpoint_override(self):
        p = LiteStartupProvider(
            "https://api.litestartup.com",
            "k",
            endpoints={"chat": "/custom/ai/chat"},
        )
        assert p.endpoint("chat") == "https://api.litestartup.com/custom/ai/chat"

    def test_auth_headers(self):
        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        headers = p.auth_headers()
        assert headers["Authorization"] == "Bearer sk-test"
        assert headers["Content-Type"] == "application/json"


# ========== Upload ==========


class TestUpload:
    @patch("chatmd.providers.litestartup.httpx.post")
    def test_upload_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "code": 201,
            "message": "File uploaded successfully",
            "data": {"publicUrl": "https://cdn.litestartup.com/img/abc.png"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.upload(Path(__file__))  # upload this test file itself

        assert result["success"] is True
        assert result["url"] == "https://cdn.litestartup.com/img/abc.png"
        call_kwargs = mock_post.call_args
        has_files = (
            "files" in call_kwargs.kwargs
            or "files" in (call_kwargs[1] if len(call_kwargs) > 1 else {})
        )
        assert has_files

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_upload_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "code": 400,
            "message": "File too large",
            "data": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.upload(Path(__file__))

        assert result["success"] is False
        assert "File too large" in result["error"]

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_upload_http_error(self, mock_post):
        resp = httpx.Response(500, request=httpx.Request("POST", "u"))
        mock_post.side_effect = httpx.HTTPStatusError(
            "", request=resp.request, response=resp,
        )

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.upload(Path(__file__))

        assert result["success"] is False
        assert "HTTP 500" in result["error"]

    def test_upload_file_not_found(self):
        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.upload(Path("/nonexistent/file.png"))

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_upload_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timeout")

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.upload(Path(__file__))

        assert result["success"] is False
        assert "timeout" in result["error"].lower()


# ========== Publish ==========


class TestPublish:
    @patch("chatmd.providers.litestartup.httpx.post")
    def test_publish_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "url": "https://litestartup.com/p/abc123",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.publish(
            html_content="<h1>Hello</h1>",
            title="Test Page",
        )

        assert result["success"] is True
        assert result["url"] == "https://litestartup.com/p/abc123"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["html"] == "<h1>Hello</h1>"
        assert payload["title"] == "Test Page"

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_publish_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": False,
            "message": "Content too long",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.publish(html_content="<h1>X</h1>", title="T")

        assert result["success"] is False
        assert "Content too long" in result["error"]

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_publish_http_error(self, mock_post):
        resp = httpx.Response(401, request=httpx.Request("POST", "u"))
        mock_post.side_effect = httpx.HTTPStatusError(
            "", request=resp.request, response=resp,
        )

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.publish(html_content="<h1>X</h1>", title="T")

        assert result["success"] is False
        assert "HTTP 401" in result["error"]


# ========== Factory / backward compat ==========


class TestCreateFromConfig:
    def test_new_config_format(self):
        """New config with explicit api_base."""
        cfg = {
            "api_base": "https://api.litestartup.com",
            "api_key": "sk-test",
            "timeout": 90,
        }
        p = create_litestartup_provider(cfg)
        assert p.api_base == "https://api.litestartup.com"
        assert p.api_key == "sk-test"
        assert p.timeout == 90

    def test_backward_compat_api_url(self):
        """Old config with api_url (full chat endpoint) should extract api_base."""
        cfg = {
            "api_url": "https://api.litestartup.com/client/v2/ai/chat",
            "api_key": "sk-old",
        }
        p = create_litestartup_provider(cfg)
        assert p.api_base == "https://api.litestartup.com"
        assert p.api_key == "sk-old"

    def test_backward_compat_api_url_custom_domain(self):
        """Old config with custom domain api_url."""
        cfg = {
            "api_url": "https://my-api.example.com/client/v2/ai/chat",
            "api_key": "sk-custom",
        }
        p = create_litestartup_provider(cfg)
        assert p.api_base == "https://my-api.example.com"

    def test_backward_compat_api_url_no_path(self):
        """Old config with api_url that has no recognizable path."""
        cfg = {
            "api_url": "https://api.example.com/some/custom/path",
            "api_key": "sk-x",
        }
        p = create_litestartup_provider(cfg)
        # Should use api_url as-is for api_base (best effort)
        assert p.api_base == "https://api.example.com"

    def test_api_base_takes_precedence(self):
        """If both api_base and api_url are present, api_base wins."""
        cfg = {
            "api_base": "https://new.api.com",
            "api_url": "https://old.api.com/client/v2/ai/chat",
            "api_key": "sk-both",
        }
        p = create_litestartup_provider(cfg)
        assert p.api_base == "https://new.api.com"

    def test_custom_endpoints(self):
        cfg = {
            "api_base": "https://api.litestartup.com",
            "api_key": "sk-test",
            "endpoints": {"chat": "/v3/ai/chat"},
        }
        p = create_litestartup_provider(cfg)
        assert p.endpoint("chat") == "https://api.litestartup.com/v3/ai/chat"
        # Other endpoints use defaults
        assert p.endpoint("upload") == "https://api.litestartup.com/client/v2/storage/upload"

    def test_minimal_config(self):
        cfg = {"api_key": "sk-min"}
        p = create_litestartup_provider(cfg)
        assert p.api_base == ""
        assert p.api_key == "sk-min"


# ========== T-MVP03-M2 · destructive Phase-2 confirm_plan ==========


class TestPlansConfirmEndpoint:
    """plans_confirm is registered in _DEFAULT_ENDPOINTS."""

    def test_plans_confirm_endpoint_registered(self):
        p = LiteStartupProvider("https://api.litestartup.com", "k")
        assert p.endpoint("plans_confirm") == (
            "https://api.litestartup.com/client/v2/ai/plans/confirm"
        )

    def test_plans_confirm_endpoint_overridable(self):
        p = LiteStartupProvider(
            "https://api.litestartup.com",
            "k",
            endpoints={"plans_confirm": "/v3/ai/plans/confirm"},
        )
        assert p.endpoint("plans_confirm") == (
            "https://api.litestartup.com/v3/ai/plans/confirm"
        )


class TestConfirmPlan:
    """LiteStartupProvider.confirm_plan() covers the Phase-2 call (LAD §R2.2)."""

    _TOKEN = "cft_" + "a" * 32  # shape-valid per LAD §R7

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": 200,
            "message": "Success",
            "data": {
                "mode": "confirm",
                "type": "plan",
                "confirm_token": self._TOKEN,
                "tool": "contact.delete",
                "rendered": "Deleted contact Alice (#42).",
                "data": {"id": 42, "name": "Alice"},
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.confirm_plan(self._TOKEN)

        assert result["success"] is True
        assert result["tool"] == "contact.delete"
        assert "Alice" in result["rendered"]
        assert result["data"]["id"] == 42

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_payload_and_url_shape(self, mock_post):
        """Captures POST to verify URL, headers, body match the contract."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": 200,
            "data": {"tool": "x", "rendered": "ok", "data": {}},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        p.confirm_plan(self._TOKEN)

        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.litestartup.com/client/v2/ai/plans/confirm"
        assert kwargs["json"] == {"confirm_token": self._TOKEN}
        assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["timeout"] == 60

    @pytest.mark.parametrize(
        ("status", "body_code", "body_msg"),
        [
            (404, 404, "Token not found"),
            (409, 409, "already consumed"),
            (410, 410, "token expired"),
            (403, 403, "forbidden"),
        ],
    )
    @patch("chatmd.providers.litestartup.httpx.post")
    def test_error_codes_propagated(
        self, mock_post, status, body_code, body_msg,
    ):
        """LS 4xx errors flow through with correct code for i18n dispatch."""
        err_resp = httpx.Response(
            status,
            json={"code": body_code, "message": body_msg},
            request=httpx.Request("POST", "u"),
        )
        mock_post.side_effect = httpx.HTTPStatusError(
            "", request=err_resp.request, response=err_resp,
        )

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.confirm_plan(self._TOKEN)

        assert result["success"] is False
        assert result["code"] == body_code
        assert body_msg in result["error"]

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timeout")

        p = LiteStartupProvider(
            "https://api.litestartup.com", "sk-test", timeout=5,
        )
        result = p.confirm_plan(self._TOKEN)

        assert result["success"] is False
        assert "Confirm timeout (5s)" in result["error"]

    @patch("chatmd.providers.litestartup.httpx.post")
    def test_network_error(self, mock_post):
        mock_post.side_effect = httpx.ConnectError("refused")

        p = LiteStartupProvider("https://api.litestartup.com", "sk-test")
        result = p.confirm_plan(self._TOKEN)

        assert result["success"] is False
        assert "Network error" in result["error"]


class TestMaskToken:
    """_mask_token() redacts confirm_tokens for log safety (§9 risk)."""

    def test_long_token_truncates_to_prefix(self):
        from chatmd.providers.litestartup import _mask_token
        token = "cft_" + "a" * 32
        masked = _mask_token(token)
        assert masked == "cft_aaaa…"
        assert len(masked) == 9
        assert "a" * 32 not in masked

    def test_short_token_returned_unchanged(self):
        from chatmd.providers.litestartup import _mask_token
        assert _mask_token("abc") == "abc"
        assert _mask_token("cft_ab") == "cft_ab"

    def test_empty_or_none(self):
        from chatmd.providers.litestartup import _mask_token
        assert _mask_token("") == ""
        # Defensive: not None, caller normalizes — but check it doesn't crash.
        assert _mask_token(None) == ""  # type: ignore[arg-type]

    def test_custom_prefix_length(self):
        from chatmd.providers.litestartup import _mask_token
        token = "cft_" + "b" * 32
        masked = _mask_token(token, prefix_len=4)
        assert masked == "cft_…"
