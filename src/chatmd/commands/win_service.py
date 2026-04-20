"""Windows Service wrapper for the ChatMD Agent using pywin32.

This module defines a ``win32serviceutil.ServiceFramework`` subclass that
the Windows Service Control Manager (SCM) can start, stop, and query.

The workspace path is stored in the Windows registry alongside the service
configuration so that each service instance knows which workspace to manage.

Requires: ``pywin32`` (``pip install pywin32``).
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import winreg
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

logger = logging.getLogger(__name__)

# Registry key under HKLM\SYSTEM\CurrentControlSet\Services\<svc>\Parameters
_REG_WORKSPACE_VALUE = "WorkspacePath"


class ChatMDService(win32serviceutil.ServiceFramework):
    """Windows Service that runs a ChatMD Agent for a specific workspace.

    The service name and display name are set dynamically at install time
    via class-attribute patching (standard pywin32 pattern).
    """

    _svc_name_ = "ChatMD"
    _svc_display_name_ = "ChatMD Agent"
    _svc_description_ = "ChatMD local-first AI Agent — file watcher and command engine"

    def __init__(self, args: list) -> None:
        win32serviceutil.ServiceFramework.__init__(self, args)
        # args[0] is the real service name assigned by SCM (e.g. "ChatMD-3fbc67dc")
        self._real_svc_name = args[0]
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._agent = None

    # -- SCM callbacks -------------------------------------------------------

    def SvcStop(self) -> None:
        """Called by SCM when the service is requested to stop."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self._stop_event)

        # Write stop.signal for the Agent's graceful shutdown loop
        workspace = self._read_workspace(self._real_svc_name)
        if workspace:
            stop_signal = Path(workspace) / ".chatmd" / "stop.signal"
            try:
                stop_signal.write_text(str(os.getpid()), encoding="utf-8")
            except OSError:
                pass

    def SvcDoRun(self) -> None:
        """Called by SCM when the service starts."""
        svc = self._real_svc_name
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (svc, ""),
        )

        workspace = self._read_workspace(svc)
        if not workspace:
            servicemanager.LogErrorMsg(
                f"ChatMD Service {svc}: "
                "no WorkspacePath in registry. Cannot start."
            )
            return

        workspace_path = Path(workspace)
        if not (workspace_path / ".chatmd").is_dir():
            servicemanager.LogErrorMsg(
                f"ChatMD Service {svc}: "
                f"workspace {workspace} is not a ChatMD workspace."
            )
            return

        try:
            self._run_agent(workspace_path)
        except Exception as exc:
            servicemanager.LogErrorMsg(
                f"ChatMD Service {svc} crashed: {exc}"
            )

    # -- Agent lifecycle -----------------------------------------------------

    def _run_agent(self, workspace: Path) -> None:
        """Set up logging and run the Agent until stop is signalled."""
        # Import here to avoid import-time side effects
        from chatmd.commands.agent_lifecycle import _setup_logging
        from chatmd.engine.agent import Agent

        _setup_logging(workspace)

        # Startup can block on network-sensitive hooks (notifications/cron restore),
        # especially during boot. Keep reporting START_PENDING to avoid SCM 1053 timeout.
        started = threading.Event()
        startup_error: list[Exception] = []

        def _start_agent() -> None:
            try:
                self._agent = Agent(workspace)
                self._agent.start()
            except Exception as exc:  # pragma: no cover - surfaced below
                startup_error.append(exc)
            finally:
                started.set()

        thread = threading.Thread(
            target=_start_agent, name=f"{self._real_svc_name}-startup", daemon=True,
        )
        thread.start()

        while not started.wait(timeout=2.0):
            self.ReportServiceStatus(
                win32service.SERVICE_START_PENDING,
                waitHint=10000,
            )

            # SCM requested stop while startup is still in progress.
            rc = win32event.WaitForSingleObject(self._stop_event, 0)
            if rc == win32event.WAIT_OBJECT_0:
                return

        if startup_error:
            raise startup_error[0]

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        # Block until SCM signals stop
        while True:
            rc = win32event.WaitForSingleObject(self._stop_event, 1000)
            if rc == win32event.WAIT_OBJECT_0:
                break
            # Also honour the Agent's own stop.signal file
            stop_signal = workspace / ".chatmd" / "stop.signal"
            if stop_signal.exists():
                break

        if self._agent:
            self._agent.stop()
            self._agent = None

    # -- Registry helpers ----------------------------------------------------

    @staticmethod
    def _read_workspace(service_name: str) -> str | None:
        """Read the WorkspacePath from the service's Parameters registry key."""
        try:
            key_path = (
                rf"SYSTEM\CurrentControlSet\Services\{service_name}\Parameters"
            )
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value, _ = winreg.QueryValueEx(key, _REG_WORKSPACE_VALUE)
                return str(value)
        except OSError:
            return None

    @classmethod
    def write_workspace_to_registry(
        cls, service_name: str, workspace: Path,
    ) -> None:
        """Write the WorkspacePath to the service's Parameters registry key.

        Called during ``chatmd service install`` (before starting the service).
        """
        key_path = (
            rf"SYSTEM\CurrentControlSet\Services\{service_name}\Parameters"
        )
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            winreg.SetValueEx(
                key, _REG_WORKSPACE_VALUE, 0, winreg.REG_SZ, str(workspace),
            )


def check_pywin32_postinstall() -> tuple[bool, str]:
    """Check whether pywin32 post-install has been run.

    ``pythonservice.exe`` requires ``pywintypes*.dll`` to be copied to a
    location on the system PATH (typically ``C:\\Windows\\system32``).
    If the DLL is missing, the service will fail with Error 1053.

    Returns ``(ok, hint_command)`` where *hint_command* is the shell
    command the user should run to fix it (empty when *ok* is True).
    """
    vi = sys.version_info
    suffix = f"{vi.major}{vi.minor}"
    dll_name = f"pywintypes{suffix}.dll"

    # Check system locations where pythonservice.exe can find the DLL
    search_dirs = [
        os.environ.get("SYSTEMROOT", r"C:\Windows") + r"\system32",
        str(Path(sys.executable).parent),
        str(Path(sys.executable).parent / "DLLs"),
    ]
    for d in search_dirs:
        if os.path.isfile(os.path.join(d, dll_name)):
            return True, ""

    # DLL not found — build the fix command
    postinstall = Path(sys.prefix) / "Scripts" / "pywin32_postinstall.py"
    if postinstall.exists():
        cmd = f'python "{postinstall}" -install'
    else:
        cmd = "python -m pywin32_postinstall -install"
    return False, cmd


def _write_python_path_to_registry(service_name: str) -> None:
    """Write current ``sys.path`` to the service's PythonPath registry key.

    ``pythonservice.exe`` reads this key at startup to populate ``sys.path``
    before importing the service class.  Without it the service will fail
    with Error 1053 whenever the ``chatmd`` package lives outside the
    default Python search path (e.g. editable / dev installs).
    """
    key_path = (
        rf"SYSTEM\CurrentControlSet\Services\{service_name}\PythonClass"
    )
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE,
    ) as key:
        # Join all path entries with ";" — the format pythonservice.exe expects
        winreg.SetValueEx(
            key, "PythonPath", 0, winreg.REG_SZ, ";".join(sys.path),
        )


def install_service(service_name: str, workspace: Path) -> None:
    """Install and start the ChatMD Windows Service for *workspace*.

    Steps:
    1. Patch the service class attributes for the target name.
    2. Call ``win32serviceutil.InstallService`` to register with SCM.
    3. Write workspace path to registry Parameters.
    4. Configure auto-restart on failure.
    5. Start the service.
    """
    display_name = f"ChatMD Agent ({workspace.name})"
    description = f"ChatMD Agent for {workspace}"

    # The service executable must be pythonservice.exe from pywin32
    # which knows how to load our ServiceFramework class.
    python_dir = Path(sys.executable).parent
    # pywin32 installs pythonservice.exe in Lib/site-packages/win32/
    pythonservice = python_dir / "Lib" / "site-packages" / "win32" / "pythonservice.exe"
    if not pythonservice.exists():
        # Fallback: check Scripts dir or the python dir itself
        for candidate in [
            python_dir / "pythonservice.exe",
            python_dir / "Scripts" / "pythonservice.exe",
        ]:
            if candidate.exists():
                pythonservice = candidate
                break

    # The class string that pythonservice.exe will load
    class_string = "chatmd.commands.win_service.ChatMDService"

    # Remove existing service if present (makes install idempotent)
    try:
        win32serviceutil.QueryServiceStatus(service_name)
        # Service exists — stop and remove it first
        try:
            win32serviceutil.StopService(service_name)
        except Exception:
            pass  # may not be running
        win32serviceutil.RemoveService(service_name)
        time.sleep(1)  # allow SCM to fully release the service
    except Exception:
        pass  # service does not exist yet

    win32serviceutil.InstallService(
        pythonClassString=class_string,
        serviceName=service_name,
        displayName=display_name,
        description=description,
        startType=win32service.SERVICE_AUTO_START,
        exeName=str(pythonservice),
    )

    # Write workspace to registry so SvcDoRun knows where to look
    ChatMDService.write_workspace_to_registry(service_name, workspace)

    # Write sys.path so pythonservice.exe can find the chatmd package
    _write_python_path_to_registry(service_name)

    # Configure failure recovery: restart after 5 seconds
    _configure_failure_recovery(service_name)
    # Delay auto-start at boot to avoid early-network / startup races.
    _configure_delayed_auto_start(service_name)

    # Start the service
    win32serviceutil.StartService(service_name)


def uninstall_service(service_name: str) -> None:
    """Stop and remove the ChatMD Windows Service."""
    try:
        win32serviceutil.StopService(service_name)
    except Exception:
        pass  # may not be running
    win32serviceutil.RemoveService(service_name)


def start_service(service_name: str) -> None:
    """Start an already-installed ChatMD Windows Service via SCM.

    Raises the underlying ``pywintypes.error`` on failure (e.g. service not
    installed, already running, access denied).  Callers are expected to
    translate that into a user-friendly message.
    """
    win32serviceutil.StartService(service_name)


def stop_service(service_name: str) -> None:
    """Stop a running ChatMD Windows Service via SCM."""
    win32serviceutil.StopService(service_name)


def query_service_status(service_name: str) -> str:
    """Query the current status of a Windows Service by name.

    Returns a human-readable status string.
    """
    _STATUS_MAP = {
        win32service.SERVICE_STOPPED: "stopped",
        win32service.SERVICE_START_PENDING: "starting",
        win32service.SERVICE_STOP_PENDING: "stopping",
        win32service.SERVICE_RUNNING: "running",
        win32service.SERVICE_CONTINUE_PENDING: "resuming",
        win32service.SERVICE_PAUSE_PENDING: "pausing",
        win32service.SERVICE_PAUSED: "paused",
    }
    try:
        status = win32serviceutil.QueryServiceStatus(service_name)
        # status is a tuple: (serviceType, currentState, ...)
        state = status[1]
        return _STATUS_MAP.get(state, f"unknown ({state})")
    except Exception:
        return "not installed"


def list_all_services() -> list[tuple[str, str, str]]:
    """List all installed ChatMD Windows Services.

    Scans ``HKLM\\SYSTEM\\CurrentControlSet\\Services`` for entries
    matching the ``ChatMD-*`` naming pattern.

    Returns a list of ``(service_name, workspace_path, status)`` tuples.
    """
    results: list[tuple[str, str, str]] = []
    services_key_path = r"SYSTEM\CurrentControlSet\Services"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, services_key_path) as key:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(key, i)
                    i += 1
                except OSError:
                    break
                if not name.startswith("ChatMD-"):
                    continue
                # Read workspace path
                ws = ChatMDService._read_workspace(name) or "?"
                status = query_service_status(name)
                results.append((name, ws, status))
    except OSError:
        pass
    return results


def _configure_failure_recovery(service_name: str) -> None:
    """Set the service to restart on failure (up to 3 times, 5s delay)."""
    import subprocess
    subprocess.run(
        [
            "sc", "failure", service_name,
            "reset=", "86400",
            "actions=", "restart/5000/restart/5000/restart/5000",
        ],
        capture_output=True, check=False,
    )


def _configure_delayed_auto_start(service_name: str) -> None:
    """Set service start mode to delayed-auto for more reliable boot startup."""
    import subprocess
    subprocess.run(
        ["sc", "config", service_name, "start=", "delayed-auto"],
        capture_output=True, check=False,
    )
