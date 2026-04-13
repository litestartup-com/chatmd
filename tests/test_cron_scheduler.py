"""Tests for CronScheduler (T-057 / US-024 / F-079~F-080)."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from chatmd.engine.cron_parser import CronExpr, CronJob, EveryExpr
from chatmd.engine.cron_scheduler import (
    CronScheduler,
    CronTaskStatus,
)

# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _make_job(
    job_id: str = "cron-test01",
    expr: str = "* * * * *",
    command: str = "/status",
    source_file: str = "cron.md",
) -> CronJob:
    return CronJob(
        job_id=job_id,
        schedule=CronExpr.parse(expr),
        command=command,
        raw_line=f"{expr}   {command}",
        source_file=Path(source_file),
        source_line_num=2,
    )


def _make_every_job(
    job_id: str = "cron-every1",
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
# CronScheduler — registration
# ═══════════════════════════════════════════════════════════════════


class TestCronSchedulerRegistration:
    """Register and unregister cron jobs."""

    def test_register_job(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        assert job.job_id in sched.get_all_states()

    def test_register_duplicate_updates(self) -> None:
        sched = CronScheduler()
        job1 = _make_job(command="/status")
        sched.register(job1)
        job2 = _make_job(command="/sync")
        sched.register(job2)
        states = sched.get_all_states()
        assert len(states) == 1
        assert states[job1.job_id].job.command == "/sync"

    def test_unregister_job(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        sched.unregister(job.job_id)
        assert job.job_id not in sched.get_all_states()

    def test_unregister_nonexistent(self) -> None:
        sched = CronScheduler()
        sched.unregister("nonexistent")  # should not raise

    def test_sync_jobs_adds_new_removes_old(self) -> None:
        sched = CronScheduler()
        job_a = _make_job(job_id="cron-aaaa")
        job_b = _make_job(job_id="cron-bbbb")
        sched.register(job_a)
        sched.register(job_b)

        # Sync with only job_b and new job_c
        job_c = _make_job(job_id="cron-cccc")
        sched.sync_jobs([job_b, job_c])
        states = sched.get_all_states()
        assert "cron-aaaa" not in states
        assert "cron-bbbb" in states
        assert "cron-cccc" in states


# ═══════════════════════════════════════════════════════════════════
# CronScheduler — state management
# ═══════════════════════════════════════════════════════════════════


class TestCronSchedulerState:
    """Task state tracking."""

    def test_initial_state_active(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        state = sched.get_state(job.job_id)
        assert state is not None
        assert state.status == CronTaskStatus.ACTIVE

    def test_pause_resume(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        sched.pause(job.job_id)
        assert sched.get_state(job.job_id).status == CronTaskStatus.PAUSED
        sched.resume(job.job_id)
        assert sched.get_state(job.job_id).status == CronTaskStatus.ACTIVE

    def test_pause_nonexistent(self) -> None:
        sched = CronScheduler()
        assert sched.pause("nope") is False

    def test_resume_nonexistent(self) -> None:
        sched = CronScheduler()
        assert sched.resume("nope") is False

    def test_execution_count_tracked(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)

        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)
        sched._tick_once()
        time.sleep(0.1)  # give thread pool time

        state = sched.get_state(job.job_id)
        assert state.run_count >= 1

    def test_failure_count_tracked(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)

        def _fail(cmd: str, job_id: str) -> None:
            raise RuntimeError("boom")

        sched.set_executor(_fail)
        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)
        sched._tick_once()
        time.sleep(0.1)

        state = sched.get_state(job.job_id)
        assert state.fail_count >= 1
        assert state.consecutive_failures >= 1


# ═══════════════════════════════════════════════════════════════════
# CronScheduler — tick and execution
# ═══════════════════════════════════════════════════════════════════


class TestCronSchedulerTick:
    """Tick-based job execution."""

    def test_tick_fires_due_job(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)

        # Force next_run to the past
        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)

        sched._tick_once()
        time.sleep(0.1)
        callback.assert_called_once()
        call_args = callback.call_args
        assert call_args[0][0] == "/status"
        assert call_args[0][1] == job.job_id

    def test_tick_skips_paused_job(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)
        sched.pause(job.job_id)

        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)
        sched._tick_once()
        time.sleep(0.1)
        callback.assert_not_called()

    def test_tick_skips_future_job(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)

        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() + timedelta(hours=1)
        sched._tick_once()
        time.sleep(0.1)
        callback.assert_not_called()

    def test_next_run_recalculated_after_fire(self) -> None:
        sched = CronScheduler()
        job = _make_job(expr="*/5 * * * *")
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)

        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)
        sched._tick_once()
        time.sleep(0.1)

        state = sched.get_state(job.job_id)
        assert state.next_run > datetime.now()

    def test_every_job_next_run(self) -> None:
        sched = CronScheduler()
        job = _make_every_job(interval="@every 10m")
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)

        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)
        sched._tick_once()
        time.sleep(0.1)

        state = sched.get_state(job.job_id)
        # Next run should be ~10m from now
        expected_min = datetime.now() + timedelta(minutes=9)
        assert state.next_run >= expected_min


# ═══════════════════════════════════════════════════════════════════
# CronScheduler — overlap prevention
# ═══════════════════════════════════════════════════════════════════


class TestCronSchedulerOverlap:
    """Overlap prevention: skip if already running."""

    def test_skip_if_running(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)

        barrier = threading.Event()
        call_count = 0

        def _slow_executor(cmd: str, job_id: str) -> None:
            nonlocal call_count
            call_count += 1
            barrier.wait(timeout=5)

        sched.set_executor(_slow_executor)
        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)

        # First tick — starts execution
        sched._tick_once()
        time.sleep(0.05)

        # Second tick — should skip (still running)
        state.next_run = datetime.now() - timedelta(seconds=1)
        sched._tick_once()
        time.sleep(0.05)

        barrier.set()
        time.sleep(0.1)
        assert call_count == 1


# ═══════════════════════════════════════════════════════════════════
# CronScheduler — start/stop lifecycle
# ═══════════════════════════════════════════════════════════════════


class TestCronSchedulerLifecycle:
    """Start and stop the background tick thread."""

    def test_start_stop(self) -> None:
        sched = CronScheduler(tick_interval=0.05)
        sched.set_executor(MagicMock())
        sched.start()
        assert sched.is_running
        time.sleep(0.15)
        sched.stop()
        assert not sched.is_running

    def test_double_start(self) -> None:
        sched = CronScheduler(tick_interval=0.05)
        sched.set_executor(MagicMock())
        sched.start()
        sched.start()  # should be idempotent
        assert sched.is_running
        sched.stop()

    def test_stop_without_start(self) -> None:
        sched = CronScheduler()
        sched.stop()  # should not raise


# ═══════════════════════════════════════════════════════════════════
# CronScheduler — auto tick interval
# ═══════════════════════════════════════════════════════════════════


class TestAutoTickInterval:
    """Auto-adjust tick interval based on minimum job interval."""

    def test_minute_level_jobs(self) -> None:
        sched = CronScheduler()
        job = _make_job(expr="*/5 * * * *")
        sched.register(job)
        interval = sched.compute_tick_interval()
        assert interval == 30.0  # >=1m → 30s tick

    def test_second_level_every(self) -> None:
        sched = CronScheduler()
        job = _make_every_job(interval="@every 30s")
        sched.register(job)
        interval = sched.compute_tick_interval()
        assert interval <= 5.0  # >=10s → 5s tick

    def test_sub_10s_every(self) -> None:
        sched = CronScheduler()
        job = _make_every_job(interval="@every 5s")
        sched.register(job)
        interval = sched.compute_tick_interval()
        assert interval <= 1.0  # <10s → 1s tick

    def test_no_jobs(self) -> None:
        sched = CronScheduler()
        interval = sched.compute_tick_interval()
        assert interval == 30.0  # default


# ═══════════════════════════════════════════════════════════════════
# CronScheduler — history
# ═══════════════════════════════════════════════════════════════════


class TestCronSchedulerHistory:
    """Execution history tracking."""

    def test_history_recorded(self) -> None:
        sched = CronScheduler()
        job = _make_job()
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)

        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)
        sched._tick_once()
        time.sleep(0.2)

        history = sched.get_history(job.job_id)
        assert len(history) >= 1
        assert history[0]["status"] in ("success", "failed")

    def test_history_max_items(self) -> None:
        sched = CronScheduler(max_history=3)
        job = _make_job()
        sched.register(job)
        callback = MagicMock()
        sched.set_executor(callback)

        state = sched.get_state(job.job_id)
        for _ in range(5):
            state.next_run = datetime.now() - timedelta(seconds=1)
            state.is_running = False
            sched._tick_once()
            time.sleep(0.15)

        history = sched.get_history(job.job_id)
        assert len(history) <= 3
