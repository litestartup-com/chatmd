"""Tests for AI command output preserving original text (T-039b).

When an AI command executes, the original user text should be preserved
above the chatmd output block.  The /cmd syntax and ::: markers are
stripped, leaving only the user's content.
"""

from pathlib import Path
from unittest.mock import MagicMock

from chatmd.engine.agent import Agent
from chatmd.skills.base import SkillResult


class TestExtractUserText:
    """Test _extract_user_text static helper."""

    def test_simple_text(self):
        assert Agent._extract_user_text("Hello world") == "Hello world"

    def test_strips_whitespace(self):
        assert Agent._extract_user_text("  hello  ") == "hello"

    def test_empty_input(self):
        assert Agent._extract_user_text("") == ""

    def test_none_like_empty(self):
        assert Agent._extract_user_text("") == ""

    def test_multiline_preserved(self):
        text = "line one\nline two\nline three"
        assert Agent._extract_user_text(text) == text.strip()


class TestWriteSkillResultAI:
    """Test that _write_skill_result preserves original text for AI commands."""

    def _make_agent_mock(self):
        """Create a minimal mock agent with the methods we need."""
        agent = MagicMock(spec=Agent)
        agent._format_output = Agent._format_output.__get__(agent, Agent)
        agent._extract_user_text = Agent._extract_user_text
        agent._write_skill_result = Agent._write_skill_result.__get__(agent, Agent)
        agent._write_back = MagicMock()
        agent._kernel_gate = MagicMock()
        agent._AI_INPUT_TRUNCATE_LEN = 80
        agent._RICH_TEXT_RE = Agent._RICH_TEXT_RE
        agent._truncate_input = Agent._truncate_input
        return agent

    def test_ai_result_preserves_original_text(self):
        agent = self._make_agent_mock()
        result = SkillResult(success=True, output="Rewritten text here")
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 5, "/rewrite Original text", "rewrite", 0.5,
            "ai", result, input_text="Original text", end_line=0,
        )

        # _write_back should have been called with combined text
        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]  # 5th positional arg is new_text

        # Should start with preserved original text
        assert new_text.startswith("Original text\n\n")
        # Should contain the chatmd info header
        assert "> chatmd /rewrite" in new_text
        # Should contain AI conversation
        assert "**You:** Original text" in new_text
        assert "**AI:** Rewritten text here" in new_text
        # Should end with separator
        assert new_text.endswith("---")

    def test_ai_result_fence_preserves_original_text(self):
        agent = self._make_agent_mock()
        result = SkillResult(success=True, output="Summary of the text")
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 3, "/summary :::\nLong text\nMore text\n:::",
            "summary", 1.2, "ai", result,
            input_text="Long text\nMore text", end_line=6,
        )

        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]

        # Should start with preserved text (fence content)
        assert new_text.startswith("Long text\nMore text\n\n")
        # Should have AI output below
        assert "> chatmd /summary" in new_text
        assert "**AI:** Summary of the text" in new_text

    def test_non_ai_does_not_preserve_text(self):
        agent = self._make_agent_mock()
        result = SkillResult(success=True, output="2026-03-31")
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 1, "/date", "date", 0.01,
            "builtin", result, input_text="", end_line=0,
        )

        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]

        # Non-AI: direct replacement, no preserved text prefix
        assert new_text == "2026-03-31"

    def test_ai_error_does_not_preserve_text(self):
        agent = self._make_agent_mock()
        result = SkillResult(success=False, output="", error="Provider timeout")
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 5, "/rewrite text", "rewrite", 0.0,
            "ai", result, input_text="text", end_line=0,
        )

        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]

        # Errors: show error, don't preserve text
        assert "❌" in new_text
        assert "Provider timeout" in new_text

    def test_ai_empty_input_still_works(self):
        agent = self._make_agent_mock()
        result = SkillResult(success=True, output="Response")
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 1, "/ask", "ask", 0.5,
            "ai", result, input_text="", end_line=0,
        )

        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]

        # Empty input: no preserved text prefix, just the output
        assert new_text.startswith("> chatmd /ask")


class TestWriteSkillResultInformational:
    """Regression tests for T-R083 / T-123.2 — informational result rendering.

    Bug D (chatmd-dev): a SkillResult with success=False, informational=True
    used to be rendered as `❌ {error or 'Unknown error'}`. Since informational
    results carry their human-friendly text in `output` and leave `error=None`,
    users saw "❌ Unknown error" instead of e.g. the /bind missing-token help.

    Fix: _write_skill_result now branches on `informational and output` to
    render the output verbatim, falling back to the error template only for
    real failures. These tests guard against regressing.
    """

    def _make_agent_mock(self):
        """Create a minimal mock agent with the methods we need."""
        agent = MagicMock(spec=Agent)
        agent._format_output = Agent._format_output.__get__(agent, Agent)
        agent._extract_user_text = Agent._extract_user_text
        agent._write_skill_result = Agent._write_skill_result.__get__(agent, Agent)
        agent._write_back = MagicMock()
        agent._kernel_gate = MagicMock()
        agent._AI_INPUT_TRUNCATE_LEN = 80
        agent._RICH_TEXT_RE = Agent._RICH_TEXT_RE
        agent._truncate_input = Agent._truncate_input
        return agent

    def test_informational_result_renders_output_verbatim(self):
        """success=False + informational=True + output=<help text> → render output as-is."""
        agent = self._make_agent_mock()
        help_text = (
            "⚠️ You already have an active binding:\n"
            "- Platform: **telegram**\n"
            "- Repo: `https://github.com/u***/r***.git`"
        )
        result = SkillResult(
            success=False,
            output=help_text,
            error=None,
            informational=True,
        )
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 1, "/bind ghp_xxx", "bind", 0.0,
            "general", result, input_text="ghp_xxx", end_line=0,
        )

        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]

        # Must NOT be the generic "Unknown error" template
        assert "Unknown error" not in new_text
        assert "❌" not in new_text
        # Must render the informational output verbatim
        assert new_text == help_text

    def test_real_error_still_uses_error_template(self):
        """success=False + informational=False + error=<msg> → render ❌ <msg>."""
        agent = self._make_agent_mock()
        result = SkillResult(
            success=False,
            output="",
            error="Network timeout after 30s",
            informational=False,
        )
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 1, "/bind ghp_xxx", "bind", 0.0,
            "general", result, input_text="ghp_xxx", end_line=0,
        )

        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]

        # Real errors keep the ❌ template + concrete error message
        assert "❌" in new_text
        assert "Network timeout after 30s" in new_text

    def test_informational_without_output_falls_through_to_error_template(self):
        """Defensive: informational=True but output='' should still fall through to error template.

        This shouldn't happen in practice (informational implies output carries
        the message) but the guard prevents a silent empty render if a skill
        author misuses the flag.
        """
        agent = self._make_agent_mock()
        result = SkillResult(
            success=False,
            output="",  # empty
            error=None,
            informational=True,
        )
        filepath = Path("/tmp/chat.md")

        agent._write_skill_result(
            filepath, 1, "/bind", "bind", 0.0,
            "general", result, input_text="", end_line=0,
        )

        agent._write_back.assert_called_once()
        call_args = agent._write_back.call_args
        new_text = call_args[0][4]

        # Falls through to "❌ Unknown error" — visible failure beats silent
        assert "❌" in new_text
        assert "Unknown error" in new_text or "unknown" in new_text.lower()
