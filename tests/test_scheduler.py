"""Tests for the task scheduler."""

import threading

from chatmd.engine.scheduler import Scheduler, TaskStatus


class TestSyncExecution:
    """Test synchronous task execution."""

    def test_sync_success(self):
        scheduler = Scheduler()
        task = scheduler.submit_sync(
            skill_name="date",
            execute_fn=lambda: "2026-03-30",
            input_text="",
        )
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "2026-03-30"
        assert task.completed_at is not None
        scheduler.shutdown(wait=False)

    def test_sync_failure(self):
        def failing():
            raise ValueError("test error")

        scheduler = Scheduler()
        task = scheduler.submit_sync(
            skill_name="fail",
            execute_fn=failing,
            input_text="",
        )
        assert task.status == TaskStatus.FAILED
        assert "test error" in task.error
        scheduler.shutdown(wait=False)


class TestAsyncExecution:
    """Test asynchronous task execution."""

    def test_async_completes(self):
        done_event = threading.Event()
        result_holder = {}

        def on_complete(task):
            result_holder["task"] = task
            done_event.set()

        scheduler = Scheduler()
        task = scheduler.submit_async(
            skill_name="ask",
            execute_fn=lambda: "AI response",
            input_text="Hello",
            on_complete=on_complete,
        )

        # Task should start as PENDING
        assert task.id.startswith("task-")

        # Wait for completion
        done_event.wait(timeout=5)
        assert result_holder["task"].status == TaskStatus.COMPLETED
        assert result_holder["task"].result == "AI response"
        scheduler.shutdown(wait=False)

    def test_async_failure(self):
        done_event = threading.Event()
        result_holder = {}

        def on_complete(task):
            result_holder["task"] = task
            done_event.set()

        scheduler = Scheduler()
        scheduler.submit_async(
            skill_name="fail",
            execute_fn=lambda: (_ for _ in ()).throw(RuntimeError("network error")),
            input_text="Hello",
            on_complete=on_complete,
        )

        done_event.wait(timeout=5)
        assert result_holder["task"].status == TaskStatus.FAILED
        assert "network error" in result_holder["task"].error
        scheduler.shutdown(wait=False)


class TestTaskManagement:
    """Test task tracking and cancellation."""

    def test_get_task(self):
        scheduler = Scheduler()
        task = scheduler.submit_sync(
            skill_name="date",
            execute_fn=lambda: "ok",
        )
        found = scheduler.get_task(task.id)
        assert found is task
        scheduler.shutdown(wait=False)

    def test_get_all_tasks(self):
        scheduler = Scheduler()
        scheduler.submit_sync(skill_name="a", execute_fn=lambda: "1")
        scheduler.submit_sync(skill_name="b", execute_fn=lambda: "2")
        assert len(scheduler.get_all_tasks()) == 2
        scheduler.shutdown(wait=False)

    def test_cancel_pending(self):
        scheduler = Scheduler(max_concurrent=1)

        # Block the executor with a slow task
        blocker_event = threading.Event()

        def slow_fn():
            blocker_event.wait(timeout=5)
            return "done"

        scheduler.submit_async(
            skill_name="slow",
            execute_fn=slow_fn,
        )
        # Submit another — it may still be pending
        task2 = scheduler.submit_async(
            skill_name="cancel_me",
            execute_fn=lambda: "never",
        )

        # Cancel attempt — may or may not succeed depending on timing
        scheduler.cancel(task2.id)

        blocker_event.set()
        scheduler.shutdown(wait=True)

    def test_task_serialization(self):
        scheduler = Scheduler()
        task = scheduler.submit_sync(
            skill_name="date",
            execute_fn=lambda: "2026-03-30",
            input_text="test",
            args={"fmt": "%Y-%m-%d"},
        )
        d = task.to_dict()
        assert d["skill_name"] == "date"
        assert d["status"] == "completed"
        assert d["result"] == "2026-03-30"
        assert d["args"] == {"fmt": "%Y-%m-%d"}
        scheduler.shutdown(wait=False)
