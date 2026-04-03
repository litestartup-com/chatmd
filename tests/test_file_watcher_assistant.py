"""Tests for assistant-mode full-directory watcher behaviour."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from chatmd.watcher.file_watcher import _EXCLUDED_DIRS, _ChangeHandler


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def handler_dot(workspace: Path) -> _ChangeHandler:
    """Handler with watch_dirs=['.'] (assistant mode)."""
    return _ChangeHandler(
        workspace=workspace,
        callback=MagicMock(),
        file_writer=MagicMock(is_agent_write=MagicMock(return_value=False)),
        watch_files=[],
        watch_dirs=["."],
        ignore_patterns=["_index.md"],
    )


@pytest.fixture()
def handler_chat(workspace: Path) -> _ChangeHandler:
    """Handler with default full-mode config."""
    return _ChangeHandler(
        workspace=workspace,
        callback=MagicMock(),
        file_writer=MagicMock(is_agent_write=MagicMock(return_value=False)),
        watch_files=["chat.md"],
        watch_dirs=["chat/"],
        ignore_patterns=["_index.md"],
    )


class TestAssistantModeWatcher:
    """watch_dirs=['.'] should match all .md files except excluded dirs."""

    def test_root_md_matched(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / "README.md") is True

    def test_nested_subdir_matched(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / "docs" / "notes.md") is True

    def test_deep_nested_matched(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / "a" / "b" / "c" / "deep.md") is True

    def test_chatmd_dir_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / ".chatmd" / "agent.yaml") is False

    def test_git_dir_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / ".git" / "HEAD") is False

    def test_node_modules_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / "node_modules" / "pkg" / "README.md") is False

    def test_obsidian_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / ".obsidian" / "config.md") is False

    def test_vscode_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / ".vscode" / "settings.md") is False

    def test_idea_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / ".idea" / "workspace.md") is False

    def test_pycache_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / "__pycache__" / "mod.md") is False

    def test_outside_workspace_rejected(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        other = workspace.parent / "other_project" / "file.md"
        assert handler_dot._is_watched(other) is False


class TestFullModeWatcherRegression:
    """Ensure full-mode watch_dirs=['chat/'] still works correctly."""

    def test_chat_md_matched(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "chat.md") is True

    def test_chat_subdir_matched(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "chat" / "topic.md") is True

    def test_root_other_md_rejected(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "README.md") is False

    def test_docs_subdir_rejected(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "docs" / "notes.md") is False

    def test_chatmd_dir_excluded(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / ".chatmd" / "agent.yaml") is False

    def test_git_dir_excluded(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / ".git" / "HEAD") is False


class TestExcludedDirsConstant:
    """Verify the _EXCLUDED_DIRS set contains expected entries."""

    @pytest.mark.parametrize(
        "dirname",
        [".chatmd", ".git", "node_modules", ".obsidian", ".vscode", ".idea", "__pycache__"],
    )
    def test_excluded_dir_present(self, dirname: str) -> None:
        assert dirname in _EXCLUDED_DIRS
