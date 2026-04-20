"""PID-file helpers with create-time verification.

Why create-time verification?
-----------------------------
Operating systems recycle process IDs.  If a ChatMD Agent crashes or is killed
ungracefully, the PID stored in ``.chatmd/agent.pid`` can later be re-used by
an unrelated process.  A naive ``OpenProcess`` / ``kill(pid, 0)`` check would
then return *True* for that recycled PID and ``chatmd status`` would falsely
report the Agent as running — while the Windows Service, SCM, or user all see
it as stopped, and commands typed into ``chat.md`` never get processed.

To prevent this we persist the **process creation time** alongside the PID:

    agent.pid:
        <pid>
        <create_time>

On every liveness check we re-read the process creation time from the OS and
compare it against the stored value.  A matching timestamp proves the live
process with that PID is indeed the Agent we started — not a recycled victim.

Legacy PID files without a create-time line are considered **stale** and will
be cleaned up on the next status/stop/start call.  This is the safe default:
the running Agent (if any) will rewrite the file in the new format on its next
``start()``.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Create-time lookup
# ---------------------------------------------------------------------------


def get_process_create_time(pid: int) -> int | None:
    """Return an opaque integer identifying the process creation time.

    Returns ``None`` when the process does not exist or its creation time
    cannot be determined.  The returned value is OS-specific and is only
    meaningful for equality comparison against a previously stored value.
    """
    if pid <= 0:
        return None

    if sys.platform == "win32":
        return _get_create_time_windows(pid)
    if sys.platform.startswith("linux"):
        return _get_create_time_linux(pid)
    # macOS / BSD fallback
    return _get_create_time_ps(pid)


def _get_create_time_windows(pid: int) -> int | None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000  # noqa: N806 — Win32 API constant
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        creation = wintypes.FILETIME()
        exit_ft = wintypes.FILETIME()
        kernel_ft = wintypes.FILETIME()
        user_ft = wintypes.FILETIME()
        ok = kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_ft),
            ctypes.byref(kernel_ft),
            ctypes.byref(user_ft),
        )
        if not ok:
            return None
        return (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    finally:
        kernel32.CloseHandle(handle)


def _get_create_time_linux(pid: int) -> int | None:
    stat_path = f"/proc/{pid}/stat"
    try:
        with open(stat_path, encoding="utf-8") as fh:
            data = fh.read()
    except OSError:
        return None
    # /proc/<pid>/stat format: "<pid> (<comm>) <state> ..." where <comm>
    # may contain spaces or parentheses.  Split after the last ')' to
    # reliably skip the comm field.
    rparen = data.rfind(")")
    if rparen == -1:
        return None
    rest = data[rparen + 1 :].split()
    # After comm, field index 0 is <state>, field 19 is <starttime>.
    if len(rest) < 20:
        return None
    try:
        return int(rest[19])
    except ValueError:
        return None


def _get_create_time_ps(pid: int) -> int | None:
    """Fallback using ``ps -o lstart=`` on macOS / BSD."""
    import subprocess

    try:
        out = subprocess.check_output(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    text = out.decode(errors="replace").strip()
    if not text:
        return None
    # Use a stable hash of the lstart string as the opaque token.
    return hash(text)


# ---------------------------------------------------------------------------
# Liveness check
# ---------------------------------------------------------------------------


def is_process_alive(pid: int, expected_create_time: int | None = None) -> bool:
    """Return True when a process with *pid* exists.

    When *expected_create_time* is given, also verify it matches the running
    process's creation time — guarding against PID reuse.  When ``None``,
    only the PID is checked (legacy behaviour, NOT recommended for Agent
    liveness).
    """
    if pid <= 0:
        return False

    if expected_create_time is not None:
        actual = get_process_create_time(pid)
        if actual is None:
            return False
        return actual == expected_create_time

    # Legacy PID-only path
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


# ---------------------------------------------------------------------------
# PID file I/O
# ---------------------------------------------------------------------------


def write_pid_file(pid_file: Path, pid: int | None = None) -> None:
    """Write ``<pid>\\n<create_time>`` to *pid_file*.

    When *pid* is ``None`` the current process's PID is used.  If the
    creation time cannot be determined (unusual), only the PID line is
    written; the file will then be treated as stale on the next check,
    prompting a clean restart.
    """
    actual_pid = pid if pid is not None else os.getpid()
    ctime = get_process_create_time(actual_pid)
    if ctime is None:
        pid_file.write_text(str(actual_pid), encoding="utf-8")
    else:
        pid_file.write_text(f"{actual_pid}\n{ctime}", encoding="utf-8")


def read_pid_file(pid_file: Path) -> tuple[int, int | None] | None:
    """Parse a PID file.

    Returns ``(pid, create_time_or_None)`` on success, or ``None`` when the
    file is missing / empty / malformed.
    """
    try:
        content = pid_file.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not content:
        return None
    lines = content.splitlines()
    try:
        pid = int(lines[0].strip())
    except (ValueError, IndexError):
        return None
    ctime: int | None = None
    if len(lines) > 1:
        try:
            ctime = int(lines[1].strip())
        except ValueError:
            ctime = None
    return pid, ctime


def is_agent_alive(pid_file: Path) -> bool:
    """Return True when *pid_file* points to a live ChatMD Agent process.

    A file without a stored create-time is treated as stale (False), which
    forces a clean restart after upgrading from an older ChatMD version.
    """
    parsed = read_pid_file(pid_file)
    if parsed is None:
        return False
    pid, expected_ctime = parsed
    if expected_ctime is None:
        return False
    return is_process_alive(pid, expected_create_time=expected_ctime)
