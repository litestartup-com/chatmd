"""Tests for /cmd{text} inline command parsing and execution (T-038).

Syntax: /cmd{text} or /cmd(params){text} anywhere in a line.
The /cmd{...} portion is replaced in-place with the skill result.
"""

from chatmd.engine.parser import CommandType, Parser


class TestInlineCmdParsing:
    """Test /cmd{text} inline command detection."""

    def setup_method(self):
        self.parser = Parser()

    def test_single_inline_cmd(self):
        """Single /en{text} in a line."""
        lines = ["Today I learned /en{量子纠缠} in class."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        cmd = commands[0]
        assert cmd.type == CommandType.INLINE_CMD
        assert cmd.command == "en"
        assert cmd.input_text == "量子纠缠"
        assert cmd.source_line == 1

    def test_multiple_inline_cmds_same_line(self):
        """Multiple /cmd{text} on one line."""
        lines = ["I like /en{苹果} and /en{香蕉}."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 2
        assert commands[0].input_text == "苹果"
        assert commands[1].input_text == "香蕉"

    def test_inline_cmd_with_params(self):
        """/translate(日文){你好} — with params."""
        lines = ["She said /translate(日文){你好} to me."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "translate"
        assert commands[0].args["_positional"] == "日文"
        assert commands[0].input_text == "你好"

    def test_inline_cmd_raw_text(self):
        """raw_text should be the full /cmd{text} match."""
        lines = ["Hello /en{世界} there."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].raw_text == "/en{世界}"

    def test_unclosed_brace_ignored(self):
        """Unclosed { should not trigger."""
        lines = ["This /en{unclosed text never ends."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 0

    def test_escaped_brace_in_text(self):
        r"""Escaped \} inside text should not close the block."""
        lines = [r"Format /en{use \} for closing} here."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].input_text == r"use \} for closing"

    def test_inline_cmd_in_code_block_ignored(self):
        """Inline commands inside code blocks should be ignored."""
        lines = [
            "```",
            "This /en{text} is protected.",
            "```",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 0

    def test_inline_cmd_in_backtick_ignored(self):
        """Inline commands inside backticks should be ignored."""
        lines = ["Use `code /en{text} here` in markdown."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 0

    def test_no_nesting(self):
        """/en{/jp{text}} — nesting not supported, inner / is literal."""
        lines = ["/en{/jp{text}}"]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        # The first } closes the brace, so input is "/jp{text"
        assert commands[0].input_text == "/jp{text"

    def test_inline_cmd_at_line_start(self):
        """/en{text} at line start should still be INLINE_CMD, not SLASH_CMD."""
        lines = ["/en{hello world}"]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].type == CommandType.INLINE_CMD
        assert commands[0].command == "en"
        assert commands[0].input_text == "hello world"

    def test_inline_cmd_coexists_with_slash_cmd(self):
        """Line-start /cmd and inline /cmd{} on different lines."""
        lines = [
            "/date",
            "Translate /en{你好} for me.",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 2
        assert commands[0].type == CommandType.SLASH_CMD
        assert commands[0].command == "date"
        assert commands[1].type == CommandType.INLINE_CMD
        assert commands[1].command == "en"

    def test_inline_cmd_empty_text_ignored(self):
        """/en{} with empty text should be ignored."""
        lines = ["Empty /en{} here."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 0

    def test_inline_cmd_in_blockquote_ignored(self):
        """Inline commands in blockquotes should be ignored."""
        lines = ["> Some /en{text} in a quote."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 0

    def test_at_ai_priority_over_inline_cmd(self):
        """@ai{} should take priority over /cmd{} on the same line."""
        lines = ["Check @ai{what is AI} and /en{hello}."]
        commands = self.parser.parse_lines(lines)
        # @ai{} takes priority — the entire line is handled as AT_AI
        assert len(commands) == 1
        assert commands[0].type == CommandType.AT_AI

    def test_inline_cmd_preserves_whitespace(self):
        """Whitespace inside braces should be preserved."""
        lines = ["See /en{  hello world  } here."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].input_text == "  hello world  "


class TestInlineCmdParsedFields:
    """Test that ParsedCommand fields are correctly set for inline commands."""

    def setup_method(self):
        self.parser = Parser()

    def test_source_line_tracked(self):
        lines = [
            "First line.",
            "Second /en{hello} line.",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].source_line == 2

    def test_multiple_inline_same_line_same_source_line(self):
        lines = ["Word /en{a} and /en{b} end."]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 2
        assert commands[0].source_line == 1
        assert commands[1].source_line == 1
