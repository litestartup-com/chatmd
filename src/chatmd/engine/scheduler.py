"""Task scheduler — sync/async execution with state machine and persistence."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    QUEUED = "queued"  # offline queue


@dataclass
class Task:
    """Represents a single scheduled task."""

    id: str
    skill_name: str
    input_text: str
    args: dict
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    result: str | None = None
    error: str | None = None
    source_file: Path | None = None
    source_line: int = 0
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize task to a dict for JSON persistence."""
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "input_text": self.input_text,
            "args": self.args,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "source_file": str(self.source_file) if self.source_file else None,
            "source_line": self.source_line,
            "raw_text": self.raw_text,
        }


def _generate_task_id() -> str:
    """Generate a short unique task ID like ``task-a1b2``."""
    return f"task-{uuid.uuid4().hex[:4]}"


class Scheduler:
    """Manages sync and async task execution.

    - Sync skills execute immediately in the calling thread.
    - Async skills are submitted to a thread pool and tracked.
    """

    def __init__(self, max_concurrent: int = 3, task_timeout: float = 60) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._max_concurrent = max_concurrent
        self._task_timeout = task_timeout

    def submit_sync(
        self,
        skill_name: str,
        execute_fn: Callable[[], str],
        *,
        input_text: str = "",
        args: dict | None = None,
        source_file: Path | None = None,
        source_line: int = 0,
        raw_text: str = "",
    ) -> Task:
        """Execute a synchronous skill immediately, returning the completed Task."""
        task = Task(
            id=_generate_task_id(),
            skill_name=skill_name,
            input_text=input_text,
            args=args or {},
            source_file=source_file,
            source_line=source_line,
            raw_text=raw_text,
        )

        with self._lock:
            self._tasks[task.id] = task

        task.status = TaskStatus.RUNNING
        try:
            result = execute_fn()
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = datetime.now()
            logger.exception("Sync task %s failed", task.id)

        return task

    def submit_async(
        self,
        skill_name: str,
        execute_fn: Callable[[], str],
        *,
        input_text: str = "",
        args: dict | None = None,
        source_file: Path | None = None,
        source_line: int = 0,
        raw_text: str = "",
        on_complete: Callable[[Task], None] | None = None,
    ) -> Task:
        """Submit an async skill for background execution.

        Returns the Task immediately in PENDING state.
        *on_complete* is called when the task finishes (in the worker thread).
        """
        task = Task(
            id=_generate_task_id(),
            skill_name=skill_name,
            input_text=input_text,
            args=args or {},
            source_file=source_file,
            source_line=source_line,
            raw_text=raw_text,
        )

        with self._lock:
            self._tasks[task.id] = task

        self._executor.submit(self._run_async, task, execute_fn, on_complete)
        return task

    def cancel(self, task_id: str) -> bool:
        """Cancel a task if it is still PENDING or QUEUED."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in (TaskStatus.PENDING, TaskStatus.QUEUED):
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                return True
            return False

    def get_task(self, task_id: str) -> Task | None:
        """Look up a task by ID."""
        return self._tasks.get(task_id)

    def get_active_tasks(self) -> list[Task]:
        """Return tasks that are PENDING or RUNNING."""
        return [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        ]

    def get_all_tasks(self) -> list[Task]:
        """Return all tracked tasks."""
        return list(self._tasks.values())

    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Shut down the executor, optionally waiting for running tasks."""
        self._executor.shutdown(wait=wait)

    def _run_async(
        self,
        task: Task,
        execute_fn: Callable[[], str],
        on_complete: Callable[[Task], None] | None,
    ) -> None:
        """Worker function that runs in the thread pool."""
        task.status = TaskStatus.RUNNING
        logger.info("Async task %s started: %s", task.id, task.skill_name)

        done_event = threading.Event()

        def _watchdog() -> None:
            """Fire after timeout — mark task FAILED if still running."""
            if not done_event.is_set() and task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
                task.error = f"Task timed out after {self._task_timeout}s"
                task.completed_at = datetime.now()
                logger.warning("Async task %s timed out after %ss", task.id, self._task_timeout)
                if on_complete:
                    try:
                        on_complete(task)
                    except Exception:
                        logger.exception(
                            "on_complete callback failed for timed-out task %s", task.id,
                        )

        # Start watchdog timer
        timer: threading.Timer | None = None
        if self._task_timeout > 0:
            timer = threading.Timer(self._task_timeout, _watchdog)
            timer.daemon = True
            timer.start()

        try:
            result = execute_fn()
            done_event.set()
            if timer:
                timer.cancel()
            # Only update if watchdog hasn't already marked it as failed
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                logger.info("Async task %s completed", task.id)
            else:
                logger.info("Async task %s finished after timeout, result discarded", task.id)
                return  # on_complete already called by watchdog
        except Exception as exc:
            done_event.set()
            if timer:
                timer.cancel()
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                task.completed_at = datetime.now()
                logger.exception("Async task %s failed", task.id)
            else:
                return  # timed out already

        if on_complete:
            try:
                on_complete(task)
            except Exception:
                logger.exception("on_complete callback failed for task %s", task.id)
