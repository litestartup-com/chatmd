"""Tests for BotNotificationChannel and LiteStartupProvider Bot API methods."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from chatmd.infra.notification import BotNotificationChannel


class TestBotNotificationChannel:
    """Tests for BotNotificationChannel."""

    def test_send_success(self) -> None:
        """Successful bot notification should log platforms."""
        provider = MagicMock()
        provider.bot_notify.return_value = {
            "success": True,
            "delivered_to": ["telegram"],
        }
        channel = BotNotificationChannel(provider=provider)

        channel.send(title="Test", body="Hello world", level="info")

        provider.bot_notify.assert_called_once()
        call_kwargs = provider.bot_notify.call_args[1]
        assert "Test" in call_kwargs["message"]
        assert "Hello world" in call_kwargs["message"]

    def test_send_with_source(self) -> None:
        """Source should be included in the message."""
        provider = MagicMock()
        provider.bot_notify.return_value = {
            "success": True,
            "delivered_to": ["telegram"],
        }
        channel = BotNotificationChannel(provider=provider)

        channel.send(
            title="Cron Done", body="Job finished",
            source="cron",
        )

        call_kwargs = provider.bot_notify.call_args[1]
        assert "cron" in call_kwargs["message"]

    def test_send_failure_logged_not_raised(self) -> None:
        """Failed bot notification should not raise."""
        provider = MagicMock()
        provider.bot_notify.return_value = {
            "success": False,
            "error": "User not bound",
        }
        channel = BotNotificationChannel(provider=provider)

        # Should not raise
        channel.send(title="Test", body="body")

    def test_send_with_level_icon(self) -> None:
        """Level icon should be included in message."""
        provider = MagicMock()
        provider.bot_notify.return_value = {
            "success": True, "delivered_to": [],
        }
        channel = BotNotificationChannel(provider=provider)

        channel.send(title="Error", body="CPU high", level="error")

        call_kwargs = provider.bot_notify.call_args[1]
        assert "❌" in call_kwargs["message"]

    def test_send_with_actions_ignored(self) -> None:
        """Actions parameter is accepted but not included in message."""
        provider = MagicMock()
        provider.bot_notify.return_value = {
            "success": True, "delivered_to": [],
        }
        channel = BotNotificationChannel(provider=provider)

        channel.send(
            title="Test", body="body",
            actions=["/cron run job1"],
        )

        provider.bot_notify.assert_called_once()


# ── LiteStartupProvider Bot API methods ──────────────────────────────────


class TestProviderBindInitiate:
    """Tests for LiteStartupProvider.bind_initiate."""

    def test_success(self) -> None:
        """Successful bind_initiate returns bind_code."""
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="http://test.local",
            api_key="test-key",
        )

        mock_response = httpx.Response(
            200,
            json={
                "code": 0,
                "message": "Binding code generated",
                "data": {
                    "bind_code": "123456",
                    "expires_in": 300,
                    "bot_username": "@TestBot",
                    "bot_deep_link": "https://t.me/TestBot",
                },
            },
            request=httpx.Request("POST", "http://test.local/api/bot/bind/initiate"),
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx, "post", lambda *a, **kw: mock_response)
            result = provider.bind_initiate(
                repo_url="https://github.com/u/r.git",
                git_token="ghp_xxx",
            )

        assert result["success"] is True
        assert result["bind_code"] == "123456"
        assert result["expires_in"] == 300

    def test_error_response(self) -> None:
        """Error response should return success=False with code."""
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="http://test.local",
            api_key="test-key",
        )

        mock_response = httpx.Response(
            200,
            json={
                "code": 1001,
                "message": "Invalid repo URL format",
            },
            request=httpx.Request("POST", "http://test.local/api/bot/bind/initiate"),
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx, "post", lambda *a, **kw: mock_response)
            result = provider.bind_initiate(
                repo_url="bad-url",
                git_token="ghp_xxx",
            )

        assert result["success"] is False
        assert result["code"] == 1001

    def test_timeout(self) -> None:
        """Timeout should return graceful error."""
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="http://test.local",
            api_key="test-key",
        )

        def raise_timeout(*a, **kw):
            raise httpx.TimeoutException("timeout")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx, "post", raise_timeout)
            result = provider.bind_initiate(
                repo_url="https://github.com/u/r.git",
                git_token="ghp_xxx",
            )

        assert result["success"] is False
        assert "timeout" in result["error"].lower()


class TestProviderBindStatus:
    """Tests for LiteStartupProvider.bind_status."""

    def test_active_status(self) -> None:
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="http://test.local",
            api_key="test-key",
        )

        mock_response = httpx.Response(
            200,
            json={
                "code": 0,
                "message": "OK",
                "data": {
                    "status": "active",
                    "platform": "telegram",
                    "repo_url_masked": "https://github.com/u***/r***.git",
                    "bound_at": "2026-04-14T10:30:00",
                    "last_sync_at": None,
                    "pending_messages": 3,
                },
            },
            request=httpx.Request("GET", "http://test.local/api/bot/bind/status"),
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx, "get", lambda *a, **kw: mock_response)
            result = provider.bind_status()

        assert result["success"] is True
        assert result["status"] == "active"
        assert result["pending_messages"] == 3

    def test_none_status(self) -> None:
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="http://test.local",
            api_key="test-key",
        )

        mock_response = httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"status": "none"},
            },
            request=httpx.Request("GET", "http://test.local/api/bot/bind/status"),
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx, "get", lambda *a, **kw: mock_response)
            result = provider.bind_status()

        assert result["success"] is True
        assert result["status"] == "none"


class TestProviderBotNotify:
    """Tests for LiteStartupProvider.bot_notify."""

    def test_success(self) -> None:
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="http://test.local",
            api_key="test-key",
        )

        mock_response = httpx.Response(
            200,
            json={
                "success": True,
                "delivered_to": ["telegram"],
            },
            request=httpx.Request("POST", "http://test.local/api/bot/notify"),
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx, "post", lambda *a, **kw: mock_response)
            result = provider.bot_notify(message="Test notification")

        assert result["success"] is True
        assert "telegram" in result["delivered_to"]

    def test_network_error(self) -> None:
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="http://test.local",
            api_key="test-key",
        )

        def raise_network_error(*a, **kw):
            raise httpx.ConnectError("Connection refused")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx, "post", raise_network_error)
            result = provider.bot_notify(message="Test")

        assert result["success"] is False
        assert "Network error" in result["error"]
