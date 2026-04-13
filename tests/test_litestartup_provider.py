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
