"""Tests for /notify skill + EmailChannel + Provider email method."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chatmd.infra.notification import (
    EmailChannel,
    FileChannel,
    NotificationManager,
    SystemChannel,
)
from chatmd.skills.base import SkillContext, SkillResult
from chatmd.skills.notify import NotifySkill


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture()
def context(tmp_path: Path) -> SkillContext:
    return SkillContext(
        source_file=tmp_path / "chat.md",
        source_line=1,
        workspace=tmp_path,
    )


def _make_mgr(*, enabled: bool = True) -> NotificationManager:
    mgr = NotificationManager(enabled=enabled)
    mgr.add_channel(FileChannel(Path("/tmp/test_notify.md")))
    return mgr


# ── NotifySkill tests ────────────────────────────────────────────────────


class TestNotifySkill:
    """Tests for the /notify skill."""

    def test_basic_notify(self, context: SkillContext) -> None:
        """Notification sent successfully with message."""
        mgr = MagicMock(spec=NotificationManager)
        mgr.enabled = True
        mgr.channel_names = ["FileChannel"]
        skill = NotifySkill(notification_mgr=mgr)

        result = skill.execute("Remember to eat dinner", {}, context)

        assert result.success is True
        assert "Remember to eat dinner" in result.output
        assert "FileChannel" in result.output
        mgr.notify.assert_called_once_with(
            title="ChatMD Reminder",
            body="Remember to eat dinner",
            level="info",
            source="user",
        )

    def test_empty_message_error(self, context: SkillContext) -> None:
        """Empty message should return error."""
        mgr = MagicMock(spec=NotificationManager)
        mgr.enabled = True
        skill = NotifySkill(notification_mgr=mgr)

        result = skill.execute("", {}, context)

        assert result.success is False
        mgr.notify.assert_not_called()

    def test_positional_arg_fallback(self, context: SkillContext) -> None:
        """If input_text is empty, use _positional arg."""
        mgr = MagicMock(spec=NotificationManager)
        mgr.enabled = True
        mgr.channel_names = ["FileChannel", "SystemChannel"]
        skill = NotifySkill(notification_mgr=mgr)

        result = skill.execute("", {"_positional": "test msg"}, context)

        assert result.success is True
        mgr.notify.assert_called_once()

    def test_no_manager_error(self, context: SkillContext) -> None:
        """No notification manager should return error."""
        skill = NotifySkill(notification_mgr=None)

        result = skill.execute("hello", {}, context)

        assert result.success is False

    def test_disabled_manager_error(self, context: SkillContext) -> None:
        """Disabled notification manager should return error."""
        mgr = MagicMock(spec=NotificationManager)
        mgr.enabled = False
        skill = NotifySkill(notification_mgr=mgr)

        result = skill.execute("hello", {}, context)

        assert result.success is False

    def test_set_notification_manager(self, context: SkillContext) -> None:
        """set_notification_manager should inject the manager."""
        skill = NotifySkill(notification_mgr=None)
        mgr = MagicMock(spec=NotificationManager)
        mgr.enabled = True
        mgr.channel_names = ["FileChannel"]
        skill.set_notification_manager(mgr)

        result = skill.execute("test", {}, context)

        assert result.success is True
        mgr.notify.assert_called_once()

    def test_skill_metadata(self) -> None:
        """Check skill name, category, aliases."""
        skill = NotifySkill()
        assert skill.name == "notify"
        assert skill.category == "general"
        assert "ntf" in skill.aliases

    def test_help_text_property(self) -> None:
        """help_text should return non-empty string from i18n."""
        skill = NotifySkill()
        text = skill.help_text
        assert isinstance(text, str)
        assert len(text) > 0

    def test_multiple_channels_listed(self, context: SkillContext) -> None:
        """Output should list all channel names."""
        mgr = MagicMock(spec=NotificationManager)
        mgr.enabled = True
        mgr.channel_names = ["FileChannel", "SystemChannel", "EmailChannel"]
        skill = NotifySkill(notification_mgr=mgr)

        result = skill.execute("test", {}, context)

        assert result.success is True
        assert "FileChannel" in result.output
        assert "EmailChannel" in result.output


# ── EmailChannel tests ───────────────────────────────────────────────────


class TestEmailChannel:
    """Tests for EmailChannel."""

    def test_send_success(self) -> None:
        """EmailChannel should call provider.send_email."""
        provider = MagicMock()
        provider.send_email.return_value = {
            "success": True, "message_id": "abc123",
        }
        channel = EmailChannel(
            provider=provider,
            from_addr="support@chatmarkdown.org",
            to_addr="user@example.com",
        )

        channel.send(
            title="Test",
            body="Hello world",
            level="info",
            source="user",
        )

        provider.send_email.assert_called_once()
        call_kwargs = provider.send_email.call_args[1]
        assert "[ChatMD] Test" in call_kwargs["subject"]
        assert call_kwargs["from_addr"] == "support@chatmarkdown.org"
        assert call_kwargs["to_addr"] == "user@example.com"
        assert "Hello world" in call_kwargs["html"]

    def test_send_failure_logged(self) -> None:
        """Failed email should log warning but not raise."""
        provider = MagicMock()
        provider.send_email.return_value = {
            "success": False, "error": "Rate limit exceeded",
        }
        channel = EmailChannel(provider=provider)

        # Should not raise
        channel.send(title="Test", body="body")

    def test_html_rendering(self) -> None:
        """HTML should contain title, body, source."""
        html = EmailChannel._render_html(
            title="Server Down",
            body="CPU > 90%",
            level="error",
            source="cron",
            actions=["/cron run job1"],
        )
        assert "Server Down" in html
        assert "CPU &gt; 90%" in html  # escaped
        assert "cron" in html
        assert "/cron run job1" in html
        assert "ChatMarkdown" in html

    def test_html_no_actions(self) -> None:
        """HTML without actions should not have Suggested actions section."""
        html = EmailChannel._render_html(
            title="Info",
            body="All good",
            level="info",
            source="",
            actions=None,
        )
        assert "Suggested actions" not in html
        assert "All good" in html

    def test_optional_params(self) -> None:
        """EmailChannel with no from/to uses provider defaults."""
        provider = MagicMock()
        provider.send_email.return_value = {"success": True}
        channel = EmailChannel(provider=provider)

        channel.send(title="Test", body="body")

        call_kwargs = provider.send_email.call_args[1]
        assert call_kwargs["from_addr"] is None
        assert call_kwargs["to_addr"] is None


# ── NotificationManager.channel_names tests ──────────────────────────────


class TestNotificationManagerChannelNames:
    """Tests for NotificationManager.channel_names property."""

    def test_empty_channels(self) -> None:
        mgr = NotificationManager()
        assert mgr.channel_names == []

    def test_single_channel(self, tmp_path: Path) -> None:
        mgr = NotificationManager()
        mgr.add_channel(FileChannel(tmp_path / "n.md"))
        assert mgr.channel_names == ["FileChannel"]

    def test_multiple_channels(self, tmp_path: Path) -> None:
        mgr = NotificationManager()
        mgr.add_channel(FileChannel(tmp_path / "n.md"))
        mgr.add_channel(SystemChannel(enabled=False))
        names = mgr.channel_names
        assert "FileChannel" in names
        assert "SystemChannel" in names
        assert len(names) == 2


# ── LiteStartupProvider.send_notification_email tests ────────────────────


class TestProviderSendEmail:
    """Tests for LiteStartupProvider.send_email."""

    def test_success(self) -> None:
        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": 200,
            "message": "Success",
            "data": {"messageId": "msg-123"},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            result = provider.send_email(
                subject="Test",
                html="<p>Hello</p>",
                from_addr="a@b.com",
                to_addr="c@d.com",
            )

        assert result["success"] is True
        assert result["message_id"] == "msg-123"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["subject"] == "Test"
        assert payload["html"] == "<p>Hello</p>"
        assert payload["from"] == "a@b.com"
        assert payload["to"] == "c@d.com"

    def test_error_response(self) -> None:
        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": 500,
            "message": "Subject is required",
            "data": [],
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_resp):
            result = provider.send_email(
                subject="",
                html="",
            )

        assert result["success"] is False
        assert "Subject is required" in result["error"]

    def test_timeout(self) -> None:
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
            timeout=5,
        )

        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            result = provider.send_email(
                subject="Test",
                html="body",
            )

        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    def test_network_error(self) -> None:
        import httpx

        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
        )

        with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
            result = provider.send_email(
                subject="Test",
                html="body",
            )

        assert result["success"] is False
        assert "Network error" in result["error"]

    def test_optional_params_omitted(self) -> None:
        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": 200, "data": {"messageId": "x"},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            provider.send_email(
                subject="Test",
                html="body",
            )

        payload = mock_post.call_args[1]["json"]
        assert "from" not in payload
        assert "to" not in payload
        assert "from_name" not in payload
        assert "to_name" not in payload

    def test_endpoint_registered(self) -> None:
        from chatmd.providers.litestartup import LiteStartupProvider

        provider = LiteStartupProvider(
            api_base="https://api.litestartup.com",
            api_key="sk-test",
        )
        url = provider.endpoint("email")
        assert url == "https://api.litestartup.com/client/v2/emails"
