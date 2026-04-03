"""Tests for Markdown template skills (T-047)."""

from pathlib import Path

from chatmd.skills.base import SkillContext
from chatmd.skills.builtin import (
    CodeSkill,
    DoneSkill,
    HeadingSkill,
    HrSkill,
    ImgSkill,
    LinkSkill,
    QuoteSkill,
    TableSkill,
    TodoSkill,
)


def _ctx(tmp_path: Path) -> SkillContext:
    return SkillContext(source_file=tmp_path / "chat.md", source_line=1, workspace=tmp_path)


# ── /todo and /done ──────────────────────────────────────────────────────


class TestTodoSkill:
    def test_empty(self, tmp_path):
        skill = TodoSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "- [ ] "

    def test_with_text(self, tmp_path):
        skill = TodoSkill()
        result = skill.execute("Buy milk", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "- [ ] Buy milk"

    def test_name_and_aliases(self):
        skill = TodoSkill()
        assert skill.name == "todo"
        assert "td" in skill.aliases


class TestDoneSkill:
    def test_empty(self, tmp_path):
        skill = DoneSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "- [x] "

    def test_with_text(self, tmp_path):
        skill = DoneSkill()
        result = skill.execute("Buy milk", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "- [x] Buy milk"

    def test_name_and_aliases(self):
        skill = DoneSkill()
        assert skill.name == "done"
        assert "dn2" in skill.aliases


# ── /table ───────────────────────────────────────────────────────────────


class TestTableSkill:
    def test_default_3x3(self, tmp_path):
        skill = TableSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        lines = result.output.splitlines()
        # header + separator + 3 body rows
        assert len(lines) == 5
        assert "Col1" in lines[0]
        assert "Col3" in lines[0]
        assert "---" in lines[1]

    def test_custom_size(self, tmp_path):
        skill = TableSkill()
        result = skill.execute("", {"_positional": "4x2"}, _ctx(tmp_path))
        assert result.success
        lines = result.output.splitlines()
        # header + sep + 2 body rows
        assert len(lines) == 4
        assert "Col4" in lines[0]

    def test_invalid_spec_fallback(self, tmp_path):
        skill = TableSkill()
        result = skill.execute("", {"_positional": "abc"}, _ctx(tmp_path))
        assert result.success
        lines = result.output.splitlines()
        assert len(lines) == 5  # default 3x3

    def test_name_and_aliases(self):
        skill = TableSkill()
        assert skill.name == "table"
        assert "tb" in skill.aliases


# ── /code ────────────────────────────────────────────────────────────────


class TestCodeSkill:
    def test_default_python(self, tmp_path):
        skill = CodeSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "```python\n\n```"

    def test_custom_language(self, tmp_path):
        skill = CodeSkill()
        result = skill.execute("", {"_positional": "javascript"}, _ctx(tmp_path))
        assert result.success
        assert result.output == "```javascript\n\n```"

    def test_name_and_aliases(self):
        skill = CodeSkill()
        assert skill.name == "code"
        assert "c" in skill.aliases


# ── /link ────────────────────────────────────────────────────────────────


class TestLinkSkill:
    def test_output(self, tmp_path):
        skill = LinkSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "[text](url)"

    def test_name_and_aliases(self):
        skill = LinkSkill()
        assert skill.name == "link"
        assert "ln" in skill.aliases


# ── /img ─────────────────────────────────────────────────────────────────


class TestImgSkill:
    def test_output(self, tmp_path):
        skill = ImgSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "![alt](url)"

    def test_name_and_aliases(self):
        skill = ImgSkill()
        assert skill.name == "img"
        assert "i" in skill.aliases


# ── /hr ──────────────────────────────────────────────────────────────────


class TestHrSkill:
    def test_output(self, tmp_path):
        skill = HrSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "---"

    def test_name_and_aliases(self):
        skill = HrSkill()
        assert skill.name == "hr"
        assert skill.aliases == []


# ── /heading ─────────────────────────────────────────────────────────────


class TestHeadingSkill:
    def test_default_h2(self, tmp_path):
        skill = HeadingSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "## "

    def test_custom_level(self, tmp_path):
        skill = HeadingSkill()
        result = skill.execute("Title", {"_positional": "3"}, _ctx(tmp_path))
        assert result.success
        assert result.output == "### Title"

    def test_level_clamped(self, tmp_path):
        skill = HeadingSkill()
        result = skill.execute("", {"_positional": "10"}, _ctx(tmp_path))
        assert result.success
        assert result.output.startswith("######")  # max H6

    def test_invalid_level_fallback(self, tmp_path):
        skill = HeadingSkill()
        result = skill.execute("", {"_positional": "abc"}, _ctx(tmp_path))
        assert result.success
        assert result.output == "## "  # default H2

    def test_name_and_aliases(self):
        skill = HeadingSkill()
        assert skill.name == "heading"
        assert "hd" in skill.aliases


# ── /quote ───────────────────────────────────────────────────────────────


class TestQuoteSkill:
    def test_empty(self, tmp_path):
        skill = QuoteSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "> "

    def test_with_text(self, tmp_path):
        skill = QuoteSkill()
        result = skill.execute("Hello world", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "> Hello world"

    def test_multiline(self, tmp_path):
        skill = QuoteSkill()
        result = skill.execute("Line 1\nLine 2", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "> Line 1\n> Line 2"

    def test_name_and_aliases(self):
        skill = QuoteSkill()
        assert skill.name == "quote"
        assert "q" in skill.aliases
