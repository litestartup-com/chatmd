"""Integration tests for suffix trigger mode — verifies Parser + SuffixTrigger end-to-end."""

from __future__ import annotations

from pathlib import Path

from chatmd.engine.parser import CommandType, Parser
from chatmd.watcher.suffix_trigger import SuffixTrigger


def _make_parser(enabled: bool = True, marker: str = ";") -> Parser:
    """Create a Parser with a SuffixTrigger attached."""
    parser = Parser(command_prefix="/")
    trigger = SuffixTrigger(marker=marker, enabled=enabled)
    parser.set_suffix_trigger(trigger)
    return parser


class TestSuffixModeSlashCommands:
    """Slash commands require suffix marker when suffix mode is enabled."""

    def test_slash_cmd_with_suffix_triggers(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["/help;"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.SLASH_CMD
        assert cmds[0].command == "help"

    def test_slash_cmd_without_suffix_ignored(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["/help"])
        assert len(cmds) == 0

    def test_slash_cmd_with_args_and_suffix(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["/ask what is ChatMD?;"])
        assert len(cmds) == 1
        assert cmds[0].command == "ask"
        assert cmds[0].input_text == "what is ChatMD?"

    def test_slash_cmd_with_params_and_suffix(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["/translate(English) hello world;"])
        assert len(cmds) == 1
        assert cmds[0].command == "translate"
        assert cmds[0].input_text == "hello world"

    def test_slash_cmd_normal_when_suffix_disabled(self) -> None:
        parser = _make_parser(enabled=False)
        cmds = parser.parse_lines(["/help"])
        assert len(cmds) == 1
        assert cmds[0].command == "help"


class TestSuffixModeNaturallyClosedSyntax:
    """Naturally-closed syntaxes do NOT require suffix marker."""

    def test_at_ai_inline_no_suffix_needed(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["@ai{what is Python?}"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.AT_AI
        assert cmds[0].input_text == "what is Python?"

    def test_at_ai_block_no_suffix_needed(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines([
            "@ai{",
            "Tell me about Python",
            "}",
        ])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.AT_AI

    def test_inline_cmd_braces_no_suffix_needed(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["/translate{hello world}"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.INLINE_CMD

    def test_content_fence_no_suffix_needed(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines([
            "/translate(English) :::",
            "hello world",
            ":::",
        ])
        assert len(cmds) == 1
        assert cmds[0].command == "translate"
        assert cmds[0].input_text == "hello world"


class TestSuffixModeOpenChat:
    """Plain text (open chat) requires suffix marker when enabled."""

    def test_open_chat_with_suffix(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["summarize this document;"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.OPEN_CHAT
        assert cmds[0].input_text == "summarize this document"

    def test_open_chat_without_suffix_ignored(self) -> None:
        parser = _make_parser(enabled=True)
        cmds = parser.parse_lines(["summarize this document"])
        assert len(cmds) == 0


class TestSuffixModeAgentWiring:
    """Verify Agent reads config and wires SuffixTrigger into Parser."""

    def test_agent_wires_suffix_trigger(self, tmp_path: Path) -> None:
        import yaml

        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        agent_yaml = {
            "trigger": {
                "signals": [
                    {"type": "file_save", "debounce_ms": 800},
                    {"type": "suffix", "marker": ";", "enabled": True},
                ],
            },
        }
        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(agent_yaml, f)
        (chatmd_dir / "user.yaml").write_text("language: en\n", encoding="utf-8")

        from chatmd.engine.agent import Agent

        agent = Agent(tmp_path)

        # Parser should have suffix trigger wired
        assert agent._parser._suffix_trigger is not None
        assert agent._parser._suffix_trigger.enabled is True
        assert agent._parser._suffix_trigger.marker == ";"

    def test_agent_suffix_disabled_by_default(self, tmp_path: Path) -> None:
        import yaml

        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        agent_yaml = {
            "trigger": {
                "signals": [
                    {"type": "file_save", "debounce_ms": 800},
                    {"type": "suffix", "marker": ";", "enabled": False},
                ],
            },
        }
        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(agent_yaml, f)
        (chatmd_dir / "user.yaml").write_text("language: en\n", encoding="utf-8")

        from chatmd.engine.agent import Agent

        agent = Agent(tmp_path)

        # Suffix trigger attached but disabled
        assert agent._parser._suffix_trigger is not None
        assert agent._parser._suffix_trigger.enabled is False

        # Slash commands should work normally without suffix
        cmds = agent._parser.parse_lines(["/help"])
        assert len(cmds) == 1
