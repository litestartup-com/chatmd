"""Tests for ``chatmd config`` CLI subcommands (T-R086)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from chatmd.cli import main
from chatmd.commands.config_cmd import (
    _flatten,
    _mask_api_key,
    config_get,
    config_list,
    config_set,
    resolve_chatmd_dir,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace with .chatmd/ and config files."""
    chatmd_dir = tmp_path / ".chatmd"
    chatmd_dir.mkdir()

    agent_yaml = {
        "version": "0.2.12",
        "ai": {
            "providers": [
                {
                    "name": "litestartup",
                    "type": "litestartup",
                    "api_url": "https://api.litestartup.com/client/v2/ai/chat",
                    "api_key": "sk-abcdef1234567890xyz",
                    "model": "default",
                    "timeout": 60,
                    "is_default": True,
                }
            ]
        },
        "trigger": {
            "signals": [
                {"type": "file_save", "debounce_ms": 800},
                {"type": "suffix", "marker": ";", "enabled": False},
            ]
        },
    }

    user_yaml = {
        "language": "en",
        "aliases": {"q": "ask"},
    }

    with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
        yaml.dump(agent_yaml, f, default_flow_style=False, allow_unicode=True)
    with open(chatmd_dir / "user.yaml", "w", encoding="utf-8") as f:
        yaml.dump(user_yaml, f, default_flow_style=False, allow_unicode=True)

    return tmp_path


@pytest.fixture()
def empty_workspace(tmp_path: Path) -> Path:
    """Create a workspace without .chatmd/ directory."""
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------


class TestMaskApiKey:
    """Tests for ``_mask_api_key``."""

    def test_long_key(self) -> None:
        assert _mask_api_key("sk-abcdef1234567890xyz") == "sk-abc...xyz"

    def test_short_key(self) -> None:
        result = _mask_api_key("abc")
        assert result == "***"

    def test_medium_key(self) -> None:
        result = _mask_api_key("abcdefgh")
        assert result == "abc...gh"

    def test_env_var_reference(self) -> None:
        assert _mask_api_key("${LITEAGENT_API_KEY}") == "${LITEAGENT_API_KEY}"

    def test_empty(self) -> None:
        assert _mask_api_key("") == ""


class TestFlatten:
    """Tests for ``_flatten``."""

    def test_simple(self) -> None:
        data = {"a": "1", "b": "2"}
        result = _flatten(data)
        assert ("a", "1") in result
        assert ("b", "2") in result

    def test_nested(self) -> None:
        data = {"a": {"b": "1"}}
        result = _flatten(data)
        assert ("a.b", "1") in result

    def test_list(self) -> None:
        data = {"items": [{"name": "x"}]}
        result = _flatten(data)
        assert ("items.0.name", "x") in result


# ---------------------------------------------------------------------------
# Unit tests: config operations
# ---------------------------------------------------------------------------


class TestConfigList:
    """Tests for ``config_list``."""

    def test_lists_agent_and_user(self, workspace: Path) -> None:
        items = config_list(str(workspace))
        keys = [k for k, _ in items]
        assert any("api_key" in k for k in keys)
        assert any(k == "language" for k in keys)

    def test_excludes_internal_version(self, workspace: Path) -> None:
        items = config_list(str(workspace))
        keys = [k for k, _ in items]
        assert "version" not in keys

    def test_api_key_masked(self, workspace: Path) -> None:
        items = config_list(str(workspace))
        for key, val in items:
            if "api_key" in key:
                assert "sk-abcdef1234567890xyz" not in val
                assert "..." in val

    def test_empty_workspace(self, empty_workspace: Path) -> None:
        # No .chatmd/ → returns empty
        items = config_list(str(empty_workspace))
        assert items == []


class TestConfigGet:
    """Tests for ``config_get``."""

    def test_get_api_key(self, workspace: Path) -> None:
        val = config_get(str(workspace), "ai.api_key")
        assert val is not None
        assert "..." in val  # masked

    def test_get_language(self, workspace: Path) -> None:
        val = config_get(str(workspace), "language")
        assert val == "en"

    def test_get_model(self, workspace: Path) -> None:
        val = config_get(str(workspace), "ai.model")
        assert val == "default"

    def test_get_trigger_mode(self, workspace: Path) -> None:
        val = config_get(str(workspace), "trigger.mode")
        assert val == "save"

    def test_get_unknown_key(self, workspace: Path) -> None:
        val = config_get(str(workspace), "nonexistent.key")
        assert val is None

    def test_get_type(self, workspace: Path) -> None:
        val = config_get(str(workspace), "ai.type")
        assert val == "litestartup"


class TestConfigSet:
    """Tests for ``config_set``."""

    def test_set_api_key(self, workspace: Path) -> None:
        target, key = config_set(str(workspace), "ai.api_key", "sk-new-key-value")
        assert target == "agent.yaml"

        # Verify persisted
        val = config_get(str(workspace), "ai.api_key")
        assert val is not None
        assert "new" in val or "..." in val

        # Read raw to verify
        with open(workspace / ".chatmd" / "agent.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["ai"]["providers"][0]["api_key"] == "sk-new-key-value"

    def test_set_language(self, workspace: Path) -> None:
        target, key = config_set(str(workspace), "language", "cn")
        assert target == "user.yaml"

        val = config_get(str(workspace), "language")
        assert val == "cn"

    def test_set_model(self, workspace: Path) -> None:
        config_set(str(workspace), "ai.model", "gpt-4o")
        val = config_get(str(workspace), "ai.model")
        assert val == "gpt-4o"

    def test_set_timeout_int(self, workspace: Path) -> None:
        config_set(str(workspace), "ai.timeout", "120")
        with open(workspace / ".chatmd" / "agent.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["ai"]["providers"][0]["timeout"] == 120

    def test_set_unknown_key_raises(self, workspace: Path) -> None:
        from click import ClickException

        with pytest.raises(ClickException):
            config_set(str(workspace), "unknown.key", "value")

    def test_set_no_workspace_raises(self, empty_workspace: Path) -> None:
        from click import ClickException

        with pytest.raises(ClickException):
            config_set(str(empty_workspace), "language", "cn")

    def test_set_env_var_reference(self, workspace: Path) -> None:
        config_set(str(workspace), "ai.api_key", "${MY_API_KEY}")
        with open(workspace / ".chatmd" / "agent.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["ai"]["providers"][0]["api_key"] == "${MY_API_KEY}"

    def test_set_creates_provider_if_empty(self, tmp_path: Path) -> None:
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        # Write agent.yaml without providers
        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"version": "0.2.12"}, f)

        config_set(str(tmp_path), "ai.api_key", "sk-test")
        with open(chatmd_dir / "agent.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["ai"]["providers"][0]["api_key"] == "sk-test"


class TestResolveChatmdDir:
    """Tests for ``resolve_chatmd_dir``."""

    def test_returns_chatmd_subdir(self, tmp_path: Path) -> None:
        result = resolve_chatmd_dir(str(tmp_path))
        assert result == tmp_path.resolve() / ".chatmd"


# ---------------------------------------------------------------------------
# CLI integration tests (Click CliRunner)
# ---------------------------------------------------------------------------


class TestConfigCLI:
    """Tests for CLI ``chatmd config`` commands via CliRunner."""

    def test_config_list(self, workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "list", "-w", str(workspace)])
        assert result.exit_code == 0
        assert "language" in result.output
        assert "..." in result.output  # masked api key

    def test_config_get(self, workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "get", "language", "-w", str(workspace)])
        assert result.exit_code == 0
        assert "en" in result.output

    def test_config_get_not_found(self, workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "get", "no.such.key", "-w", str(workspace)])
        assert result.exit_code == 1

    def test_config_set(self, workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["config", "set", "language", "cn", "-w", str(workspace)]
        )
        assert result.exit_code == 0
        assert "language" in result.output

        # Verify
        get_result = runner.invoke(
            main, ["config", "get", "language", "-w", str(workspace)]
        )
        assert "cn" in get_result.output

    def test_config_set_api_key(self, workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["config", "set", "ai.api_key", "sk-newkey123", "-w", str(workspace)]
        )
        assert result.exit_code == 0

    def test_config_list_no_workspace(self, empty_workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "list", "-w", str(empty_workspace)])
        assert result.exit_code == 1

    def test_config_init_interactive(self, workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["config", "init", "-w", str(workspace)],
            input="litestartup\nsk-test-key\nen\n",
        )
        assert result.exit_code == 0
        assert "Configuration saved" in result.output or "配置已保存" in result.output

    def test_config_init_skip_provider(self, workspace: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["config", "init", "-w", str(workspace)],
            input="skip\ncn\n",
        )
        assert result.exit_code == 0

    def test_config_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "get" in result.output
        assert "set" in result.output
        assert "init" in result.output
