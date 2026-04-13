"""Cron safety — dangerous command blacklist + auto-pause (T-064 / US-027).

Provides:
- Dangerous command blacklist for cron scheduling.
- Auto-pause mechanism for jobs with consecutive failures.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatmd.engine.cron_scheduler import CronScheduler

logger = logging.getLogger(__name__)

# Commands that should not be allowed in cron schedules.
DANGEROUS_COMMANDS: frozenset[str] = frozenset({
    "upload",
    "new",
    "upgrade",
})


def is_dangerous_command(command: str) -> bool:
    """Check if a command string uses a blacklisted command.

    Extracts the command name (first word after ``/``) and checks against
    the blacklist. Case-insensitive.
    """
    cmd = command.strip().lstrip("/").split()[0].lower() if command.strip() else ""
    return cmd in DANGEROUS_COMMANDS


def auto_pause_on_failures(
    scheduler: CronScheduler,
    max_failures: int = 5,
) -> list[str]:
    """Pause jobs that have exceeded the consecutive failure threshold.

    Returns a list of job IDs that were newly paused.
    """
    from chatmd.engine.cron_scheduler import CronTaskStatus

    newly_paused: list[str] = []
    for job_id, state in scheduler.get_all_states().items():
        if state.status == CronTaskStatus.PAUSED:
            continue
        if state.consecutive_failures >= max_failures:
            scheduler.pause(job_id)
            newly_paused.append(job_id)
            logger.warning(
                "Cron job %s auto-paused after %d consecutive failures",
                job_id,
                state.consecutive_failures,
            )
    return newly_paused
