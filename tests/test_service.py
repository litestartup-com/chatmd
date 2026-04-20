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
    """Test Windows Service helpers (pywin32-based)."""

    def test_win_service_name(self) -> None:
        from chatmd.commands.service import _win_service_name
        ws = Path("C:/Users/test/workspace")
        name = _win_service_name(ws)
        assert name.startswith("ChatMD-")
        assert len(name) == len("ChatMD-") + 8

    def test_check_pywin32_available(self) -> None:
        from chatmd.commands.service import _check_pywin32
        # On Windows with pywin32 installed, this should return True
        if sys.platform == "win32":
            result = _check_pywin32()
            if not result:
                pytest.skip("pywin32 not installed")
            assert result is True

    def test_cleanup_legacy_task(self) -> None:
        from chatmd.commands.service import _cleanup_legacy_task
        ws = Path("C:/Users/test/workspace")
        with patch("subprocess.run") as mock_run:
            # Simulate no legacy task found
            mock_run.return_value = type("R", (), {"returncode": 1, "stdout": ""})()
            _cleanup_legacy_task(ws)
        # Should have queried schtasks
        assert mock_run.called


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
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output

    def test_service_start_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["service", "start", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output

    def test_service_stop_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["service", "stop", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output

    def test_service_restart_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["service", "restart", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output

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
    def test_install_windows(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        from chatmd.commands.service import _check_pywin32, run_service_install
        if not _check_pywin32():
            pytest.skip("pywin32 not installed")
        with (
            patch("chatmd.commands.service._install_windows", return_value="ChatMD-abc12345"),
        ):
            run_service_install(str(workspace))
        captured = capsys.readouterr()
        assert "installed" in captured.out.lower() or "已安装" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_uninstall_windows(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        from chatmd.commands.service import _check_pywin32, run_service_uninstall
        if not _check_pywin32():
            pytest.skip("pywin32 not installed")
        with patch("chatmd.commands.service._uninstall_windows", return_value="ChatMD-abc12345"):
            run_service_uninstall(str(workspace))
        captured = capsys.readouterr()
        assert "uninstalled" in captured.out.lower() or "已卸载" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_status_windows(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        from chatmd.commands.service import _check_pywin32, run_service_status
        if not _check_pywin32():
            pytest.skip("pywin32 not installed")
        with patch("chatmd.commands.service._status_windows", return_value="not installed"):
            run_service_status(str(workspace))
        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower() or "服务" in captured.out

    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
    def test_install_systemd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_install
        with patch("subprocess.run"):
            run_service_install(str(workspace))
        captured = capsys.readouterr()
        assert "installed" in captured.out.lower() or "已安装" in captured.out

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_install_launchd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_install
        with patch("subprocess.run"):
            run_service_install(str(workspace))
        captured = capsys.readouterr()
        assert "installed" in captured.out.lower() or "已安装" in captured.out


class TestServiceStartStopRestart:
    """Tests for `chatmd service start | stop | restart`."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        (chatmd_dir / "agent.yaml").write_text("watcher:\n  debounce_ms: 300\n")
        (chatmd_dir / "user.yaml").write_text("language: en\n")
        return tmp_path

    def test_start_rejects_non_workspace(self, tmp_path: Path) -> None:
        from chatmd.commands.service import run_service_start
        with pytest.raises(SystemExit):
            run_service_start(str(tmp_path))

    def test_stop_rejects_non_workspace(self, tmp_path: Path) -> None:
        from chatmd.commands.service import run_service_stop
        with pytest.raises(SystemExit):
            run_service_stop(str(tmp_path))

    def test_restart_rejects_non_workspace(self, tmp_path: Path) -> None:
        from chatmd.commands.service import run_service_restart
        with pytest.raises(SystemExit):
            run_service_restart(str(tmp_path))

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_start_windows(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        from chatmd.commands.service import _check_pywin32, run_service_start
        if not _check_pywin32():
            pytest.skip("pywin32 not installed")
        with patch(
            "chatmd.commands.service._start_windows", return_value="ChatMD-abc12345",
        ):
            run_service_start(str(workspace))
        captured = capsys.readouterr()
        assert "started" in captured.out.lower() or "已启动" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_stop_windows(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        from chatmd.commands.service import _check_pywin32, run_service_stop
        if not _check_pywin32():
            pytest.skip("pywin32 not installed")
        with patch(
            "chatmd.commands.service._stop_windows", return_value="ChatMD-abc12345",
        ):
            run_service_stop(str(workspace))
        captured = capsys.readouterr()
        assert "stopped" in captured.out.lower() or "已停止" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_start_windows_failure_is_reported(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        from chatmd.commands.service import _check_pywin32, run_service_start
        if not _check_pywin32():
            pytest.skip("pywin32 not installed")
        with patch(
            "chatmd.commands.service._start_windows",
            side_effect=RuntimeError("service not installed"),
        ):
            with pytest.raises(SystemExit):
                run_service_start(str(workspace))
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower() or "失败" in captured.out

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_restart_windows_tolerates_stop_failure(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        """restart must still start the service when stop fails (already stopped)."""
        from chatmd.commands.service import _check_pywin32, run_service_restart
        if not _check_pywin32():
            pytest.skip("pywin32 not installed")
        started: list[str] = []
        with (
            patch(
                "chatmd.commands.service._stop_windows",
                side_effect=RuntimeError("service not running"),
            ),
            patch(
                "chatmd.commands.service._start_windows",
                side_effect=lambda ws: started.append("ok") or "ChatMD-abc12345",
            ),
        ):
            run_service_restart(str(workspace))
        assert started == ["ok"]

    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
    def test_start_systemd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_start
        with patch("subprocess.run") as mock_run:
            run_service_start(str(workspace))
        # The systemctl command should have been invoked
        assert mock_run.called
        captured = capsys.readouterr()
        assert "started" in captured.out.lower() or "已启动" in captured.out

    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
    def test_stop_systemd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_stop
        with patch("subprocess.run") as mock_run:
            run_service_stop(str(workspace))
        assert mock_run.called
        captured = capsys.readouterr()
        assert "stopped" in captured.out.lower() or "已停止" in captured.out

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_start_launchd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_start
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"returncode": 0, "stdout": ""})()
            run_service_start(str(workspace))
        assert mock_run.called
        captured = capsys.readouterr()
        assert "started" in captured.out.lower() or "已启动" in captured.out

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_stop_launchd(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        from chatmd.commands.service import run_service_stop
        with patch("subprocess.run"):
            run_service_stop(str(workspace))
        captured = capsys.readouterr()
        assert "stopped" in captured.out.lower() or "已停止" in captured.out
