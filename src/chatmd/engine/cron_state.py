"""Cron state persistence — save/load cron_state.json (T-063 / US-027 / F-096~F-097).

Persists cron job runtime state (last_run, next_run, run_count, fail_count,
consecutive_failures, status) to ``.chatmd/state/cron_state.json`` so the
scheduler can recover after Agent restart and detect missed jobs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"


def save_cron_state(
    state_path: Path,
    states: dict[str, Any],
) -> None:
    """Persist cron scheduler state to JSON.

    Parameters
    ----------
    state_path:
        Path to ``cron_state.json``.
    states:
        Dict of ``{job_id: CronTaskState}`` from the scheduler.
    """
    data: dict[str, Any] = {}
    for job_id, st in states.items():
        data[job_id] = {
            "status": st.status.value,
            "last_run": st.last_run.strftime(_ISO_FMT) if st.last_run else None,
            "next_run": st.next_run.strftime(_ISO_FMT) if st.next_run else None,
            "run_count": st.run_count,
            "fail_count": st.fail_count,
            "consecutive_failures": st.consecutive_failures,
        }

    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug("Cron state saved to %s (%d jobs)", state_path, len(data))


def load_cron_state(state_path: Path) -> dict[str, dict]:
    """Load persisted cron state from JSON.

    Returns a dict of ``{job_id: {status, last_run, next_run, ...}}``.
    Returns empty dict if file doesn't exist or is invalid.
    """
    if not state_path.exists():
        return {}
    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        # Parse datetime strings back
        for _jid, entry in data.items():
            for key in ("last_run", "next_run"):
                val = entry.get(key)
                if val:
                    entry[key] = datetime.strptime(val, _ISO_FMT)
                else:
                    entry[key] = None
        return data
    except (json.JSONDecodeError, ValueError, KeyError):
        logger.warning("Failed to load cron state from %s", state_path)
        return {}


def detect_missed_jobs(
    saved_state: dict[str, dict],
    current_time: datetime | None = None,
) -> list[str]:
    """Detect jobs that were missed while Agent was offline.

    A job is considered missed if its ``next_run`` is in the past.

    Returns a list of missed job IDs.
    """
    if current_time is None:
        current_time = datetime.now()

    missed: list[str] = []
    for job_id, entry in saved_state.items():
        next_run = entry.get("next_run")
        if next_run and isinstance(next_run, datetime) and next_run < current_time:
            missed.append(job_id)
    return missed


def restore_scheduler_state(
    scheduler: Any,
    saved_state: dict[str, dict],
) -> None:
    """Restore persisted state into a running CronScheduler.

    Only restores state for jobs that are currently registered in the scheduler.
    """
    from chatmd.engine.cron_scheduler import CronTaskStatus

    for job_id, entry in saved_state.items():
        state = scheduler.get_state(job_id)
        if not state:
            continue
        # Restore counters
        state.run_count = entry.get("run_count", 0)
        state.fail_count = entry.get("fail_count", 0)
        state.consecutive_failures = entry.get("consecutive_failures", 0)
        # Restore last_run
        if entry.get("last_run"):
            state.last_run = entry["last_run"]
        # Restore status
        saved_status = entry.get("status", "active")
        if saved_status == "paused":
            state.status = CronTaskStatus.PAUSED
    logger.debug("Restored cron state for %d jobs", len(saved_state))
