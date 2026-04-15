"""Tests for the daily_note custom skill (T-073).

Tests cover:
- Content generation (journal, dudu, youyou, family, weekly)
- File creation logic
- Archive logic (move expired, delete unedited)
- Subcommand routing
- configure() with custom config
- status subcommand
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Add note-kaka skills dir to path so we can import the skill
_SKILL_PATH = Path(r"C:\Workplace\gitee\note-kaka\.chatmd\skills")
if str(_SKILL_PATH) not in sys.path:
    sys.path.insert(0, str(_SKILL_PATH))

from daily_note import (  # noqa: E402
    DailyNoteSkill,
    _find_expired,
    _gen_daily_journal,
    _gen_dudu_log,
    _gen_family_log,
    _gen_weekly_report,
    _gen_youyou_log,
    _is_unedited,
    _week_number,
    _weekday_cn,
)  # noqa: I001

from chatmd.skills.base import SkillContext  # noqa: E402


def _ctx(workspace: Path) -> SkillContext:
    return SkillContext(source_file=workspace, source_line=0, workspace=workspace)


# ---------------------------------------------------------------------------
# Content generation tests
# ---------------------------------------------------------------------------

class TestContentGeneration:
    def test_daily_journal_header(self):
        dt = datetime(2026, 4, 10, 8, 0)
        content = _gen_daily_journal(dt)
        assert "# 0410 - 星期五" in content
        assert "2026年04月10日" in content

    def test_dudu_log_header(self):
        dt = datetime(2026, 4, 10)
        content = _gen_dudu_log(dt)
        assert "嘟嘟成长记" in content
        assert "2026年04月10日" in content

    def test_youyou_log_header(self):
        dt = datetime(2026, 4, 10)
        content = _gen_youyou_log(dt)
        assert "呦呦成长记" in content

    def test_family_log_header(self):
        dt = datetime(2026, 4, 10)
        content = _gen_family_log(dt)
        assert "家庭日志" in content

    def test_weekly_report_contains_sections(self):
        dt = datetime(2026, 4, 6)  # Monday
        content = _gen_weekly_report(dt, "https://example.com?week={week}")
        assert "周周报" in content
        assert "上周回顾" in content
        assert "本周计划" in content
        assert "下周计划" in content
        assert "example.com" in content

    def test_weekday_cn(self):
        assert _weekday_cn(datetime(2026, 4, 6)) == "星期一"
        assert _weekday_cn(datetime(2026, 4, 10)) == "星期五"


# ---------------------------------------------------------------------------
# File creation tests
# ---------------------------------------------------------------------------

class TestFileCreation:
    def test_create_journal(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        today = datetime(2026, 4, 10)
        lines, written = skill._do_generate(tmp_path, today, "journal")
        assert len(lines) == 1
        assert "[CREATED]" in lines[0]
        fp = tmp_path / "A00-0410-日志.md"
        assert fp.exists()
        assert "0410" in fp.read_text(encoding="utf-8")

    def test_skip_existing(self, tmp_path):
        (tmp_path / "A00-0410-日志.md").write_text("existing", encoding="utf-8")
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        today = datetime(2026, 4, 10)
        lines, written = skill._do_generate(tmp_path, today, "journal")
        assert lines == []
        assert written == []

    def test_create_weekly(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        today = datetime(2026, 4, 6)  # Monday
        lines, written = skill._do_weekly(tmp_path, today)
        assert len(lines) == 1
        assert "周报" in lines[0]

    def test_create_dudu(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        today = datetime(2026, 4, 10)
        lines, written = skill._do_generate(tmp_path, today, "dudu")
        fp = tmp_path / "A00-0410-嘟嘟成长记.md"
        assert fp.exists()


# ---------------------------------------------------------------------------
# Archive tests
# ---------------------------------------------------------------------------

class TestArchive:
    def test_find_expired_daily(self, tmp_path):
        today = datetime(2026, 4, 10)
        (tmp_path / "A00-0409-日志.md").write_text("content", encoding="utf-8")
        expired = _find_expired(tmp_path, today)
        assert len(expired) == 1
        assert expired[0][0].name == "A00-0409-日志.md"

    def test_no_expired_today(self, tmp_path):
        today = datetime(2026, 4, 10)
        (tmp_path / "A00-0410-日志.md").write_text("content", encoding="utf-8")
        expired = _find_expired(tmp_path, today)
        assert len(expired) == 0

    def test_find_expired_weekly(self, tmp_path):
        today = datetime(2026, 4, 10)
        wn = _week_number(today)
        # Create a weekly report from a previous week
        (tmp_path / f"A00-第{wn - 1}周周报.md").write_text("content", encoding="utf-8")
        expired = _find_expired(tmp_path, today)
        assert len(expired) == 1

    def test_archive_moves_edited_file(self, tmp_path):
        today = datetime(2026, 4, 10)
        src = tmp_path / "A00-0409-日志.md"
        src.write_text("# My edited journal\nSome real content", encoding="utf-8")


        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        lines, written = skill._do_archive(tmp_path, today)
        assert any("[MOVED]" in line for line in lines)
        assert not src.exists()

    def test_archive_deletes_unedited(self, tmp_path):
        today = datetime(2026, 4, 10)
        # Create a file with exact template content for yesterday
        yesterday = datetime(2026, 4, 9)
        content = _gen_daily_journal(yesterday)
        src = tmp_path / "A00-0409-日志.md"
        src.write_text(content, encoding="utf-8")

        assert _is_unedited(src, today)

        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        skill._delete_unedited = True
        lines, written = skill._do_archive(tmp_path, today)
        assert any("[DELETED]" in line for line in lines)
        assert not src.exists()

    def test_archive_keeps_unedited_when_disabled(self, tmp_path):
        today = datetime(2026, 4, 10)
        yesterday = datetime(2026, 4, 9)
        content = _gen_daily_journal(yesterday)
        src = tmp_path / "A00-0409-日志.md"
        src.write_text(content, encoding="utf-8")

        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        skill._delete_unedited = False
        lines, written = skill._do_archive(tmp_path, today)
        # Should move, not delete
        assert any("[MOVED]" in line for line in lines)

    def test_is_unedited_false_for_edited(self, tmp_path):
        today = datetime(2026, 4, 10)
        src = tmp_path / "A00-0409-日志.md"
        src.write_text("# Custom content", encoding="utf-8")
        assert not _is_unedited(src, today)

    def test_is_unedited_false_for_weekly(self, tmp_path):
        src = tmp_path / "A00-第15周周报.md"
        src.write_text("anything", encoding="utf-8")
        assert not _is_unedited(src, datetime(2026, 4, 10))


# ---------------------------------------------------------------------------
# Subcommand routing tests
# ---------------------------------------------------------------------------

class TestSubcommands:
    def test_daily_subcommand(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        ctx = _ctx(tmp_path)
        result = skill.execute("daily", {}, ctx)
        assert result.success

    def test_archive_subcommand(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        ctx = _ctx(tmp_path)
        result = skill.execute("archive", {}, ctx)
        assert result.success
        assert "No expired files" in result.output

    def test_status_subcommand(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        ctx = _ctx(tmp_path)
        result = skill.execute("status", {}, ctx)
        assert result.success
        assert "/note status" in result.output

    def test_unknown_subcommand_shows_help(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        ctx = _ctx(tmp_path)
        result = skill.execute("unknown_cmd", {}, ctx)
        assert result.success
        assert "/note" in result.output

    def test_empty_input_defaults_to_daily(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        ctx = _ctx(tmp_path)
        result = skill.execute("", {}, ctx)
        assert result.success

    def test_journal_subcommand(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        ctx = _ctx(tmp_path)
        result = skill.execute("journal", {}, ctx)
        assert result.success
        assert "[CREATED]" in result.output


# ---------------------------------------------------------------------------
# Configure tests
# ---------------------------------------------------------------------------

class TestConfigure:
    def test_configure_sets_workspace(self, tmp_path):
        skill = DailyNoteSkill()
        ctx = _ctx(tmp_path)
        skill.configure({"enabled_logs": ["journal"]}, ctx)
        assert skill._workspace == tmp_path
        assert skill._enabled_logs == ["journal"]

    def test_configure_custom_prefix(self, tmp_path):
        skill = DailyNoteSkill()
        ctx = _ctx(tmp_path)
        skill.configure({"root_prefix": "B01"}, ctx)
        assert skill._root_prefix == "B01"

    def test_daily_uses_configured_logs(self, tmp_path):
        skill = DailyNoteSkill()
        ctx = _ctx(tmp_path)
        skill.configure({"enabled_logs": ["dudu"]}, ctx)
        result = skill.execute("daily", {}, ctx)
        assert result.success
        # Should only create dudu, not journal or youyou
        assert (tmp_path / "A00-{}-嘟嘟成长记.md".format(
            datetime.now().strftime("%m%d")
        )).exists()

    def test_written_files_in_metadata(self, tmp_path):
        skill = DailyNoteSkill()
        skill._workspace = tmp_path
        ctx = _ctx(tmp_path)
        result = skill.execute("journal", {}, ctx)
        assert result.metadata is not None
        assert "written_files" in result.metadata
        assert len(result.metadata["written_files"]) == 1
