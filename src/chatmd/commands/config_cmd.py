"""``chatmd config`` — CLI configuration management (list/get/set/init).

Provides a user-friendly interface to view and modify ChatMD configuration
stored in ``.chatmd/agent.yaml`` and ``.chatmd/user.yaml`` without requiring
manual YAML editing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
import yaml

from chatmd.i18n import t

# ---------------------------------------------------------------------------
# Key alias mapping: shorthand → (target_file, yaml_path_segments)
# For ``agent.yaml`` provider keys, we target ``ai.providers[0].<field>``.
# ---------------------------------------------------------------------------

_AGENT_PROVIDER_KEYS: dict[str, str] = {
    "ai.api_key": "api_key",
    "ai.api_url": "api_url",
    "ai.model": "model",
    "ai.type": "type",
    "ai.timeout": "timeout",
}

_USER_KEYS: set[str] = {"language"}

_TRIGGER_MODE_KEY = "trigger.mode"

# All recognized shorthand keys (for validation)
_ALL_SHORTHAND_KEYS: set[str] = {*_AGENT_PROVIDER_KEYS, *_USER_KEYS, _TRIGGER_MODE_KEY}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_api_key(value: str) -> str:
    """Mask an API key for display: show first 6 + last 3 chars."""
    if not value or value.startswith("${"):
        return value
    if len(value) <= 12:
        return value[:3] + "..." + value[-2:] if len(value) > 5 else "***"
    return value[:6] + "..." + value[-3:]


def _load_yaml(path: Path) -> dict:
    """Load a YAML file, returning empty dict on missing/invalid."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _save_yaml(path: Path, data: dict) -> None:
    """Write a dict to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _flatten(data: dict, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten a nested dict into dotted-key / value pairs."""
    items: list[tuple[str, str]] = []
    for key, value in data.items():
        full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            items.extend(_flatten(value, full_key))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    items.extend(_flatten(item, f"{full_key}.{i}"))
                else:
                    items.append((f"{full_key}.{i}", str(item)))
        else:
            items.append((full_key, str(value)))
    return items


def _should_mask(key: str) -> bool:
    """Return True if the key refers to an API key that should be masked."""
    return "api_key" in key


# Internal keys excluded from ``config list`` (not user-facing settings).
_INTERNAL_KEYS: set[str] = {"version"}


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def resolve_chatmd_dir(workspace: str) -> Path:
    """Resolve the ``.chatmd`` directory for the given workspace."""
    return Path(workspace).resolve() / ".chatmd"


def config_list(workspace: str) -> list[tuple[str, str]]:
    """Return a flat list of (key, display_value) pairs for the workspace."""
    chatmd_dir = resolve_chatmd_dir(workspace)
    agent_path = chatmd_dir / "agent.yaml"
    user_path = chatmd_dir / "user.yaml"

    result: list[tuple[str, str]] = []

    agent_data = _load_yaml(agent_path)
    if agent_data:
        for k, v in _flatten(agent_data):
            if k in _INTERNAL_KEYS:
                continue
            display = _mask_api_key(v) if _should_mask(k) else v
            result.append((k, display))

    user_data = _load_yaml(user_path)
    if user_data:
        for k, v in _flatten(user_data):
            result.append((k, v))

    return result


def config_get(workspace: str, key: str) -> str | None:
    """Get a single config value by shorthand or dotted key.

    Returns the display value (masked for API keys), or None if not found.
    """
    chatmd_dir = resolve_chatmd_dir(workspace)
    agent_path = chatmd_dir / "agent.yaml"
    user_path = chatmd_dir / "user.yaml"

    # Shorthand for provider keys
    if key in _AGENT_PROVIDER_KEYS:
        agent_data = _load_yaml(agent_path)
        providers = agent_data.get("ai", {}).get("providers", [])
        if providers and isinstance(providers, list) and len(providers) > 0:
            val = providers[0].get(_AGENT_PROVIDER_KEYS[key])
            if val is not None:
                return _mask_api_key(str(val)) if _should_mask(key) else str(val)
        return None

    # Trigger mode shorthand
    if key == _TRIGGER_MODE_KEY:
        agent_data = _load_yaml(agent_path)
        signals = agent_data.get("trigger", {}).get("signals", [])
        for sig in signals:
            if sig.get("type") == "suffix" and sig.get("enabled", False):
                return "suffix"
        return "save"

    # User keys
    if key in _USER_KEYS:
        user_data = _load_yaml(user_path)
        val = user_data.get(key)
        return str(val) if val is not None else None

    # Fallback: search flattened keys
    all_items = config_list(workspace)
    for k, v in all_items:
        if k == key:
            return v
    return None


def config_set(workspace: str, key: str, value: str) -> tuple[str, str]:
    """Set a config value. Returns (target_file_name, display_key).

    Raises ``click.ClickException`` on invalid key or missing workspace.
    """
    chatmd_dir = resolve_chatmd_dir(workspace)
    if not chatmd_dir.exists():
        raise click.ClickException(t("config.no_workspace"))

    agent_path = chatmd_dir / "agent.yaml"
    user_path = chatmd_dir / "user.yaml"

    # Provider keys → agent.yaml
    if key in _AGENT_PROVIDER_KEYS:
        field = _AGENT_PROVIDER_KEYS[key]
        data = _load_yaml(agent_path)
        providers = data.setdefault("ai", {}).setdefault("providers", [])
        if not providers:
            providers.append({
                "name": "litestartup",
                "type": "litestartup",
                "api_key": "",
                "model": "default",
                "is_default": True,
            })
        # Type coerce timeout to int
        coerced: Any = value
        if field == "timeout":
            try:
                coerced = int(value)
            except ValueError:
                raise click.ClickException(t("config.invalid_value", name=key, val=value))
        providers[0][field] = coerced
        _save_yaml(agent_path, data)
        return ("agent.yaml", key)

    # Trigger mode → agent.yaml (delegate to existing logic)
    if key == _TRIGGER_MODE_KEY:
        if value not in ("suffix", "save"):
            raise click.ClickException(
                t("config.invalid_value", name=key, val=value)
            )
        # Use Config class for trigger mode update
        from chatmd.infra.config import Config

        cfg = Config(Path(workspace).resolve())
        cfg.update_trigger_mode(value)
        return ("agent.yaml", key)

    # User keys → user.yaml
    if key in _USER_KEYS:
        data = _load_yaml(user_path)
        data[key] = value
        _save_yaml(user_path, data)
        return ("user.yaml", key)

    raise click.ClickException(t("config.unknown_key", name=key))


def config_init_interactive(workspace: str) -> None:
    """Run interactive configuration wizard."""
    chatmd_dir = resolve_chatmd_dir(workspace)
    if not chatmd_dir.exists():
        raise click.ClickException(t("config.no_workspace"))

    click.echo(t("config.init.welcome"))
    click.echo()

    # Provider selection
    provider = click.prompt(
        t("config.init.provider_prompt"),
        type=click.Choice(["litestartup", "openai", "skip"]),
        default="litestartup",
    )

    if provider != "skip":
        api_key = click.prompt(
            t("config.init.api_key_prompt"),
            hide_input=False,
            default="",
        )
        if api_key:
            config_set(workspace, "ai.api_key", api_key)
            if provider == "openai":
                config_set(workspace, "ai.type", "openai")
                api_url = click.prompt(
                    t("config.init.api_url_prompt"),
                    default="https://api.openai.com/v1/chat/completions",
                )
                config_set(workspace, "ai.api_url", api_url)

    # Language selection
    language = click.prompt(
        t("config.init.language_prompt"),
        type=click.Choice(["en", "cn"]),
        default="en",
    )
    config_set(workspace, "language", language)

    click.echo()
    click.echo(t("config.init.success"))
    click.echo(t("config.init.doctor_hint"))


# ---------------------------------------------------------------------------
# CLI commands (registered in cli.py)
# ---------------------------------------------------------------------------


def run_config_list(workspace: str) -> None:
    """Execute ``chatmd config list``."""
    chatmd_dir = resolve_chatmd_dir(workspace)
    if not chatmd_dir.exists():
        click.echo(t("config.no_workspace"), err=True)
        sys.exit(1)

    items = config_list(workspace)
    if not items:
        click.echo(t("config.empty"))
        return
    for key, value in items:
        click.echo(f"{key} = {value}")


def run_config_get(workspace: str, key: str) -> None:
    """Execute ``chatmd config get <key>``."""
    chatmd_dir = resolve_chatmd_dir(workspace)
    if not chatmd_dir.exists():
        click.echo(t("config.no_workspace"), err=True)
        sys.exit(1)

    value = config_get(workspace, key)
    if value is None:
        click.echo(t("config.key_not_found", name=key), err=True)
        sys.exit(1)
    click.echo(value)


def run_config_set(workspace: str, key: str, value: str) -> None:
    """Execute ``chatmd config set <key> <value>``."""
    target_file, display_key = config_set(workspace, key, value)
    click.echo(t("config.set_success", name=display_key, file=f".chatmd/{target_file}"))


def run_config_init(workspace: str) -> None:
    """Execute ``chatmd config init``."""
    config_init_interactive(workspace)
