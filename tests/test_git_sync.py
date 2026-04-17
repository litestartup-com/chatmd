"""Tests for Git sync."""

import subprocess
import threading
import time

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

    def test_sync_pull_without_local_changes(self, tmp_path):
        """When local has no changes but remote has new commits, /sync should still pull."""
        # Set up a bare "remote" repo
        remote = tmp_path / "remote.git"
        remote.mkdir()
        subprocess.run(["git", "init", "--bare"], cwd=remote, capture_output=True, check=True)

        # Clone it to a "local" working copy
        local = tmp_path / "local"
        subprocess.run(
            ["git", "clone", str(remote), str(local)],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=local, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=local, capture_output=True, check=True,
        )
        # Create initial commit and push
        (local / "README.md").write_text("init", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=local, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=local, capture_output=True, check=True,
        )
        subprocess.run(["git", "push"], cwd=local, capture_output=True, check=True)

        # Simulate remote change: clone again, commit, push
        other = tmp_path / "other"
        subprocess.run(
            ["git", "clone", str(remote), str(other)],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "other@test.com"],
            cwd=other, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Other"],
            cwd=other, capture_output=True, check=True,
        )
        (other / "inbox.md").write_text("hello from bot", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=other, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "bot: new inbox"],
            cwd=other, capture_output=True, check=True,
        )
        subprocess.run(["git", "push"], cwd=other, capture_output=True, check=True)

        # Now local has no changes, but remote has a new commit
        assert not (local / "inbox.md").exists()

        gs = GitSync(local)
        success, msg = gs.sync_now()
        assert success
        assert "sync completed" in msg
        # The remote file should now be pulled into local
        assert (local / "inbox.md").exists()
        assert (local / "inbox.md").read_text(encoding="utf-8") == "hello from bot"

    def test_constructor_simple(self, tmp_path):
        gs = GitSync(tmp_path)
        assert gs._workspace == tmp_path

    def test_sync_error_includes_git_stderr(self, tmp_path, monkeypatch):
        gs = GitSync(tmp_path)

        monkeypatch.setattr(gs, "_is_git_repo", lambda: True)
        monkeypatch.setattr(gs, "_has_remote", lambda: False)

        def fake_run_git(*args, check=True):
            if args[:2] == ("status", "--porcelain"):
                return " M chat.md\n"
            if args and args[0] == "commit":
                raise subprocess.CalledProcessError(
                    128,
                    ["git", *args],
                    output="",
                    stderr="fatal: Unable to create '.git/index.lock': File exists.",
                )
            return ""

        monkeypatch.setattr(gs, "_run_git", fake_run_git)
        success, msg = gs.sync_now()
        assert not success
        assert "index.lock" in msg
        assert "another git process may be running" in msg

    def test_sync_operations_are_serialized(self, tmp_path, monkeypatch):
        gs = GitSync(tmp_path)
        monkeypatch.setattr(gs, "_is_git_repo", lambda: True)
        monkeypatch.setattr(gs, "_has_remote", lambda: False)

        counter_lock = threading.Lock()
        active = 0
        max_active = 0

        def fake_run_git(*args, check=True):
            nonlocal active, max_active
            with counter_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with counter_lock:
                active -= 1
            if args[:2] == ("status", "--porcelain"):
                return ""
            return ""

        monkeypatch.setattr(gs, "_run_git", fake_run_git)

        results: list[tuple[bool, str]] = []

        def _runner() -> None:
            results.append(gs.sync_now())

        t1 = threading.Thread(target=_runner)
        t2 = threading.Thread(target=_runner)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2
        assert max_active == 1

    def test_commit_falls_back_to_last_commit_identity(self, tmp_path, monkeypatch):
        gs = GitSync(tmp_path)
        monkeypatch.setattr(gs, "_is_git_repo", lambda: True)
        monkeypatch.setattr(gs, "_has_remote", lambda: False)

        state = {"status_calls": 0, "fallback_called": 0}

        def fake_run_git(*args, check=True):
            if args[:2] == ("status", "--porcelain"):
                state["status_calls"] += 1
                return " M chat.md\n" if state["status_calls"] == 1 else ""
            if args and args[0] == "commit":
                raise subprocess.CalledProcessError(
                    128,
                    ["git", *args],
                    output="",
                    stderr=(
                        "Author identity unknown\n"
                        "*** Please tell me who you are."
                    ),
                )
            if args[:2] == ("log", "-1"):
                return "Existing User\x00existing@example.com"
            return ""

        def fake_run_git_with_configs(configs, *args):
            state["fallback_called"] += 1
            assert configs["user.name"] == "Existing User"
            assert configs["user.email"] == "existing@example.com"
            assert args == ("commit", "-m", "chatmd: auto sync")
            return ""

        monkeypatch.setattr(gs, "_run_git", fake_run_git)
        monkeypatch.setattr(gs, "_run_git_with_configs", fake_run_git_with_configs)

        success, _ = gs.sync_now()
        assert success
        assert state["fallback_called"] == 1
