"""chatmd upgrade — versioned configuration migrations.

Each migration function transforms workspace config from one version to the next.
Migrations are registered in ``MIGRATIONS`` and executed sequentially by
``run_migrations()``.
"""

from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Type alias: (workspace, agent_config_dict) -> modified agent_config_dict
MigrateFn = Callable[[Path, dict[str, Any]], dict[str, Any]]

# ── Migration registry ────────────────────────────────────────────
# Each entry: (from_version, to_version, migrate_fn)
# Executed in order when upgrading from an older version.

MIGRATIONS: list[tuple[str, str, MigrateFn]] = []


def _register(from_ver: str, to_ver: str) -> Callable[[MigrateFn], MigrateFn]:
    """Decorator to register a migration function."""
    def decorator(fn: MigrateFn) -> MigrateFn:
        MIGRATIONS.append((from_ver, to_ver, fn))
        return fn
    return decorator


# ── Public API ────────────────────────────────────────────────────


def run_migrations(workspace: Path) -> list[str]:
    """Run all pending migrations on the workspace.

    Returns a list of human-readable messages describing what was done.
    An empty list means no migrations were needed.
    """
    agent_yaml = workspace / ".chatmd" / "agent.yaml"
    if not agent_yaml.exists():
        return []

    config = _load_yaml(agent_yaml)
    current_version = str(config.get("version", "0.1"))
    messages: list[str] = []

    for from_ver, to_ver, migrate_fn in MIGRATIONS:
        if current_version != from_ver:
            continue

        # Backup before first migration
        if not messages:
            _backup_agent_yaml(agent_yaml)

        config = migrate_fn(workspace, config)
        config["version"] = to_ver
        current_version = to_ver
        messages.append(f"[migrate] {from_ver} → {to_ver}")

    if messages:
        _write_yaml(agent_yaml, config)
        messages.append(f"Config version updated to {current_version}")

    return messages


# ── Migration: 0.1 → 0.2.3 ──────────────────────────────────────


@_register("0.1", "0.2.3")
def migrate_0_1_to_0_2_3(
    workspace: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Migrate from config version 0.1 to 0.2.3.

    Changes:
    - Remove ``sync.auto_commit`` and ``sync.interval`` (now driven by cron).
    - Ensure ``cron.md`` contains ``@every 5m /sync`` if ``sync.mode == git``.
    """
    # Clean up sync config
    sync_cfg = config.get("sync", {})
    if isinstance(sync_cfg, dict):
        sync_cfg.pop("auto_commit", None)
        sync_cfg.pop("interval", None)
        config["sync"] = sync_cfg

    # Ensure cron is enabled
    cron_cfg = config.get("cron", {})
    if isinstance(cron_cfg, dict) and not cron_cfg.get("enabled"):
        cron_cfg["enabled"] = True
        cron_cfg.setdefault("cron_file", "cron.md")
        config["cron"] = cron_cfg

    # Add /sync cron job to cron.md if sync mode is git
    if sync_cfg.get("mode") == "git":
        _ensure_sync_cron_job(workspace, config)

    return config


# ── Migration: 0.2.3 → 0.2.4 ──────────────────────────────────────


@_register("0.2.3", "0.2.4")
def migrate_0_2_3_to_0_2_4(
    workspace: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Migrate from config version 0.2.3 to 0.2.4.

    Changes:
    - Add ``trigger.confirm`` section (enabled: false, commands list).
    """
    trigger = config.setdefault("trigger", {})
    if "confirm" not in trigger:
        trigger["confirm"] = {
            "enabled": False,
            "commands": ["/sync", "/upload", "/new", "/upgrade"],
        }
    return config


# ── Helpers ───────────────────────────────────────────────────────

_SYNC_PATTERN = re.compile(r"/sync\b")


def _ensure_sync_cron_job(workspace: Path, config: dict[str, Any]) -> None:
    """Add ``@every 5m /sync`` to cron.md if not already present."""
    cron_cfg = config.get("cron", {})
    cron_file_name = cron_cfg.get("cron_file", "cron.md")
    cron_path = workspace / "chatmd" / cron_file_name

    if cron_path.exists():
        content = cron_path.read_text(encoding="utf-8")
        if _SYNC_PATTERN.search(content):
            return  # Already has a /sync job

        # Append inside existing cron block or create one
        marker = "```cron"
        end_marker = "```\n"
        if marker in content:
            idx = content.rfind(end_marker)
            if idx > content.find(marker):
                content = (
                    content[:idx] + "@every 5m /sync\n" + content[idx:]
                )
            else:
                content += f"\n{marker}\n@every 5m /sync\n{end_marker}"
        else:
            content += f"\n{marker}\n@every 5m /sync\n{end_marker}"
        cron_path.write_text(content, encoding="utf-8")
    else:
        cron_path.parent.mkdir(parents=True, exist_ok=True)
        cron_path.write_text(
            "# Cron Tasks\n\n```cron\n@every 5m /sync\n```\n",
            encoding="utf-8",
        )


def _backup_agent_yaml(agent_yaml: Path) -> Path:
    """Create a timestamped backup of agent.yaml."""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = agent_yaml.with_name(f"agent.yaml.bak.{ts}")
    shutil.copy2(agent_yaml, backup)
    logger.info("Backup created: %s", backup.name)
    return backup


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file as dict."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write a dict to a YAML file."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
