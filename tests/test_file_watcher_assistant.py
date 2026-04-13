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
        watch_dirs=["chatmd/"],
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


class TestDefaultWatcherRegression:
    """Ensure default watch_dirs=['chatmd/'] works correctly."""

    def test_chatmd_chat_md_matched(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "chatmd" / "chat.md") is True

    def test_chatmd_subdir_matched(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "chatmd" / "chat" / "topic.md") is True

    def test_chatmd_cron_matched(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "chatmd" / "cron.md") is True

    def test_root_md_rejected(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "README.md") is False

    def test_docs_subdir_rejected(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / "docs" / "notes.md") is False

    def test_dotchatmd_excluded(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / ".chatmd" / "agent.yaml") is False

    def test_git_dir_excluded(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        assert handler_chat._is_watched(workspace / ".git" / "HEAD") is False


class TestDotfileFiltering:
    """Dotfiles (names starting with .) should be skipped everywhere."""

    def test_dotfile_in_root_excluded(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        assert handler_dot._is_watched(workspace / ".~chat.md") is False

    def test_dotfile_in_chatmd_dir(self, handler_chat: _ChangeHandler, workspace: Path) -> None:
        # .~chat.md is a dotfile — rel.parts includes ".~chat.md" which starts with "."
        # _is_watched filters any path part starting with ".", including filenames
        # Additionally, on_modified also has an early dotfile check
        assert handler_chat._is_watched(workspace / "chatmd" / ".~chat.md") is False

    def test_dotdir_excluded_generically(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        """Any dot-prefixed directory should be excluded, not just the explicit set."""
        assert handler_dot._is_watched(workspace / ".hidden_dir" / "notes.md") is False

    def test_dotdir_not_in_excluded_set(self, handler_dot: _ChangeHandler, workspace: Path) -> None:
        """A new dot-prefixed dir not in _EXCLUDED_DIRS should still be excluded."""
        assert handler_dot._is_watched(workspace / ".my_custom_tool" / "file.md") is False


class TestExcludedDirsConstant:
    """Verify the _EXCLUDED_DIRS set contains expected entries."""

    @pytest.mark.parametrize(
        "dirname",
        [".chatmd", ".git", "node_modules", ".obsidian", ".vscode", ".idea", "__pycache__"],
    )
    def test_excluded_dir_present(self, dirname: str) -> None:
        assert dirname in _EXCLUDED_DIRS
