"""Tests for built-in skills."""

from pathlib import Path

from chatmd.engine.router import Router
from chatmd.skills.base import SkillContext
from chatmd.skills.builtin import DateSkill, HelpSkill, NowSkill, TimeSkill, register_builtin_skills


def _make_context(tmp_path: Path) -> SkillContext:
    return SkillContext(source_file=tmp_path / "chat.md", source_line=1, workspace=tmp_path)


class TestDateSkill:
    def test_default_format(self, tmp_path):
        skill = DateSkill()
        result = skill.execute("", {}, _make_context(tmp_path))
        assert result.success
        # Should look like YYYY-MM-DD
        assert len(result.output) == 10
        assert result.output[4] == "-"

    def test_custom_format(self, tmp_path):
        skill = DateSkill()
        result = skill.execute("", {"_positional": "%Y/%m/%d"}, _make_context(tmp_path))
        assert result.success
        assert "/" in result.output


class TestTimeSkill:
    def test_returns_time(self, tmp_path):
        skill = TimeSkill()
        result = skill.execute("", {}, _make_context(tmp_path))
        assert result.success
        assert ":" in result.output


class TestNowSkill:
    def test_returns_datetime(self, tmp_path):
        skill = NowSkill()
        result = skill.execute("", {}, _make_context(tmp_path))
        assert result.success
        assert "-" in result.output
        assert ":" in result.output


class TestHelpSkill:
    def test_lists_commands(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("", {}, _make_context(tmp_path))
        assert result.success
        assert "/date" in result.output
        assert "/help" in result.output

    def test_no_router_returns_error(self, tmp_path):
        skill = HelpSkill(router=None)
        result = skill.execute("", {}, _make_context(tmp_path))
        assert not result.success

    def test_grouped_output_has_overview_table(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("", {}, _make_context(tmp_path))
        assert result.success
        # Overview mode: group names in table rows
        assert "Date & Time" in result.output
        assert "Markdown Templates" in result.output
        assert "Utilities" in result.output
        assert "/help dt" in result.output

    def test_help_group_detail(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("datetime", {}, _make_context(tmp_path))
        assert result.success
        # Group detail shows individual commands
        assert "`/date`" in result.output
        assert "`/time`" in result.output

    def test_help_cmd_detail(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("date", {}, _make_context(tmp_path))
        assert result.success
        assert "## /date" in result.output
        assert "Description" in result.output

    def test_help_cmd_not_found(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("nonexistent", {}, _make_context(tmp_path))
        assert not result.success

    def test_help_group_empty(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        # AI group has no skills registered by default
        result = help_skill.execute("ai", {}, _make_context(tmp_path))
        assert result.success

    def test_help_group_alias_dt(self, tmp_path):
        """Short alias 'dt' should expand to datetime group."""
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("dt", {}, _make_context(tmp_path))
        assert result.success
        assert "`/date`" in result.output
        assert "`/time`" in result.output

    def test_help_group_alias_u(self, tmp_path):
        """Short alias 'u' should expand to utility group."""
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("u", {}, _make_context(tmp_path))
        assert result.success
        assert "`/help`" in result.output

    def test_help_group_alias_md(self, tmp_path):
        """Short alias 'md' should expand to markdown group."""
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("md", {}, _make_context(tmp_path))
        assert result.success

    def test_overview_shows_aliases(self, tmp_path):
        """Overview table should display short aliases in parentheses."""
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("", {}, _make_context(tmp_path))
        assert result.success
        assert "(`dt`)" in result.output
        assert "(`u`)" in result.output

    def test_classify_method(self):
        assert HelpSkill._classify(DateSkill()) == "datetime"
        assert HelpSkill._classify(HelpSkill()) == "utility"
        assert HelpSkill._classify(NowSkill()) == "datetime"


class TestRegisterBuiltinSkills:
    def test_all_registered(self):
        router = Router()
        register_builtin_skills(router)
        skills = router.list_skills()
        names = {s.name for s in skills}
        assert "date" in names
        assert "time" in names
        assert "now" in names
        assert "help" in names
