"""Tests for chatmd upgrade migrations."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chatmd.commands.migrations import (
    MIGRATIONS,
    _ensure_sync_cron_job,
    run_migrations,
)


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace with v0.1 config."""
    chatmd_dir = tmp_path / ".chatmd"
    chatmd_dir.mkdir()
    interact_root = tmp_path / "chatmd"
    interact_root.mkdir()

    agent_yaml = chatmd_dir / "agent.yaml"
    config = {
        "version": "0.1",
        "sync": {"mode": "git", "auto_commit": True, "interval": 300},
        "cron": {"enabled": False, "cron_file": "cron.md"},
    }
    with open(agent_yaml, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)

    return tmp_path


@pytest.fixture()
def workspace_current(tmp_path: Path) -> Path:
    """Create a workspace already at current version."""
    chatmd_dir = tmp_path / ".chatmd"
    chatmd_dir.mkdir()

    agent_yaml = chatmd_dir / "agent.yaml"
    config = {"version": "0.2.4", "sync": {"mode": "git"}}
    with open(agent_yaml, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)

    return tmp_path


class TestRunMigrations:
    """Test the run_migrations() orchestrator."""

    def test_migrate_0_1_to_latest(self, workspace: Path) -> None:
        """Full migration from 0.1 to latest (0.2.4)."""
        messages = run_migrations(workspace)

        assert any("0.1 → 0.2.3" in m for m in messages)
        assert any("0.2.3 → 0.2.4" in m for m in messages)

        # Verify config was updated
        agent_yaml = workspace / ".chatmd" / "agent.yaml"
        with open(agent_yaml, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config["version"] == "0.2.4"
        assert "auto_commit" not in config.get("sync", {})
        assert "interval" not in config.get("sync", {})
        assert config["sync"]["mode"] == "git"

    def test_backup_created(self, workspace: Path) -> None:
        """Backup file is created before migration."""
        run_migrations(workspace)

        backups = list((workspace / ".chatmd").glob("agent.yaml.bak.*"))
        assert len(backups) == 1

    def test_no_migration_needed(self, workspace_current: Path) -> None:
        """No messages when already at current version."""
        messages = run_migrations(workspace_current)
        assert messages == []

    def test_idempotent(self, workspace: Path) -> None:
        """Running migrations twice produces no changes on second run."""
        run_migrations(workspace)
        messages = run_migrations(workspace)
        assert messages == []

    def test_no_agent_yaml(self, tmp_path: Path) -> None:
        """Gracefully handle missing agent.yaml."""
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        messages = run_migrations(tmp_path)
        assert messages == []

    def test_missing_chatmd_dir(self, tmp_path: Path) -> None:
        """Gracefully handle missing .chatmd directory."""
        messages = run_migrations(tmp_path)
        assert messages == []


class TestMigrate01To023:
    """Test the 0.1 → 0.2.3 migration specifics."""

    def test_sync_config_cleaned(self, workspace: Path) -> None:
        """auto_commit and interval are removed from sync config."""
        run_migrations(workspace)

        with open(workspace / ".chatmd" / "agent.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        sync = config["sync"]
        assert sync == {"mode": "git"}

    def test_cron_enabled(self, workspace: Path) -> None:
        """Cron is enabled after migration."""
        run_migrations(workspace)

        with open(workspace / ".chatmd" / "agent.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config["cron"]["enabled"] is True

    def test_cron_md_created(self, workspace: Path) -> None:
        """cron.md is created with /sync job."""
        run_migrations(workspace)

        cron_md = workspace / "chatmd" / "cron.md"
        assert cron_md.exists()
        content = cron_md.read_text(encoding="utf-8")
        assert "@every 5m /sync" in content

    def test_cron_md_existing_no_sync(self, workspace: Path) -> None:
        """If cron.md exists without /sync, the job is appended."""
        cron_md = workspace / "chatmd" / "cron.md"
        cron_md.write_text(
            "# Cron\n\n```cron\n@daily /date\n```\n",
            encoding="utf-8",
        )

        run_migrations(workspace)

        content = cron_md.read_text(encoding="utf-8")
        assert "@every 5m /sync" in content
        assert "@daily /date" in content

    def test_cron_md_existing_with_sync(self, workspace: Path) -> None:
        """If cron.md already has /sync, don't add duplicate."""
        cron_md = workspace / "chatmd" / "cron.md"
        original = "# Cron\n\n```cron\n@every 10m /sync\n```\n"
        cron_md.write_text(original, encoding="utf-8")

        run_migrations(workspace)

        content = cron_md.read_text(encoding="utf-8")
        # Should still have original, not duplicated
        assert content.count("/sync") == 1

    def test_sync_mode_none_no_cron_job(self, tmp_path: Path) -> None:
        """If sync.mode is not git, no cron job is added."""
        chatmd_dir = tmp_path / ".chatmd"
        chatmd_dir.mkdir()
        interact_root = tmp_path / "chatmd"
        interact_root.mkdir()

        config = {
            "version": "0.1",
            "sync": {"mode": "none"},
            "cron": {"enabled": False},
        }
        with open(chatmd_dir / "agent.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        run_migrations(tmp_path)

        cron_md = interact_root / "cron.md"
        assert not cron_md.exists()


class TestEnsureSyncCronJob:
    """Test the _ensure_sync_cron_job helper."""

    def test_creates_cron_md(self, tmp_path: Path) -> None:
        """Creates cron.md if it doesn't exist."""
        interact = tmp_path / "chatmd"
        interact.mkdir()
        config = {"cron": {"cron_file": "cron.md"}}

        _ensure_sync_cron_job(tmp_path, config)

        cron_md = interact / "cron.md"
        assert cron_md.exists()
        content = cron_md.read_text(encoding="utf-8")
        assert "```cron" in content
        assert "@every 5m /sync" in content

    def test_appends_to_existing_block(self, tmp_path: Path) -> None:
        """Appends /sync inside an existing cron block."""
        interact = tmp_path / "chatmd"
        interact.mkdir()
        cron_md = interact / "cron.md"
        cron_md.write_text(
            "# Tasks\n\n```cron\n@daily /date\n```\n",
            encoding="utf-8",
        )
        config = {"cron": {"cron_file": "cron.md"}}

        _ensure_sync_cron_job(tmp_path, config)

        content = cron_md.read_text(encoding="utf-8")
        assert "@every 5m /sync" in content
        assert "@daily /date" in content

    def test_skip_if_sync_exists(self, tmp_path: Path) -> None:
        """Don't add if /sync already present."""
        interact = tmp_path / "chatmd"
        interact.mkdir()
        cron_md = interact / "cron.md"
        original = "```cron\n@every 3m /sync\n```\n"
        cron_md.write_text(original, encoding="utf-8")
        config = {"cron": {"cron_file": "cron.md"}}

        _ensure_sync_cron_job(tmp_path, config)

        assert cron_md.read_text(encoding="utf-8") == original


class TestMigrationRegistry:
    """Test the migration registry itself."""

    def test_migrations_registered(self) -> None:
        """At least one migration is registered."""
        assert len(MIGRATIONS) >= 1

    def test_migration_chain_continuous(self) -> None:
        """Migration versions form a continuous chain."""
        for i in range(len(MIGRATIONS) - 1):
            _, to_ver, _ = MIGRATIONS[i]
            from_ver, _, _ = MIGRATIONS[i + 1]
            assert to_ver == from_ver, (
                f"Gap in migration chain: {to_ver} != {from_ver}"
            )
