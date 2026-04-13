"""End-to-end integration tests for v0.2.0 (T-048).

These tests verify the full skill registration + routing pipeline,
ensuring all v0.2.0 commands are accessible and produce valid output.
"""

from __future__ import annotations

import re
from pathlib import Path

from chatmd.engine.router import Router
from chatmd.skills.base import SkillContext
from chatmd.skills.builtin import register_builtin_skills


def _ctx(tmp_path: Path) -> SkillContext:
    return SkillContext(source_file=tmp_path / "chat.md", source_line=1, workspace=tmp_path)


def _make_router() -> Router:
    """Create a Router with all built-in skills registered."""
    router = Router()
    register_builtin_skills(router)
    return router


# ── Registration completeness ────────────────────────────────────────────


class TestSkillRegistration:
    """All v0.2.0 builtin skills must be registered and routable."""

    EXPECTED_SKILLS = {
        # v0.1.0
        "date", "time", "now", "help", "status", "list",
        # T-045
        "datetime", "timestamp",
        # T-046
        "week", "weekday", "progress", "daynum", "countdown",
        # T-047
        "todo", "done", "table", "code", "link", "img", "hr", "heading", "quote",
    }

    def test_all_skills_registered(self):
        router = _make_router()
        names = {s.name for s in router.list_skills()}
        for expected in self.EXPECTED_SKILLS:
            assert expected in names, f"Skill '{expected}' not registered"

    def test_skill_count(self):
        router = _make_router()
        skills = router.list_skills()
        assert len(skills) >= len(self.EXPECTED_SKILLS)


class TestAliasRouting:
    """All aliases must resolve to the correct skill."""

    ALIAS_MAP = {
        "d": "date",
        "h": "help",
        "st": "status",
        "ls": "list",
        "dt": "datetime",
        "ts": "timestamp",
        "w": "week",
        "wd": "weekday",
        "pg": "progress",
        "dn": "daynum",
        "cd": "countdown",
        "td": "todo",
        "dn2": "done",
        "tb": "table",
        "c": "code",
        "ln": "link",
        "i": "img",
        "hd": "heading",
        "q": "quote",
    }

    def test_all_aliases_resolve(self):
        router = _make_router()
        for alias, skill_name in self.ALIAS_MAP.items():
            # Aliases are stored in router._aliases -> skill name
            resolved_name = router._aliases.get(alias)
            assert resolved_name is not None, f"Alias '/{alias}' not registered"
            assert resolved_name == skill_name, (
                f"Alias '/{alias}' maps to '{resolved_name}', expected '{skill_name}'"
            )
            skill = router.get_skill(resolved_name)
            assert skill is not None, f"Skill '{resolved_name}' not found"


# ── E2E: execute each skill and verify output ───────────────────────────


class TestE2EDateTimeSkills:
    """Run each date/time skill and verify output sanity."""

    def test_date(self, tmp_path):
        skill = _make_router().get_skill("date")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert re.match(r"\d{4}-\d{2}-\d{2}$", result.output)

    def test_time(self, tmp_path):
        skill = _make_router().get_skill("time")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert re.match(r"\d{2}:\d{2}:\d{2}$", result.output)

    def test_now(self, tmp_path):
        skill = _make_router().get_skill("now")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", result.output)

    def test_now_full(self, tmp_path):
        skill = _make_router().get_skill("now")
        result = skill.execute("", {"_positional": "full"}, _ctx(tmp_path))
        assert result.success
        assert "|" in result.output
        assert "%" in result.output

    def test_datetime(self, tmp_path):
        skill = _make_router().get_skill("datetime")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", result.output)

    def test_timestamp(self, tmp_path):
        skill = _make_router().get_skill("timestamp")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output.isdigit()
        assert len(result.output) == 10  # Unix seconds

    def test_week(self, tmp_path):
        skill = _make_router().get_skill("week")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert len(result.output) > 0

    def test_weekday(self, tmp_path):
        skill = _make_router().get_skill("weekday")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert len(result.output) > 0

    def test_progress(self, tmp_path):
        skill = _make_router().get_skill("progress")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "%" in result.output

    def test_daynum(self, tmp_path):
        skill = _make_router().get_skill("daynum")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert len(result.output) > 0

    def test_countdown_default(self, tmp_path):
        skill = _make_router().get_skill("countdown")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success

    def test_countdown_specific(self, tmp_path):
        skill = _make_router().get_skill("countdown")
        result = skill.execute("", {"_positional": "2030-12-31"}, _ctx(tmp_path))
        assert result.success
        assert "2030-12-31" in result.output

    def test_countdown_invalid(self, tmp_path):
        skill = _make_router().get_skill("countdown")
        result = skill.execute("", {"_positional": "xyz"}, _ctx(tmp_path))
        assert not result.success


class TestE2EMarkdownSkills:
    """Run each markdown template skill and verify output."""

    def test_todo(self, tmp_path):
        skill = _make_router().get_skill("todo")
        result = skill.execute("Task", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "- [ ] Task"

    def test_done(self, tmp_path):
        skill = _make_router().get_skill("done")
        result = skill.execute("Task", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "- [x] Task"

    def test_table(self, tmp_path):
        skill = _make_router().get_skill("table")
        result = skill.execute("", {"_positional": "2x2"}, _ctx(tmp_path))
        assert result.success
        lines = result.output.splitlines()
        assert len(lines) == 4  # header + sep + 2 rows
        assert "Col1" in lines[0]
        assert "Col2" in lines[0]

    def test_code(self, tmp_path):
        skill = _make_router().get_skill("code")
        result = skill.execute("", {"_positional": "rust"}, _ctx(tmp_path))
        assert result.success
        assert result.output == "```rust\n\n```"

    def test_link(self, tmp_path):
        skill = _make_router().get_skill("link")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "[text](url)"

    def test_img(self, tmp_path):
        skill = _make_router().get_skill("img")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "![alt](url)"

    def test_hr(self, tmp_path):
        skill = _make_router().get_skill("hr")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "---"

    def test_heading(self, tmp_path):
        skill = _make_router().get_skill("heading")
        result = skill.execute("Title", {"_positional": "3"}, _ctx(tmp_path))
        assert result.success
        assert result.output == "### Title"

    def test_quote(self, tmp_path):
        skill = _make_router().get_skill("quote")
        result = skill.execute("Hello", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "> Hello"


class TestE2EUtilitySkills:
    """Run help/status/list and verify basic output structure."""

    def test_help_lists_all(self, tmp_path):
        router = _make_router()
        skill = router.get_skill("help")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        # Overview mode shows group names
        assert "Date & Time" in result.output
        assert "Markdown Templates" in result.output
        assert "Utilities" in result.output
        # /help <group> should show individual commands
        detail = skill.execute("markdown", {}, _ctx(tmp_path))
        assert detail.success
        assert "/todo" in detail.output
        assert "/heading" in detail.output

    def test_status(self, tmp_path):
        skill = _make_router().get_skill("status")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success

    def test_list_empty_workspace(self, tmp_path):
        skill = _make_router().get_skill("list")
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success


# ── E2E: i18n key completeness ───────────────────────────────────────────


class TestI18nCoverage:
    """All skill descriptions should have i18n keys in both locales."""

    def test_en_has_all_skill_descriptions(self):
        from chatmd.i18n.en import MESSAGES
        router = _make_router()
        for skill in router.list_skills():
            key = f"skill.{skill.name}.description"
            assert key in MESSAGES, f"Missing en i18n key: {key}"

    def test_zh_has_all_skill_descriptions(self):
        from chatmd.i18n.zh_CN import MESSAGES
        router = _make_router()
        for skill in router.list_skills():
            key = f"skill.{skill.name}.description"
            assert key in MESSAGES, f"Missing zh_CN i18n key: {key}"

    def test_en_zh_key_parity(self):
        from chatmd.i18n.en import MESSAGES as EN
        from chatmd.i18n.zh_CN import MESSAGES as ZH
        en_keys = set(EN.keys())
        zh_keys = set(ZH.keys())
        missing_in_zh = en_keys - zh_keys
        missing_in_en = zh_keys - en_keys
        assert not missing_in_zh, f"Keys in en but not zh_CN: {missing_in_zh}"
        assert not missing_in_en, f"Keys in zh_CN but not en: {missing_in_en}"
