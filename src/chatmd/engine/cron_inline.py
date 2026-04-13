"""Cron inline_status — write back job ID + status as comments in cron blocks.

After scanning cron.md, this module updates each task line with an inline
comment showing the assigned job ID, status, and next run time.

Format::

    0 9 * * *   /ask daily    # [cron-a1b2] ✅ next: 2026-04-09 09:00
    @hourly     /sync         # [cron-c3d4] ⏸ paused
    bad expr    /foo          # ❌ syntax error
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Pattern to match an existing inline status comment
_INLINE_COMMENT_RE = re.compile(r"\s+#\s*\[cron-[a-f0-9]+\].*$")
_ERROR_COMMENT_RE = re.compile(r"\s+#\s*❌.*$")


def _strip_inline_comment(line: str) -> str:
    """Remove any existing inline status comment from a cron line."""
    line = _INLINE_COMMENT_RE.sub("", line)
    line = _ERROR_COMMENT_RE.sub("", line)
    return line.rstrip()


def write_inline_status(
    cron_file: Path,
    job_states: dict[str, dict],
    line_to_job: dict[int, str] | None = None,
) -> bool:
    """Update cron.md with inline status comments.

    Parameters
    ----------
    cron_file:
        Path to the cron.md file.
    job_states:
        Dict of ``{job_id: {"status": str, "next_run": str|None, ...}}``.
    line_to_job:
        Optional mapping of ``{line_number: job_id}`` for precise line matching.
        If not provided, matches are done by scanning for job commands.

    Returns
    -------
    True if the file was modified, False otherwise.
    """
    if not cron_file.exists():
        return False

    content = cron_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    modified = False
    in_cron_block = False

    # Build reverse lookup: raw_line_content → job_id (stripped)
    job_by_content: dict[str, str] = {}
    for job_id, info in job_states.items():
        raw = info.get("raw_line", "")
        if raw:
            job_by_content[raw.strip()] = job_id

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "```cron":
            in_cron_block = True
            continue
        if stripped == "```" and in_cron_block:
            in_cron_block = False
            continue
        if not in_cron_block:
            continue
        if not stripped or stripped.startswith("#"):
            continue

        # This is a task line inside a cron block
        clean_line = _strip_inline_comment(line)
        clean_stripped = clean_line.strip()

        # Try to match this line to a job
        matched_job_id = None

        # Method 1: line_to_job mapping
        if line_to_job and (i + 1) in line_to_job:
            matched_job_id = line_to_job[i + 1]

        # Method 2: content matching
        if not matched_job_id:
            matched_job_id = job_by_content.get(clean_stripped)

        if matched_job_id and matched_job_id in job_states:
            info = job_states[matched_job_id]
            status = info.get("status", "active")
            next_run = info.get("next_run_str", "")

            if status == "paused":
                comment = f"# [{matched_job_id}] ⏸ paused"
            elif next_run:
                comment = f"# [{matched_job_id}] ✅ next: {next_run}"
            else:
                comment = f"# [{matched_job_id}] ✅"

            new_line = f"{clean_line}    {comment}"
            if new_line != line:
                lines[i] = new_line
                modified = True

    if modified:
        cron_file.write_text("\n".join(lines), encoding="utf-8")
        logger.debug("Inline status updated in %s", cron_file)

    return modified
