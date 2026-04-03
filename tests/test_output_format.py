"""Tests for Agent output formatting — two-tier strategy + AI conversation display."""

from chatmd.engine.agent import Agent


class TestFormatOutputSimple:
    """Tier 1: Simple commands — direct replacement, no wrapping."""

    def test_plain_text_direct_replacement(self):
        result = Agent._format_output(Agent, "2026-03-30", "date", 0.01, "builtin")
        assert result == "2026-03-30"

    def test_time_direct_replacement(self):
        result = Agent._format_output(Agent, "16:30:00", "time", 0.01, "builtin")
        assert result == "16:30:00"

    def test_no_wrapping_for_plain(self):
        result = Agent._format_output(Agent, "- [ ] ", "todo", 0.01, "builtin")
        # No blockquote header, no separator
        assert not result.startswith(">")
        assert "---" not in result


class TestFormatOutputRichText:
    """Tier 2: Rich text commands — blockquote header + body + separator."""

    def test_heading_triggers_rich(self):
        output = "## Available Commands\n\n| cmd | desc |"
        result = Agent._format_output(Agent, output, "help", 0.03, "builtin")
        assert result.startswith("> chatmd /help 0.03s")
        assert "## Available Commands" in result
        assert result.endswith("---")

    def test_table_triggers_rich(self):
        output = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = Agent._format_output(Agent, output, "list", 0.02, "builtin")
        assert result.startswith("> chatmd /list 0.02s")
        assert result.endswith("---")

    def test_bold_triggers_rich(self):
        output = "**Important** info here"
        result = Agent._format_output(Agent, output, "status", 0.01, "builtin")
        assert result.startswith("> chatmd /status 0.01s")

    def test_image_triggers_rich(self):
        output = "![alt](image.png)"
        result = Agent._format_output(Agent, output, "img", 0.01, "builtin")
        assert result.startswith("> chatmd /img 0.01s")


class TestFormatOutputAI:
    """AI commands — rich text with conversation display (You/AI)."""

    def test_ai_uses_rich_format_not_code_block(self):
        result = Agent._format_output(
            Agent, "AI response", "ask", 1.20, "ai", input_text="Hello",
        )
        # Should NOT contain code block markers
        assert "```" not in result
        # Should use rich text format
        assert result.startswith("> chatmd /ask 1.20s")
        assert result.endswith("---")

    def test_ai_shows_conversation(self):
        result = Agent._format_output(
            Agent, "量子纠缠是一种现象", "ask", 1.20, "ai",
            input_text="什么是量子纠缠？",
        )
        assert "**You:** 什么是量子纠缠？" in result
        assert "**AI:** 量子纠缠是一种现象" in result

    def test_ai_translate_shows_conversation(self):
        result = Agent._format_output(
            Agent, "你好，你好吗？", "translate", 0.85, "ai",
            input_text="Hello, how are you?",
        )
        assert "**You:** Hello, how are you?" in result
        assert "**AI:** 你好，你好吗？" in result

    def test_ai_full_structure(self):
        result = Agent._format_output(
            Agent, "response text", "ask", 2.00, "ai",
            input_text="question text",
        )
        lines = result.split("\n")
        # Line 0: > chatmd /ask 2.00s
        assert lines[0] == "> chatmd /ask 2.00s"
        # Line 1: empty
        assert lines[1] == ""
        # Line 2: **You:** question text
        assert lines[2] == "**You:** question text"
        # Line 3: empty
        assert lines[3] == ""
        # Line 4: **AI:** response text
        assert lines[4] == "**AI:** response text"
        # Line 5: empty
        assert lines[5] == ""
        # Line 6: ---
        assert lines[6] == "---"

    def test_ai_empty_input_text(self):
        result = Agent._format_output(
            Agent, "response", "ask", 1.00, "ai", input_text="",
        )
        assert "**You:** " in result
        assert "**AI:** response" in result

    def test_ai_no_elapsed(self):
        result = Agent._format_output(
            Agent, "resp", "ask", 0.0, "ai", input_text="q",
        )
        assert result.startswith("> chatmd /ask")
        assert "**You:** q" in result


class TestTruncateInput:
    """User input truncation for AI conversation display."""

    def test_short_input_not_truncated(self):
        text = "short question"
        assert Agent._truncate_input(text) == "short question"

    def test_exactly_80_chars_not_truncated(self):
        text = "a" * 80
        assert Agent._truncate_input(text) == text

    def test_over_80_chars_truncated(self):
        text = "a" * 100
        result = Agent._truncate_input(text)
        assert result == "a" * 80 + "..."
        assert len(result) == 83

    def test_multiline_collapsed_to_single_line(self):
        text = "line one\nline two\nline three"
        result = Agent._truncate_input(text)
        assert "\n" not in result
        assert result == "line one line two line three"

    def test_multiline_long_truncated(self):
        text = "word " * 30  # 150 chars
        result = Agent._truncate_input(text)
        assert len(result) == 83  # 80 + "..."
        assert result.endswith("...")

    def test_empty_input(self):
        assert Agent._truncate_input("") == ""

    def test_whitespace_only(self):
        result = Agent._truncate_input("   \n  \t  ")
        assert result == ""


class TestFormatOutputNoCodeBlock:
    """Ensure the old code-block format is completely removed."""

    def test_ai_never_uses_code_fence(self):
        result = Agent._format_output(
            Agent, "long response\nwith multiple\nlines", "ask", 1.50, "ai",
            input_text="test question",
        )
        assert "```chatmd" not in result
        assert "```" not in result

    def test_ai_always_rich_even_plain_output(self):
        result = Agent._format_output(
            Agent, "simple answer", "ask", 0.50, "ai",
            input_text="simple question",
        )
        # Even plain text AI output should use rich format
        assert result.startswith("> chatmd /ask 0.50s")
        assert "**You:**" in result
        assert "**AI:**" in result
        assert result.endswith("---")
