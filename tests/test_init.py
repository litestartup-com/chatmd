"""Tests for chatmd init command."""


from click.testing import CliRunner

from chatmd.cli import main


class TestInitCommand:
    """Test the chatmd init CLI command."""

    def test_init_new_dir(self, tmp_path):
        target = tmp_path / "workspace"
        runner = CliRunner()
        result = runner.invoke(main, ["init", str(target)])
        assert result.exit_code == 0
        assert "✅" in result.output

        # Verify full structure always created
        assert (target / "chatmd" / "chat.md").exists()
        assert (target / "chatmd" / "chat").is_dir()
        assert (target / "chatmd" / "notification.md").exists()
        assert (target / ".chatmd" / "agent.yaml").exists()
        assert (target / ".chatmd" / "user.yaml").exists()
        assert (target / ".chatmd" / "skills").is_dir()
        assert (target / ".chatmd" / "memory").is_dir()
        assert (target / ".chatmd" / "logs").is_dir()

    def test_init_existing_dir(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        (target / "README.md").write_text("Existing project", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["init", str(target)])
        assert result.exit_code == 0

        # Full structure created alongside existing files
        assert (target / ".chatmd" / "agent.yaml").exists()
        assert (target / "chatmd" / "chat.md").exists()
        # Original files untouched
        assert (target / "README.md").read_text(encoding="utf-8") == "Existing project"

    def test_init_no_git(self, tmp_path):
        target = tmp_path / "nogit"
        runner = CliRunner()
        result = runner.invoke(main, ["init", str(target), "--no-git"])
        assert result.exit_code == 0
        assert not (target / ".git").exists()

    def test_init_gitignore_runtime_files(self, tmp_path):
        target = tmp_path / "workspace"
        runner = CliRunner()
        result = runner.invoke(main, ["init", str(target)])
        assert result.exit_code == 0
        gitignore = (target / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("agent.pid", "stop.signal", ".chatmd/logs/", ".chatmd/state/"):
            assert pattern in gitignore, f"{pattern} missing from .gitignore"

    def test_init_idempotent(self, tmp_path):
        target = tmp_path / "workspace"
        runner = CliRunner()
        # First init
        runner.invoke(main, ["init", str(target), "--no-git"])
        # Write something to chat.md
        (target / "chatmd" / "chat.md").write_text("User content", encoding="utf-8")
        # Second init — should not overwrite chat.md
        result = runner.invoke(main, ["init", str(target), "--no-git"])
        assert result.exit_code == 0
        assert (target / "chatmd" / "chat.md").read_text(encoding="utf-8") == "User content"
