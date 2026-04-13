"""Cron management skill — /cron subcommands for scheduled task management."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from chatmd.i18n import t
from chatmd.skills.base import Skill, SkillContext, SkillResult

if TYPE_CHECKING:
    from chatmd.engine.cron_scheduler import CronScheduler
    from chatmd.infra.file_writer import FileWriter


class CronSkill(Skill):
    """/cron command — manage cron scheduled tasks."""

    name = "cron"
    description = "cron"
    category = "builtin"
    aliases = []

    _SUBCOMMANDS = frozenset({
        "status", "next", "pause", "resume", "run", "test", "validate", "history",
    })

    @property
    def help_text(self) -> str:
        """Rich help text for /help cron — subcommands + config + safety."""
        return t("skill.cron.help_text")

    def __init__(
        self,
        cron_scheduler: CronScheduler | None = None,
    ) -> None:
        self._cron_scheduler = cron_scheduler
        self._cron_file: Path | None = None
        self._file_writer: FileWriter | None = None

    def set_cron_scheduler(self, scheduler: CronScheduler) -> None:
        """Inject the CronScheduler after construction."""
        self._cron_scheduler = scheduler

    def set_cron_file(self, path: Path) -> None:
        """Set the cron.md file path for add/remove operations."""
        self._cron_file = path

    def set_file_writer(self, writer: FileWriter) -> None:
        """Inject FileWriter to mark agent writes on cron.md."""
        self._file_writer = writer

    def execute(
        self,
        input_text: str,
        args: dict,
        context: SkillContext,
    ) -> SkillResult:
        if not self._cron_scheduler:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_not_configured"),
            )

        parts = input_text.strip().split(None, 1)
        subcmd = parts[0].lower() if parts else ""
        sub_args = parts[1] if len(parts) > 1 else ""

        if not subcmd:
            return self._cmd_list()

        dispatch = {
            "status": lambda: self._cmd_status(),
            "next": lambda: self._cmd_next(sub_args),
            "pause": lambda: self._cmd_pause(sub_args),
            "resume": lambda: self._cmd_resume(sub_args),
            "run": lambda: self._cmd_run(sub_args),
            "test": lambda: self._cmd_test(sub_args),
            "validate": lambda: self._cmd_validate(),
            "history": lambda: self._cmd_history(sub_args),
            "add": lambda: self._cmd_add(sub_args),
            "remove": lambda: self._cmd_remove(sub_args),
        }
        handler = dispatch.get(subcmd)
        if handler:
            return handler()

        return SkillResult(
            success=False, output="",
            error=t("error.cron_unknown_subcommand", subcmd=subcmd),
        )

    # ── /cron (list) ──────────────────────────────────────────────

    def _cmd_list(self) -> SkillResult:
        """List all registered cron jobs with next run time."""
        assert self._cron_scheduler is not None
        states = self._cron_scheduler.get_all_states()

        if not states:
            return SkillResult(
                success=True,
                output=t("output.cron.list_empty"),
            )

        lines = [t("output.cron.list_header", count=len(states))]
        lines.append(
            "| ID | Command | Status | Next Run |",
        )
        lines.append("|---|---|---|---|")

        for jid, state in sorted(states.items()):
            status = state.status.value
            next_run = (
                state.next_run.strftime("%Y-%m-%d %H:%M")
                if state.next_run
                else "-"
            )
            cmd = state.job.command
            lines.append(f"| `{jid}` | `{cmd}` | {status} | {next_run} |")

        return SkillResult(success=True, output="\n".join(lines))

    # ── /cron status ──────────────────────────────────────────────

    def _cmd_status(self) -> SkillResult:
        """List jobs with detailed statistics."""
        assert self._cron_scheduler is not None
        states = self._cron_scheduler.get_all_states()

        if not states:
            return SkillResult(
                success=True,
                output=t("output.cron.list_empty"),
            )

        total_runs = sum(s.run_count for s in states.values())
        total_fails = sum(s.fail_count for s in states.values())
        active = sum(
            1 for s in states.values()
            if s.status.value == "active"
        )
        paused = sum(
            1 for s in states.values()
            if s.status.value == "paused"
        )

        lines = [
            t(
                "output.cron.status_summary",
                total=len(states),
                active=active,
                paused=paused,
                runs=total_runs,
                fails=total_fails,
            ),
        ]
        lines.append("")
        lines.append(
            "| ID | Command | Status | Runs | Fails | Next Run |",
        )
        lines.append("|---|---|---|---|---|---|")

        for jid, state in sorted(states.items()):
            status = state.status.value
            next_run = (
                state.next_run.strftime("%Y-%m-%d %H:%M")
                if state.next_run
                else "-"
            )
            cmd = state.job.command
            lines.append(
                f"| `{jid}` | `{cmd}` | {status}"
                f" | {state.run_count}"
                f" | {state.fail_count}"
                f" | {next_run} |",
            )

        return SkillResult(success=True, output="\n".join(lines))

    # ── /cron next [N] ────────────────────────────────────────────

    def _cmd_next(self, sub_args: str) -> SkillResult:
        """Preview next N fire times for all active jobs."""
        assert self._cron_scheduler is not None
        states = self._cron_scheduler.get_all_states()

        count = 5
        if sub_args.strip().isdigit():
            count = min(int(sub_args.strip()), 20)

        if not states:
            return SkillResult(
                success=True,
                output=t("output.cron.list_empty"),
            )

        lines = [
            t("output.cron.next_header", count=count),
        ]
        lines.append("| # | Time | Job | Command |")
        lines.append("|---|---|---|---|")

        # Collect upcoming fire times across all active jobs
        upcoming: list[tuple[datetime, str, str]] = []
        now = datetime.now()

        for jid, state in states.items():
            if state.status.value != "active":
                continue
            sched = state.job.schedule
            cursor = now
            for _ in range(count):
                from chatmd.engine.cron_parser import CronExpr, EveryExpr

                if isinstance(sched, CronExpr):
                    nxt = sched.next_fire(cursor)
                elif isinstance(sched, EveryExpr):
                    nxt = sched.next_fire(
                        cursor,
                        last_run=state.last_run,
                    )
                else:
                    break  # pragma: no cover
                upcoming.append((nxt, jid, state.job.command))
                cursor = nxt

        # Sort by time and take top N
        upcoming.sort(key=lambda x: x[0])
        for i, (fire_time, jid, cmd) in enumerate(upcoming[:count], 1):
            time_str = fire_time.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"| {i} | {time_str} | `{jid}` | `{cmd}` |")

        return SkillResult(success=True, output="\n".join(lines))

    # ── /cron pause <ID> ──────────────────────────────────────────

    def _cmd_pause(self, sub_args: str) -> SkillResult:
        """Pause a cron job."""
        assert self._cron_scheduler is not None
        job_id = sub_args.strip()
        if not job_id:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_missing_id"),
            )
        if self._cron_scheduler.pause(job_id):
            return SkillResult(
                success=True,
                output=t("output.cron.paused", job_id=job_id),
            )
        return SkillResult(
            success=False, output="",
            error=t("error.cron_job_not_found", job_id=job_id),
        )

    # ── /cron resume <ID> ─────────────────────────────────────────

    def _cmd_resume(self, sub_args: str) -> SkillResult:
        """Resume a paused cron job."""
        assert self._cron_scheduler is not None
        job_id = sub_args.strip()
        if not job_id:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_missing_id"),
            )
        if self._cron_scheduler.resume(job_id):
            return SkillResult(
                success=True,
                output=t("output.cron.resumed", job_id=job_id),
            )
        return SkillResult(
            success=False, output="",
            error=t("error.cron_job_not_found", job_id=job_id),
        )

    # ── /cron run <ID> ────────────────────────────────────────────

    def _cmd_run(self, sub_args: str) -> SkillResult:
        """Manually trigger a cron job."""
        assert self._cron_scheduler is not None
        job_id = sub_args.strip()
        if not job_id:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_missing_id"),
            )
        state = self._cron_scheduler.get_state(job_id)
        if not state:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_job_not_found", job_id=job_id),
            )
        # Execute synchronously via the scheduler's executor
        executor = self._cron_scheduler._executor
        if executor:
            try:
                executor(state.job.command, job_id)
            except Exception as exc:
                return SkillResult(
                    success=False, output="",
                    error=str(exc),
                )
        return SkillResult(
            success=True,
            output=t("output.cron.run_triggered", job_id=job_id),
        )

    # ── /cron test <ID> ───────────────────────────────────────────

    def _cmd_test(self, sub_args: str) -> SkillResult:
        """Test-execute a cron job (dry run, marked as TEST)."""
        assert self._cron_scheduler is not None
        job_id = sub_args.strip()
        if not job_id:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_missing_id"),
            )
        state = self._cron_scheduler.get_state(job_id)
        if not state:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_job_not_found", job_id=job_id),
            )
        # Execute via executor, mark as TEST
        executor = self._cron_scheduler._executor
        if executor:
            try:
                executor(state.job.command, job_id)
            except Exception as exc:
                return SkillResult(
                    success=False, output="",
                    error=str(exc),
                )
        return SkillResult(
            success=True,
            output=t("output.cron.test_complete", job_id=job_id),
        )

    # ── /cron validate ────────────────────────────────────────────

    def _cmd_validate(self) -> SkillResult:
        """Validate all registered cron jobs."""
        assert self._cron_scheduler is not None
        states = self._cron_scheduler.get_all_states()

        if not states:
            return SkillResult(
                success=True,
                output=t("output.cron.list_empty"),
            )

        lines = [t("output.cron.validate_header", count=len(states))]
        for jid, state in sorted(states.items()):
            lines.append(f"- ✅ `{jid}`: `{state.job.command}` — valid")

        return SkillResult(success=True, output="\n".join(lines))

    # ── /cron history [ID] ────────────────────────────────────────

    def _cmd_history(self, sub_args: str) -> SkillResult:
        """Show execution history."""
        assert self._cron_scheduler is not None
        job_id = sub_args.strip() or None
        records = self._cron_scheduler.get_history(job_id=job_id, limit=20)

        if not records:
            return SkillResult(
                success=True,
                output=t("output.cron.history_empty"),
            )

        lines = [t("output.cron.history_header", count=len(records))]
        lines.append("| Time | Job | Command | Status |")
        lines.append("|---|---|---|---|")

        for rec in records:
            status_icon = "✅" if rec.get("status") == "success" else "❌"
            lines.append(
                f"| {rec.get('time', '-')} | `{rec.get('job_id', '-')}` "
                f"| `{rec.get('command', '-')}` | {status_icon} |",
            )

        return SkillResult(success=True, output="\n".join(lines))

    # ── /cron add <expr> <cmd> ────────────────────────────────────

    def _cmd_add(self, sub_args: str) -> SkillResult:
        """Add a cron task to cron.md."""
        assert self._cron_scheduler is not None
        tokens = sub_args.strip().split()
        if len(tokens) < 2:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_add_usage"),
            )
        # Determine expression vs command
        if tokens[0].startswith("@"):
            expr = tokens[0]
            command = " ".join(tokens[1:])
        elif len(tokens) >= 6:
            # 5-field cron: first 5 are the expression
            expr = " ".join(tokens[:5])
            command = " ".join(tokens[5:])
        else:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_add_usage"),
            )

        if not command:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_add_usage"),
            )

        from chatmd.engine.cron_safety import is_dangerous_command

        if is_dangerous_command(command):
            return SkillResult(
                success=False, output="",
                error=t("error.cron_dangerous_command", command=command),
            )

        if not self._cron_file:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_no_file"),
            )

        # Append to cron.md
        line = f"{expr}   {command}"
        cron_file = self._cron_file
        if cron_file.exists():
            content = cron_file.read_text(encoding="utf-8")
            marker = "```cron"
            end_marker = "```\n"
            if marker in content:
                idx = content.rfind(end_marker)
                if idx > content.find(marker):
                    content = (
                        content[:idx] + line + "\n" + content[idx:]
                    )
                    cron_file.write_text(content, encoding="utf-8")
                else:
                    content += f"\n{line}\n"
                    cron_file.write_text(content, encoding="utf-8")
            else:
                content += f"\n```cron\n{line}\n```\n"
                cron_file.write_text(content, encoding="utf-8")
        else:
            cron_file.write_text(
                f"# Cron Tasks\n\n```cron\n{line}\n```\n",
                encoding="utf-8",
            )

        return SkillResult(
            success=True,
            output=t("output.cron.added", expr=expr, command=command),
        )

    # ── /cron remove <ID> ─────────────────────────────────────────

    def _cmd_remove(self, sub_args: str) -> SkillResult:
        """Remove a cron job: unregister from scheduler + comment out in cron.md."""
        assert self._cron_scheduler is not None
        job_id = sub_args.strip()
        if not job_id:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_missing_id"),
            )
        state = self._cron_scheduler.get_state(job_id)
        if not state:
            return SkillResult(
                success=False, output="",
                error=t("error.cron_job_not_found", job_id=job_id),
            )
        raw_line = state.job.raw_line
        self._cron_scheduler.unregister(job_id)
        self._comment_out_in_cron_file(raw_line)
        return SkillResult(
            success=True,
            output=t("output.cron.removed", job_id=job_id),
        )

    def _comment_out_in_cron_file(self, raw_line: str) -> None:
        """Comment out a matching line in cron.md (preserves history)."""
        if not self._cron_file or not self._cron_file.exists():
            return

        content = self._cron_file.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        matched = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Strip existing inline status comments for matching
            clean = re.sub(r"\s+#\s*\[cron-[a-f0-9]+\].*$", "", stripped)
            clean = re.sub(r"\s+#\s*\u274c.*$", "", clean).strip()
            if clean == raw_line:
                # Preserve leading whitespace, add # comment prefix
                leading = len(line) - len(line.lstrip())
                lines[i] = line[:leading] + "# " + line[leading:]
                matched = True
                break

        if matched:
            if self._file_writer:
                self._file_writer._mark_agent_write(self._cron_file)
            try:
                self._cron_file.write_text("".join(lines), encoding="utf-8")
            finally:
                if self._file_writer:
                    self._file_writer._unmark_agent_write(self._cron_file)
