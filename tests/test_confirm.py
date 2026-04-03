"""Tests for confirmation window."""

import threading
import time

from chatmd.engine.confirm import ConfirmationWindow


class TestConfirmationWindow:
    def test_skip_commands(self):
        cw = ConfirmationWindow(delay=1.0, skip_commands=["date", "help"])
        assert not cw.needs_confirmation("date")
        assert not cw.needs_confirmation("help")
        assert cw.needs_confirmation("translate")

    def test_request_and_cancel(self):
        cw = ConfirmationWindow(delay=5.0)
        called = []
        pending = cw.request_confirmation(
            command_text="/dangerous",
            source_file=None,
            source_line=1,
            callback=lambda: called.append(True),
        )
        assert pending.confirm_id.startswith("confirm-")
        assert cw.cancel(pending.confirm_id)
        time.sleep(0.1)
        assert called == []

    def test_timer_fires_executes(self):
        cw = ConfirmationWindow(delay=0.1)
        event = threading.Event()
        cw.request_confirmation(
            command_text="/do-it",
            source_file=None,
            source_line=1,
            callback=event.set,
        )
        event.wait(timeout=2.0)
        assert event.is_set()

    def test_cancel_nonexistent(self):
        cw = ConfirmationWindow()
        assert not cw.cancel("nonexistent-id")

    def test_cancel_all(self):
        cw = ConfirmationWindow(delay=10.0)
        for i in range(3):
            cw.request_confirmation(
                command_text=f"/cmd{i}",
                source_file=None,
                source_line=i,
                callback=lambda: None,
            )
        assert len(cw.list_pending()) == 3
        cancelled = cw.cancel_all()
        assert cancelled == 3
        assert len(cw.list_pending()) == 0

    def test_confirmation_marker(self):
        cw = ConfirmationWindow(delay=1.5)
        marker = cw.confirmation_marker("confirm-1", "/translate")
        assert "confirm-1" in marker
        assert "/translate" in marker
        assert "1.5s" in marker

    def test_get_pending(self):
        cw = ConfirmationWindow(delay=10.0)
        pending = cw.request_confirmation(
            command_text="/test",
            source_file=None,
            source_line=1,
            callback=lambda: None,
        )
        found = cw.get_pending(pending.confirm_id)
        assert found is not None
        assert found.command_text == "/test"
        cw.cancel_all()

    def test_delay_setter(self):
        cw = ConfirmationWindow(delay=1.0)
        assert cw.delay == 1.0
        cw.delay = 2.5
        assert cw.delay == 2.5
        cw.delay = -1.0
        assert cw.delay == 0.0
