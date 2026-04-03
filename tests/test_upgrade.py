"""Tests for chatmd upgrade command."""

from chatmd.commands.upgrade import run_upgrade


class TestUpgrade:
    def test_upgrade_no_workspace(self, tmp_path, capsys):
        run_upgrade(str(tmp_path), full=True)
        out = capsys.readouterr().out
        assert "Not a ChatMD workspace" in out

    def test_upgrade_to_full(self, tmp_path, capsys):
        # Setup assistant workspace
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()

        import yaml

        agent_yaml = chatmd_dir / "agent.yaml"
        agent_yaml.write_text(
            yaml.dump({"workspace": {"mode": "assistant"}}),
            encoding="utf-8",
        )

        run_upgrade(str(tmp_path), full=True)
        out = capsys.readouterr().out
        assert "Upgrade completed" in out
        assert (tmp_path / "chat.md").exists()
        assert (tmp_path / "chat").is_dir()

        # Verify agent.yaml updated
        with open(agent_yaml, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert config["workspace"]["mode"] == "full"

    def test_upgrade_already_full(self, tmp_path, capsys):
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        (tmp_path / "chat.md").write_text("hi", encoding="utf-8")
        (tmp_path / "chat").mkdir()

        import yaml

        (chatmd_dir / "agent.yaml").write_text(
            yaml.dump({"workspace": {"mode": "full"}}),
            encoding="utf-8",
        )

        run_upgrade(str(tmp_path), full=True)
        out = capsys.readouterr().out
        # Only agent.yaml mode change is reported (or already full)
        assert "Upgrade completed" in out or "already in full mode" in out

    def test_upgrade_no_option(self, tmp_path, capsys):
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        run_upgrade(str(tmp_path), full=False)
        out = capsys.readouterr().out
        assert "specify an upgrade option" in out
