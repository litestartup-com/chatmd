"""Tests for chatmd init command."""


import yaml
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
        assert (target / "chatmd" / "README.md").exists()
        assert (target / "chatmd" / "chat").is_dir()
        assert (target / "chatmd" / "notification.md").exists()
        assert (target / ".chatmd" / "agent.yaml").exists()
        assert (target / ".chatmd" / "user.yaml").exists()
        assert (target / ".chatmd" / "skills").is_dir()
        assert (target / ".chatmd" / "memory").is_dir()
        assert (target / ".chatmd" / "logs").is_dir()
        interaction_readme = (target / "chatmd" / "README.md").read_text(encoding="utf-8")
        assert "Third-party tools" in interaction_readme
        assert "explicit confirmation" in interaction_readme

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

    def test_init_personal_profile(self, tmp_path):
        target = tmp_path / "personal"
        runner = CliRunner()
        result = runner.invoke(main, [
            "init", str(target), "--no-git", "--profile", "personal",
        ])
        assert result.exit_code == 0

        assert not (target / "chatmd").exists()
        assert (target / "A-ChatMD" / "chat.md").exists()
        assert (target / "B-Dashboard" / "Home.md").exists()
        assert (target / "A-ChatMD" / "README.md").exists()
        assert (target / "C-Inbox" / "README.md").exists()
        assert (target / "E-Projects" / "README.md").exists()
        assert (target / "K-Notes" / "README.md").exists()
        assert (target / "Z-Archive" / "README.md").exists()
        assert (target / "K-Notes" / "01-Ideas").is_dir()
        assert (target / "L-Resources" / "01-Templates" / "daily.md").exists()
        assert (target / "L-Resources" / "01-Templates" / "report.md").exists()
        assert (target / "L-Resources" / "01-Templates" / "output.md").exists()
        assert (target / ".chatmd" / "kb.yaml").exists()
        assert (target / ".chatmd" / "privacy.yaml").exists()

        readme = (target / "README.md").read_text(encoding="utf-8")
        assert "Capture" in readme
        assert "Produce" in readme
        interaction_readme = (target / "A-ChatMD" / "README.md").read_text(encoding="utf-8")
        assert "Third-party tools" in interaction_readme
        report = (target / "L-Resources" / "01-Templates" / "report.md").read_text(
            encoding="utf-8",
        )
        assert "## Recommendation" in report
        home = (target / "B-Dashboard" / "Home.md").read_text(encoding="utf-8")
        today = (target / "B-Dashboard" / "Today.md").read_text(encoding="utf-8")
        knowledge_map = (
            target / "B-Dashboard" / "Knowledge-Map.md"
        ).read_text(encoding="utf-8")
        assert "lightweight operating dashboard" in home
        assert "## This Week" in home
        assert "## One Thing" in today
        assert "## Inbox Triage" in today
        assert "manually maintained map" in knowledge_map
        assert "## Knowledge Areas" in knowledge_map
        assert "## Open Questions" in knowledge_map
        assert "not search prompts" in knowledge_map
        assert "Query Prompts" not in knowledge_map
        assert "Where to Put Things" not in knowledge_map

        kb = yaml.safe_load((target / ".chatmd" / "kb.yaml").read_text(encoding="utf-8"))
        assert kb["profile"] == "personal"
        assert kb["roots"]["agent"] == "A-ChatMD"
        assert kb["entrypoints"]["chat"] == "A-ChatMD/chat.md"
        assert kb["write_targets"]["inbox"] == "C-Inbox"

    def test_init_twin_profile_privacy(self, tmp_path):
        target = tmp_path / "twin"
        runner = CliRunner()
        result = runner.invoke(main, [
            "init", str(target), "--no-git", "--profile", "twin",
        ])
        assert result.exit_code == 0

        assert (target / "F-People" / "01-Contacts").is_dir()
        assert (target / "J-Health" / "01-Logs").is_dir()
        assert (target / "L-Resources" / "01-Templates" / "health-log.md").exists()
        assert (target / "L-Resources" / "01-Templates" / "life-review.md").exists()
        assert (target / "L-Resources" / "01-Templates" / "identity.md").exists()
        assert (target / "L-Resources" / "01-Templates" / "monthly-review.md").exists()
        assert (target / "L-Resources" / "01-Templates" / "quarterly-review.md").exists()
        assert (target / "F-People" / "README.md").exists()
        assert (target / "G-Goals" / "README.md").exists()
        assert (target / "H-Habits" / "README.md").exists()
        assert (target / "J-Health" / "README.md").exists()

        people_readme = (target / "F-People" / "README.md").read_text(encoding="utf-8")
        health_log = (
            target / "L-Resources" / "01-Templates" / "health-log.md"
        ).read_text(encoding="utf-8")
        assert "sensitive information" in people_readme
        assert "sensitive information" in health_log

        privacy = yaml.safe_load(
            (target / ".chatmd" / "privacy.yaml").read_text(encoding="utf-8"),
        )
        sensitive = {item["root"] for item in privacy["sensitive_roots"]}
        assert sensitive == {"F-People", "J-Health"}

    def test_init_language_cn(self, tmp_path):
        target = tmp_path / "cn"
        runner = CliRunner()
        result = runner.invoke(main, [
            "init", str(target), "--no-git", "--profile", "personal", "--language", "cn",
        ])
        assert result.exit_code == 0

        user = yaml.safe_load((target / ".chatmd" / "user.yaml").read_text(encoding="utf-8"))
        kb = yaml.safe_load((target / ".chatmd" / "kb.yaml").read_text(encoding="utf-8"))
        assert user["language"] == "cn"
        assert kb["language"] == "cn"
        assert "个人工作区" in (target / "README.md").read_text(encoding="utf-8")
        interaction_readme = (target / "A-ChatMD" / "README.md").read_text(
            encoding="utf-8",
        )
        assert "第三方工具" in interaction_readme
        assert "明确确认" in interaction_readme
        daily_template = (
            target / "L-Resources" / "01-Templates" / "daily.md"
        ).read_text(encoding="utf-8")
        assert "什么有效？" in daily_template
        knowledge_map = (
            target / "B-Dashboard" / "Knowledge-Map.md"
        ).read_text(encoding="utf-8")
        assert "知识资产全景图" in knowledge_map
        assert "不是自动索引" in knowledge_map
        assert "开放问题" in knowledge_map
        assert "查询提示" not in knowledge_map
