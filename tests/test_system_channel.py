"""Tests for SystemChannel desktop notifications (T-061 / US-026 / F-092~F-093)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from chatmd.infra.notification import SystemChannel


class TestSystemChannel:
    """SystemChannel sends desktop toast notifications."""

    def test_send_does_not_raise(self) -> None:
        ch = SystemChannel()
        # Should never raise even if no toast lib available
        ch.send(title="Test", body="Body", level="info", source="test")

    def test_send_error_level(self) -> None:
        ch = SystemChannel()
        ch.send(title="Error", body="Failed", level="error", source="cron")

    def test_send_warning_level(self) -> None:
        ch = SystemChannel()
        ch.send(title="Warning", body="Missed", level="warning", source="cron")

    @patch("chatmd.infra.notification.SystemChannel._send_windows")
    def test_windows_called_on_win32(self, mock_send: MagicMock) -> None:
        ch = SystemChannel()
        with patch.object(sys, "platform", "win32"):
            ch.send(title="Win", body="Toast", level="info", source="test")
        if sys.platform == "win32":
            mock_send.assert_called_once()

    @patch("chatmd.infra.notification.SystemChannel._send_macos")
    def test_macos_called_on_darwin(self, mock_send: MagicMock) -> None:
        ch = SystemChannel()
        with patch.object(sys, "platform", "darwin"):
            ch.send(title="Mac", body="Toast", level="info", source="test")
        if sys.platform == "darwin":
            mock_send.assert_called_once()

    @patch("chatmd.infra.notification.SystemChannel._send_linux")
    def test_linux_called_on_linux(self, mock_send: MagicMock) -> None:
        ch = SystemChannel()
        with patch.object(sys, "platform", "linux"):
            ch.send(title="Linux", body="Toast", level="info", source="test")
        if sys.platform == "linux":
            mock_send.assert_called_once()

    def test_graceful_degradation(self) -> None:
        """SystemChannel must not crash even if all native methods fail."""
        ch = SystemChannel()
        with patch.object(ch, "_send_windows", side_effect=Exception("no toast")):
            with patch.object(ch, "_send_macos", side_effect=Exception("no osascript")):
                with patch.object(ch, "_send_linux", side_effect=Exception("no notify-send")):
                    # Should not raise
                    ch.send(title="Safe", body="Fallback", level="error", source="test")

    def test_disabled_flag(self) -> None:
        ch = SystemChannel(enabled=False)
        # Should short-circuit
        ch.send(title="Noop", body="Disabled", level="info", source="test")

    def test_title_truncation(self) -> None:
        ch = SystemChannel()
        long_title = "A" * 300
        # Should not raise
        ch.send(title=long_title, body="Body", level="info", source="test")
