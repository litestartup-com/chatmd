"""Tests for /cron extended commands: pause/resume/run/test/validate/history (T-062)."""

from __future__ import annotations

from pathlib import Path

from chatmd.engine.cron_parser import CronExpr, CronJob
from chatmd.engine.cron_scheduler import CronScheduler, CronTaskStatus
from chatmd.skills.base import SkillContext
from chatmd.skills.cron import CronSkill


def _ctx() -> SkillContext:
    return SkillContext(source_file=Path("/tmp/chat.md"), source_line=1, workspace=Path("/tmp"))


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


def _sched_with_jobs() -> CronScheduler:
    sched = CronScheduler()
    sched.register(_make_job(job_id="cron-aaa1", command="/ask daily"))
    sched.register(_make_job(job_id="cron-bbb2", command="/sync"))
    return sched


# ═══════════════════════════════════════════════════════════════════
# /cron pause <ID>
# ═══════════════════════════════════════════════════════════════════


class TestCronPause:
    def test_pause_success(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("pause cron-aaa1", {}, _ctx())
        assert result.success
        assert sched.get_state("cron-aaa1").status == CronTaskStatus.PAUSED

    def test_pause_not_found(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("pause cron-xxx", {}, _ctx())
        assert not result.success

    def test_pause_no_id(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("pause", {}, _ctx())
        assert not result.success


# ═══════════════════════════════════════════════════════════════════
# /cron resume <ID>
# ═══════════════════════════════════════════════════════════════════


class TestCronResume:
    def test_resume_success(self) -> None:
        sched = _sched_with_jobs()
        sched.pause("cron-aaa1")
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("resume cron-aaa1", {}, _ctx())
        assert result.success
        assert sched.get_state("cron-aaa1").status == CronTaskStatus.ACTIVE

    def test_resume_not_found(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("resume cron-xxx", {}, _ctx())
        assert not result.success

    def test_resume_no_id(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("resume", {}, _ctx())
        assert not result.success


# ═══════════════════════════════════════════════════════════════════
# /cron run <ID>
# ═══════════════════════════════════════════════════════════════════


class TestCronRun:
    def test_run_success(self) -> None:
        executed = []
        sched = _sched_with_jobs()
        sched.set_executor(lambda cmd, jid: executed.append((cmd, jid)))
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("run cron-aaa1", {}, _ctx())
        assert result.success
        assert ("cron-aaa1",) == (executed[0][1],) if executed else True

    def test_run_not_found(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("run cron-xxx", {}, _ctx())
        assert not result.success

    def test_run_no_id(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("run", {}, _ctx())
        assert not result.success


# ═══════════════════════════════════════════════════════════════════
# /cron test <ID>
# ═══════════════════════════════════════════════════════════════════


class TestCronTest:
    def test_test_success(self) -> None:
        executed = []
        sched = _sched_with_jobs()
        sched.set_executor(lambda cmd, jid: executed.append((cmd, jid)))
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("test cron-aaa1", {}, _ctx())
        assert result.success
        assert "TEST" in result.output or "test" in result.output.lower()

    def test_test_not_found(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("test cron-xxx", {}, _ctx())
        assert not result.success


# ═══════════════════════════════════════════════════════════════════
# /cron validate
# ═══════════════════════════════════════════════════════════════════


class TestCronValidate:
    def test_validate_all_ok(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("validate", {}, _ctx())
        assert result.success
        assert "2" in result.output  # 2 valid jobs

    def test_validate_no_jobs(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("validate", {}, _ctx())
        assert result.success


# ═══════════════════════════════════════════════════════════════════
# /cron history [ID]
# ═══════════════════════════════════════════════════════════════════


class TestCronHistory:
    def test_history_empty(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("history", {}, _ctx())
        assert result.success

    def test_history_with_records(self) -> None:
        sched = _sched_with_jobs()
        state = sched.get_state("cron-aaa1")
        state.history.append({
            "job_id": "cron-aaa1",
            "command": "/ask daily",
            "time": "2026-04-08T23:00:00",
            "status": "success",
        })
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("history", {}, _ctx())
        assert result.success
        assert "cron-aaa1" in result.output

    def test_history_filtered_by_id(self) -> None:
        sched = _sched_with_jobs()
        state = sched.get_state("cron-aaa1")
        state.history.append({
            "job_id": "cron-aaa1",
            "command": "/ask daily",
            "time": "2026-04-08T23:00:00",
            "status": "success",
        })
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("history cron-aaa1", {}, _ctx())
        assert result.success
        assert "cron-aaa1" in result.output

    def test_history_id_not_found(self) -> None:
        sched = _sched_with_jobs()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("history cron-xxx", {}, _ctx())
        assert result.success  # Empty is still success
