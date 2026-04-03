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

    def test_grouped_output_has_section_headers(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("", {}, _make_context(tmp_path))
        assert result.success
        # Should have group headers (en default)
        assert "### Date & Time" in result.output
        assert "### Markdown Templates" in result.output
        assert "### Utilities" in result.output

    def test_datetime_skills_in_datetime_group(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("", {}, _make_context(tmp_path))
        output = result.output
        # /date should appear after "Date & Time" header
        dt_pos = output.index("Date & Time")
        date_pos = output.index("`/date`")
        assert date_pos > dt_pos

    def test_utility_skills_in_utility_group(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("", {}, _make_context(tmp_path))
        output = result.output
        util_pos = output.index("Utilities")
        help_pos = output.index("`/help`")
        assert help_pos > util_pos

    def test_ai_group_not_shown_when_no_ai_skills(self, tmp_path):
        router = Router()
        register_builtin_skills(router)
        help_skill = router.get_skill("help")
        result = help_skill.execute("", {}, _make_context(tmp_path))
        # No AI skills registered, so AI section should not appear
        assert "### AI" not in result.output

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
