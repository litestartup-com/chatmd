"""Git sync — manual Git synchronization.

Automatic periodic sync is handled by cron (``@every 5m /sync`` in cron.md).
This module only provides the ``sync_now()`` operation used by ``/sync``.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from chatmd.i18n import t

logger = logging.getLogger(__name__)


class GitSync:
    """Handles Git sync operations for ``/sync`` command and cron."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

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
