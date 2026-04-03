"""Tests for date/time extension skills (T-045) and week/progress skills (T-046)."""

import re
import time as _time
from datetime import date
from pathlib import Path

from chatmd.skills.base import SkillContext
from chatmd.skills.builtin import (
    CountdownSkill,
    DatetimeSkill,
    DaynumSkill,
    NowSkill,
    ProgressSkill,
    TimestampSkill,
    WeekdaySkill,
    WeekSkill,
)


def _ctx(tmp_path: Path) -> SkillContext:
    return SkillContext(source_file=tmp_path / "chat.md", source_line=1, workspace=tmp_path)


# ── T-045: /datetime and /timestamp ──────────────────────────────────────


class TestDatetimeSkill:
    def test_returns_datetime_format(self, tmp_path):
        skill = DatetimeSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        # YYYY-MM-DD HH:MM:SS
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result.output)

    def test_name_and_aliases(self):
        skill = DatetimeSkill()
        assert skill.name == "datetime"
        assert "dt" in skill.aliases


class TestTimestampSkill:
    def test_returns_unix_timestamp(self, tmp_path):
        skill = TimestampSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        ts = int(result.output)
        # Should be close to current time
        assert abs(ts - int(_time.time())) < 2

    def test_name_and_aliases(self):
        skill = TimestampSkill()
        assert skill.name == "timestamp"
        assert "ts" in skill.aliases


# ── T-046: /week, /weekday, /progress, /daynum, /countdown ──────────────


class TestWeekSkill:
    def test_returns_week_number(self, tmp_path):
        skill = WeekSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        week_num = date.today().isocalendar()[1]
        assert str(week_num) in result.output

    def test_name_and_aliases(self):
        skill = WeekSkill()
        assert skill.name == "week"
        assert "w" in skill.aliases


class TestWeekdaySkill:
    def test_returns_weekday_name(self, tmp_path):
        skill = WeekdaySkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert len(result.output) > 0
        # Should be one of the weekday names
        expected = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        assert result.output in expected

    def test_name_and_aliases(self):
        skill = WeekdaySkill()
        assert skill.name == "weekday"
        assert "wd" in skill.aliases


class TestProgressSkill:
    def test_returns_percentage(self, tmp_path):
        skill = ProgressSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert "%" in result.output
        assert str(date.today().year) in result.output

    def test_name_and_aliases(self):
        skill = ProgressSkill()
        assert skill.name == "progress"
        assert "pg" in skill.aliases


class TestDaynumSkill:
    def test_returns_day_number(self, tmp_path):
        skill = DaynumSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        day = date.today().timetuple().tm_yday
        assert str(day) in result.output

    def test_name_and_aliases(self):
        skill = DaynumSkill()
        assert skill.name == "daynum"
        assert "dn" in skill.aliases


class TestCountdownSkill:
    def test_default_one_year(self, tmp_path):
        skill = CountdownSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        # Should contain days count and next year
        assert str(date.today().year + 1) in result.output

    def test_specific_date(self, tmp_path):
        skill = CountdownSkill()
        target = "2030-01-01"
        result = skill.execute("", {"_positional": target}, _ctx(tmp_path))
        assert result.success
        assert target in result.output
        delta = (date.fromisoformat(target) - date.today()).days
        assert str(delta) in result.output

    def test_invalid_date(self, tmp_path):
        skill = CountdownSkill()
        result = skill.execute("", {"_positional": "not-a-date"}, _ctx(tmp_path))
        assert not result.success
        assert "not-a-date" in result.error

    def test_name_and_aliases(self):
        skill = CountdownSkill()
        assert skill.name == "countdown"
        assert "cd" in skill.aliases


# ── /now(full) enhancement ───────────────────────────────────────────────


class TestNowFullMode:
    def test_now_default_unchanged(self, tmp_path):
        skill = NowSkill()
        result = skill.execute("", {}, _ctx(tmp_path))
        assert result.success
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result.output)

    def test_now_full_mode(self, tmp_path):
        skill = NowSkill()
        result = skill.execute("", {"_positional": "full"}, _ctx(tmp_path))
        assert result.success
        # Should contain date, weekday, week number, day number, progress
        assert "|" in result.output
        assert "%" in result.output
        assert str(date.today().year) in result.output
