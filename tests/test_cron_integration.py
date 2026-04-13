"""Tests for Agent ↔ CronScheduler integration (T-059 / US-024 / F-081~F-082)."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from chatmd.engine.cron_inline import write_inline_status
from chatmd.engine.cron_parser import CronExpr, CronJob, CronParser
from chatmd.engine.cron_scheduler import CronScheduler
from chatmd.infra.config import Config


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _init_workspace(tmp_path: Path) -> Path:
    """Create a minimal ChatMD workspace for integration tests."""
    ws = tmp_path / "ws"
    ws.mkdir()
    chatmd_dir = ws / ".chatmd"
    chatmd_dir.mkdir()
    for sub in ("skills", "memory", "logs", "history", "state"):
        (chatmd_dir / sub).mkdir()
    _write_yaml(chatmd_dir / "agent.yaml", {
        "version": "0.1",
        "ai": {"providers": []},
        "trigger": {"signals": [{"type": "file_save", "debounce_ms": 800}]},
        "watcher": {
            "debounce_ms": 300,
            "watch_dirs": ["chatmd/"],
            "ignore_patterns": ["_index.md"],
        },
        "commands": {"prefix": "/"},
        "async": {"max_concurrent": 3, "timeout": 60},
        "sync": {"mode": "git", "auto_commit": True, "interval": 300},
        "logging": {"level": "INFO", "audit": True},
        "cron": {"enabled": True},
    })
    _write_yaml(chatmd_dir / "user.yaml", {"language": "en"})
    # Create chatmd/ interaction directory
    interact = ws / "chatmd"
    interact.mkdir()
    (interact / "chat.md").write_text("# ChatMD\n\n---\n\n", encoding="utf-8")
    return ws


# ═══════════════════════════════════════════════════════════════════
# Cron config parsing
# ═══════════════════════════════════════════════════════════════════


class TestCronConfig:
    """Cron-related config in agent.yaml."""

    def test_cron_enabled_default(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cfg = Config(ws)
        assert cfg.get("cron.enabled", False) is True

    def test_cron_disabled(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        _write_yaml(ws / ".chatmd" / "agent.yaml", {
            "cron": {"enabled": False},
        })
        cfg = Config(ws)
        assert cfg.get("cron.enabled", True) is False

    def test_cron_source_default(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cfg = Config(ws)
        assert cfg.get("cron.source", "central") == "central"

    def test_cron_file_default(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cfg = Config(ws)
        assert cfg.get("cron.cron_file", "cron.md") == "cron.md"


# ═══════════════════════════════════════════════════════════════════
# Cron file scanning
# ═══════════════════════════════════════════════════════════════════


class TestCronFileScanning:
    """Scan cron.md and register jobs with CronScheduler."""

    def test_scan_cron_md(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cron_md = ws / "cron.md"
        cron_md.write_text(
            "# My cron tasks\n\n"
            "```cron\n"
            "0 9 * * *   /ask daily\n"
            "@hourly     /sync\n"
            "```\n",
            encoding="utf-8",
        )

        jobs = CronParser.parse_file(cron_md)
        sched = CronScheduler()
        for job in jobs:
            sched.register(job)

        states = sched.get_all_states()
        assert len(states) == 2

    def test_scan_empty_cron_md(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cron_md = ws / "cron.md"
        cron_md.write_text("# Empty\n", encoding="utf-8")

        jobs = CronParser.parse_file(cron_md)
        assert len(jobs) == 0

    def test_scan_nonexistent_cron_md(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        jobs = CronParser.parse_file(ws / "cron.md")
        assert len(jobs) == 0

    def test_rescan_updates_jobs(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cron_md = ws / "cron.md"

        # Initial scan with 1 job
        cron_md.write_text("```cron\n0 9 * * *   /ask daily\n```\n", encoding="utf-8")
        jobs = CronParser.parse_file(cron_md)
        sched = CronScheduler()
        sched.sync_jobs(jobs)
        assert len(sched.get_all_states()) == 1

        # Re-scan with 2 jobs
        cron_md.write_text(
            "```cron\n0 9 * * *   /ask daily\n@hourly   /sync\n```\n",
            encoding="utf-8",
        )
        jobs = CronParser.parse_file(cron_md)
        sched.sync_jobs(jobs)
        assert len(sched.get_all_states()) == 2

    def test_rescan_removes_deleted_jobs(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        cron_md = ws / "cron.md"

        cron_md.write_text(
            "```cron\n0 9 * * *  /ask d\n@hourly  /sync\n```\n",
            encoding="utf-8",
        )
        sched = CronScheduler()
        sched.sync_jobs(CronParser.parse_file(cron_md))
        assert len(sched.get_all_states()) == 2

        # Remove one job
        cron_md.write_text("```cron\n0 9 * * *  /ask d\n```\n", encoding="utf-8")
        sched.sync_jobs(CronParser.parse_file(cron_md))
        assert len(sched.get_all_states()) == 1


# ═══════════════════════════════════════════════════════════════════
# Cron log writing
# ═══════════════════════════════════════════════════════════════════


class TestCronLogWriting:
    """Cron execution results written to .chatmd/logs/cron_log.md."""

    def test_cron_log_created(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        log_path = ws / ".chatmd" / "logs" / "cron_log.md"

        from chatmd.engine.cron_log import write_cron_log
        write_cron_log(
            log_path,
            job_id="cron-test01",
            command="/status",
            output="Agent running",
            success=True,
        )
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "cron-test01" in content
        assert "/status" in content
        assert "Agent running" in content

    def test_cron_log_failure(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        log_path = ws / ".chatmd" / "logs" / "cron_log.md"

        from chatmd.engine.cron_log import write_cron_log
        write_cron_log(
            log_path,
            job_id="cron-fail01",
            command="/sync",
            output="Connection failed",
            success=False,
        )
        content = log_path.read_text(encoding="utf-8")
        assert "❌" in content
        assert "cron-fail01" in content

    def test_cron_log_append(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        log_path = ws / ".chatmd" / "logs" / "cron_log.md"

        from chatmd.engine.cron_log import write_cron_log
        write_cron_log(log_path, "cron-a", "/date", "2026-04-08", True)
        write_cron_log(log_path, "cron-b", "/time", "15:00", True)
        content = log_path.read_text(encoding="utf-8")
        assert "cron-a" in content
        assert "cron-b" in content


# ═══════════════════════════════════════════════════════════════════
# Cron file watched by FileWatcher
# ═══════════════════════════════════════════════════════════════════


class TestCronFileWatched:
    """cron.md included in FileWatcher scope."""

    def test_cron_md_covered_by_default_watch_dirs(self, tmp_path: Path) -> None:
        """cron.md is inside chatmd/ which is always watched."""
        ws = _init_workspace(tmp_path)
        _write_yaml(ws / ".chatmd" / "agent.yaml", {
            "cron": {"enabled": True},
        })
        cfg = Config(ws)
        dirs = cfg.resolve_watch_paths()
        assert "chatmd/" in dirs

    def test_cron_path_resolved_via_interaction_path(self, tmp_path: Path) -> None:
        ws = _init_workspace(tmp_path)
        _write_yaml(ws / ".chatmd" / "agent.yaml", {
            "cron": {"enabled": True, "cron_file": "cron.md"},
        })
        cfg = Config(ws)
        assert cfg.interaction_path("cron.md") == ws / "chatmd" / "cron.md"


# ═══════════════════════════════════════════════════════════════════
# CronScheduler executor integration
# ═══════════════════════════════════════════════════════════════════


class TestCronExecutor:
    """CronScheduler executor callback fires and logs results."""

    def test_executor_callback_invoked(self, tmp_path: Path) -> None:
        _init_workspace(tmp_path)

        results = []

        def executor(command: str, job_id: str) -> None:
            results.append((command, job_id))

        sched = CronScheduler(tick_interval=0.05)
        sched.set_executor(executor)

        job = CronJob(
            job_id="cron-exec1",
            schedule=CronExpr.parse("* * * * *"),
            command="/status",
            raw_line="* * * * *   /status",
            source_file=Path("cron.md"),
            source_line_num=2,
        )
        sched.register(job)
        state = sched.get_state(job.job_id)
        state.next_run = datetime.now() - timedelta(seconds=1)

        sched.start()
        time.sleep(0.3)
        sched.stop()

        assert len(results) >= 1
        assert results[0] == ("/status", "cron-exec1")


# ═══════════════════════════════════════════════════════════════════
# Inline status writeback (T-065 / F-097)
# ═══════════════════════════════════════════════════════════════════


class TestCronInlineStatus:
    """write_inline_status writes job ID + next run as inline comments."""

    def test_writeback_adds_comment(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n* * * * * /date\n```\n", encoding="utf-8",
        )
        job_states = {
            "cron-ab12": {
                "status": "active",
                "next_run_str": "2026-04-09 21:00",
                "raw_line": "* * * * * /date",
            },
        }
        assert write_inline_status(cron_file, job_states) is True
        content = cron_file.read_text(encoding="utf-8")
        assert "[cron-ab12]" in content
        assert "2026-04-09 21:00" in content
        assert "✅" in content

    def test_writeback_paused_status(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n0 9 * * * /ask daily\n```\n", encoding="utf-8",
        )
        job_states = {
            "cron-cd34": {
                "status": "paused",
                "next_run_str": "",
                "raw_line": "0 9 * * * /ask daily",
            },
        }
        assert write_inline_status(cron_file, job_states) is True
        content = cron_file.read_text(encoding="utf-8")
        assert "[cron-cd34]" in content
        assert "⏸" in content
        assert "paused" in content

    def test_writeback_idempotent(self, tmp_path: Path) -> None:
        """Second write with same state produces no changes."""
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n* * * * * /date\n```\n", encoding="utf-8",
        )
        job_states = {
            "cron-ab12": {
                "status": "active",
                "next_run_str": "2026-04-09 21:00",
                "raw_line": "* * * * * /date",
            },
        }
        write_inline_status(cron_file, job_states)
        # Second call should return False (no modification)
        assert write_inline_status(cron_file, job_states) is False

    def test_writeback_no_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.md"
        assert write_inline_status(missing, {}) is False


class TestParserStripsInlineComments:
    """Parser must strip inline status comments on re-scan."""

    def test_parse_after_writeback(self, tmp_path: Path) -> None:
        """Parsing a file with inline comments yields same jobs."""
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n* * * * * /date\n```\n", encoding="utf-8",
        )
        jobs_before = CronParser.parse_file(cron_file)
        assert len(jobs_before) == 1

        # Write inline status
        job_states = {
            jobs_before[0].job_id: {
                "status": "active",
                "next_run_str": "2026-04-09 21:00",
                "raw_line": jobs_before[0].raw_line,
            },
        }
        write_inline_status(cron_file, job_states)

        # Re-parse — should get same job_id and command
        jobs_after = CronParser.parse_file(cron_file)
        assert len(jobs_after) == 1
        assert jobs_after[0].job_id == jobs_before[0].job_id
        assert jobs_after[0].command == "/date"
        assert jobs_after[0].raw_line == "* * * * * /date"

    def test_parse_with_error_comment(self, tmp_path: Path) -> None:
        """Lines with error comments are stripped before parsing."""
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n@hourly /sync    # ❌ syntax error\n```\n",
            encoding="utf-8",
        )
        jobs = CronParser.parse_file(cron_file)
        assert len(jobs) == 1
        assert jobs[0].command == "/sync"


class TestSchedulerInlineIntegration:
    """End-to-end: scan → register → build states → writeback."""

    def test_scan_register_writeback(self, tmp_path: Path) -> None:
        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n* * * * * /date\n0 9 * * * /ask daily\n```\n",
            encoding="utf-8",
        )
        jobs = CronParser.parse_file(cron_file)
        assert len(jobs) == 2

        sched = CronScheduler()
        sched.sync_jobs(jobs)

        # Build job_states like agent does
        all_states = sched.get_all_states()
        job_states: dict[str, dict] = {}
        for jid, state in all_states.items():
            next_str = ""
            if state.next_run:
                next_str = state.next_run.strftime("%Y-%m-%d %H:%M:%S")
            job_states[jid] = {
                "status": state.status.value,
                "next_run_str": next_str,
                "raw_line": state.job.raw_line,
            }

        modified = write_inline_status(cron_file, job_states)
        assert modified is True

        content = cron_file.read_text(encoding="utf-8")
        # Both lines should have inline comments
        for jid in job_states:
            assert f"[{jid}]" in content

        # Re-parse should produce identical jobs
        jobs2 = CronParser.parse_file(cron_file)
        assert len(jobs2) == 2
        for j1, j2 in zip(jobs, jobs2):
            assert j1.job_id == j2.job_id
            assert j1.command == j2.command


class TestCronRemoveCommentsOut:
    """Test that /cron remove comments out the line in cron.md."""

    def test_remove_comments_out_plain_line(self, tmp_path: Path) -> None:
        """Removing a job comments out its line in cron.md."""
        from chatmd.skills.cron import CronSkill

        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n* * * * * /date\n@every 5s /ping\n```\n",
            encoding="utf-8",
        )

        jobs = CronParser.parse_file(cron_file)
        assert len(jobs) == 2

        sched = CronScheduler()
        sched.sync_jobs(jobs)

        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_file)

        # Remove the first job (*/date)
        date_job = [j for j in jobs if j.command == "/date"][0]
        result = skill.execute(f"remove {date_job.job_id}", {}, None)
        assert result.success

        content = cron_file.read_text(encoding="utf-8")
        assert "# * * * * * /date" in content
        assert "@every 5s /ping" in content

        # Re-parse should only find 1 job
        remaining = CronParser.parse_file(cron_file)
        assert len(remaining) == 1
        assert remaining[0].command == "/ping"

    def test_remove_comments_out_line_with_inline_status(
        self, tmp_path: Path,
    ) -> None:
        """Removing a job with inline status comments still matches."""
        from chatmd.skills.cron import CronSkill

        cron_file = tmp_path / "cron.md"
        cron_file.write_text(
            "```cron\n"
            "* * * * * /date # [cron-abc123] \u2705 next: 2026-04-10 00:00:00\n"
            "```\n",
            encoding="utf-8",
        )

        jobs = CronParser.parse_file(cron_file)
        assert len(jobs) == 1

        sched = CronScheduler()
        sched.sync_jobs(jobs)

        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_file)

        result = skill.execute(f"remove {jobs[0].job_id}", {}, None)
        assert result.success

        content = cron_file.read_text(encoding="utf-8")
        assert content.count("# ") >= 1
        # Re-parse should find 0 jobs
        remaining = CronParser.parse_file(cron_file)
        assert len(remaining) == 0
