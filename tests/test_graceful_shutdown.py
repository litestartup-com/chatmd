"""Tests for cross-platform graceful shutdown (T-051) and daemon mode (T-052)."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Agent stop-signal unit tests
# ---------------------------------------------------------------------------

class TestAgentStopSignal:
    """Test Agent._check_stop_signal / _clean_stop_signal / run_forever integration."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace with .chatmd/ directory."""
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        # Minimal agent.yaml so Config doesn't fail
        (chatmd_dir / "agent.yaml").write_text("watcher:\n  debounce_ms: 300\n")
        (chatmd_dir / "user.yaml").write_text("language: en\n")
        # chat.md for watcher
        (tmp_path / "chat.md").write_text("# Chat\n")
        return tmp_path

    def test_check_stop_signal_returns_false_when_no_file(self, workspace: Path) -> None:
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)
        assert agent._check_stop_signal() is False

    def test_check_stop_signal_returns_true_when_file_exists(self, workspace: Path) -> None:
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)
        agent._stop_signal_file.write_text("12345", encoding="utf-8")
        assert agent._check_stop_signal() is True

    def test_clean_stop_signal_removes_file(self, workspace: Path) -> None:
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)
        agent._stop_signal_file.write_text("12345", encoding="utf-8")
        assert agent._stop_signal_file.exists()
        agent._clean_stop_signal()
        assert not agent._stop_signal_file.exists()

    def test_clean_stop_signal_noop_when_no_file(self, workspace: Path) -> None:
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)
        # Should not raise
        agent._clean_stop_signal()

    def test_start_cleans_stale_stop_signal(self, workspace: Path) -> None:
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)
        agent._stop_signal_file.write_text("stale", encoding="utf-8")
        agent.start()
        assert not agent._stop_signal_file.exists()
        agent.stop()

    def test_stop_cleans_stop_signal(self, workspace: Path) -> None:
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)
        agent.start()
        agent._stop_signal_file.write_text("12345", encoding="utf-8")
        agent.stop()
        assert not agent._stop_signal_file.exists()

    def test_stop_signal_file_path(self, workspace: Path) -> None:
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)
        expected = workspace / ".chatmd" / "stop.signal"
        assert agent._stop_signal_file == expected

    def test_run_forever_exits_on_stop_signal(self, workspace: Path) -> None:
        """Agent.run_forever() should exit within ~2s when stop.signal appears."""
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)

        def write_signal_after_delay() -> None:
            time.sleep(0.5)
            agent._stop_signal_file.write_text("stop", encoding="utf-8")

        writer = threading.Thread(target=write_signal_after_delay)
        writer.start()

        t0 = time.monotonic()
        agent.run_forever()
        elapsed = time.monotonic() - t0

        writer.join(timeout=2)
        # Should exit within ~2s (0.5s delay + 1s poll cycle max)
        assert elapsed < 5.0
        assert not agent.is_running

    def test_run_forever_exits_on_stop_event(self, workspace: Path) -> None:
        """Agent.run_forever() should exit when _stop_event is set."""
        from chatmd.engine.agent import Agent
        agent = Agent(workspace)

        def set_event_after_delay() -> None:
            time.sleep(0.3)
            agent._stop_event.set()

        setter = threading.Thread(target=set_event_after_delay)
        setter.start()

        t0 = time.monotonic()
        agent.run_forever()
        elapsed = time.monotonic() - t0

        setter.join(timeout=2)
        assert elapsed < 5.0


# ---------------------------------------------------------------------------
# CLI run_stop unit tests
# ---------------------------------------------------------------------------

class TestRunStopSignalFile:
    """Test that run_stop writes a stop signal file."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        return tmp_path

    def test_run_stop_writes_signal_file(self, workspace: Path) -> None:
        """run_stop should create .chatmd/stop.signal."""
        from chatmd.commands.agent_lifecycle import run_stop

        pid_file = workspace / ".chatmd" / "agent.pid"
        stop_signal = workspace / ".chatmd" / "stop.signal"
        pid_file.write_text("99999", encoding="utf-8")

        # First call: alive check before writing signal → True
        # Subsequent calls (wait loop): → False so it exits quickly
        alive_calls = iter([True, False])

        with (
            patch(
                "chatmd.commands.agent_lifecycle._is_process_alive",
                side_effect=lambda _pid: next(alive_calls, False),
            ),
            patch("os.kill"),  # no-op, avoid actually signaling
            patch("time.sleep"),  # skip wait
        ):
            run_stop(str(workspace))

        # Signal file should have been created
        assert stop_signal.exists()

    def test_run_stop_no_pid_file(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        """run_stop should report no running agent when PID file is missing."""
        from chatmd.commands.agent_lifecycle import run_stop
        run_stop(str(workspace))
        captured = capsys.readouterr()
        assert "No running Agent" in captured.out or "没有正在运行" in captured.out

    def test_run_stop_corrupted_pid(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        """run_stop should handle corrupted PID file."""
        from chatmd.commands.agent_lifecycle import run_stop
        pid_file = workspace / ".chatmd" / "agent.pid"
        pid_file.write_text("not-a-number", encoding="utf-8")
        run_stop(str(workspace))
        captured = capsys.readouterr()
        assert "PID" in captured.out or "pid" in captured.out.lower()
        # PID file should be cleaned up
        assert not pid_file.exists()


# ---------------------------------------------------------------------------
# Daemon mode tests (T-052)
# ---------------------------------------------------------------------------

class TestDaemonMode:
    """Test run_start_daemon behaviour."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        (chatmd_dir / "agent.yaml").write_text("watcher:\n  debounce_ms: 300\n")
        (chatmd_dir / "user.yaml").write_text("language: en\n")
        (tmp_path / "chat.md").write_text("# Chat\n")
        return tmp_path

    def test_daemon_rejects_non_workspace(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        """run_start_daemon should exit if .chatmd/ doesn't exist."""
        from chatmd.commands.agent_lifecycle import run_start_daemon
        with pytest.raises(SystemExit):
            run_start_daemon(str(tmp_path))
        captured = capsys.readouterr()
        assert "workspace" in captured.out.lower() or "工作空间" in captured.out

    def test_daemon_detects_existing_instance(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        """run_start_daemon should refuse if another instance is running."""
        import os

        from chatmd.commands.agent_lifecycle import run_start_daemon

        pid_file = workspace / ".chatmd" / "agent.pid"
        # Write our own PID so os.kill(pid, 0) succeeds
        pid_file.write_text(str(os.getpid()), encoding="utf-8")
        run_start_daemon(str(workspace))
        captured = capsys.readouterr()
        assert "already running" in captured.out.lower() or "已在运行" in captured.out

    def test_daemon_cleans_stale_pid(self, workspace: Path) -> None:
        """run_start_daemon should clean up a stale PID file."""
        from chatmd.commands.agent_lifecycle import run_start_daemon

        pid_file = workspace / ".chatmd" / "agent.pid"
        # Use a PID that almost certainly doesn't exist
        pid_file.write_text("2999999", encoding="utf-8")

        # The daemon will try to spawn a subprocess — mock Popen to avoid that
        mock_proc = type("MockProc", (), {"pid": 12345, "poll": lambda self: None})()
        with patch("subprocess.Popen", return_value=mock_proc):
            with patch("time.sleep"):
                run_start_daemon(str(workspace))

        # Stale PID file should have been removed before subprocess was spawned
        # (new agent.pid will be written by the child process, not by run_start_daemon)

    def test_daemon_spawns_subprocess(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        """run_start_daemon should call subprocess.Popen with correct args."""
        import sys as _sys

        from chatmd.commands.agent_lifecycle import run_start_daemon

        mock_proc = type("MockProc", (), {"pid": 42, "poll": lambda self: None})()
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("time.sleep"):
                run_start_daemon(str(workspace))

        # Verify Popen was called
        assert mock_popen.called
        call_args = mock_popen.call_args
        cmd = call_args[0][0]  # positional arg 0
        assert cmd[0] == _sys.executable
        assert "-m" in cmd
        assert "chatmd" in cmd
        assert "start" in cmd
        assert "-w" in cmd
        assert str(workspace) in cmd

        captured = capsys.readouterr()
        assert "42" in captured.out  # PID shown

    def test_daemon_reports_failure(self, workspace: Path, capsys: pytest.CaptureFixture) -> None:
        """run_start_daemon should report failure if child exits immediately."""
        from chatmd.commands.agent_lifecycle import run_start_daemon

        mock_proc = type("MockProc", (), {"pid": 99, "poll": lambda self: 1, "returncode": 1})()
        with patch("subprocess.Popen", return_value=mock_proc):
            with patch("time.sleep"):
                with pytest.raises(SystemExit):
                    run_start_daemon(str(workspace))
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower() or "失败" in captured.out

    def test_cli_start_has_daemon_flag(self) -> None:
        """The `chatmd start` CLI command should accept --daemon / -d."""
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["start", "--help"])
        assert "--daemon" in result.output or "-d" in result.output


# ---------------------------------------------------------------------------
# restart tests
# ---------------------------------------------------------------------------


class TestRestart:
    """Tests for ``chatmd restart`` (run_restart)."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        (chatmd_dir / "agent.yaml").write_text("watcher:\n  debounce_ms: 300\n")
        (chatmd_dir / "user.yaml").write_text("language: en\n")
        (tmp_path / "chat.md").write_text("# Chat\n")
        return tmp_path

    def test_restart_no_running_agent(self, workspace: Path, capsys) -> None:
        """restart when no agent is running should start a new daemon."""
        from chatmd.commands.agent_lifecycle import run_restart

        with patch("chatmd.commands.agent_lifecycle.run_start_daemon") as mock_daemon:
            run_restart(str(workspace))

        captured = capsys.readouterr()
        assert "No running Agent" in captured.out or "未发现" in captured.out
        mock_daemon.assert_called_once_with(str(workspace))

    def test_restart_with_running_agent(self, workspace: Path, capsys) -> None:
        """restart when agent is running should stop then start daemon."""
        from chatmd.commands.agent_lifecycle import run_restart

        # Simulate a running PID
        pid_file = workspace / ".chatmd" / "agent.pid"
        pid_file.write_text("99999", encoding="utf-8")

        with (
            patch("chatmd.commands.agent_lifecycle._is_process_alive", return_value=False),
            patch("chatmd.commands.agent_lifecycle.run_start_daemon") as mock_daemon,
        ):
            run_restart(str(workspace))

        # PID 99999 is not alive, so it cleans up and starts fresh
        mock_daemon.assert_called_once_with(str(workspace))

    def test_restart_stops_alive_process(self, workspace: Path, capsys) -> None:
        """restart should call run_stop when process is alive."""
        from chatmd.commands.agent_lifecycle import run_restart

        pid_file = workspace / ".chatmd" / "agent.pid"
        pid_file.write_text("12345", encoding="utf-8")

        call_count = [0]

        def fake_alive(pid: int) -> bool:
            # First few calls: alive; then dead after stop
            call_count[0] += 1
            return call_count[0] <= 2

        with (
            patch("chatmd.commands.agent_lifecycle._is_process_alive", side_effect=fake_alive),
            patch("chatmd.commands.agent_lifecycle.run_stop") as mock_stop,
            patch("chatmd.commands.agent_lifecycle.run_start_daemon") as mock_daemon,
        ):
            run_restart(str(workspace))

        mock_stop.assert_called_once_with(str(workspace))
        mock_daemon.assert_called_once_with(str(workspace))
        captured = capsys.readouterr()
        assert "Stopping" in captured.out or "停止" in captured.out
        assert "Restarting" in captured.out or "重启" in captured.out

    def test_restart_not_workspace(self, tmp_path: Path) -> None:
        """restart on non-workspace should exit with error."""
        from chatmd.commands.agent_lifecycle import run_restart

        with pytest.raises(SystemExit):
            run_restart(str(tmp_path))

    def test_cli_restart_has_workspace_option(self) -> None:
        """The ``chatmd restart`` CLI command should accept -w."""
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["restart", "--help"])
        assert "--workspace" in result.output or "-w" in result.output
