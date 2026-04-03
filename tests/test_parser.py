"""Tests for the command parser."""

from pathlib import Path

from chatmd.engine.parser import CommandType, Parser


class TestSlashCommands:
    """Test slash command parsing."""

    def setup_method(self):
        self.parser = Parser()

    def test_simple_command(self):
        cmd = self.parser.parse_changed_line("/date")
        assert cmd is not None
        assert cmd.type == CommandType.SLASH_CMD
        assert cmd.command == "date"
        assert cmd.input_text == ""
        assert cmd.args == {}

    def test_command_with_input(self):
        cmd = self.parser.parse_changed_line("/translate Hello World")
        assert cmd is not None
        assert cmd.command == "translate"
        assert cmd.input_text == "Hello World"

    def test_command_with_positional_param(self):
        cmd = self.parser.parse_changed_line("/translate(日文) Hello World")
        assert cmd is not None
        assert cmd.command == "translate"
        assert cmd.args["_positional"] == "日文"
        assert cmd.input_text == "Hello World"

    def test_command_with_named_param(self):
        cmd = self.parser.parse_changed_line("/translate(lang=日文) Hello")
        assert cmd is not None
        assert cmd.args["lang"] == "日文"
        assert cmd.input_text == "Hello"

    def test_command_no_params_no_input(self):
        cmd = self.parser.parse_changed_line("/help")
        assert cmd is not None
        assert cmd.command == "help"
        assert cmd.args == {}

    def test_empty_line_returns_none(self):
        assert self.parser.parse_changed_line("") is None
        assert self.parser.parse_changed_line("   ") is None

    def test_non_command_returns_none(self):
        assert self.parser.parse_changed_line("Hello World") is None
        assert self.parser.parse_changed_line("This is normal text") is None


class TestAtAi:
    """Test @ai{} syntax parsing."""

    def setup_method(self):
        self.parser = Parser()

    def test_at_ai_simple(self):
        cmd = self.parser.parse_changed_line("@ai{帮我翻译这段话}")
        assert cmd is not None
        assert cmd.type == CommandType.AT_AI
        assert cmd.input_text == "帮我翻译这段话"

    def test_at_ai_with_spaces(self):
        cmd = self.parser.parse_changed_line("@ai{帮我翻译上面这段话成日文}")
        assert cmd is not None
        assert cmd.input_text == "帮我翻译上面这段话成日文"


class TestProtectedRegions:
    """Test that commands in code fences and blockquotes are skipped."""

    def setup_method(self):
        self.parser = Parser()

    def test_code_fence_protection(self):
        lines = [
            "Some text",
            "```",
            "/date",
            "```",
            "/help",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "help"

    def test_blockquote_protection(self):
        lines = [
            "/date",
            "> /help",
            "> some result",
            "/time",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 2
        assert commands[0].command == "date"
        assert commands[1].command == "time"

    def test_nested_code_fence(self):
        lines = [
            "```python",
            "def foo():",
            "    return '/date'",
            "```",
            "/now",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "now"

    def test_source_line_tracking(self):
        lines = [
            "Hello",
            "/date",
            "",
            "/help",
        ]
        commands = self.parser.parse_lines(lines, source_file=Path("test.md"))
        assert len(commands) == 2
        assert commands[0].source_line == 2
        assert commands[1].source_line == 4
        assert commands[0].source_file == Path("test.md")
