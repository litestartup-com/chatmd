"""Tests for cron state persistence + missed_policy (T-063 / US-027 / F-096~F-097)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from chatmd.engine.cron_parser import CronExpr, CronJob
from chatmd.engine.cron_scheduler import CronScheduler, CronTaskStatus
from chatmd.engine.cron_state import (
    detect_missed_jobs,
    load_cron_state,
    restore_scheduler_state,
    save_cron_state,
)


def _make_job(job_id: str = "cron-abc1", command: str = "/ask daily") -> CronJob:
    return CronJob(
        job_id=job_id,
        schedule=CronExpr.parse("0 9 * * *"),
        command=command,
        raw_line=f"0 9 * * *   {command}",
        source_file=Path("cron.md"),
        source_line_num=2,
    )


# ═══════════════════════════════════════════════════════════════════
# save_cron_state
# ═══════════════════════════════════════════════════════════════════


class TestSaveCronState:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".chatmd" / "state" / "cron_state.json"
        sched = CronScheduler()
        sched.register(_make_job())
        save_cron_state(state_path, sched.get_all_states())
        assert state_path.exists()

    def test_save_contents(self, tmp_path: Path) -> None:
        state_path = tmp_path / "cron_state.json"
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-test1"))
        st = sched.get_state("cron-test1")
        st.run_count = 5
        st.fail_count = 1
        st.last_run = datetime(2026, 4, 8, 23, 0, 0)
        save_cron_state(state_path, sched.get_all_states())

        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert "cron-test1" in data
        assert data["cron-test1"]["run_count"] == 5
        assert data["cron-test1"]["fail_count"] == 1
        assert data["cron-test1"]["last_run"] == "2026-04-08T23:00:00"

    def test_save_paused_status(self, tmp_path: Path) -> None:
        state_path = tmp_path / "cron_state.json"
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-paused1"))
        sched.pause("cron-paused1")
        save_cron_state(state_path, sched.get_all_states())

        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["cron-paused1"]["status"] == "paused"

    def test_save_multiple_jobs(self, tmp_path: Path) -> None:
        state_path = tmp_path / "cron_state.json"
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-a"))
        sched.register(_make_job(job_id="cron-b"))
        save_cron_state(state_path, sched.get_all_states())

        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert len(data) == 2


# ═══════════════════════════════════════════════════════════════════
# load_cron_state
# ═══════════════════════════════════════════════════════════════════


class TestLoadCronState:
    def test_load_nonexistent(self, tmp_path: Path) -> None:
        result = load_cron_state(tmp_path / "nope.json")
        assert result == {}

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        result = load_cron_state(p)
        assert result == {}

    def test_load_roundtrip(self, tmp_path: Path) -> None:
        state_path = tmp_path / "cron_state.json"
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-rt"))
        st = sched.get_state("cron-rt")
        st.run_count = 3
        st.last_run = datetime(2026, 4, 8, 12, 0, 0)
        save_cron_state(state_path, sched.get_all_states())

        loaded = load_cron_state(state_path)
        assert "cron-rt" in loaded
        assert loaded["cron-rt"]["run_count"] == 3
        assert loaded["cron-rt"]["last_run"] == datetime(2026, 4, 8, 12, 0, 0)

    def test_load_null_datetimes(self, tmp_path: Path) -> None:
        state_path = tmp_path / "cron_state.json"
        state_path.write_text(
            json.dumps({"cron-x": {
                "status": "active",
                "last_run": None,
                "next_run": None,
                "run_count": 0,
                "fail_count": 0,
                "consecutive_failures": 0,
            }}),
            encoding="utf-8",
        )
        loaded = load_cron_state(state_path)
        assert loaded["cron-x"]["last_run"] is None
        assert loaded["cron-x"]["next_run"] is None


# ═══════════════════════════════════════════════════════════════════
# detect_missed_jobs
# ═══════════════════════════════════════════════════════════════════


class TestDetectMissedJobs:
    def test_no_missed(self) -> None:
        now = datetime.now()
        saved = {
            "cron-a": {"next_run": now + timedelta(hours=1)},
        }
        assert detect_missed_jobs(saved, now) == []

    def test_one_missed(self) -> None:
        now = datetime.now()
        saved = {
            "cron-a": {"next_run": now - timedelta(hours=1)},
            "cron-b": {"next_run": now + timedelta(hours=1)},
        }
        missed = detect_missed_jobs(saved, now)
        assert missed == ["cron-a"]

    def test_all_missed(self) -> None:
        now = datetime.now()
        saved = {
            "cron-a": {"next_run": now - timedelta(hours=2)},
            "cron-b": {"next_run": now - timedelta(minutes=5)},
        }
        missed = detect_missed_jobs(saved, now)
        assert len(missed) == 2

    def test_null_next_run(self) -> None:
        now = datetime.now()
        saved = {"cron-a": {"next_run": None}}
        assert detect_missed_jobs(saved, now) == []

    def test_empty_state(self) -> None:
        assert detect_missed_jobs({}) == []


# ═══════════════════════════════════════════════════════════════════
# restore_scheduler_state
# ═══════════════════════════════════════════════════════════════════


class TestRestoreSchedulerState:
    def test_restore_counters(self, tmp_path: Path) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-r1"))

        saved = {
            "cron-r1": {
                "status": "active",
                "run_count": 10,
                "fail_count": 2,
                "consecutive_failures": 1,
                "last_run": datetime(2026, 4, 8, 12, 0, 0),
            },
        }
        restore_scheduler_state(sched, saved)

        st = sched.get_state("cron-r1")
        assert st.run_count == 10
        assert st.fail_count == 2
        assert st.consecutive_failures == 1
        assert st.last_run == datetime(2026, 4, 8, 12, 0, 0)

    def test_restore_paused_status(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-p1"))

        saved = {
            "cron-p1": {
                "status": "paused",
                "run_count": 0,
                "fail_count": 0,
                "consecutive_failures": 0,
            },
        }
        restore_scheduler_state(sched, saved)

        st = sched.get_state("cron-p1")
        assert st.status == CronTaskStatus.PAUSED

    def test_restore_ignores_unknown_jobs(self) -> None:
        sched = CronScheduler()
        sched.register(_make_job(job_id="cron-known"))

        saved = {
            "cron-unknown": {"status": "active", "run_count": 5},
        }
        restore_scheduler_state(sched, saved)
        # Should not crash, and known job should be unchanged
        st = sched.get_state("cron-known")
        assert st.run_count == 0

    def test_full_save_restore_cycle(self, tmp_path: Path) -> None:
        state_path = tmp_path / "cron_state.json"

        # Create scheduler with state
        sched1 = CronScheduler()
        sched1.register(_make_job(job_id="cron-cycle"))
        st = sched1.get_state("cron-cycle")
        st.run_count = 7
        st.fail_count = 3
        st.last_run = datetime(2026, 4, 8, 22, 0, 0)
        sched1.pause("cron-cycle")

        # Save
        save_cron_state(state_path, sched1.get_all_states())

        # Load into new scheduler
        sched2 = CronScheduler()
        sched2.register(_make_job(job_id="cron-cycle"))
        loaded = load_cron_state(state_path)
        restore_scheduler_state(sched2, loaded)

        st2 = sched2.get_state("cron-cycle")
        assert st2.run_count == 7
        assert st2.fail_count == 3
        assert st2.status == CronTaskStatus.PAUSED
        assert st2.last_run == datetime(2026, 4, 8, 22, 0, 0)
