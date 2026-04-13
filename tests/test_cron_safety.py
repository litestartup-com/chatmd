"""Tests for /cron add/remove, timeout, failure pause, blacklist (T-064 / US-025/027)."""

from __future__ import annotations

from pathlib import Path

from chatmd.engine.cron_parser import CronExpr, CronJob
from chatmd.engine.cron_safety import (
    DANGEROUS_COMMANDS,
    auto_pause_on_failures,
    is_dangerous_command,
)
from chatmd.engine.cron_scheduler import CronScheduler, CronTaskStatus
from chatmd.skills.base import SkillContext
from chatmd.skills.cron import CronSkill


def _ctx() -> SkillContext:
    return SkillContext(
        source_file=Path("/tmp/chat.md"), source_line=1, workspace=Path("/tmp"),
    )


def _make_job(job_id: str = "cron-t1", command: str = "/sync") -> CronJob:
    return CronJob(
        job_id=job_id,
        schedule=CronExpr.parse("0 9 * * *"),
        command=command,
        raw_line=f"0 9 * * *   {command}",
        source_file=Path("cron.md"),
        source_line_num=2,
    )


# ═══════════════════════════════════════════════════════════════════
# Dangerous command blacklist
# ═══════════════════════════════════════════════════════════════════


class TestDangerousCommands:
    def test_known_dangerous(self) -> None:
        assert is_dangerous_command("/upload")
        assert is_dangerous_command("/new")

    def test_safe_commands(self) -> None:
        assert not is_dangerous_command("/ask daily report")
        assert not is_dangerous_command("/sync")
        assert not is_dangerous_command("/date")
        assert not is_dangerous_command("/cron status")

    def test_case_insensitive(self) -> None:
        assert is_dangerous_command("/Upload")
        assert is_dangerous_command("/NEW")

    def test_with_args(self) -> None:
        assert is_dangerous_command("/upload image.png")
        assert is_dangerous_command("/new session1")

    def test_blacklist_not_empty(self) -> None:
        assert len(DANGEROUS_COMMANDS) > 0


# ═══════════════════════════════════════════════════════════════════
# Auto-pause on consecutive failures
# ═══════════════════════════════════════════════════════════════════


class TestAutoFailurePause:
    def test_pause_on_threshold(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-fail1"))
        state = sched.get_state("cron-fail1")
        state.consecutive_failures = 5
        paused = auto_pause_on_failures(sched, max_failures=5)
        assert "cron-fail1" in paused
        assert state.status == CronTaskStatus.PAUSED

    def test_no_pause_below_threshold(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-ok1"))
        state = sched.get_state("cron-ok1")
        state.consecutive_failures = 2
        paused = auto_pause_on_failures(sched, max_failures=5)
        assert paused == []
        assert state.status == CronTaskStatus.ACTIVE

    def test_already_paused_not_counted(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-p1"))
        sched.pause("cron-p1")
        state = sched.get_state("cron-p1")
        state.consecutive_failures = 10
        paused = auto_pause_on_failures(sched, max_failures=3)
        assert paused == []  # Already paused, don't report again

    def test_multiple_jobs(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-a"))
        sched.register(_make_job(job_id="cron-b"))
        sched.get_state("cron-a").consecutive_failures = 5
        sched.get_state("cron-b").consecutive_failures = 1
        paused = auto_pause_on_failures(sched, max_failures=3)
        assert "cron-a" in paused
        assert "cron-b" not in paused


# ═══════════════════════════════════════════════════════════════════
# /cron add <expr> <cmd>
# ═══════════════════════════════════════════════════════════════════


class TestCronAdd:
    def test_add_success(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "# Cron\n\n```cron\n0 9 * * *   /ask daily\n```\n",
            encoding="utf-8",
        )
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_file)
        result = skill.execute("add @hourly /sync", {}, _ctx())
        assert result.success
        content = cron_file.read_text(encoding="utf-8")
        assert "@hourly" in content
        assert "/sync" in content

    def test_add_creates_cron_block(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text("# Cron\n\nNo tasks yet.\n", encoding="utf-8")
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_file)
        result = skill.execute("add @daily /ask report", {}, _ctx())
        assert result.success
        content = cron_file.read_text(encoding="utf-8")
        assert "```cron" in content
        assert "@daily" in content

    def test_add_dangerous_rejected(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text("# Cron\n", encoding="utf-8")
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_file)
        result = skill.execute("add @hourly /upload", {}, _ctx())
        assert not result.success

    def test_add_no_args(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("add", {}, _ctx())
        assert not result.success

    def test_add_missing_command(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("add @hourly", {}, _ctx())
        assert not result.success


# ═══════════════════════════════════════════════════════════════════
# /cron remove <ID>
# ═══════════════════════════════════════════════════════════════════


class TestCronRemove:
    def test_remove_success(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-rm1"))
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("remove cron-rm1", {}, _ctx())
        assert result.success
        assert sched.get_state("cron-rm1") is None

    def test_remove_not_found(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("remove cron-xxx", {}, _ctx())
        assert not result.success

    def test_remove_no_id(self) -> None:
        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        result = skill.execute("remove", {}, _ctx())
        assert not result.success
