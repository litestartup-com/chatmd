"""Tests for NotificationManager + FileChannel (T-060 / US-026 / F-091)."""

from __future__ import annotations

from pathlib import Path

import yaml

from chatmd.infra.config import Config


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _init_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    chatmd_dir = ws / ".chatmd"
    chatmd_dir.mkdir()
    for sub in ("skills", "memory", "logs", "history", "state"):
        (chatmd_dir / sub).mkdir()
    _write_yaml(chatmd_dir / "agent.yaml", {
        "version": "0.1",
        "notification": {
            "enabled": True,
            "notification_file": "notification.md",
            "system_notify": False,
            "max_items": 50,
            "auto_archive": True,
        },
    })
    _write_yaml(chatmd_dir / "user.yaml", {"language": "en"})
    # Create chatmd/ and notification.md
    interact = ws / "chatmd"
    interact.mkdir()
    (interact / "notification.md").write_text(
        "# Notifications\n\n> Your notification inbox\n\n---\n\n",
        encoding="utf-8",
    )
    return ws


# ═══════════════════════════════════════════════════════════════════
# FileChannel — write notifications to notification.md
# ═══════════════════════════════════════════════════════════════════


class TestFileChannel:
    """FileChannel writes notifications to notification.md."""

    def test_write_notification(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(
            title="Cron task failed",
            body="Job `cron-a1b2` command `/sync` failed: Connection refused",
            level="error",
            source="cron",
            actions=["/cron run cron-a1b2", "/cron pause cron-a1b2"],
        )

        content = notif_path.read_text(encoding="utf-8")
        assert "Cron task failed" in content
        assert "cron-a1b2" in content
        assert "/cron run cron-a1b2" in content
        assert "❌" in content or "error" in content.lower()

    def test_write_warning(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(
            title="Missed cron task",
            body="Job `cron-x1` was missed while Agent was offline",
            level="warning",
            source="cron",
            actions=["/cron run cron-x1", "/cron skip cron-x1"],
        )

        content = notif_path.read_text(encoding="utf-8")
        assert "Missed cron task" in content
        assert "⚠️" in content or "warning" in content.lower()

    def test_write_info(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(
            title="Cron task completed",
            body="Job `cron-ok` finished successfully",
            level="info",
            source="cron",
        )

        content = notif_path.read_text(encoding="utf-8")
        assert "Cron task completed" in content
        assert "ℹ️" in content or "info" in content.lower()

    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "new_notification.md"
        assert not notif_path.exists()

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(title="Test", body="Body", level="info", source="test")

        assert notif_path.exists()
        content = notif_path.read_text(encoding="utf-8")
        assert "Test" in content

    def test_multiple_notifications_append(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(title="First", body="Body 1", level="info", source="test")
        ch.send(title="Second", body="Body 2", level="warning", source="test")

        content = notif_path.read_text(encoding="utf-8")
        assert "First" in content
        assert "Second" in content

    def test_actions_as_code_block(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(
            title="Action needed",
            body="Please decide",
            level="warning",
            source="cron",
            actions=["/cron run cron-x1", "/cron skip cron-x1"],
        )

        content = notif_path.read_text(encoding="utf-8")
        assert "/cron run cron-x1" in content
        assert "/cron skip cron-x1" in content


# ═══════════════════════════════════════════════════════════════════
# NotificationManager — dispatch to channels
# ═══════════════════════════════════════════════════════════════════


class TestNotificationManager:
    """NotificationManager dispatches to registered channels."""

    def test_manager_dispatches_to_file_channel(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel, NotificationManager
        mgr = NotificationManager()
        mgr.add_channel(FileChannel(notif_path))
        mgr.notify(
            title="Test dispatch",
            body="Dispatched via manager",
            level="info",
            source="test",
        )

        content = notif_path.read_text(encoding="utf-8")
        assert "Test dispatch" in content

    def test_manager_no_channels(self, tmp_path: Path) -> None:
        from chatmd.infra.notification import NotificationManager
        mgr = NotificationManager()
        # Should not raise
        mgr.notify(title="Noop", body="Nothing", level="info", source="test")

    def test_manager_enabled_flag(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel, NotificationManager
        mgr = NotificationManager(enabled=False)
        mgr.add_channel(FileChannel(notif_path))
        mgr.notify(
            title="Should not appear",
            body="Disabled",
            level="info",
            source="test",
        )

        content = notif_path.read_text(encoding="utf-8")
        assert "Should not appear" not in content

    def test_manager_multiple_channels(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        path1 = ws / "notif1.md"
        path2 = ws / "notif2.md"

        from chatmd.infra.notification import FileChannel, NotificationManager
        mgr = NotificationManager()
        mgr.add_channel(FileChannel(path1))
        mgr.add_channel(FileChannel(path2))
        mgr.notify(title="Dual", body="Both", level="info", source="test")

        assert "Dual" in path1.read_text(encoding="utf-8")
        assert "Dual" in path2.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
# Notification config
# ═══════════════════════════════════════════════════════════════════


class TestNotificationConfig:
    """notification: config section in agent.yaml."""

    def test_notification_enabled(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cfg = Config(ws)
        assert cfg.get("notification.enabled", False) is True

    def test_notification_file(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cfg = Config(ws)
        assert cfg.get("notification.notification_file", "notification.md") == "notification.md"

    def test_system_notify_disabled(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cfg = Config(ws)
        assert cfg.get("notification.system_notify", True) is False

    def test_max_items(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cfg = Config(ws)
        assert cfg.get("notification.max_items", 50) == 50


# ═══════════════════════════════════════════════════════════════════
# Notification level icons
# ═══════════════════════════════════════════════════════════════════


class TestNotificationFormat:
    """Notification output format matches design spec."""

    def test_error_has_icon(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(title="Err", body="fail", level="error", source="test")
        content = notif_path.read_text(encoding="utf-8")
        assert "❌" in content

    def test_warning_has_icon(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(title="Warn", body="caution", level="warning", source="test")
        content = notif_path.read_text(encoding="utf-8")
        assert "⚠️" in content

    def test_info_has_icon(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        from chatmd.infra.notification import FileChannel
        ch = FileChannel(notif_path)
        ch.send(title="Info", body="note", level="info", source="test")
        content = notif_path.read_text(encoding="utf-8")
        assert "ℹ️" in content
