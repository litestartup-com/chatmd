"""Notification module — NotificationManager + multi-channel dispatch.

Architecture::

    NotificationManager
    ├─ FileChannel (default, always present) → writes to notification.md
    ├─ SystemChannel (optional) → desktop toast (T-061)
    ├─ EmailChannel (optional) → LiteStartup Email API (T-078)
    └─ (future) WebhookChannel / NostrChannel
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatmd.providers.litestartup import LiteStartupProvider

logger = logging.getLogger(__name__)

_LEVEL_ICONS = {
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
}


class NotificationChannel(ABC):
    """Base class for notification channels."""

    @abstractmethod
    def send(
        self,
        title: str,
        body: str,
        level: str = "info",
        source: str = "",
        actions: list[str] | None = None,
    ) -> None:
        """Send a notification through this channel."""


class FileChannel(NotificationChannel):
    """Write notifications to a Markdown file (notification.md).

    Format::

        ### ❌ Cron task failed (2026-04-08 23:00:00)

        > **Source:** cron

        Job `cron-a1b2` command `/sync` failed: Connection refused

        **Suggested actions:**
        - `/cron run cron-a1b2`
        - `/cron pause cron-a1b2`

        ---
    """

    def __init__(self, filepath: Path) -> None:
        self._filepath = filepath

    def send(
        self,
        title: str,
        body: str,
        level: str = "info",
        source: str = "",
        actions: list[str] | None = None,
    ) -> None:
        """Append a notification entry to the file."""
        icon = _LEVEL_ICONS.get(level, "ℹ️")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"### {icon} {title} ({now})"

        parts = [f"\n{header}\n"]
        if source:
            parts.append(f"> **Source:** {source}\n")
        parts.append(f"{body}\n")

        if actions:
            parts.append("**Suggested actions:**\n")
            for action in actions:
                parts.append(f"- `{action}`")
            parts.append("")

        parts.append("---\n")
        entry = "\n".join(parts)

        if not self._filepath.exists():
            self._filepath.parent.mkdir(parents=True, exist_ok=True)
            self._filepath.write_text(
                f"# Notifications\n\n---\n{entry}",
                encoding="utf-8",
            )
        else:
            with open(self._filepath, "a", encoding="utf-8") as f:
                f.write(entry)

        logger.debug("Notification written to %s: %s", self._filepath, title)


class SystemChannel(NotificationChannel):
    """Desktop toast notifications (Windows/macOS/Linux).

    Graceful degradation: if the native notification mechanism is unavailable,
    the channel silently logs a warning and does nothing.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    def send(
        self,
        title: str,
        body: str,
        level: str = "info",
        source: str = "",
        actions: list[str] | None = None,
    ) -> None:
        """Send a desktop notification."""
        if not self._enabled:
            return

        import sys

        icon = _LEVEL_ICONS.get(level, "ℹ️")
        display_title = f"{icon} {title}"[:200]
        display_body = body[:500]

        try:
            if sys.platform == "win32":
                self._send_windows(display_title, display_body)
            elif sys.platform == "darwin":
                self._send_macos(display_title, display_body)
            else:
                self._send_linux(display_title, display_body)
        except Exception:
            logger.debug(
                "Desktop notification unavailable, skipping: %s", title,
            )

    # PowerShell's registered AppUserModelID — required for toast
    # notifications to appear in Windows 10/11 Action Center.
    _PS_AUMID = (
        "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
        "\\WindowsPowerShell\\v1.0\\powershell.exe"
    )

    @staticmethod
    def _send_windows(title: str, body: str) -> None:
        """Windows toast via PowerShell Modern Toast API (Win 10+).

        Uses ``-EncodedCommand`` (Base64 UTF-16LE) to avoid shell
        escaping issues with ``$`` variables and quotes.  The toast is
        sent through PowerShell's own registered AppUserModelID so it
        reliably appears in the Windows Action Center.
        """
        import base64
        import subprocess

        # Escape XML special chars for toast template
        safe_title = (
            title.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        safe_body = (
            body.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        aumid = SystemChannel._PS_AUMID
        ps_script = (
            "[Windows.UI.Notifications.ToastNotificationManager, "
            "Windows.UI.Notifications, ContentType = WindowsRuntime] "
            "| Out-Null;\n"
            "[Windows.Data.Xml.Dom.XmlDocument, "
            "Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] "
            "| Out-Null;\n"
            "$t = '<toast><visual><binding template=\"ToastGeneric\">"
            f"<text>{safe_title}</text>"
            f"<text>{safe_body}</text>"
            "</binding></visual></toast>';\n"
            "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument;\n"
            "$xml.LoadXml($t);\n"
            "$toast = [Windows.UI.Notifications.ToastNotification]"
            "::new($xml);\n"
            f"$aumid = '{aumid}';\n"
            "[Windows.UI.Notifications.ToastNotificationManager]"
            "::CreateToastNotifier($aumid).Show($toast);\n"
        )
        encoded = base64.b64encode(
            ps_script.encode("utf-16-le"),
        ).decode("ascii")
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden",
             "-EncodedCommand", encoded],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )

    @staticmethod
    def _send_macos(title: str, body: str) -> None:
        """macOS notification via osascript."""
        import subprocess

        escaped_title = title.replace('"', '\\"')
        escaped_body = body.replace('"', '\\"')
        script = (
            f'display notification "{escaped_body}" '
            f'with title "{escaped_title}"'
        )
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _send_linux(title: str, body: str) -> None:
        """Linux notification via notify-send."""
        import subprocess

        subprocess.Popen(
            ["notify-send", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class EmailChannel(NotificationChannel):
    """Send notifications via LiteStartup Email API.

    Uses the general ``/client/v2/emails`` endpoint.
    """

    def __init__(
        self,
        provider: LiteStartupProvider,
        *,
        from_addr: str | None = None,
        from_name: str | None = None,
        to_addr: str | None = None,
        to_name: str | None = None,
    ) -> None:
        self._provider = provider
        self._from_addr = from_addr
        self._from_name = from_name
        self._to_addr = to_addr
        self._to_name = to_name

    def send(
        self,
        title: str,
        body: str,
        level: str = "info",
        source: str = "",
        actions: list[str] | None = None,
    ) -> None:
        """Send a notification email."""
        icon = _LEVEL_ICONS.get(level, "ℹ️")
        subject = f"{icon} [ChatMD] {title}"
        html = self._render_html(title, body, level, source, actions)

        result = self._provider.send_email(
            subject=subject,
            html=html,
            from_addr=self._from_addr,
            from_name=self._from_name,
            to_addr=self._to_addr,
            to_name=self._to_name,
        )
        if result["success"]:
            logger.debug("Email notification sent: %s", title)
        else:
            logger.warning(
                "Email notification failed: %s — %s",
                title, result.get("error"),
            )

    @staticmethod
    def _render_html(
        title: str,
        body: str,
        level: str,
        source: str,
        actions: list[str] | None,
    ) -> str:
        """Render a simple HTML notification email."""
        icon = _LEVEL_ICONS.get(level, "ℹ️")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Escape HTML special chars in body
        safe_body = (
            body.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", "<br>")
        )
        safe_title = (
            title.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        parts = [
            '<div style="font-family:sans-serif;max-width:600px;margin:0 auto">',
            f'<h2 style="color:#333">{icon} {safe_title}</h2>',
        ]
        if source:
            parts.append(
                f'<p style="color:#888;font-size:0.9em">'
                f'Source: <strong>{source}</strong> | {now}</p>',
            )
        else:
            parts.append(
                f'<p style="color:#888;font-size:0.9em">{now}</p>',
            )
        parts.append(f'<p style="font-size:1em;line-height:1.6">{safe_body}</p>')

        if actions:
            parts.append('<p><strong>Suggested actions:</strong></p><ul>')
            for action in actions:
                safe_action = action.replace("<", "&lt;").replace(">", "&gt;")
                parts.append(f'<li><code>{safe_action}</code></li>')
            parts.append('</ul>')

        parts.append(
            '<hr style="border:none;border-top:1px solid #eee;margin:20px 0">',
        )
        parts.append(
            '<p style="color:#aaa;font-size:0.8em">'
            'Sent by ChatMarkdown</p>',
        )
        parts.append('</div>')
        return "\n".join(parts)


class NotificationManager:
    """Dispatch notifications to registered channels.

    Usage::

        mgr = NotificationManager(enabled=True)
        mgr.add_channel(FileChannel(Path("notification.md")))
        mgr.notify(title="...", body="...", level="error", source="cron")
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._channels: list[NotificationChannel] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def channel_names(self) -> list[str]:
        """Return the names of all registered channels."""
        return [type(ch).__name__ for ch in self._channels]

    def add_channel(self, channel: NotificationChannel) -> None:
        """Register a notification channel."""
        self._channels.append(channel)

    def notify(
        self,
        title: str,
        body: str,
        level: str = "info",
        source: str = "",
        actions: list[str] | None = None,
    ) -> None:
        """Send a notification to all registered channels."""
        if not self._enabled:
            return

        for channel in self._channels:
            try:
                channel.send(
                    title=title,
                    body=body,
                    level=level,
                    source=source,
                    actions=actions,
                )
            except Exception:
                logger.exception(
                    "Failed to send notification via %s",
                    type(channel).__name__,
                )
