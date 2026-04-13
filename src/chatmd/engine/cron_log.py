"""Cron execution log writer — appends results to .chatmd/logs/cron_log.md."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def write_cron_log(
    log_path: Path,
    job_id: str,
    command: str,
    output: str,
    success: bool,
) -> None:
    """Append a cron execution record to the log file.

    Format::

        ### ✅ cron-abc1 — /ask daily (2026-04-08 15:00:00)
        > Agent running

        ---

    Or on failure::

        ### ❌ cron-fail1 — /sync (2026-04-08 15:00:00)
        > Connection failed

        ---
    """
    icon = "✅" if success else "❌"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"### {icon} {job_id} — `{command}` ({now})"

    # Indent output lines as blockquote
    output_lines = output.strip().splitlines() if output.strip() else ["(no output)"]
    quoted = "\n".join(f"> {line}" for line in output_lines)

    entry = f"\n{header}\n\n{quoted}\n\n---\n"

    # Create file with header if new
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"# Cron Execution Log\n\n---\n{entry}",
            encoding="utf-8",
        )
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
