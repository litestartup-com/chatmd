"""Tests for hardcoded interaction_dir='chatmd' and simplified watcher (R-057 / US-032)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chatmd.infra.config import Config


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a minimal ChatMD workspace."""
    chatmd_dir = tmp_path / ".chatmd"
    chatmd_dir.mkdir()
    for sub in ("skills", "memory", "logs", "history"):
        (chatmd_dir / sub).mkdir()
    return tmp_path


def _write_agent_yaml(workspace: Path, data: dict) -> None:
    with open(workspace / ".chatmd" / "agent.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _write_user_yaml(workspace: Path, data: dict) -> None:
    with open(workspace / ".chatmd" / "user.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ---------- interaction_dir property ----------


class TestInteractionDirProperty:
    """Config.interaction_dir is always 'chatmd'."""

    def test_hardcoded_chatmd(self, workspace: Path) -> None:
        cfg = Config(workspace)
        assert cfg.interaction_dir == "chatmd"

    def test_ignores_old_config_values(self, workspace: Path) -> None:
        """Old agent.yaml with workspace.interaction_dir is silently ignored."""
        _write_agent_yaml(workspace, {
            "workspace": {"mode": "full", "interaction_dir": "notes"},
        })
        _write_user_yaml(workspace, {"language": "en"})
        cfg = Config(workspace)
        assert cfg.interaction_dir == "chatmd"

    def test_ignores_old_mode(self, workspace: Path) -> None:
        """Old agent.yaml with workspace.mode is silently ignored."""
        _write_agent_yaml(workspace, {"workspace": {"mode": "assistant"}})
        _write_user_yaml(workspace, {"language": "en"})
        cfg = Config(workspace)
        assert cfg.interaction_dir == "chatmd"


# ---------- interaction_path helper ----------


class TestInteractionPath:
    """Config.interaction_path() always resolves to workspace / chatmd / relative."""

    def test_chat_md(self, workspace: Path) -> None:
        cfg = Config(workspace)
        assert cfg.interaction_path("chat.md") == workspace / "chatmd" / "chat.md"

    def test_nested_file(self, workspace: Path) -> None:
        cfg = Config(workspace)
        assert cfg.interaction_path("chat/topic.md") == workspace / "chatmd" / "chat" / "topic.md"

    def test_cron_md(self, workspace: Path) -> None:
        cfg = Config(workspace)
        assert cfg.interaction_path("cron.md") == workspace / "chatmd" / "cron.md"

    def test_dot_relative(self, workspace: Path) -> None:
        cfg = Config(workspace)
        assert cfg.interaction_path(".") == workspace / "chatmd" / "."


# ---------- resolve_watch_paths helper ----------


class TestResolveWatchPaths:
    """Config.resolve_watch_paths() returns watch_dirs with chatmd/ always included."""

    def test_default_watch_dirs(self, workspace: Path) -> None:
        cfg = Config(workspace)
        dirs = cfg.resolve_watch_paths()
        assert "chatmd/" in dirs

    def test_custom_watch_dirs_still_includes_chatmd(self, workspace: Path) -> None:
        _write_agent_yaml(workspace, {
            "watcher": {"watch_dirs": ["docs/"]},
        })
        _write_user_yaml(workspace, {"language": "en"})
        cfg = Config(workspace)
        dirs = cfg.resolve_watch_paths()
        assert "chatmd/" in dirs
        assert "docs/" in dirs

    def test_explicit_chatmd_not_duplicated(self, workspace: Path) -> None:
        _write_agent_yaml(workspace, {
            "watcher": {"watch_dirs": ["chatmd/", "extra/"]},
        })
        _write_user_yaml(workspace, {"language": "en"})
        cfg = Config(workspace)
        dirs = cfg.resolve_watch_paths()
        assert dirs.count("chatmd/") == 1
        assert "extra/" in dirs

    def test_dot_watch_dir(self, workspace: Path) -> None:
        """watch_dirs=['.'] means watch entire workspace."""
        _write_agent_yaml(workspace, {
            "watcher": {"watch_dirs": ["."]},
        })
        _write_user_yaml(workspace, {"language": "en"})
        cfg = Config(workspace)
        dirs = cfg.resolve_watch_paths()
        assert "." in dirs
        assert "chatmd/" in dirs


# ---------- backward compatibility ----------


class TestBackwardCompat:
    """Existing workspaces with old config values are silently accepted."""

    def test_old_config_with_mode_still_works(self, workspace: Path) -> None:
        _write_agent_yaml(workspace, {
            "version": "0.1",
            "workspace": {"mode": "full"},
        })
        _write_user_yaml(workspace, {"language": "en"})
        cfg = Config(workspace)
        assert cfg.interaction_dir == "chatmd"
        assert cfg.interaction_path("chat.md") == workspace / "chatmd" / "chat.md"

    def test_old_config_with_interaction_dir_ignored(self, workspace: Path) -> None:
        _write_agent_yaml(workspace, {
            "version": "0.1",
            "workspace": {"mode": "assistant", "interaction_dir": "."},
        })
        _write_user_yaml(workspace, {"language": "en"})
        cfg = Config(workspace)
        assert cfg.interaction_dir == "chatmd"
        assert cfg.interaction_path("chat.md") == workspace / "chatmd" / "chat.md"
