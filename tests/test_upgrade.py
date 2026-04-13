"""Tests for chatmd upgrade command."""

from chatmd.commands.upgrade import run_upgrade


class TestUpgrade:
    def test_upgrade_no_workspace(self, tmp_path, capsys):
        run_upgrade(str(tmp_path), full=True)
        out = capsys.readouterr().out
        assert "Not a ChatMD workspace" in out

    def test_upgrade_creates_missing_structure(self, tmp_path, capsys):
        # Setup workspace with .chatmd/ but no chatmd/ structure
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        for sub in ("skills", "memory", "logs", "history", "state"):
            (chatmd_dir / sub).mkdir()

        import yaml

        (chatmd_dir / "agent.yaml").write_text(
            yaml.dump({"version": "0.2.3"}), encoding="utf-8",
        )
        (chatmd_dir / "user.yaml").write_text(
            yaml.dump({"language": "en"}), encoding="utf-8",
        )

        run_upgrade(str(tmp_path), full=True)
        out = capsys.readouterr().out
        assert "Upgrade completed" in out
        assert (tmp_path / "chatmd" / "chat.md").exists()
        assert (tmp_path / "chatmd" / "chat").is_dir()
        assert (tmp_path / "chatmd" / "notification.md").exists()
        assert (tmp_path / "chatmd" / "cron.md").exists()

    def test_upgrade_already_complete(self, tmp_path, capsys):
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        interact = tmp_path / "chatmd"
        interact.mkdir()
        (interact / "chat.md").write_text("hi", encoding="utf-8")
        (interact / "chat").mkdir()
        (interact / "notification.md").write_text("notif", encoding="utf-8")
        (interact / "cron.md").write_text("# Cron", encoding="utf-8")

        import yaml

        (chatmd_dir / "agent.yaml").write_text(
            yaml.dump({"version": "0.2.3"}), encoding="utf-8",
        )
        (chatmd_dir / "user.yaml").write_text(
            yaml.dump({"language": "en"}), encoding="utf-8",
        )

        run_upgrade(str(tmp_path), full=True)
        out = capsys.readouterr().out
        assert "already complete" in out

    def test_upgrade_no_option(self, tmp_path, capsys):
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()

        import yaml

        (chatmd_dir / "agent.yaml").write_text(
            yaml.dump({"version": "0.2.4"}), encoding="utf-8",
        )
        run_upgrade(str(tmp_path), full=False)
        out = capsys.readouterr().out
        assert "specify an upgrade option" in out

    def test_upgrade_runs_migration(self, tmp_path, capsys):
        """Verify that upgrade without --full still runs migrations."""
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        (tmp_path / "chatmd").mkdir()

        import yaml

        (chatmd_dir / "agent.yaml").write_text(
            yaml.dump({"version": "0.1", "sync": {"mode": "git", "auto_commit": True}}),
            encoding="utf-8",
        )
        run_upgrade(str(tmp_path), full=False)
        out = capsys.readouterr().out
        assert "0.1 → 0.2.3" in out
        assert "0.2.3" in out
