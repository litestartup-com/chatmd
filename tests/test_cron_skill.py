"""Tests for /cron Skill — list / status / next (T-058 / US-025 / F-083~F-084)."""

from __future__ import annotations

from pathlib import Path

from chatmd.engine.cron_parser import CronExpr, CronJob, EveryExpr
from chatmd.engine.cron_scheduler import CronScheduler
from chatmd.skills.base import SkillContext
from chatmd.skills.cron import CronSkill


def _ctx(workspace: Path | None = None) -> SkillContext:
    ws = workspace or Path("/tmp/test")
    return SkillContext(source_file=ws / "chat.md", source_line=1, workspace=ws)


def _make_job(
    job_id: str = "cron-abc1",
    expr: str = "0 9 * * *",
    command: str = "/ask daily",
) -> CronJob:
    return CronJob(
        job_id=job_id,
        schedule=CronExpr.parse(expr),
        command=command,
        raw_line=f"{expr}   {command}",
        source_file=Path("cron.md"),
        source_line_num=2,
    )


def _make_every_job(
    job_id: str = "cron-ev01",
    interval: str = "@every 5m",
    command: str = "/status",
) -> CronJob:
    return CronJob(
        job_id=job_id,
        schedule=EveryExpr.parse(interval),
        command=command,
        raw_line=f"{interval}   {command}",
        source_file=Path("cron.md"),
        source_line_num=3,
    )


# ═══════════════════════════════════════════════════════════════════
# /cron (list) — default subcommand
# ═══════════════════════════════════════════════════════════════════


class TestCronList:
    """``/cron`` lists all registered jobs."""

    def test_no_jobs(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("", {}, _ctx())
        assert result.success
        assert "0" in result.output  # 0 jobs

    def test_with_jobs(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-aaa1", command="/ask daily"))
        sched.register(_make_job(job_id="cron-bbb2", command="/sync"))
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("", {}, _ctx())
        assert result.success
        assert "cron-aaa1" in result.output
        assert "cron-bbb2" in result.output
        assert "/ask daily" in result.output
        assert "/sync" in result.output

    def test_shows_next_run(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job())
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("", {}, _ctx())
        # Should contain a datetime-like string for next run
        assert "202" in result.output  # year prefix

    def test_shows_status(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        sched.pause(job.job_id)
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("", {}, _ctx())
        assert "paused" in result.output.lower()


# ═══════════════════════════════════════════════════════════════════
# /cron status — with statistics
# ═══════════════════════════════════════════════════════════════════


class TestCronStatus:
    """/cron status shows job list + run statistics."""

    def test_status_output(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        # Simulate some runs
        state = sched.get_state(job.job_id)
        state.run_count = 10
        state.fail_count = 2

        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("status", {}, _ctx())
        assert result.success
        assert "10" in result.output
        assert "2" in result.output

    def test_status_no_jobs(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("status", {}, _ctx())
        assert result.success


# ═══════════════════════════════════════════════════════════════════
# /cron next — upcoming execution preview
# ═══════════════════════════════════════════════════════════════════


class TestCronNext:
    """/cron next [N] shows next N fire times."""

    def test_default_5(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(expr="*/10 * * * *"))
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("next", {}, _ctx())
        assert result.success
        # Should have multiple time entries
        lines = [
            ln for ln in result.output.splitlines()
            if "202" in ln  # lines with year
        ]
        assert len(lines) >= 3  # at least a few entries

    def test_custom_count(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(expr="*/10 * * * *"))
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("next 3", {}, _ctx())
        assert result.success

    def test_next_no_jobs(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("next", {}, _ctx())
        assert result.success

    def test_next_every_job(self) -> None:
        sched = CronScheduler()
        sched.register(_make_every_job(interval="@every 10m"))
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("next 3", {}, _ctx())
        assert result.success


# ═══════════════════════════════════════════════════════════════════
# Subcommand routing
# ═══════════════════════════════════════════════════════════════════


class TestCronSubcommandRouting:
    """Input text is routed to the correct subcommand."""

    def test_empty_routes_to_list(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        r1 = skill.execute("", {}, _ctx())
        r2 = skill.execute("  ", {}, _ctx())
        assert r1.success
        assert r2.success

    def test_unknown_subcommand(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("foobar", {}, _ctx())
        assert not result.success

    def test_skill_metadata(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        assert skill.name == "cron"
        assert skill.category == "builtin"
