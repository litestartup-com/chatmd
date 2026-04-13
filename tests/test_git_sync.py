"""Tests for Git sync."""

import subprocess

from chatmd.infra.git_sync import GitSync


class TestGitSync:
    def test_sync_no_git_repo(self, tmp_path):
        gs = GitSync(tmp_path)
        success, msg = gs.sync_now()
        assert not success
        assert "not a Git repository" in msg

    def test_sync_clean_repo(self, tmp_path):
        # Init a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        # Create initial commit
        (tmp_path / "README.md").write_text("init", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        gs = GitSync(tmp_path)
        success, msg = gs.sync_now()
        assert success
        assert "No changes to sync" in msg

    def test_sync_with_changes(self, tmp_path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path, capture_output=True, check=True,
        )
        (tmp_path / "README.md").write_text("init", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, capture_output=True, check=True,
        )

        # Make a change
        (tmp_path / "chat.md").write_text("/date", encoding="utf-8")

        gs = GitSync(tmp_path)
        success, msg = gs.sync_now()
        assert success
        assert "sync completed" in msg

    def test_constructor_simple(self, tmp_path):
        gs = GitSync(tmp_path)
        assert gs._workspace == tmp_path
