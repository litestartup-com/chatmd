"""E2E tests for v0.2.2 features — Cron + Notification + /help refactor (T-066)."""

from __future__ import annotations

from pathlib import Path

import yaml

from chatmd.engine.agent import Agent
from chatmd.engine.cron_inline import write_inline_status
from chatmd.engine.cron_parser import CronParser
from chatmd.engine.cron_safety import auto_pause_on_failures
from chatmd.engine.cron_scheduler import CronScheduler
from chatmd.engine.cron_state import (
    load_cron_state,
    restore_scheduler_state,
    save_cron_state,
)
from chatmd.infra.notification import FileChannel, NotificationManager, SystemChannel
from chatmd.skills.base import SkillContext
from chatmd.skills.cron import CronSkill


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _init_ws(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    chatmd_dir = ws / ".chatmd"
    chatmd_dir.mkdir()
    for sub in ("skills", "memory", "logs", "history", "state"):
        (chatmd_dir / sub).mkdir()
    _write_yaml(chatmd_dir / "agent.yaml", {
        "version": "0.1",
        "ai": {"providers": []},
        "cron": {"enabled": True, "cron_file": "cron.md"},
        "notification": {
            "enabled": True,
            "notification_file": "notification.md",
            "system_notify": False,
        },
        "watcher": {
            "debounce_ms": 300,
            "watch_dirs": ["chatmd/"],
        },
    })
    _write_yaml(chatmd_dir / "user.yaml", {"language": "en", "aliases": {}})
    interact = ws / "chatmd"
    interact.mkdir()
    (interact / "chat.md").write_text("# Chat\n\n---\n", encoding="utf-8")
    (interact / "chat").mkdir()
    return ws


def _ctx(ws: Path) -> SkillContext:
    return SkillContext(
        source_file=ws / "chatmd" / "chat.md", source_line=1, workspace=ws,
    )


# ═══════════════════════════════════════════════════════════════════
# E2E: Cron full lifecycle
# ═══════════════════════════════════════════════════════════════════


class TestCronFullLifecycle:
    """End-to-end: parse cron.md → register → execute → persist → restore."""

    def test_parse_register_execute(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        cron_md = ws / "cron.md"
        cron_md.write_text(
            "# Cron\n\n```cron\n@hourly   /date\n```\n",
            encoding="utf-8",
        )
        parser = CronParser()
        jobs = parser.parse_file(cron_md)
        assert len(jobs) == 1

        sched = CronScheduler()
        sched.sync_jobs(jobs)
        assert len(sched.get_all_states()) == 1

    def test_persist_and_restore(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        state_path = ws / ".chatmd" / "state" / "cron_state.json"

        sched1 = CronScheduler()
        cron_md = ws / "cron.md"
        cron_md.write_text(
            "# Cron\n\n```cron\n0 9 * * *   /ask daily\n```\n",
            encoding="utf-8",
        )
        jobs = CronParser().parse_file(cron_md)
        sched1.sync_jobs(jobs)
        st = sched1.get_state(jobs[0].job_id)
        st.run_count = 5

        save_cron_state(state_path, sched1.get_all_states())

        sched2 = CronScheduler()
        sched2.sync_jobs(jobs)
        loaded = load_cron_state(state_path)
        restore_scheduler_state(sched2, loaded)
        assert sched2.get_state(jobs[0].job_id).run_count == 5


# ═══════════════════════════════════════════════════════════════════
# E2E: Notification pipeline
# ═══════════════════════════════════════════════════════════════════


class TestNotificationPipeline:
    """End-to-end: NotificationManager → FileChannel → notification.md."""

    def test_cron_failure_notification(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        notif_path = ws / "notification.md"

        mgr = NotificationManager()
        mgr.add_channel(FileChannel(notif_path))
        mgr.add_channel(SystemChannel(enabled=False))

        mgr.notify(
            title="Cron task failed",
            body="Job `cron-x1` command `/sync` failed",
            level="error",
            source="cron",
            actions=["/cron run cron-x1"],
        )

        content = notif_path.read_text(encoding="utf-8")
        assert "Cron task failed" in content
        assert "/cron run cron-x1" in content
        assert "❌" in content


# ═══════════════════════════════════════════════════════════════════
# E2E: /cron skill full flow
# ═══════════════════════════════════════════════════════════════════


class TestCronSkillFlow:
    """End-to-end: /cron add → list → pause → resume → remove."""

    def test_full_cron_management(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        cron_md = ws / "cron.md"
        cron_md.write_text("# Cron\n\n```cron\n```\n", encoding="utf-8")

        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_md)
        ctx = _ctx(ws)

        # Add
        r = skill.execute("add @hourly /date", {}, ctx)
        assert r.success
        content = cron_md.read_text(encoding="utf-8")
        assert "@hourly" in content

        # Register jobs from file
        jobs = CronParser().parse_file(cron_md)
        sched.sync_jobs(jobs)
        assert len(sched.get_all_states()) >= 1

        jid = list(sched.get_all_states().keys())[0]

        # List
        r = skill.execute("", {}, ctx)
        assert r.success
        assert jid in r.output

        # Pause
        r = skill.execute(f"pause {jid}", {}, ctx)
        assert r.success

        # Resume
        r = skill.execute(f"resume {jid}", {}, ctx)
        assert r.success

        # Remove
        r = skill.execute(f"remove {jid}", {}, ctx)
        assert r.success
        assert sched.get_state(jid) is None


# ═══════════════════════════════════════════════════════════════════
# E2E: /help refactored flow
# ═══════════════════════════════════════════════════════════════════


class TestHelpRefactoredFlow:
    """End-to-end: /help → /help <group> → /help <cmd>."""

    def test_help_three_levels(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        agent = Agent(ws)
        help_skill = agent.router.get_skill("help")
        ctx = _ctx(ws)

        # Overview
        r = help_skill.execute("", {}, ctx)
        assert r.success
        assert "Date & Time" in r.output

        # Group detail
        r = help_skill.execute("datetime", {}, ctx)
        assert r.success
        assert "`/date`" in r.output

        # Single command
        r = help_skill.execute("date", {}, ctx)
        assert r.success
        assert "## /date" in r.output


# ═══════════════════════════════════════════════════════════════════
# E2E: Safety checks
# ═══════════════════════════════════════════════════════════════════


class TestSafetyChecks:
    """Dangerous command blacklist + auto-pause integration."""

    def test_dangerous_blocked_in_add(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        cron_md = ws / "cron.md"
        cron_md.write_text("# Cron\n", encoding="utf-8")

        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_md)

        r = skill.execute("add @hourly /upload", {}, _ctx(ws))
        assert not r.success

    def test_auto_pause_integration(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        cron_md = ws / "cron.md"
        cron_md.write_text(
            "# Cron\n\n```cron\n@hourly /sync\n```\n",
            encoding="utf-8",
        )
        sched = CronScheduler()
        jobs = CronParser().parse_file(cron_md)
        sched.sync_jobs(jobs)

        jid = jobs[0].job_id
        sched.get_state(jid).consecutive_failures = 6
        paused = auto_pause_on_failures(sched, max_failures=5)
        assert jid in paused


# ═══════════════════════════════════════════════════════════════════
# E2E: Inline status writeback
# ═══════════════════════════════════════════════════════════════════


class TestInlineStatusE2E:
    """End-to-end: parse → register → write inline status back."""

    def test_inline_writeback(self, tmp_path: Path) -> None:
        ws = _init_ws(tmp_path)
        cron_md = ws / "cron.md"
        cron_md.write_text(
            "# Cron\n\n```cron\n0 9 * * *   /ask daily\n```\n",
            encoding="utf-8",
        )
        jobs = CronParser().parse_file(cron_md)
        sched = CronScheduler()
        sched.sync_jobs(jobs)

        jid = jobs[0].job_id
        st = sched.get_state(jid)
        next_str = st.next_run.strftime("%Y-%m-%d %H:%M") if st.next_run else ""

        states = {
            jid: {
                "status": "active",
                "next_run_str": next_str,
                "raw_line": jobs[0].raw_line,
            },
        }
        modified = write_inline_status(cron_md, states)
        assert modified
        content = cron_md.read_text(encoding="utf-8")
        assert f"[{jid}]" in content
