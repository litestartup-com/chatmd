"""Tests for chatmd.infra.pid_utils — create-time PID verification.

Regression tests for the bug where ``chatmd status`` reported the Agent as
running even though the Windows Service was stopped and commands typed into
``chat.md`` never got processed.  Root cause: PID recycling after the Agent
crashed/was killed ungracefully left a stale ``agent.pid``; a simple
``OpenProcess`` check then returned True for the recycled PID.
"""

from __future__ import annotations

import os
from pathlib import Path

from chatmd.infra.pid_utils import (
    get_process_create_time,
    is_agent_alive,
    is_process_alive,
    read_pid_file,
    write_pid_file,
)


class TestCreateTimeLookup:
    def test_current_process_has_create_time(self) -> None:
        """The current process must expose a non-None create-time token."""
        ctime = get_process_create_time(os.getpid())
        assert ctime is not None
        assert isinstance(ctime, int)

    def test_nonexistent_pid_returns_none(self) -> None:
        """A PID that is almost certainly unused must return None."""
        assert get_process_create_time(2_999_999) is None

    def test_invalid_pid_returns_none(self) -> None:
        assert get_process_create_time(0) is None
        assert get_process_create_time(-1) is None


class TestReadWritePidFile:
    def test_roundtrip_current_process(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "agent.pid"
        write_pid_file(pid_file)
        parsed = read_pid_file(pid_file)
        assert parsed is not None
        pid, ctime = parsed
        assert pid == os.getpid()
        assert ctime == get_process_create_time(os.getpid())

    def test_legacy_format_missing_ctime(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "agent.pid"
        pid_file.write_text("12345", encoding="utf-8")
        parsed = read_pid_file(pid_file)
        assert parsed == (12345, None)

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert read_pid_file(tmp_path / "missing.pid") is None

    def test_malformed_file_returns_none(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "agent.pid"
        pid_file.write_text("not-a-number", encoding="utf-8")
        assert read_pid_file(pid_file) is None

    def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "agent.pid"
        pid_file.write_text("", encoding="utf-8")
        assert read_pid_file(pid_file) is None


class TestIsAgentAlive:
    """End-to-end liveness check — the actual bug regression suite."""

    def test_current_process_is_alive(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "agent.pid"
        write_pid_file(pid_file)
        assert is_agent_alive(pid_file) is True

    def test_stale_pid_without_ctime_is_treated_as_dead(self, tmp_path: Path) -> None:
        """Legacy pid files (pre-create-time) must be treated as stale.

        This forces a clean restart after upgrading from an older ChatMD
        version and prevents the status/service mismatch described in the
        bug report.
        """
        pid_file = tmp_path / "agent.pid"
        # Current process's PID *with no ctime* — must NOT be reported alive.
        pid_file.write_text(str(os.getpid()), encoding="utf-8")
        assert is_agent_alive(pid_file) is False

    def test_ctime_mismatch_detected(self, tmp_path: Path) -> None:
        """When the stored ctime doesn't match, the PID has been recycled.

        This is the exact failure mode that caused ``chatmd status`` to
        report the Agent as running while the Windows Service was stopped.
        """
        pid_file = tmp_path / "agent.pid"
        # Real PID, but a fake creation time — simulates PID reuse.
        pid_file.write_text(f"{os.getpid()}\n1", encoding="utf-8")
        assert is_agent_alive(pid_file) is False

    def test_nonexistent_pid_is_not_alive(self, tmp_path: Path) -> None:
        pid_file = tmp_path / "agent.pid"
        pid_file.write_text("2999999\n12345", encoding="utf-8")
        assert is_agent_alive(pid_file) is False

    def test_missing_pid_file_is_not_alive(self, tmp_path: Path) -> None:
        assert is_agent_alive(tmp_path / "missing.pid") is False


class TestLegacyIsProcessAlive:
    """The legacy PID-only helper is still used for quick reality checks."""

    def test_current_process(self) -> None:
        assert is_process_alive(os.getpid()) is True

    def test_nonexistent(self) -> None:
        assert is_process_alive(2_999_999) is False

    def test_with_matching_ctime(self) -> None:
        pid = os.getpid()
        ctime = get_process_create_time(pid)
        assert is_process_alive(pid, expected_create_time=ctime) is True

    def test_with_mismatched_ctime(self) -> None:
        assert is_process_alive(os.getpid(), expected_create_time=1) is False
