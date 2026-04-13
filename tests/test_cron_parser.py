"""Tests for CronParser (T-056 / US-024 / F-076~F-078)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from chatmd.engine.cron_parser import (
    CronExpr,
    CronParser,
    CronSyntaxError,
    EveryExpr,
)

# ═══════════════════════════════════════════════════════════════════
# CronExpr — 5-field expression parsing
# ═══════════════════════════════════════════════════════════════════


class TestCronExprParsing:
    """Parse standard 5-field cron expressions."""

    def test_all_stars(self) -> None:
        expr = CronExpr.parse("* * * * *")
        assert expr.minutes == set(range(60))
        assert expr.hours == set(range(24))
        assert expr.days == set(range(1, 32))
        assert expr.months == set(range(1, 13))
        assert expr.weekdays == set(range(7))

    def test_single_values(self) -> None:
        expr = CronExpr.parse("30 9 15 6 3")
        assert expr.minutes == {30}
        assert expr.hours == {9}
        assert expr.days == {15}
        assert expr.months == {6}
        assert expr.weekdays == {3}

    def test_comma_list(self) -> None:
        expr = CronExpr.parse("0,15,30,45 * * * *")
        assert expr.minutes == {0, 15, 30, 45}

    def test_range(self) -> None:
        expr = CronExpr.parse("0 9-17 * * *")
        assert expr.hours == set(range(9, 18))

    def test_step(self) -> None:
        expr = CronExpr.parse("*/5 * * * *")
        assert expr.minutes == {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}

    def test_range_with_step(self) -> None:
        expr = CronExpr.parse("0 8-18/2 * * *")
        assert expr.hours == {8, 10, 12, 14, 16, 18}

    def test_weekday_names(self) -> None:
        expr = CronExpr.parse("0 9 * * MON-FRI")
        assert expr.weekdays == {1, 2, 3, 4, 5}

    def test_weekday_names_lowercase(self) -> None:
        expr = CronExpr.parse("0 9 * * mon,wed,fri")
        assert expr.weekdays == {1, 3, 5}

    def test_month_names(self) -> None:
        expr = CronExpr.parse("0 0 1 JAN,JUL *")
        assert expr.months == {1, 7}

    def test_sunday_as_0_and_7(self) -> None:
        expr0 = CronExpr.parse("0 0 * * 0")
        expr7 = CronExpr.parse("0 0 * * 7")
        assert expr0.weekdays == {0}
        assert expr7.weekdays == {0}

    def test_complex_expression(self) -> None:
        expr = CronExpr.parse("0,30 9-17 1-15 1,4,7,10 MON-FRI")
        assert expr.minutes == {0, 30}
        assert expr.hours == set(range(9, 18))
        assert expr.days == set(range(1, 16))
        assert expr.months == {1, 4, 7, 10}
        assert expr.weekdays == {1, 2, 3, 4, 5}


class TestCronExprInvalid:
    """Invalid expressions raise CronSyntaxError."""

    def test_too_few_fields(self) -> None:
        with pytest.raises(CronSyntaxError):
            CronExpr.parse("* * *")

    def test_too_many_fields(self) -> None:
        with pytest.raises(CronSyntaxError):
            CronExpr.parse("* * * * * *")

    def test_invalid_value(self) -> None:
        with pytest.raises(CronSyntaxError):
            CronExpr.parse("60 * * * *")

    def test_invalid_range(self) -> None:
        with pytest.raises(CronSyntaxError):
            CronExpr.parse("* 25 * * *")

    def test_invalid_weekday_name(self) -> None:
        with pytest.raises(CronSyntaxError):
            CronExpr.parse("0 0 * * XYZ")


# ═══════════════════════════════════════════════════════════════════
# CronExpr.next_fire — next fire time calculation
# ═══════════════════════════════════════════════════════════════════


class TestCronExprNextFire:
    """Calculate next fire time from a given datetime."""

    def test_every_minute(self) -> None:
        expr = CronExpr.parse("* * * * *")
        now = datetime(2026, 4, 8, 10, 30, 15)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2026, 4, 8, 10, 31)

    def test_specific_time_in_future(self) -> None:
        expr = CronExpr.parse("30 9 * * *")
        now = datetime(2026, 4, 8, 8, 0, 0)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2026, 4, 8, 9, 30)

    def test_specific_time_already_passed(self) -> None:
        expr = CronExpr.parse("30 9 * * *")
        now = datetime(2026, 4, 8, 10, 0, 0)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2026, 4, 9, 9, 30)

    def test_day_of_week(self) -> None:
        expr = CronExpr.parse("0 9 * * 1")  # Monday
        # 2026-04-08 is a Wednesday
        now = datetime(2026, 4, 8, 10, 0, 0)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2026, 4, 13, 9, 0)  # Next Monday

    def test_month_rollover(self) -> None:
        expr = CronExpr.parse("0 0 1 * *")  # 1st of each month
        now = datetime(2026, 4, 15, 0, 0, 0)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2026, 5, 1, 0, 0)

    def test_year_rollover(self) -> None:
        expr = CronExpr.parse("0 0 1 1 *")  # Jan 1st
        now = datetime(2026, 4, 8, 0, 0, 0)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2027, 1, 1, 0, 0)

    def test_exact_match_skips_to_next(self) -> None:
        """If now is exactly on a fire time, next should be the *next* one."""
        expr = CronExpr.parse("30 9 * * *")
        now = datetime(2026, 4, 8, 9, 30, 0)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2026, 4, 9, 9, 30)

    def test_every_5_minutes(self) -> None:
        expr = CronExpr.parse("*/5 * * * *")
        now = datetime(2026, 4, 8, 10, 7, 0)
        nxt = expr.next_fire(now)
        assert nxt == datetime(2026, 4, 8, 10, 10)


# ═══════════════════════════════════════════════════════════════════
# Shortcut expressions (@hourly, @daily, etc.)
# ═══════════════════════════════════════════════════════════════════


class TestShortcuts:
    """Parse @ shortcut expressions."""

    def test_hourly(self) -> None:
        expr = CronExpr.from_shortcut("@hourly")
        assert expr.minutes == {0}
        assert expr.hours == set(range(24))

    def test_daily(self) -> None:
        expr = CronExpr.from_shortcut("@daily")
        assert expr.minutes == {0}
        assert expr.hours == {0}

    def test_midnight(self) -> None:
        expr = CronExpr.from_shortcut("@midnight")
        assert expr.minutes == {0}
        assert expr.hours == {0}

    def test_weekly(self) -> None:
        expr = CronExpr.from_shortcut("@weekly")
        assert expr.weekdays == {0}

    def test_monthly(self) -> None:
        expr = CronExpr.from_shortcut("@monthly")
        assert expr.days == {1}

    def test_unknown_shortcut(self) -> None:
        with pytest.raises(CronSyntaxError):
            CronExpr.from_shortcut("@biweekly")


# ═══════════════════════════════════════════════════════════════════
# @every extension
# ═══════════════════════════════════════════════════════════════════


class TestEveryExpr:
    """Parse and evaluate @every expressions."""

    def test_seconds(self) -> None:
        ev = EveryExpr.parse("@every 30s")
        assert ev.interval == timedelta(seconds=30)

    def test_minutes(self) -> None:
        ev = EveryExpr.parse("@every 5m")
        assert ev.interval == timedelta(minutes=5)

    def test_hours(self) -> None:
        ev = EveryExpr.parse("@every 2h")
        assert ev.interval == timedelta(hours=2)

    def test_days(self) -> None:
        ev = EveryExpr.parse("@every 1d")
        assert ev.interval == timedelta(days=1)

    def test_next_fire(self) -> None:
        ev = EveryExpr.parse("@every 5m")
        now = datetime(2026, 4, 8, 10, 30, 0)
        nxt = ev.next_fire(now)
        assert nxt == datetime(2026, 4, 8, 10, 35, 0)

    def test_next_fire_with_last_run(self) -> None:
        ev = EveryExpr.parse("@every 10m")
        last = datetime(2026, 4, 8, 10, 25, 0)
        now = datetime(2026, 4, 8, 10, 30, 0)
        nxt = ev.next_fire(now, last_run=last)
        assert nxt == datetime(2026, 4, 8, 10, 35, 0)

    def test_next_fire_overdue(self) -> None:
        """If last_run + interval is in the past, fire immediately (now)."""
        ev = EveryExpr.parse("@every 5m")
        last = datetime(2026, 4, 8, 10, 0, 0)
        now = datetime(2026, 4, 8, 10, 30, 0)
        nxt = ev.next_fire(now, last_run=last)
        assert nxt == now

    def test_invalid_unit(self) -> None:
        with pytest.raises(CronSyntaxError):
            EveryExpr.parse("@every 5w")

    def test_invalid_format(self) -> None:
        with pytest.raises(CronSyntaxError):
            EveryExpr.parse("@every abc")

    def test_zero_interval(self) -> None:
        with pytest.raises(CronSyntaxError):
            EveryExpr.parse("@every 0s")


# ═══════════════════════════════════════════════════════════════════
# CronParser — Markdown code block extraction
# ═══════════════════════════════════════════════════════════════════


class TestCronParserCodeBlock:
    """Extract cron jobs from Markdown code blocks."""

    def test_single_job(self) -> None:
        text = (
            "# My tasks\n\n"
            "```cron\n"
            "0 9 * * *   /ask 生成日报\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 1
        assert jobs[0].command == "/ask 生成日报"
        assert isinstance(jobs[0].schedule, CronExpr)

    def test_multiple_jobs(self) -> None:
        text = (
            "```cron\n"
            "0 9 * * *   /ask 日报\n"
            "0 * * * *   /sync\n"
            "@hourly     /status\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 3

    def test_comments_and_blanks(self) -> None:
        text = (
            "```cron\n"
            "# This is a comment\n"
            "\n"
            "0 9 * * *   /ask daily\n"
            "  # another comment\n"
            "@daily      /sync\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 2

    def test_every_expression(self) -> None:
        text = (
            "```cron\n"
            "@every 5m   /status\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 1
        assert isinstance(jobs[0].schedule, EveryExpr)

    def test_shortcut(self) -> None:
        text = (
            "```cron\n"
            "@daily   /sync\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 1
        assert isinstance(jobs[0].schedule, CronExpr)

    def test_multiple_blocks(self) -> None:
        text = (
            "# Tasks A\n\n"
            "```cron\n"
            "0 9 * * *   /ask 日报\n"
            "```\n\n"
            "# Tasks B\n\n"
            "```cron\n"
            "@daily   /sync\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 2

    def test_non_cron_blocks_ignored(self) -> None:
        text = (
            "```python\n"
            "print('hello')\n"
            "```\n\n"
            "```cron\n"
            "0 9 * * *   /ask test\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 1

    def test_empty_cron_block(self) -> None:
        text = (
            "```cron\n"
            "# only comments\n"
            "```\n"
        )
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 0

    def test_no_cron_blocks(self) -> None:
        text = "# Just a normal file\n\nSome text.\n"
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 0


# ═══════════════════════════════════════════════════════════════════
# CronJob — ID and attributes
# ═══════════════════════════════════════════════════════════════════


class TestCronJobId:
    """CronJob ID is deterministic based on source_file + line content."""

    def test_deterministic_id(self) -> None:
        text = (
            "```cron\n"
            "0 9 * * *   /ask test\n"
            "```\n"
        )
        jobs1 = CronParser.parse_text(text, source_file=Path("cron.md"))
        jobs2 = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert jobs1[0].job_id == jobs2[0].job_id

    def test_different_files_different_ids(self) -> None:
        text = "```cron\n0 9 * * *   /ask test\n```\n"
        j1 = CronParser.parse_text(text, source_file=Path("a.md"))
        j2 = CronParser.parse_text(text, source_file=Path("b.md"))
        assert j1[0].job_id != j2[0].job_id

    def test_id_format(self) -> None:
        text = "```cron\n0 9 * * *   /ask test\n```\n"
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        # ID should be "cron-" + short hash
        assert jobs[0].job_id.startswith("cron-")
        assert len(jobs[0].job_id) == len("cron-") + 8

    def test_job_attributes(self) -> None:
        text = "```cron\n0 9 * * *   /ask daily report\n```\n"
        jobs = CronParser.parse_text(
            text, source_file=Path("cron.md"),
        )
        job = jobs[0]
        assert job.command == "/ask daily report"
        assert job.raw_line == "0 9 * * *   /ask daily report"
        assert job.source_file == Path("cron.md")
        assert job.source_line_num > 0


# ═══════════════════════════════════════════════════════════════════
# CronParser.parse_file — read from actual file
# ═══════════════════════════════════════════════════════════════════


class TestCronParserFile:
    """Parse cron jobs from actual files."""

    def test_parse_file(self, tmp_path: Path) -> None:
        cron_md = tmp_path / "cron.md"
        cron_md.write_text(
            "# My cron\n\n"
            "```cron\n"
            "@daily   /sync\n"
            "0 */2 * * *   /status\n"
            "```\n",
            encoding="utf-8",
        )
        jobs = CronParser.parse_file(cron_md)
        assert len(jobs) == 2

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        jobs = CronParser.parse_file(tmp_path / "missing.md")
        assert jobs == []

    def test_reboot_job(self) -> None:
        """@reboot is parsed but flagged — it fires on agent start only."""
        text = "```cron\n@reboot   /status\n```\n"
        jobs = CronParser.parse_text(text, source_file=Path("cron.md"))
        assert len(jobs) == 1
        assert jobs[0].is_reboot is True


# ═══════════════════════════════════════════════════════════════════
# Syntax error jobs — collected as errors instead of crashing
# ═══════════════════════════════════════════════════════════════════


class TestCronParserErrors:
    """Invalid lines are collected as errors, not exceptions."""

    def test_invalid_line_collected(self) -> None:
        text = (
            "```cron\n"
            "0 9 * * *   /ask ok\n"
            "BAD LINE\n"
            "@daily   /sync\n"
            "```\n"
        )
        jobs, errors = CronParser.parse_text_with_errors(
            text, source_file=Path("cron.md"),
        )
        assert len(jobs) == 2
        assert len(errors) == 1
        assert "BAD LINE" in errors[0].raw_line

    def test_missing_command(self) -> None:
        text = "```cron\n0 9 * * *\n```\n"
        jobs, errors = CronParser.parse_text_with_errors(
            text, source_file=Path("cron.md"),
        )
        assert len(jobs) == 0
        assert len(errors) == 1
