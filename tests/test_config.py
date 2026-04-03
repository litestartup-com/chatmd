"""Tests for configuration management."""

import os

import pytest
import yaml

from chatmd.infra.config import Config


@pytest.fixture
def workspace(tmp_path):
    """Create a minimal workspace with .chatmd/ directory."""
    chatmd_dir = tmp_path / ".chatmd"
    chatmd_dir.mkdir()
    return tmp_path


@pytest.fixture
def workspace_with_config(workspace):
    """Create workspace with agent.yaml and user.yaml."""
    agent_cfg = {
        "version": "0.1",
        "workspace": {"mode": "full"},
        "logging": {"level": "DEBUG"},
    }
    user_cfg = {
        "display_name": "Test User",
        "aliases": {"en": "translate(English)", "q": "ask"},
    }
    with open(workspace / ".chatmd" / "agent.yaml", "w", encoding="utf-8") as f:
        yaml.dump(agent_cfg, f)
    with open(workspace / ".chatmd" / "user.yaml", "w", encoding="utf-8") as f:
        yaml.dump(user_cfg, f)
    return workspace


class TestConfigLoading:
    """Test config loading and defaults."""

    def test_defaults_when_no_files(self, workspace):
        config = Config(workspace)
        assert config.workspace_mode == "full"
        assert config.get("logging.level") == "INFO"
        assert config.get("watcher.debounce_ms") == 300

    def test_override_from_agent_yaml(self, workspace_with_config):
        config = Config(workspace_with_config)
        assert config.get("logging.level") == "DEBUG"
        assert config.workspace_mode == "full"

    def test_user_aliases(self, workspace_with_config):
        config = Config(workspace_with_config)
        assert config.aliases["en"] == "translate(English)"
        assert config.aliases["q"] == "ask"

    def test_get_nonexistent_key(self, workspace):
        config = Config(workspace)
        assert config.get("nonexistent.key") is None
        assert config.get("nonexistent.key", "default") == "default"

    def test_deep_merge_preserves_defaults(self, workspace_with_config):
        config = Config(workspace_with_config)
        # agent.yaml only overrides logging.level, other defaults should remain
        assert config.get("watcher.debounce_ms") == 300
        assert config.get("async.max_concurrent") == 3


class TestEnvVarResolution:
    """Test ${ENV_VAR} resolution."""

    def test_env_var_resolved(self, workspace):
        os.environ["TEST_CHATMD_KEY"] = "secret123"
        try:
            agent_cfg = {"ai": {"providers": [{"api_key": "${TEST_CHATMD_KEY}"}]}}
            with open(workspace / ".chatmd" / "agent.yaml", "w", encoding="utf-8") as f:
                yaml.dump(agent_cfg, f)
            config = Config(workspace)
            providers = config.get("ai.providers")
            assert providers[0]["api_key"] == "secret123"
        finally:
            del os.environ["TEST_CHATMD_KEY"]

    def test_unset_env_var_kept_as_is(self, workspace):
        agent_cfg = {"ai": {"providers": [{"api_key": "${NONEXISTENT_VAR}"}]}}
        with open(workspace / ".chatmd" / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(agent_cfg, f)
        config = Config(workspace)
        providers = config.get("ai.providers")
        assert providers[0]["api_key"] == "${NONEXISTENT_VAR}"
