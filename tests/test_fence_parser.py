"""Tests for ::: fence (long text) parsing in Parser.

Fence syntax: /command ::: or /command::: on the same line opens a fence.
Closing ::: must be on its own line.
"""

from chatmd.engine.parser import CommandType, Parser


class TestFenceParsing:
    """Test ::: inline fence multi-line input collection."""

    def setup_method(self):
        self.parser = Parser()

    def test_basic_fence_with_space(self):
        """/translate(English) ::: — space before :::"""
        lines = [
            "/translate(English) :::",
            "First paragraph.",
            "",
            "Second paragraph.",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        cmd = commands[0]
        assert cmd.type == CommandType.SLASH_CMD
        assert cmd.command == "translate"
        assert cmd.args["_positional"] == "English"
        assert "First paragraph." in cmd.input_text
        assert "Second paragraph." in cmd.input_text
        assert cmd.source_line == 1

    def test_basic_fence_no_space(self):
        """/translate(English)::: — no space before :::"""
        lines = [
            "/translate(English):::",
            "Hello world.",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "translate"
        assert commands[0].input_text == "Hello world."

    def test_fence_no_params(self):
        """/summary ::: — command without params"""
        lines = [
            "/summary :::",
            "Some text to summarize.",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "summary"
        assert commands[0].input_text == "Some text to summarize."

    def test_fence_no_params_no_space(self):
        """/summary::: — command without params, no space"""
        lines = [
            "/summary:::",
            "Text here.",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "summary"
        assert commands[0].input_text == "Text here."

    def test_fence_preserves_markdown(self):
        lines = [
            "/summary :::",
            "## Heading",
            "",
            "**Bold text** and `code`.",
            "",
            "> A blockquote inside fence",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert "## Heading" in commands[0].input_text
        assert "**Bold text**" in commands[0].input_text
        assert "> A blockquote inside fence" in commands[0].input_text

    def test_fence_preserves_code_block(self):
        lines = [
            "/ask :::",
            "Explain this code:",
            "```python",
            "def foo():",
            "    return 42",
            "```",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert "```python" in commands[0].input_text
        assert "def foo():" in commands[0].input_text

    def test_unclosed_fence_no_command(self):
        """Unclosed fence should not trigger command execution."""
        lines = [
            "/translate(English) :::",
            "Some text without closing fence.",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 0

    def test_fence_raw_text_includes_full_block(self):
        """raw_text should cover the command + entire fence block for replacement."""
        lines = [
            "/translate(English) :::",
            "Hello world.",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert ":::" in commands[0].raw_text
        assert "/translate(English)" in commands[0].raw_text

    def test_fence_end_line_tracked(self):
        """end_line should point to the closing ::: line."""
        lines = [
            "/translate(English) :::",
            "Line A",
            "Line B",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].source_line == 1
        assert commands[0].end_line == 4

    def test_multiple_fenced_commands(self):
        lines = [
            "/translate(English) :::",
            "Text A",
            ":::",
            "",
            "/summary :::",
            "Text B",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 2
        assert commands[0].input_text == "Text A"
        assert commands[1].input_text == "Text B"

    def test_command_after_fence(self):
        """Normal commands after a fenced command should still work."""
        lines = [
            "/translate(English) :::",
            "Fenced text.",
            ":::",
            "/date",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 2
        assert commands[0].command == "translate"
        assert commands[0].input_text == "Fenced text."
        assert commands[1].command == "date"

    def test_fence_inside_code_block_ignored(self):
        """Fence markers inside code blocks should be ignored."""
        lines = [
            "```",
            "/translate :::",
            "Protected text",
            ":::",
            "```",
            "/date",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "date"

    def test_fence_empty_content(self):
        """Empty fence should result in empty input_text."""
        lines = [
            "/ask :::",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].input_text == ""

    def test_command_without_fence_executes_normally(self):
        """/date (no :::) should execute immediately."""
        lines = [
            "/date",
            "",
            "some text",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "date"

    def test_command_with_input_text_not_fence(self):
        """/translate(English) Hello — normal input, not fence."""
        lines = [
            "/translate(English) Hello World",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "translate"
        assert commands[0].input_text == "Hello World"
        assert commands[0].end_line == 0

    def test_command_with_text_and_triple_colon_not_fence(self):
        """/cmd ::: some text — ::: followed by text is not a fence."""
        lines = [
            "/translate(English) ::: some text",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        # ::: followed by text → treated as normal input
        assert commands[0].input_text == "::: some text"
        assert commands[0].end_line == 0

    def test_command_at_eof(self):
        """/date at EOF should still be emitted."""
        lines = [
            "Some text",
            "/date",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 1
        assert commands[0].command == "date"

    def test_standalone_triple_colon_ignored(self):
        """Standalone ::: without a preceding command is just text."""
        lines = [
            "Some text",
            ":::",
            "Not a command fence.",
            ":::",
        ]
        commands = self.parser.parse_lines(lines)
        assert len(commands) == 0
