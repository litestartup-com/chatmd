"""System service management — install, uninstall, status.

Generates platform-specific service configurations:
- Linux: systemd user unit (~/.config/systemd/user/chatmd-<hash>.service)
- macOS: launchd user agent (~/Library/LaunchAgents/com.chatmd.<hash>.plist)
- Windows: Windows Service via pywin32 (SCM managed)
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
# Windows Service (pywin32)
# ---------------------------------------------------------------------------

def _win_service_name(workspace: Path) -> str:
    """Return the Windows Service name for a workspace."""
    return f"ChatMD-{_workspace_hash(workspace)}"


def _check_pywin32() -> bool:
    """Check whether pywin32 is installed."""
    try:
        import win32serviceutil  # noqa: F401
        return True
    except ImportError:
        return False


def _install_windows(workspace: Path) -> str:
    """Install and start a Windows Service for the ChatMD Agent."""
    from chatmd.commands.win_service import install_service

    svc_name = _win_service_name(workspace)
    install_service(svc_name, workspace)

    # Clean up legacy Task Scheduler entry if it exists
    _cleanup_legacy_task(workspace)

    return svc_name


def _uninstall_windows(workspace: Path) -> str:
    """Stop and remove the Windows Service."""
    from chatmd.commands.win_service import uninstall_service

    svc_name = _win_service_name(workspace)
    uninstall_service(svc_name)

    # Also clean up legacy Task Scheduler entry
    _cleanup_legacy_task(workspace)

    return svc_name


def _status_windows(workspace: Path) -> str:
    """Query Windows Service status."""
    from chatmd.commands.win_service import query_service_status

    svc_name = _win_service_name(workspace)
    return query_service_status(svc_name)


def _cleanup_legacy_task(workspace: Path) -> None:
    """Remove legacy Task Scheduler entry (pre-v0.2.7 migration)."""
    task_name = f"ChatMD-{_workspace_hash(workspace)}"
    result = subprocess.run(
        ["schtasks", "/query", "/tn", task_name, "/fo", "csv", "/nh"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True, text=True, check=False,
        )
        logger.info("Removed legacy Task Scheduler entry: %s", task_name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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
        if not _check_pywin32():
            click.echo(t("service.pywin32_required"))
            sys.exit(1)
        # Ensure pywin32 DLLs are in place (pywin32_postinstall.py)
        from chatmd.commands.win_service import check_pywin32_postinstall
        dll_ok, fix_cmd = check_pywin32_postinstall()
        if not dll_ok:
            click.echo(t("service.pywin32_postinstall_required", command=fix_cmd))
            sys.exit(1)
        try:
            name = _install_windows(workspace)
            click.echo(t("service.installed", platform="Windows Service", name=name))
            click.echo(t("service.auto_start"))
            click.echo(t("service.win_hints"))
        except Exception as exc:
            click.echo(t("service.win_install_failed", error=str(exc)))
            sys.exit(1)
    else:
        click.echo(t("service.unsupported_platform", platform=platform))
        sys.exit(1)


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
        if not _check_pywin32():
            click.echo(t("service.pywin32_required"))
            sys.exit(1)
        try:
            name = _uninstall_windows(workspace)
            click.echo(t("service.uninstalled", platform="Windows Service", path=name))
        except Exception as exc:
            click.echo(t("service.win_uninstall_failed", error=str(exc)))
    else:
        click.echo(t("service.unsupported_platform", platform=platform))
        sys.exit(1)


def run_service_status(workspace_str: str | None) -> None:
    """Show the ChatMD Agent system service status.

    When *workspace_str* is ``None``, list all installed ChatMD services
    (Windows only for now).
    """
    if workspace_str is None:
        # List all services
        run_service_status_all()
        return

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
        if not _check_pywin32():
            click.echo(t("service.pywin32_required"))
            sys.exit(1)
        status = _status_windows(workspace)
        name = _win_service_name(workspace)
        click.echo(t("service.status_info", platform="Windows Service", name=name, status=status))
    else:
        click.echo(t("service.unsupported_platform", platform=platform))


def run_service_status_all() -> None:
    """List all installed ChatMD services (Windows only for now)."""
    platform = sys.platform
    if platform == "win32":
        if not _check_pywin32():
            click.echo(t("service.pywin32_required"))
            sys.exit(1)
        from chatmd.commands.win_service import list_all_services
        services = list_all_services()
        if not services:
            click.echo(t("service.no_services_found"))
            return
        click.echo(t("service.all_services_header", count=len(services)))
        for name, ws, status in services:
            click.echo(f"  {name}  {status:<10}  {ws}")
    elif platform == "linux":
        click.echo(t("service.status_all_hint_linux"))
    elif platform == "darwin":
        click.echo(t("service.status_all_hint_macos"))
    else:
        click.echo(t("service.unsupported_platform", platform=platform))


def run_service_uninstall_all() -> None:
    """Uninstall all ChatMD Windows Services."""
    platform = sys.platform
    if platform != "win32":
        click.echo(t("service.uninstall_all_win_only"))
        return
    if not _check_pywin32():
        click.echo(t("service.pywin32_required"))
        sys.exit(1)
    from chatmd.commands.win_service import list_all_services, uninstall_service
    services = list_all_services()
    if not services:
        click.echo(t("service.no_services_found"))
        return
    for name, ws, _status in services:
        try:
            uninstall_service(name)
            click.echo(t("service.uninstalled", platform="Windows Service", path=name))
        except Exception as exc:
            click.echo(t("service.win_uninstall_failed", error=str(exc)))
    # Also clean up legacy Task Scheduler entries
    for name, ws, _status in services:
        if ws != "?":
            _cleanup_legacy_task(Path(ws))
