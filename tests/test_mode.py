"""Tests for chatmd mode command — trigger mode switching (T-054)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


class TestModeCommand:
    """Test chatmd mode CLI command."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        agent_yaml = {
            "trigger": {
                "signals": [
                    {"type": "file_save", "debounce_ms": 800},
                    {"type": "suffix", "marker": ";", "enabled": False},
                ],
            },
        }
        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(agent_yaml, f)
        (chatmd_dir / "user.yaml").write_text("language: en\n", encoding="utf-8")
        return tmp_path

    def test_show_mode_default_save(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from chatmd.commands.mode import run_mode

        run_mode(str(workspace), None)
        captured = capsys.readouterr()
        assert "save" in captured.out.lower()

    def test_show_mode_suffix(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from chatmd.commands.mode import run_mode

        # First switch to suffix
        run_mode(str(workspace), "suffix")
        capsys.readouterr()

        # Then show
        run_mode(str(workspace), None)
        captured = capsys.readouterr()
        assert "suffix" in captured.out.lower()
        assert ";" in captured.out

    def test_switch_to_suffix(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from chatmd.commands.mode import run_mode

        run_mode(str(workspace), "suffix")
        captured = capsys.readouterr()
        assert "suffix" in captured.out.lower()

        # Verify agent.yaml was updated
        with open(workspace / ".chatmd" / "agent.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        signals = data["trigger"]["signals"]
        suffix_sig = next(s for s in signals if s["type"] == "suffix")
        assert suffix_sig["enabled"] is True

    def test_switch_to_save(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from chatmd.commands.mode import run_mode

        # Switch to suffix first
        run_mode(str(workspace), "suffix")
        capsys.readouterr()

        # Switch back to save
        run_mode(str(workspace), "save")
        captured = capsys.readouterr()
        assert "save" in captured.out.lower()

        # Verify agent.yaml was updated
        with open(workspace / ".chatmd" / "agent.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        signals = data["trigger"]["signals"]
        suffix_sig = next(s for s in signals if s["type"] == "suffix")
        assert suffix_sig["enabled"] is False

    def test_rejects_non_workspace(self, tmp_path: Path) -> None:
        from chatmd.commands.mode import run_mode

        with pytest.raises(SystemExit):
            run_mode(str(tmp_path), "suffix")


class TestModeCLI:
    """Test CLI registration."""

    def test_mode_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["mode", "--help"])
        assert result.exit_code == 0
        assert "suffix" in result.output
        assert "save" in result.output

    def test_mode_no_arg_shows_current(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        agent_yaml = {"trigger": {"signals": [{"type": "suffix", "enabled": False}]}}
        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(agent_yaml, f)
        (chatmd_dir / "user.yaml").write_text("language: en\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["mode", "-w", str(tmp_path)])
        assert result.exit_code == 0
        assert "save" in result.output.lower()


class TestConfigTriggerMode:
    """Test Config.get_trigger_mode and update_trigger_mode."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        agent_yaml = {
            "trigger": {
                "signals": [
                    {"type": "file_save", "debounce_ms": 800},
                    {"type": "suffix", "marker": ";", "enabled": False},
                ],
            },
        }
        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(agent_yaml, f)
        (chatmd_dir / "user.yaml").write_text("language: en\n", encoding="utf-8")
        return tmp_path

    def test_default_mode_is_save(self, workspace: Path) -> None:
        from chatmd.infra.config import Config

        config = Config(workspace)
        assert config.get_trigger_mode() == "save"

    def test_switch_to_suffix(self, workspace: Path) -> None:
        from chatmd.infra.config import Config

        config = Config(workspace)
        config.update_trigger_mode("suffix")
        assert config.get_trigger_mode() == "suffix"

    def test_switch_back_to_save(self, workspace: Path) -> None:
        from chatmd.infra.config import Config

        config = Config(workspace)
        config.update_trigger_mode("suffix")
        config.update_trigger_mode("save")
        assert config.get_trigger_mode() == "save"

    def test_get_suffix_marker(self, workspace: Path) -> None:
        from chatmd.infra.config import Config

        config = Config(workspace)
        assert config.get_suffix_marker() == ";"

    def test_persists_to_yaml(self, workspace: Path) -> None:
        from chatmd.infra.config import Config

        config = Config(workspace)
        config.update_trigger_mode("suffix")

        # Reload from disk
        config2 = Config(workspace)
        assert config2.get_trigger_mode() == "suffix"
