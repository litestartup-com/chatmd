"""CronScheduler — background tick-based cron job executor.

Manages cron job registration, scheduling, execution, overlap prevention,
and execution history. Designed to be integrated with the Agent.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from chatmd.engine.cron_parser import CronExpr, CronJob, EveryExpr

logger = logging.getLogger(__name__)

# Type alias for the executor callback: (command, job_id) -> None
CronExecutor = Callable[[str, str], None]


class CronTaskStatus(Enum):
    """Cron task lifecycle status."""

    ACTIVE = "active"
    PAUSED = "paused"


@dataclass
class CronTaskState:
    """Runtime state for a registered cron job."""

    job: CronJob
    status: CronTaskStatus = CronTaskStatus.ACTIVE
    next_run: datetime | None = None
    last_run: datetime | None = None
    run_count: int = 0
    fail_count: int = 0
    consecutive_failures: int = 0
    is_running: bool = False
    history: list[dict] = field(default_factory=list)


class CronScheduler:
    """Background cron scheduler with tick-based execution.

    Usage::

        sched = CronScheduler()
        sched.set_executor(my_callback)
        sched.register(job)
        sched.start()
        # ... later ...
        sched.stop()
    """

    def __init__(
        self,
        tick_interval: float | None = None,
        max_history: int = 20,
        job_timeout: float = 300.0,
    ) -> None:
        self._states: dict[str, CronTaskState] = {}
        self._lock = threading.Lock()
        self._executor: CronExecutor | None = None
        self._on_job_complete: Callable[[str], None] | None = None
        self._tick_interval = tick_interval
        self._max_history = max_history
        self._job_timeout = job_timeout
        self._running = False
        self._stop_event = threading.Event()
        self._tick_thread: threading.Thread | None = None
        self._worker_pool: list[threading.Thread] = []

    # ── Executor ──────────────────────────────────────────────────

    def set_executor(self, executor: CronExecutor) -> None:
        """Set the callback that executes cron commands."""
        self._executor = executor

    def set_on_job_complete(self, callback: Callable[[str], None]) -> None:
        """Set a callback invoked after each job completes (success or failure)."""
        self._on_job_complete = callback

    # ── Registration ──────────────────────────────────────────────

    def register(self, job: CronJob) -> None:
        """Register or update a cron job."""
        with self._lock:
            existing = self._states.get(job.job_id)
            if existing:
                # Update the job definition, preserve runtime state
                existing.job = job
                if existing.next_run is None:
                    existing.next_run = self._calc_next_run(job)
            else:
                state = CronTaskState(
                    job=job,
                    next_run=self._calc_next_run(job),
                )
                self._states[job.job_id] = state
        logger.debug("Cron job registered: %s → %s", job.job_id, job.command)

    def unregister(self, job_id: str) -> None:
        """Remove a cron job."""
        with self._lock:
            self._states.pop(job_id, None)
        logger.debug("Cron job unregistered: %s", job_id)

    def sync_jobs(self, jobs: list[CronJob]) -> None:
        """Synchronize registered jobs with a new list.

        Adds new jobs, updates existing ones, removes jobs not in the list.
        """
        new_ids = {j.job_id for j in jobs}
        with self._lock:
            # Remove jobs no longer in the list
            to_remove = [
                jid for jid in self._states if jid not in new_ids
            ]
            for jid in to_remove:
                self._states.pop(jid, None)
                logger.debug("Cron job removed (sync): %s", jid)

        # Register/update remaining jobs (outside lock — register() locks)
        for job in jobs:
            self.register(job)

    # ── State queries ─────────────────────────────────────────────

    def get_state(self, job_id: str) -> CronTaskState | None:
        """Get the runtime state of a job."""
        return self._states.get(job_id)

    def get_all_states(self) -> dict[str, CronTaskState]:
        """Return all registered job states."""
        return dict(self._states)

    def get_history(
        self,
        job_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Get execution history, optionally filtered by job_id."""
        if limit is None:
            limit = self._max_history

        if job_id:
            state = self._states.get(job_id)
            if not state:
                return []
            return list(state.history[-limit:])

        # All jobs, sorted by time descending
        all_history: list[dict] = []
        for st in self._states.values():
            all_history.extend(st.history)
        all_history.sort(key=lambda h: h.get("time", ""), reverse=True)
        return all_history[:limit]

    # ── Pause / Resume ────────────────────────────────────────────

    def pause(self, job_id: str) -> bool:
        """Pause a job. Returns False if job not found."""
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return False
            state.status = CronTaskStatus.PAUSED
            return True

    def resume(self, job_id: str) -> bool:
        """Resume a paused job. Returns False if job not found."""
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return False
            state.status = CronTaskStatus.ACTIVE
            return True

    # ── Tick interval ─────────────────────────────────────────────

    def compute_tick_interval(self) -> float:
        """Compute optimal tick interval based on registered jobs.

        Strategy:
        - @every with interval < 10s → 1s tick
        - @every with interval < 60s → 5s tick
        - All others (minute-level cron) → 30s tick
        """
        min_interval_secs = float("inf")

        for state in self._states.values():
            sched = state.job.schedule
            if isinstance(sched, EveryExpr):
                secs = sched.interval.total_seconds()
                min_interval_secs = min(min_interval_secs, secs)

        if min_interval_secs < 10:
            return 1.0
        if min_interval_secs < 60:
            return 5.0
        return 30.0

    # ── Lifecycle ─────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the background tick thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._tick_thread = threading.Thread(
            target=self._tick_loop,
            name="cron-scheduler",
            daemon=True,
        )
        self._tick_thread.start()
        logger.info("CronScheduler started")

    def stop(self) -> None:
        """Stop the background tick thread."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._tick_thread:
            self._tick_thread.join(timeout=10)
            self._tick_thread = None
        # Wait for any running workers
        for t in self._worker_pool:
            t.join(timeout=5)
        self._worker_pool.clear()
        logger.info("CronScheduler stopped")

    # ── Internal tick ─────────────────────────────────────────────

    def _tick_loop(self) -> None:
        """Main tick loop running in background thread."""
        while not self._stop_event.is_set():
            interval = (
                self._tick_interval
                if self._tick_interval is not None
                else self.compute_tick_interval()
            )
            try:
                self._tick_once()
            except Exception:
                logger.exception("CronScheduler tick error")
            self._stop_event.wait(timeout=interval)

    def _tick_once(self) -> None:
        """Check all jobs and fire any that are due."""
        now = datetime.now()
        with self._lock:
            states_snapshot = list(self._states.values())

        for state in states_snapshot:
            if state.status != CronTaskStatus.ACTIVE:
                continue
            if state.is_running:
                continue  # overlap prevention
            if state.next_run is None:
                continue
            if state.next_run > now:
                continue

            # Job is due — fire it
            self._fire_job(state, now)

    def _fire_job(self, state: CronTaskState, now: datetime) -> None:
        """Execute a due job in a worker thread."""
        if self._executor is None:
            logger.warning(
                "No executor set, skipping cron job: %s",
                state.job.job_id,
            )
            return

        state.is_running = True
        # Pre-calculate next_run so it's ready for the next tick
        state.next_run = self._calc_next_run(state.job, now)

        worker = threading.Thread(
            target=self._run_job,
            args=(state, now),
            name=f"cron-{state.job.job_id}",
            daemon=True,
        )
        self._worker_pool.append(worker)
        worker.start()

        # Clean up finished workers
        self._worker_pool = [
            t for t in self._worker_pool if t.is_alive()
        ]

    def _run_job(self, state: CronTaskState, fired_at: datetime) -> None:
        """Worker thread: execute the job with timeout and record result."""
        job = state.job
        logger.info("Cron job firing: %s → %s", job.job_id, job.command)

        record: dict = {
            "job_id": job.job_id,
            "command": job.command,
            "time": fired_at.isoformat(),
        }

        # Run executor in a sub-thread so we can enforce a timeout
        result_holder: dict = {}
        done_event = threading.Event()

        def _exec() -> None:
            try:
                assert self._executor is not None
                self._executor(job.command, job.job_id)
                result_holder["ok"] = True
            except Exception as exc:
                result_holder["error"] = exc
            finally:
                done_event.set()

        exec_thread = threading.Thread(
            target=_exec,
            name=f"cron-exec-{job.job_id}",
            daemon=True,
        )
        exec_thread.start()
        timed_out = not done_event.wait(timeout=self._job_timeout)

        if timed_out:
            record["status"] = "timeout"
            record["error"] = (
                f"Job timed out after {self._job_timeout}s"
            )
            state.run_count += 1
            state.fail_count += 1
            state.consecutive_failures += 1
            state.last_run = datetime.now()
            logger.error(
                "Cron job timed out after %.0fs: %s",
                self._job_timeout, job.job_id,
            )
        elif "error" in result_holder:
            exc = result_holder["error"]
            record["status"] = "failed"
            record["error"] = str(exc)
            state.run_count += 1
            state.fail_count += 1
            state.consecutive_failures += 1
            state.last_run = datetime.now()
            logger.exception("Cron job failed: %s", job.job_id)
        else:
            record["status"] = "success"
            state.run_count += 1
            state.consecutive_failures = 0
            state.last_run = datetime.now()
            logger.info("Cron job completed: %s", job.job_id)

        state.is_running = False
        # Append to history, trim if needed
        state.history.append(record)
        if len(state.history) > self._max_history:
            state.history = state.history[-self._max_history:]

        # Notify completion listener (e.g. to refresh inline status)
        if self._on_job_complete:
            try:
                self._on_job_complete(job.job_id)
            except Exception:
                logger.exception("on_job_complete callback failed")

    # ── Next-run calculation ──────────────────────────────────────

    @staticmethod
    def _calc_next_run(
        job: CronJob,
        after: datetime | None = None,
    ) -> datetime | None:
        """Calculate the next run time for a job."""
        if after is None:
            after = datetime.now()

        sched = job.schedule
        if isinstance(sched, CronExpr):
            return sched.next_fire(after)
        if isinstance(sched, EveryExpr):
            return sched.next_fire(after)
        return None  # pragma: no cover
