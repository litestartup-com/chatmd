"""README smoke tests — verify every user-facing command in README is actually routable.

This test guards against the failure mode where code exists in isolation but is
never wired into the Agent's initialization.  Every command listed in the README
"命令一览" table MUST be routable through a fully-initialized Agent instance.

Ref: rules/dev_workflow.md §9
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from chatmd.engine.agent import Agent
from chatmd.engine.parser import CommandType, Parser
from chatmd.skills.base import SkillContext

# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a minimal ChatMD workspace for Agent initialization."""
    chatmd_dir = tmp_path / ".chatmd"
    chatmd_dir.mkdir()
    (chatmd_dir / "skills").mkdir()
    (chatmd_dir / "memory").mkdir()
    (chatmd_dir / "logs").mkdir()
    (chatmd_dir / "history").mkdir()

    agent_yaml = {
        "version": "0.1",
        "workspace": {"mode": "full"},
        "ai": {"providers": []},
        "trigger": {
            "signals": [{"type": "file_save", "debounce_ms": 800}],
            "confirm": {"delay": 1.5, "skip": ["date", "time", "help", "status"]},
        },
        "watcher": {
            "debounce_ms": 300,
            "watch_files": ["chat.md"],
            "watch_dirs": ["chat/"],
            "ignore_patterns": ["_index.md"],
        },
        "commands": {"prefix": "/", "natural_language": {"enabled": True}},
        "async": {"max_concurrent": 3, "timeout": 60, "retry": 2},
        "sync": {"mode": "git", "auto_commit": True, "interval": 300},
        "logging": {"level": "INFO", "audit": True},
    }
    user_yaml = {
        "display_name": "",
        "language": "en",
        "preferences": {"result_format": "blockquote"},
        "aliases": {
            "en": "translate(English)",
            "jp": "translate(Japanese)",
            "cn": "translate(Chinese)",
            "q": "ask",
        },
    }

    with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
        yaml.dump(agent_yaml, f)
    with open(chatmd_dir / "user.yaml", "w", encoding="utf-8") as f:
        yaml.dump(user_yaml, f)

    # Create chat.md and chat/ directory
    (tmp_path / "chat.md").write_text("# ChatMD\n---\n", encoding="utf-8")
    (tmp_path / "chat").mkdir()

    return tmp_path


@pytest.fixture()
def agent(workspace: Path) -> Agent:
    """Create a fully-initialized Agent instance."""
    return Agent(workspace)


# ── README command routing smoke tests ───────────────────────────────────────

# Every command from README "命令一览" table
_README_COMMANDS = [
    "/help",
    "/date",
    "/time",
    "/now",
    "/ask question",
    "/translate(English) hello",
    "/status",
    "/list",
    "/sync",
    "/log",
    "/log 5",
]

# Aliases from README / user.yaml defaults
_README_ALIASES = [
    ("/h", "help"),
    ("/d", "date"),
    ("/st", "status"),
    ("/ls", "list"),
    ("/tran", "translate"),
    ("/q", "ask"),
]


class TestREADMECommandsRoutable:
    """Every command listed in README must be routable after Agent init."""

    @pytest.mark.parametrize("command", _README_COMMANDS)
    def test_command_routable(self, agent: Agent, command: str):
        parser = Parser()
        cmds = parser.parse_lines([command])
        assert len(cmds) == 1, f"Parser failed to parse: {command}"
        skill, resolved = agent.router.route(cmds[0])
        assert skill is not None, f"No skill found for: {command}"

    @pytest.mark.parametrize("alias,expected_skill", _README_ALIASES)
    def test_alias_routable(self, agent: Agent, alias: str, expected_skill: str):
        parser = Parser()
        cmds = parser.parse_lines([alias])
        assert len(cmds) == 1
        skill, resolved = agent.router.route(cmds[0])
        assert skill.name == expected_skill, (
            f"Alias {alias} routed to {skill.name}, expected {expected_skill}"
        )


class TestREADMECommandsExecutable:
    """Every README command must not only route but also execute successfully."""

    def _exec(self, agent: Agent, command: str) -> None:
        parser = Parser()
        cmds = parser.parse_lines([command])
        skill, resolved = agent.router.route(cmds[0])
        ctx = SkillContext(
            source_file=None, source_line=1, workspace=agent.workspace,
        )
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success, f"{command} failed: {result.error}"

    def test_help_executable(self, agent: Agent):
        self._exec(agent, "/help")

    def test_date_executable(self, agent: Agent):
        self._exec(agent, "/date")

    def test_time_executable(self, agent: Agent):
        self._exec(agent, "/time")

    def test_now_executable(self, agent: Agent):
        self._exec(agent, "/now")

    def test_status_executable(self, agent: Agent):
        self._exec(agent, "/status")

    def test_list_executable(self, agent: Agent):
        self._exec(agent, "/list")

    def test_log_executable(self, agent: Agent):
        self._exec(agent, "/log")

    def test_sync_executable_with_git_repo(self, tmp_path: Path):
        """Verify /sync works when sync.mode=git and workspace is a git repo."""

        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        for sub in ("skills", "memory", "logs", "history"):
            (chatmd_dir / sub).mkdir()

        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump({
                "version": "0.1",
                "ai": {"providers": []},
                "sync": {"mode": "git", "auto_commit": True, "interval": 300},
            }, f)
        with open(chatmd_dir / "user.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"language": "en", "aliases": {}}, f)

        (tmp_path / "chat.md").write_text("---\n", encoding="utf-8")
        (tmp_path / "chat").mkdir()

        # Init a git repo so sync_now() can actually run
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        agent = Agent(tmp_path)
        parser = Parser()
        cmds = parser.parse_lines(["/sync"])
        skill, resolved = agent.router.route(cmds[0])
        ctx = SkillContext(source_file=None, source_line=1, workspace=tmp_path)
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success, f"/sync failed: {result.error}"

    def test_sync_not_configured_error_gone(self, agent: Agent):
        """With sync.mode=git in config, /sync must NOT return 'not configured'."""
        parser = Parser()
        cmds = parser.parse_lines(["/sync"])
        skill, resolved = agent.router.route(cmds[0])
        ctx = SkillContext(
            source_file=None, source_line=1, workspace=agent.workspace,
        )
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        # Even without a .git dir it should NOT say "not configured"
        assert "not configured" not in (result.error or "")


class TestHelpListsAllREADMECommands:
    """/help output must include every command from README."""

    _EXPECTED_IN_HELP = ["help", "date", "time", "now", "ask", "translate",
                         "status", "list", "sync", "log"]

    def test_help_contains_all_commands(self, agent: Agent):
        parser = Parser()
        cmds = parser.parse_lines(["/help"])
        skill, resolved = agent.router.route(cmds[0])
        ctx = SkillContext(
            source_file=None, source_line=1, workspace=agent.workspace,
        )
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success

        for cmd in self._EXPECTED_IN_HELP:
            assert f"/{cmd}" in result.output, (
                f"/help output missing /{cmd}. Output:\n{result.output}"
            )


class TestCustomSkillDescriptionInHelp:
    """Custom skill descriptions must show actual description, not i18n key."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        for sub in ("skills", "memory", "logs", "history"):
            (chatmd_dir / sub).mkdir()

        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"version": "0.1", "ai": {"providers": []}}, f)
        with open(chatmd_dir / "user.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"language": "en", "aliases": {}}, f)

        (tmp_path / "chat.md").write_text("---\n", encoding="utf-8")
        (tmp_path / "chat").mkdir()
        return tmp_path

    def test_yaml_skill_description_in_help(self, tmp_path: Path):
        ws = self._make_workspace(tmp_path)
        (ws / ".chatmd" / "skills" / "greet.yaml").write_text(
            'name: greet\ndescription: "Say hello"\ntemplate: "Hi!"',
            encoding="utf-8",
        )
        agent = Agent(ws)
        parser = Parser()
        cmds = parser.parse_lines(["/help"])
        skill, resolved = agent.router.route(cmds[0])
        ctx = SkillContext(source_file=None, source_line=1, workspace=ws)
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success
        assert "Say hello" in result.output
        assert "skill.greet.description" not in result.output

    def test_python_skill_description_in_help(self, tmp_path: Path):
        ws = self._make_workspace(tmp_path)
        (ws / ".chatmd" / "skills" / "my_skill.py").write_text(
            'from chatmd.skills.base import Skill, SkillContext, SkillResult\n\n'
            'class EchoSkill(Skill):\n'
            '    name = "echo"\n'
            '    description = "Echo back input"\n'
            '    category = "custom"\n\n'
            '    def execute(self, input_text, args, context):\n'
            '        return SkillResult(success=True, output=input_text)\n',
            encoding="utf-8",
        )
        agent = Agent(ws)
        parser = Parser()
        cmds = parser.parse_lines(["/help"])
        skill, resolved = agent.router.route(cmds[0])
        ctx = SkillContext(source_file=None, source_line=1, workspace=ws)
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success
        assert "Echo back input" in result.output
        assert "skill.echo.description" not in result.output


class TestCustomSkillLoading:
    """Custom YAML and Python skills must be loadable via Agent init."""

    def test_yaml_skill_loaded(self, tmp_path: Path):
        """A YAML skill in .chatmd/skills/ must be routable after Agent init."""
        # Set up workspace with a custom YAML skill
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        for sub in ("skills", "memory", "logs", "history"):
            (chatmd_dir / sub).mkdir()

        agent_yaml = {
            "version": "0.1",
            "workspace": {"mode": "full"},
            "ai": {"providers": []},
        }
        user_yaml = {"language": "en", "aliases": {}}

        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(agent_yaml, f)
        with open(chatmd_dir / "user.yaml", "w", encoding="utf-8") as f:
            yaml.dump(user_yaml, f)

        (tmp_path / "chat.md").write_text("---\n", encoding="utf-8")
        (tmp_path / "chat").mkdir()

        # Create a YAML skill
        (chatmd_dir / "skills" / "greet.yaml").write_text(
            'name: greet\ndescription: "Hello"\n'
            'aliases: [hi, hello]\n'
            'template: "Hello, {{input}}!"',
            encoding="utf-8",
        )

        agent = Agent(tmp_path)

        parser = Parser()
        cmds = parser.parse_lines(["/greet World"])
        skill, resolved = agent.router.route(cmds[0])
        assert skill.name == "greet"
        ctx = SkillContext(source_file=None, source_line=1, workspace=tmp_path)
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success
        assert result.output == "Hello, World!"

    def test_yaml_skill_alias_routable(self, tmp_path: Path):
        """YAML skill aliases must also be routable."""
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        for sub in ("skills", "memory", "logs", "history"):
            (chatmd_dir / sub).mkdir()

        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"version": "0.1", "ai": {"providers": []}}, f)
        with open(chatmd_dir / "user.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"language": "en", "aliases": {}}, f)

        (tmp_path / "chat.md").write_text("---\n", encoding="utf-8")
        (tmp_path / "chat").mkdir()

        (chatmd_dir / "skills" / "greet.yaml").write_text(
            'name: greet\naliases: [hi, hello]\ntemplate: "Hi, {{input}}!"',
            encoding="utf-8",
        )

        agent = Agent(tmp_path)

        parser = Parser()
        for alias_cmd in ["/hi World", "/hello World"]:
            cmds = parser.parse_lines([alias_cmd])
            skill, resolved = agent.router.route(cmds[0])
            assert skill.name == "greet", f"{alias_cmd} did not route to greet"

    def test_python_skill_loaded(self, tmp_path: Path):
        """A Python skill in .chatmd/skills/ must be routable after Agent init."""
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        for sub in ("skills", "memory", "logs", "history"):
            (chatmd_dir / sub).mkdir()

        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"version": "0.1", "ai": {"providers": []}}, f)
        with open(chatmd_dir / "user.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"language": "en", "aliases": {}}, f)

        (tmp_path / "chat.md").write_text("---\n", encoding="utf-8")
        (tmp_path / "chat").mkdir()

        # Create a Python skill
        (chatmd_dir / "skills" / "my_skill.py").write_text(
            'from chatmd.skills.base import Skill, SkillContext, SkillResult\n\n'
            'class EchoSkill(Skill):\n'
            '    name = "echo"\n'
            '    description = "Echo input"\n'
            '    category = "custom"\n\n'
            '    def execute(self, input_text, args, context):\n'
            '        return SkillResult(success=True, output=input_text)\n',
            encoding="utf-8",
        )

        agent = Agent(tmp_path)

        parser = Parser()
        cmds = parser.parse_lines(["/echo hello world"])
        skill, resolved = agent.router.route(cmds[0])
        assert skill.name == "echo"
        ctx = SkillContext(source_file=None, source_line=1, workspace=tmp_path)
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success
        assert result.output == "hello world"


class TestAtAiRoutable:
    """@ai{} commands must be routable (even without AI provider configured)."""

    def test_at_ai_inline_routable(self, agent: Agent):
        parser = Parser()
        cmds = parser.parse_lines(["@ai{what is python}"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.AT_AI
        skill, resolved = agent.router.route(cmds[0])
        assert skill.name == "ask"

    def test_at_ai_block_routable(self, agent: Agent):
        parser = Parser()
        cmds = parser.parse_lines(["@ai{", "translate this", "}"])
        assert len(cmds) == 1
        skill, resolved = agent.router.route(cmds[0])
        assert skill.name == "ask"
