"""System service management — install, uninstall, status.

Generates platform-specific service configurations:
- Linux: systemd user unit (~/.config/systemd/user/chatmd-<hash>.service)
- macOS: launchd user agent (~/Library/LaunchAgents/com.chatmd.<hash>.plist)
- Windows: Task Scheduler XML (schtasks /create)
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import sys
import textwrap
from pathlib import Path

import click

from chatmd.i18n import t

logger = logging.getLogger(__name__)

# Short hash of workspace path for unique service naming
_HASH_LEN = 8


def _workspace_hash(workspace: Path) -> str:
    """Return a short hash of the workspace path for unique service naming."""
    return hashlib.md5(str(workspace).encode()).hexdigest()[:_HASH_LEN]


def _service_name(workspace: Path) -> str:
    """Return the service/unit name for a workspace."""
    return f"chatmd-{_workspace_hash(workspace)}"


# ---------------------------------------------------------------------------
# systemd (Linux)
# ---------------------------------------------------------------------------

def _systemd_unit_path(workspace: Path) -> Path:
    """Return the systemd user unit file path."""
    config_dir = Path.home() / ".config" / "systemd" / "user"
    return config_dir / f"{_service_name(workspace)}.service"


def _systemd_unit_content(workspace: Path) -> str:
    """Generate a systemd user unit file."""
    python = sys.executable
    return textwrap.dedent(f"""\
        [Unit]
        Description=ChatMD Agent ({workspace})
        After=network.target

        [Service]
        Type=simple
        ExecStart={python} -m chatmd start -w {workspace}
        WorkingDirectory={workspace}
        Restart=on-failure
        RestartSec=5

        [Install]
        WantedBy=default.target
    """)


def _install_systemd(workspace: Path) -> str:
    """Install a systemd user service."""
    unit_path = _systemd_unit_path(workspace)
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(_systemd_unit_content(workspace), encoding="utf-8")

    svc = _service_name(workspace)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", f"{svc}.service"], check=False)
    subprocess.run(["systemctl", "--user", "start", f"{svc}.service"], check=False)
    return str(unit_path)


def _uninstall_systemd(workspace: Path) -> str:
    """Uninstall a systemd user service."""
    svc = _service_name(workspace)
    subprocess.run(["systemctl", "--user", "stop", f"{svc}.service"], check=False)
    subprocess.run(["systemctl", "--user", "disable", f"{svc}.service"], check=False)

    unit_path = _systemd_unit_path(workspace)
    if unit_path.exists():
        unit_path.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    return str(unit_path)


def _status_systemd(workspace: Path) -> str:
    """Check systemd user service status."""
    svc = _service_name(workspace)
    result = subprocess.run(
        ["systemctl", "--user", "is-active", f"{svc}.service"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() or "unknown"


# ---------------------------------------------------------------------------
# launchd (macOS)
# ---------------------------------------------------------------------------

def _launchd_plist_path(workspace: Path) -> Path:
    """Return the launchd plist file path."""
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    label = f"com.chatmd.{_workspace_hash(workspace)}"
    return agents_dir / f"{label}.plist"


def _launchd_plist_content(workspace: Path) -> str:
    """Generate a launchd plist file."""
    python = sys.executable
    label = f"com.chatmd.{_workspace_hash(workspace)}"
    log_dir = workspace / ".chatmd" / "logs"
    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
          "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>{label}</string>
            <key>ProgramArguments</key>
            <array>
                <string>{python}</string>
                <string>-m</string>
                <string>chatmd</string>
                <string>start</string>
                <string>-w</string>
                <string>{workspace}</string>
            </array>
            <key>WorkingDirectory</key>
            <string>{workspace}</string>
            <key>RunAtLoad</key>
            <true/>
            <key>KeepAlive</key>
            <true/>
            <key>StandardOutPath</key>
            <string>{log_dir / "daemon_stdout.log"}</string>
            <key>StandardErrorPath</key>
            <string>{log_dir / "daemon_stderr.log"}</string>
        </dict>
        </plist>
    """)


def _install_launchd(workspace: Path) -> str:
    """Install a launchd user agent."""
    plist_path = _launchd_plist_path(workspace)
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure log directory exists
    (workspace / ".chatmd" / "logs").mkdir(parents=True, exist_ok=True)

    plist_path.write_text(_launchd_plist_content(workspace), encoding="utf-8")
    subprocess.run(["launchctl", "load", str(plist_path)], check=False)
    return str(plist_path)


def _uninstall_launchd(workspace: Path) -> str:
    """Uninstall a launchd user agent."""
    plist_path = _launchd_plist_path(workspace)
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
        plist_path.unlink()
    return str(plist_path)


def _status_launchd(workspace: Path) -> str:
    """Check launchd user agent status."""
    label = f"com.chatmd.{_workspace_hash(workspace)}"
    result = subprocess.run(
        ["launchctl", "list", label],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        return "running"
    return "not loaded"


# ---------------------------------------------------------------------------
# Windows Task Scheduler
# ---------------------------------------------------------------------------

def _pythonw_executable() -> str:
    """Return pythonw.exe path (no-console Python), fallback to python.exe."""
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if pythonw.exists():
        return str(pythonw)
    return sys.executable


def _win_task_name(workspace: Path) -> str:
    """Return the Windows Task Scheduler task name."""
    return f"ChatMD-{_workspace_hash(workspace)}"


def _install_windows(workspace: Path) -> str:
    """Install a Windows Task Scheduler task that runs at logon."""
    python = _pythonw_executable()
    task_name = _win_task_name(workspace)
    cmd_line = f'"{python}" -m chatmd start -w "{workspace}"'

    # schtasks /create with logon trigger
    args = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", cmd_line,
        "/sc", "onlogon",
        "/rl", "limited",
        "/f",  # force overwrite
    ]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning("schtasks create failed: %s", result.stderr.strip())
    return task_name


def _uninstall_windows(workspace: Path) -> str:
    """Remove the Windows Task Scheduler task."""
    task_name = _win_task_name(workspace)
    subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True, text=True, check=False,
    )
    return task_name


def _status_windows(workspace: Path) -> str:
    """Check Windows Task Scheduler task status."""
    task_name = _win_task_name(workspace)
    result = subprocess.run(
        ["schtasks", "/query", "/tn", task_name, "/fo", "csv", "/nh"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return "registered"
    return "not registered"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _start_agent_now(workspace: Path) -> int | None:
    """Start the agent as a daemon right now.  Returns PID or None on failure."""
    import os
    import time

    python = _pythonw_executable() if sys.platform == "win32" else sys.executable
    cmd = [python, "-m", "chatmd", "start", "-w", str(workspace)]
    log_dir = workspace / ".chatmd" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    if sys.platform == "win32":
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
        proc = subprocess.Popen(
            cmd,
            stdout=open(log_dir / "daemon_stdout.log", "a", encoding="utf-8"),
            stderr=open(log_dir / "daemon_stderr.log", "a", encoding="utf-8"),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )

    time.sleep(0.5)
    if proc.poll() is not None:
        return None
    return proc.pid


def run_service_install(workspace_str: str) -> None:
    """Install the ChatMD Agent as a system service and start it immediately."""
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        sys.exit(1)

    platform = sys.platform
    if platform == "linux":
        path = _install_systemd(workspace)
        svc = _service_name(workspace)
        click.echo(t("service.installed", platform="systemd", name=svc))
        click.echo(t("service.file_created", path=path))
        click.echo(t("service.auto_start"))
        click.echo(t("service.systemd_hints", name=svc))
    elif platform == "darwin":
        path = _install_launchd(workspace)
        click.echo(t("service.installed", platform="launchd", name=path))
        click.echo(t("service.file_created", path=path))
        click.echo(t("service.auto_start"))
        click.echo(t("service.launchd_hints"))
    elif platform == "win32":
        name = _install_windows(workspace)
        click.echo(t("service.installed", platform="Task Scheduler", name=name))
        click.echo(t("service.auto_start"))
        click.echo(t("service.win_hints"))
    else:
        click.echo(t("service.unsupported_platform", platform=platform))
        sys.exit(1)

    # Also start the agent right now so the user doesn't have to wait for reboot
    click.echo(t("service.starting_now"))
    pid = _start_agent_now(workspace)
    if pid:
        click.echo(t("service.started_now", pid=pid))
    else:
        click.echo(t("service.start_failed"))


def run_service_uninstall(workspace_str: str) -> None:
    """Uninstall the ChatMD Agent system service."""
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        sys.exit(1)

    platform = sys.platform
    if platform == "linux":
        path = _uninstall_systemd(workspace)
        click.echo(t("service.uninstalled", platform="systemd", path=path))
    elif platform == "darwin":
        path = _uninstall_launchd(workspace)
        click.echo(t("service.uninstalled", platform="launchd", path=path))
    elif platform == "win32":
        name = _uninstall_windows(workspace)
        click.echo(t("service.uninstalled", platform="Task Scheduler", path=name))
    else:
        click.echo(t("service.unsupported_platform", platform=platform))
        sys.exit(1)


def run_service_status(workspace_str: str) -> None:
    """Show the ChatMD Agent system service status."""
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        sys.exit(1)

    platform = sys.platform
    if platform == "linux":
        status = _status_systemd(workspace)
        svc = _service_name(workspace)
        click.echo(t("service.status_info", platform="systemd", name=svc, status=status))
    elif platform == "darwin":
        status = _status_launchd(workspace)
        label = f"com.chatmd.{_workspace_hash(workspace)}"
        click.echo(t("service.status_info", platform="launchd", name=label, status=status))
    elif platform == "win32":
        status = _status_windows(workspace)
        name = _win_task_name(workspace)
        click.echo(t("service.status_info", platform="Task Scheduler", name=name, status=status))
    else:
        click.echo(t("service.unsupported_platform", platform=platform))
