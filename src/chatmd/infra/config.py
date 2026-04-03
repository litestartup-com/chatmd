"""Configuration manager — loads agent.yaml and user.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from chatmd.exceptions import ConfigError
from chatmd.i18n import set_locale

_DEFAULT_AGENT_CONFIG: dict[str, Any] = {
    "version": "0.1",
    "workspace": {"mode": "full"},
    "ai": {"providers": []},
    "trigger": {
        "signals": [
            {"type": "file_save", "debounce_ms": 800},
            {"type": "suffix", "marker": ";", "enabled": False},
        ],
    },
    "watcher": {
        "debounce_ms": 300,
        "watch_files": ["chat.md"],
        "watch_dirs": ["chat/"],
        "ignore_patterns": ["_index.md"],
    },
    "commands": {"prefix": "/"},
    "async": {"max_concurrent": 3, "timeout": 60},
    "sync": {"mode": "git", "auto_commit": True, "interval": 300},
    "logging": {"level": "INFO", "audit": True},
}

_DEFAULT_USER_CONFIG: dict[str, Any] = {
    "language": "en",
    "aliases": {
        "en": "translate(English)",
        "jp": "translate(Japanese)",
        "cn": "translate(Chinese)",
        "q": "ask",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_env_vars(obj: Any) -> Any:
    """Replace ``${ENV_VAR}`` references with actual environment values."""
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        var_name = obj[2:-1]
        return os.environ.get(var_name, obj)
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj


class Config:
    """Loads and manages ChatMD configuration."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.chatmd_dir = workspace / ".chatmd"
        self._agent: dict[str, Any] = {}
        self._user: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration files, merging with defaults."""
        agent_path = self.chatmd_dir / "agent.yaml"
        user_path = self.chatmd_dir / "user.yaml"

        agent_raw = self._load_yaml(agent_path) if agent_path.exists() else {}
        user_raw = self._load_yaml(user_path) if user_path.exists() else {}

        self._agent = _resolve_env_vars(_deep_merge(_DEFAULT_AGENT_CONFIG, agent_raw))
        self._user = _resolve_env_vars(_deep_merge(_DEFAULT_USER_CONFIG, user_raw))

        # Initialize i18n locale from user config
        locale = self._user.get("language", "en")
        set_locale(locale)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot-separated path. Searches agent then user."""
        val = self._get_nested(self._agent, key)
        if val is not None:
            return val
        val = self._get_nested(self._user, key)
        return val if val is not None else default

    @property
    def agent(self) -> dict[str, Any]:
        """Return the full agent config dict."""
        return self._agent

    @property
    def user(self) -> dict[str, Any]:
        """Return the full user config dict."""
        return self._user

    @property
    def aliases(self) -> dict[str, str]:
        """Return user-defined command aliases."""
        return self._user.get("aliases", {})

    @property
    def workspace_mode(self) -> str:
        """Return workspace mode (full or assistant)."""
        return self._agent.get("workspace", {}).get("mode", "full")

    def get_trigger_mode(self) -> str:
        """Return the current trigger mode: 'suffix' or 'save'."""
        signals = self._agent.get("trigger", {}).get("signals", [])
        for sig in signals:
            if sig.get("type") == "suffix" and sig.get("enabled", False):
                return "suffix"
        return "save"

    def get_suffix_marker(self) -> str:
        """Return the suffix marker character."""
        signals = self._agent.get("trigger", {}).get("signals", [])
        for sig in signals:
            if sig.get("type") == "suffix":
                return sig.get("marker", ";")
        return ";"

    def update_trigger_mode(self, mode: str) -> None:
        """Switch trigger mode to 'suffix' or 'save' and persist to agent.yaml."""
        agent_path = self.chatmd_dir / "agent.yaml"
        raw = self._load_yaml(agent_path) if agent_path.exists() else {}

        signals = raw.setdefault("trigger", {}).setdefault("signals", [])

        # Ensure both signal types exist
        suffix_found = False
        for sig in signals:
            if sig.get("type") == "suffix":
                sig["enabled"] = mode == "suffix"
                suffix_found = True
        if not suffix_found:
            signals.append({"type": "suffix", "marker": ";", "enabled": mode == "suffix"})

        with open(agent_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Reload config in memory
        self.load()

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        """Load a YAML file, returning an empty dict on parse failure."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Failed to parse {path}: {exc}") from exc

    @staticmethod
    def _get_nested(data: dict, dotted_key: str) -> Any:
        """Traverse a nested dict using a dot-separated key."""
        keys = dotted_key.split(".")
        current: Any = data
        for k in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(k)
            if current is None:
                return None
        return current
