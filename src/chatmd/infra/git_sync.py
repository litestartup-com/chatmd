"""Git sync — automatic and manual Git synchronization."""

from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path

from chatmd.i18n import t

logger = logging.getLogger(__name__)


class GitSync:
    """Handles Git auto-commit and sync operations."""

    def __init__(
        self,
        workspace: Path,
        auto_commit: bool = True,
        interval: int = 300,
    ) -> None:
        self._workspace = workspace
        self._auto_commit = auto_commit
        self._interval = interval
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self) -> None:
        """Start the periodic auto-sync timer."""
        if not self._auto_commit:
            logger.info("Git auto-sync disabled")
            return
        if not self._is_git_repo():
            logger.info("Not a git repository, skipping auto-sync")
            return
        self._running = True
        self._schedule_next()
        logger.info("Git auto-sync started (interval=%ds)", self._interval)

    def stop(self) -> None:
        """Stop the auto-sync timer."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Git auto-sync stopped")

    def sync_now(self) -> tuple[bool, str]:
        """Perform an immediate git add + commit + pull + push cycle.

        Returns ``(success, message)``.
        """
        if not self._is_git_repo():
            return False, t("output.sync.not_git_repo")

        try:
            # Stage all changes
            self._run_git("add", "-A")

            # Check if there's anything to commit
            status = self._run_git("status", "--porcelain")
            if not status.strip():
                return True, t("output.sync.no_changes")

            # Commit
            self._run_git("commit", "-m", "chatmd: auto sync")

            # Pull (rebase to reduce merge commits)
            has_remote = self._has_remote()
            if has_remote:
                pull_result = self._run_git("pull", "--rebase", check=False)
                if "CONFLICT" in pull_result:
                    return False, t("output.sync.conflict")

                # Push
                self._run_git("push", check=False)

            return True, t("output.sync.success")
        except subprocess.CalledProcessError as exc:
            return False, t("output.sync.git_failed", error=exc)
        except FileNotFoundError:
            return False, t("output.sync.git_not_installed")

    def _schedule_next(self) -> None:
        """Schedule the next auto-sync."""
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._auto_sync)
        self._timer.daemon = True
        self._timer.start()

    def _auto_sync(self) -> None:
        """Perform auto-sync and reschedule."""
        if not self._running:
            return
        logger.debug("Auto-sync triggered")
        success, msg = self.sync_now()
        if not success:
            logger.warning("Auto-sync failed: %s", msg)
        self._schedule_next()

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

    def _run_git(self, *args: str, check: bool = True) -> str:
        """Run a git command and return stdout."""
        result = subprocess.run(
            ["git", *args],
            cwd=self._workspace,
            capture_output=True,
            text=True,
            check=check,
        )
        return result.stdout
