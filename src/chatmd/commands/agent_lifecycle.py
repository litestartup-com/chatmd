"""Agent lifecycle commands — start, stop, status."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import click

from chatmd.exceptions import AgentError
from chatmd.i18n import t
from chatmd.infra.pid_utils import (
    is_agent_alive,
    is_process_alive,
    read_pid_file,
)

logger = logging.getLogger(__name__)


def _is_process_alive(pid: int) -> bool:
    """Legacy PID-only liveness check (cross-platform).

    Prefer :func:`_is_agent_alive` which also verifies the process creation
    time and thus avoids PID-reuse false positives.
    """
    return is_process_alive(pid)


def _is_agent_alive(pid_file: Path) -> bool:
    """Return True when *pid_file* belongs to a live ChatMD Agent process.

    See :mod:`chatmd.infra.pid_utils` for the create-time verification that
    protects against PID reuse (stopped Windows Service leaving behind a
    stale ``agent.pid`` whose PID was later re-assigned by the OS).
    """
    return is_agent_alive(pid_file)


def _read_log_level(workspace: Path) -> int:
    """Read ``logging.level`` from agent.yaml, defaulting to INFO."""
    agent_yaml = workspace / ".chatmd" / "agent.yaml"
    if agent_yaml.exists():
        try:
            import yaml
            with open(agent_yaml, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            level_str = (data.get("logging") or {}).get("level", "INFO")
            return getattr(logging, str(level_str).upper(), logging.INFO)
        except Exception:
            pass
    return logging.INFO


def _setup_logging(workspace: Path) -> None:
    """Configure logging for the Agent process."""
    log_dir = workspace / ".chatmd" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_level = _read_log_level(workspace)

    root = logging.getLogger("chatmd")
    root.setLevel(logging.DEBUG)

    # Console handler — always INFO regardless of config
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root.addHandler(console)

    # File handler — respects logging.level from agent.yaml
    fh = logging.FileHandler(log_dir / "agent.log", encoding="utf-8")
    fh.setLevel(file_level)
    fh.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root.addHandler(fh)


def run_start(workspace_str: str) -> None:
    """Start the ChatMD Agent in the foreground."""
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        click.echo(t("cli.run_init_first"))
        sys.exit(1)

    _setup_logging(workspace)

    from chatmd.engine.agent import Agent

    try:
        agent = Agent(workspace)
        click.echo(t("cli.starting", workspace=workspace))
        click.echo(t("cli.press_ctrl_c"))
        agent.run_forever()
    except AgentError as exc:
        click.echo(f"❌ {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo(t("cli.agent_stopped"))


def run_start_daemon(workspace_str: str) -> None:
    """Start the ChatMD Agent as a detached background process.

    Spawns ``chatmd start -w <workspace>`` in a new detached process,
    then the current (parent) process exits immediately.

    Cross-platform:
    - Windows: subprocess.CREATE_NO_WINDOW + CREATE_NEW_PROCESS_GROUP
    - Unix: start_new_session=True (setsid)

    Logs go to .chatmd/logs/agent.log (same as foreground mode).
    """
    import subprocess

    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        click.echo(t("cli.run_init_first"))
        sys.exit(1)

    # Check for existing instance via PID file (with create-time verification)
    pid_file = chatmd_dir / "agent.pid"
    if pid_file.exists():
        if _is_agent_alive(pid_file):
            parsed = read_pid_file(pid_file)
            pid = parsed[0] if parsed else 0
            click.echo(t("cli.daemon_already_running", pid=pid))
            return
        # Stale, legacy, or recycled PID — remove so this daemon can start
        pid_file.unlink(missing_ok=True)

    # Build the command: re-invoke chatmd start (without --daemon) for this workspace
    cmd = [sys.executable, "-m", "chatmd", "start", "-w", str(workspace)]

    # Ensure log directory exists
    log_dir = chatmd_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "agent.log"

    # Inherit current env and force UTF-8 for the child process (avoids GBK crash on Windows)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    if sys.platform == "win32":
        # Windows: CREATE_NO_WINDOW prevents a console window from appearing
        # CREATE_NEW_PROCESS_GROUP detaches from parent's console group
        creation_flags = (
            subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        proc = subprocess.Popen(
            cmd,
            stdout=open(log_dir / "daemon_stdout.log", "a", encoding="utf-8"),
            stderr=open(log_dir / "daemon_stderr.log", "a", encoding="utf-8"),
            stdin=subprocess.DEVNULL,
            creationflags=creation_flags,
            env=env,
        )
    else:
        # Unix: start_new_session=True calls setsid(), fully detaching
        proc = subprocess.Popen(
            cmd,
            stdout=open(log_dir / "daemon_stdout.log", "a", encoding="utf-8"),
            stderr=open(log_dir / "daemon_stderr.log", "a", encoding="utf-8"),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )

    # Wait briefly to check if the process started successfully
    import time
    time.sleep(0.5)

    if proc.poll() is not None:
        click.echo(t("cli.daemon_failed", code=proc.returncode))
        sys.exit(1)

    click.echo(t("cli.daemon_started", pid=proc.pid, workspace=workspace))
    click.echo(t("cli.daemon_log_hint", log=log_file))
    click.echo(t("cli.daemon_stop_hint"))


def run_stop(workspace_str: str) -> None:
    """Stop a running ChatMD Agent using a signal file (cross-platform).

    Strategy:
    1. Write .chatmd/stop.signal — the Agent main loop detects this and
       shuts down gracefully (works on all platforms).
    2. On Unix, also send SIGTERM as a belt-and-suspenders fallback.
    3. Wait briefly for the process to exit, then clean up.
    """
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"
    pid_file = chatmd_dir / "agent.pid"
    stop_signal = chatmd_dir / "stop.signal"

    if not pid_file.exists():
        click.echo(t("cli.no_running_agent"))
        return

    parsed = read_pid_file(pid_file)
    if parsed is None:
        click.echo(t("cli.pid_corrupted"))
        pid_file.unlink(missing_ok=True)
        return

    pid = parsed[0]

    # Verify the agent is actually running (PID + create-time match) before
    # sending the stop signal.  This catches stale or recycled PIDs that
    # would otherwise cause the user to chase a non-existent process.
    if not _is_agent_alive(pid_file):
        click.echo(t("cli.process_not_found"))
        pid_file.unlink(missing_ok=True)
        stop_signal.unlink(missing_ok=True)
        return

    # 1. Write stop signal file (cross-platform, always works)
    try:
        stop_signal.write_text(str(pid), encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to write stop signal file: %s", exc)

    # 2. On Unix, also send SIGTERM as fallback
    if sys.platform != "win32":
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            click.echo(t("cli.process_not_found"))
            pid_file.unlink(missing_ok=True)
            stop_signal.unlink(missing_ok=True)
            return
        except PermissionError:
            click.echo(t("cli.no_permission", pid=pid))
            return

    # 3. Wait for process to exit (up to 5 seconds)
    import time
    for _ in range(10):
        if not _is_process_alive(pid):
            break
        time.sleep(0.5)

    click.echo(t("cli.stop_signal_sent", pid=pid))


def run_restart(workspace_str: str) -> None:
    """Restart the ChatMD Agent (stop then start as daemon).

    Behaviour:
    - If a daemon is running → stop it, then start a new daemon.
    - If no daemon is running → just start a new daemon.
    - Always restarts in daemon (background) mode.
    """
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        click.echo(t("cli.run_init_first"))
        sys.exit(1)

    pid_file = chatmd_dir / "agent.pid"
    was_running = False

    if pid_file.exists():
        if _is_agent_alive(pid_file):
            parsed = read_pid_file(pid_file)
            pid = parsed[0] if parsed else 0
            was_running = True
            click.echo(t("cli.restart_stopping", pid=pid))
            run_stop(workspace_str)

            # Wait for process to fully exit (up to 5s)
            import time
            for _ in range(10):
                if not _is_process_alive(pid):
                    break
                time.sleep(0.5)
        else:
            # Stale, legacy, or recycled PID file — clean it up
            pid_file.unlink(missing_ok=True)

    if was_running:
        click.echo(t("cli.restart_starting"))
    else:
        click.echo(t("cli.restart_not_running"))

    run_start_daemon(workspace_str)


def run_status(workspace_str: str) -> None:
    """Show Agent status."""
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        return

    pid_file = chatmd_dir / "agent.pid"
    if not pid_file.exists():
        click.echo(t("cli.agent_not_running"))
        return

    parsed = read_pid_file(pid_file)
    if parsed is None:
        click.echo(t("cli.agent_not_running_stale"))
        pid_file.unlink(missing_ok=True)
        return

    pid = parsed[0]

    # Use PID + create-time verification to avoid false positives when the
    # OS has recycled the stored PID (e.g. after a Windows Service crash or
    # hard-kill that left agent.pid on disk).
    if _is_agent_alive(pid_file):
        click.echo(t("cli.agent_running", pid=pid))
    else:
        click.echo(t("cli.agent_not_running_stale"))
        pid_file.unlink(missing_ok=True)

    # Show workspace info
    click.echo(t("cli.workspace_label", workspace=workspace))

    skills_dir = chatmd_dir / "skills"
    if skills_dir.exists():
        yaml_count = len(list(skills_dir.glob("*.yaml")))
        py_count = len(list(skills_dir.glob("*.py")))
        click.echo(t("cli.custom_skills", yaml_count=yaml_count, py_count=py_count))
