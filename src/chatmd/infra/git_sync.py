"""Git sync — manual Git synchronization.

Automatic periodic sync is handled by cron (``@every 5m /sync`` in cron.md).
This module only provides the ``sync_now()`` operation used by ``/sync``.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from pathlib import Path

from chatmd.i18n import t

logger = logging.getLogger(__name__)


class GitSync:
    """Handles Git sync operations for ``/sync`` command and cron."""

    _lock_registry_guard = threading.Lock()
    _workspace_locks: dict[str, threading.Lock] = {}

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace
        self._sync_lock = self._get_workspace_lock()

    def _get_workspace_lock(self) -> threading.Lock:
        """Return a shared lock for the same workspace path."""
        key = str(self._workspace.resolve())
        with self._lock_registry_guard:
            lock = self._workspace_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._workspace_locks[key] = lock
            return lock

    def sync_now(self) -> tuple[bool, str]:
        """Perform an immediate git add + commit + pull (merge) + push cycle.

        Uses merge (not rebase) so that concurrent appends to inbox files
        by the Bot and local edits can be auto-merged by git's ort strategy.

        Returns ``(success, message)``.
        """
        if not self._is_git_repo():
            return False, t("output.sync.not_git_repo")

        try:
            # Serialize /sync operations per workspace to avoid git index.lock
            # races between cron-triggered and manual /sync runs.
            with self._sync_lock:
                has_remote = self._has_remote()
                had_local_changes = False
                pulled = 0
                pushed = 0

                # Stage all changes
                self._run_git("add", "-A")

                # Check if there's anything to commit
                status = self._run_git("status", "--porcelain")
                if status.strip():
                    self._commit_auto_sync()
                    had_local_changes = True

                # Always pull when remote exists (even without local changes)
                if has_remote:
                    # Count incoming commits before pull
                    pulled = self._count_remote_commits()

                    # Use merge (not rebase) — concurrent appends to the same
                    # file (e.g. inbox) merge cleanly with ort strategy.
                    rc, pull_out, pull_err = self._run_git_rc(
                        "pull", "--no-rebase",
                    )
                    pull_combined = pull_out + pull_err
                    if rc != 0:
                        logger.warning("git pull failed (rc=%d): %s", rc, pull_combined)
                        if "CONFLICT" in pull_combined:
                            self._run_git("merge", "--abort", check=False)
                            return False, t("output.sync.conflict")
                        return False, t(
                            "output.sync.git_failed",
                            error=pull_combined.strip(),
                        )

                    # Re-stage any changes that appeared after pull (e.g.
                    # file_watcher wrote while we were pulling)
                    self._run_git("add", "-A")
                    post_status = self._run_git("status", "--porcelain")
                    if post_status.strip():
                        self._commit_auto_sync()

                    # Push all unpushed commits
                    if self._has_unpushed_commits() or had_local_changes:
                        pushed = self._count_unpushed_commits()
                        push_rc, _, push_err = self._run_git_rc("push")
                        if push_rc != 0:
                            logger.warning("git push failed: %s", push_err)
                            pushed = 0

                elif not had_local_changes:
                    return True, t("output.sync.no_changes")

                return True, self._build_success_message(pulled, pushed)
        except subprocess.CalledProcessError as exc:
            return False, t(
                "output.sync.git_failed",
                error=self._format_git_error(exc),
            )
        except FileNotFoundError:
            return False, t("output.sync.git_not_installed")

    def _build_success_message(self, pulled: int, pushed: int) -> str:
        """Build a detailed sync success message with pull/push stats."""
        if pulled == 0 and pushed == 0:
            return t("output.sync.success")

        parts: list[str] = []
        if pulled > 0:
            parts.append(t("output.sync.pulled", count=pulled))
        if pushed > 0:
            parts.append(t("output.sync.pushed", count=pushed))

        detail = ", ".join(parts)
        return t("output.sync.success_detail", detail=detail)

    def _is_git_repo(self) -> bool:
        """Check if the workspace is a Git repository."""
        return (self._workspace / ".git").is_dir()

    def _has_remote(self) -> bool:
        """Check if the repo has any remote configured."""
        try:
            result = self._run_git("remote")
            return bool(result.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _has_unpushed_commits(self) -> bool:
        """Check if local branch is ahead of its remote tracking branch."""
        return self._count_unpushed_commits() > 0

    def _count_unpushed_commits(self) -> int:
        """Count commits ahead of remote tracking branch."""
        try:
            result = self._run_git(
                "rev-list", "--count", "@{u}..HEAD", check=False,
            )
            return int(result.strip()) if result.strip() else 0
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return 0

    def _count_remote_commits(self) -> int:
        """Count commits on remote that are not yet in local (fetch first)."""
        try:
            self._run_git("fetch", check=False)
            result = self._run_git(
                "rev-list", "--count", "HEAD..@{u}", check=False,
            )
            return int(result.strip()) if result.strip() else 0
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return 0

    def _run_git(self, *args: str, check: bool = True) -> str:
        """Run a git command and return stdout."""
        cmd = ["git", *args]
        retries = 2 if check else 0
        for attempt in range(retries + 1):
            result = subprocess.run(
                cmd,
                cwd=self._workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            if not check or result.returncode == 0:
                return result.stdout

            stderr = (result.stderr or "").lower()
            if result.returncode == 128 and "index.lock" in stderr and attempt < retries:
                time.sleep(0.2 * (attempt + 1))
                continue

            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr=result.stderr,
            )
        return ""

    def _run_git_rc(self, *args: str) -> tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        result = subprocess.run(
            ["git", *args],
            cwd=self._workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr

    def _commit_auto_sync(self) -> None:
        """Commit staged changes with fallback identity for service contexts."""
        commit_exc: subprocess.CalledProcessError | None = None
        try:
            self._run_git("commit", "-m", "chatmd: auto sync")
            return
        except subprocess.CalledProcessError as exc:
            commit_exc = exc
            err = self._format_git_error(exc).lower()
            # Some service/task contexts don't have global git identity.
            if not self._is_identity_error(err):
                raise

        identity = self._last_commit_identity()
        if not identity:
            assert commit_exc is not None
            raise commit_exc

        name, email = identity
        self._run_git_with_configs(
            {"user.name": name, "user.email": email},
            "commit", "-m", "chatmd: auto sync",
        )

    def _last_commit_identity(self) -> tuple[str, str] | None:
        """Read author identity from latest commit as fallback."""
        out = self._run_git("log", "-1", "--format=%an%x00%ae", check=False).strip()
        if "\x00" not in out:
            return None
        name, email = out.split("\x00", 1)
        name = name.strip()
        email = email.strip()
        if not name or not email:
            return None
        return name, email

    @staticmethod
    def _is_identity_error(detail: str) -> bool:
        return (
            "author identity unknown" in detail
            or "committer identity unknown" in detail
            or "unable to auto-detect email address" in detail
            or "please tell me who you are" in detail
        )

    def _run_git_with_configs(self, configs: dict[str, str], *args: str) -> str:
        """Run git with temporary -c key=value configs."""
        config_args: list[str] = []
        for key, value in configs.items():
            config_args.extend(["-c", f"{key}={value}"])
        cmd = ["git", *config_args, *args]
        result = subprocess.run(
            cmd,
            cwd=self._workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr=result.stderr,
            )
        return result.stdout

    @staticmethod
    def _format_git_error(exc: subprocess.CalledProcessError) -> str:
        """Extract actionable git error details from CalledProcessError."""
        stderr = (exc.stderr or "").strip()
        stdout = (exc.output or "").strip()
        detail = stderr or stdout or str(exc)

        if exc.returncode == 128 and "index.lock" in detail.lower():
            detail += " (another git process may be running; retry shortly)"

        return detail
