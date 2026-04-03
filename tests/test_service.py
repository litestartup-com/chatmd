"""Tests for system service management — install, uninstall, status (T-053)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestServiceHelpers:
    """Test service module helper functions."""

    def test_workspace_hash_deterministic(self) -> None:
        from chatmd.commands.service import _workspace_hash
        p = Path("/tmp/test-workspace")
        assert _workspace_hash(p) == _workspace_hash(p)
        assert len(_workspace_hash(p)) == 8

    def test_workspace_hash_unique(self) -> None:
        from chatmd.commands.service import _workspace_hash
        h1 = _workspace_hash(Path("/tmp/ws1"))
        h2 = _workspace_hash(Path("/tmp/ws2"))
        assert h1 != h2

    def test_service_name_format(self) -> None:
        from chatmd.commands.service import _service_name
        name = _service_name(Path("/tmp/ws"))
        assert name.startswith("chatmd-")
        assert len(name) == len("chatmd-") + 8


class TestSystemdTemplates:
    """Test systemd unit file generation."""

    def test_systemd_unit_content(self) -> None:
        from chatmd.commands.service import _systemd_unit_content
        ws = Path("/home/user/my-workspace")
        content = _systemd_unit_content(ws)
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content
        assert str(ws) in content
        assert "chatmd start" in content
        assert sys.executable in content

    def test_systemd_unit_path(self) -> None:
        from chatmd.commands.service import _systemd_unit_path
        ws = Path("/home/user/my-workspace")
        path = _systemd_unit_path(ws)
        # Use PurePosixPath string for cross-platform assertion
        assert "systemd" in str(path) and "user" in str(path)
        assert path.suffix == ".service"
        assert "chatmd-" in path.name


class TestLaunchdTemplates:
    """Test launchd plist file generation."""

    def test_launchd_plist_content(self) -> None:
        from chatmd.commands.service import _launchd_plist_content
        ws = Path("/Users/test/my-workspace")
        content = _launchd_plist_content(ws)
        assert "<?xml" in content
        assert "plist" in content
        assert "com.chatmd." in content
        assert str(ws) in content
        assert "chatmd" in content
        assert "RunAtLoad" in content
        assert "KeepAlive" in content

    def test_launchd_plist_path(self) -> None:
        from chatmd.commands.service import _launchd_plist_path
        ws = Path("/Users/test/my-workspace")
        path = _launchd_plist_path(ws)
        assert "LaunchAgents" in str(path)
        assert path.suffix == ".plist"
        assert "com.chatmd." in path.name


class TestWindowsService:
    """Test Windows Task Scheduler helpers."""

    def test_win_task_name(self) -> None:
        from chatmd.commands.service import _win_task_name
        ws = Path("C:/Users/test/workspace")
        name = _win_task_name(ws)
        assert name.startswith("ChatMD-")
        assert len(name) == len("ChatMD-") + 8

    def test_pythonw_executable_returns_pythonw_when_exists(self) -> None:
        from chatmd.commands.service import _pythonw_executable
        with patch.object(Path, "exists", return_value=True):
            result = _pythonw_executable()
        assert result.endswith("pythonw.exe")

    def test_pythonw_executable_fallback(self) -> None:
        from chatmd.commands.service import _pythonw_executable
        with patch.object(Path, "exists", return_value=False):
            result = _pythonw_executable()
        assert result == sys.executable

    def test_install_windows_uses_pythonw(self) -> None:
        from chatmd.commands.service import _install_windows
        ws = Path("C:/Users/test/workspace")
        with (
            patch("subprocess.run") as mock_run,
            patch("chatmd.commands.service._pythonw_executable",
                  return_value="C:/Python/pythonw.exe"),
        ):
            mock_run.return_value = type("R", (), {"returncode": 0, "stderr": ""})()
            _install_windows(ws)
        call_args = mock_run.call_args[0][0]
        tr_value = call_args[call_args.index("/tr") + 1]
        assert "pythonw.exe" in tr_value
        assert "python.exe" not in tr_value.replace("pythonw.exe", "")


class TestServiceCLI:
    """Test CLI subcommand registration."""

    def test_service_group_exists(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["service", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output
        assert "status" in result.output

    def test_service_install_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["service", "install", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output

    def test_service_uninstall_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["service", "uninstall", "--help"])
        assert result.exit_code == 0

    def test_service_status_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["service", "status", "--help"])
        assert result.exit_code == 0


class TestServiceInstallIntegration:
    """Test service install/uninstall with mocked subprocess calls."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        (chatmd_dir / "agent.yaml").write_text("watcher:\n  debounce_ms: 300\n")
        (chatmd_dir / "user.yaml").write_text("language: en\n")
        return tmp_path

    def test_install_rejects_non_workspace(self, tmp_path: Path) -> None:
        from chatmd.commands.service import run_service_install
        with pytest.raises(SystemExit):
            run_service_install(str(tmp_path))

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_install_windows(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_install
        with (
            patch("subprocess.run") as mock_run,
            patch("chatmd.commands.service._start_agent_now", return_value=12345),
        ):
            mock_run.return_value = type("R", (), {"returncode": 0, "stderr": ""})()
            run_service_install(str(workspace))
        captured = capsys.readouterr()
        assert "installed" in captured.out.lower() or "已安装" in captured.out
        assert "12345" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_uninstall_windows(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_uninstall
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 0})()
            run_service_uninstall(str(workspace))
        captured = capsys.readouterr()
        assert "uninstalled" in captured.out.lower() or "已卸载" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_status_windows(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_status
        mock_result = type("R", (), {"returncode": 1, "stdout": ""})()
        with patch("subprocess.run", return_value=mock_result):
            run_service_status(str(workspace))
        captured = capsys.readouterr()
        assert "not registered" in captured.out.lower() or "服务" in captured.out

    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
    def test_install_systemd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_install
        with (
            patch("subprocess.run"),
            patch("chatmd.commands.service._start_agent_now", return_value=12345),
        ):
            run_service_install(str(workspace))
        captured = capsys.readouterr()
        assert "installed" in captured.out.lower() or "已安装" in captured.out

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_install_launchd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_install
        with (
            patch("subprocess.run"),
            patch("chatmd.commands.service._start_agent_now", return_value=12345),
        ):
            run_service_install(str(workspace))
        captured = capsys.readouterr()
        assert "installed" in captured.out.lower() or "已安装" in captured.out
