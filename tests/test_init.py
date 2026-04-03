"""Tests for chatmd init command."""


from click.testing import CliRunner

from chatmd.cli import main


class TestInitCommand:
    """Test the chatmd init CLI command."""

    def test_init_full_mode_new_dir(self, tmp_path):
        target = tmp_path / "workspace"
        runner = CliRunner()
        result = runner.invoke(main, ["init", str(target), "--mode=full"])
        assert result.exit_code == 0
        assert "✅" in result.output

        # Verify structure
        assert (target / "chat.md").exists()
        assert (target / "chat").is_dir()
        assert (target / ".chatmd" / "agent.yaml").exists()
        assert (target / ".chatmd" / "user.yaml").exists()
        assert (target / ".chatmd" / "skills").is_dir()
        assert (target / ".chatmd" / "memory").is_dir()
        assert (target / ".chatmd" / "logs").is_dir()

    def test_init_assistant_mode(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        (target / "README.md").write_text("Existing project", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["init", str(target), "--mode=assistant"])
        assert result.exit_code == 0
        assert "assistant" in result.output

        # .chatmd exists but chat.md was NOT created
        assert (target / ".chatmd" / "agent.yaml").exists()
        assert not (target / "chat.md").exists()
        # Original files untouched
        assert (target / "README.md").read_text(encoding="utf-8") == "Existing project"

    def test_init_no_git(self, tmp_path):
        target = tmp_path / "nogit"
        runner = CliRunner()
        result = runner.invoke(main, ["init", str(target), "--mode=full", "--no-git"])
        assert result.exit_code == 0
        assert not (target / ".git").exists()

    def test_init_idempotent(self, tmp_path):
        target = tmp_path / "workspace"
        runner = CliRunner()
        # First init
        runner.invoke(main, ["init", str(target), "--mode=full", "--no-git"])
        # Write something to chat.md
        (target / "chat.md").write_text("User content", encoding="utf-8")
        # Second init — should not overwrite chat.md
        result = runner.invoke(main, ["init", str(target), "--mode=full", "--no-git"])
        assert result.exit_code == 0
        assert (target / "chat.md").read_text(encoding="utf-8") == "User content"
