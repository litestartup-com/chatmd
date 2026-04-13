"""PO Simulated Validation — zero-mock, real file I/O end-to-end tests (R-055).

Simulates what a PO would do manually after each release:
  1. chatmd init --mode=full  → verify dir structure + agent.yaml
  2. Cron full lifecycle       → parse → register → execute → inline writeback
  3. Notification pipeline     → FileChannel → notification.md format
  4. /cron skill commands      → add/list/pause/resume/run/test/validate/history/remove
  5. Safety blacklist          → dangerous commands rejected by /cron add
  6. Auto-pause on failures    → consecutive_failures > threshold → paused
  7. Cron persistence          → save → load → restore → data consistency
  8. /help three levels        → overview → group detail → single command detail
  9. /confirm skill flow       → confirm/list/cancel (R-040)
 10. Confirmation gate         → Agent intercepts commands needing confirmation
 11. Custom skill plugin       → auto-discover → load → execute → teardown
 12. /notify skill             → send notification via skill command

Run:  pytest tests/test_po_validation.py -v
"""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from chatmd.cli import main
from chatmd.engine.agent import Agent
from chatmd.engine.confirm import ConfirmationWindow
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
from chatmd.skills.confirm import ConfirmSkill
from chatmd.skills.cron import CronSkill
from chatmd.skills.loader import load_plugin_skills, load_skills_config

# ─── helpers ────────────────────────────────────────────────────────


def _ctx(ws: Path) -> SkillContext:
    """Build a SkillContext pointing at chatmd/chat.md."""
    return SkillContext(
        source_file=ws / "chatmd" / "chat.md",
        source_line=1,
        workspace=ws,
    )


def _init_full_workspace(tmp_path: Path) -> Path:
    """Run `chatmd init --no-git` and return workspace path."""
    ws = tmp_path / "workspace"
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(ws), "--no-git"])
    assert result.exit_code == 0, f"chatmd init failed: {result.output}"
    return ws


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ═════════════════════════════════════════════════════════════════════
# Scenario 1: chatmd init --mode=full → verify directory & config
# ═════════════════════════════════════════════════════════════════════


class TestPoInitWorkspace:
    """PO: chatmd init → check directory structure and agent.yaml content."""

    def test_init_and_verify_structure(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)

        # ── directory structure ──
        assert (ws / ".chatmd").is_dir(), ".chatmd/ not created"
        assert (ws / ".chatmd" / "agent.yaml").exists(), "agent.yaml missing"
        assert (ws / ".chatmd" / "user.yaml").exists(), "user.yaml missing"
        for sub in ("skills", "memory", "logs", "history", "state"):
            assert (ws / ".chatmd" / sub).is_dir(), f".chatmd/{sub}/ missing"

        # ── interaction_dir default = chatmd ──
        assert (ws / "chatmd").is_dir(), "chatmd/ subdir not created"
        assert (ws / "chatmd" / "chat.md").exists(), "chatmd/chat.md missing"
        assert (ws / "chatmd" / "chat").is_dir(), "chatmd/chat/ missing"

        # ── agent.yaml content ──
        cfg = _read_yaml(ws / ".chatmd" / "agent.yaml")
        assert "workspace" not in cfg, "workspace section should not exist in new config"
        assert cfg.get("cron", {}).get("enabled") is True, "cron.enabled should be True"
        assert cfg.get("cron", {}).get("cron_file") == "cron.md", "cron_file should be cron.md"

        # ── user.yaml content ──
        ucfg = _read_yaml(ws / ".chatmd" / "user.yaml")
        assert "language" in ucfg, "user.yaml missing language"
        assert "aliases" in ucfg, "user.yaml missing aliases"

        # ── chat.md has welcome content ──
        content = (ws / "chatmd" / "chat.md").read_text(encoding="utf-8")
        assert "---" in content, "chat.md missing separator"


# ═════════════════════════════════════════════════════════════════════
# Scenario 2: Cron full lifecycle
# ═════════════════════════════════════════════════════════════════════


class TestPoCronFullLifecycle:
    """PO: write cron.md → parse → register → execute → inline writeback."""

    def test_cron_lifecycle(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        cron_md = ws / "chatmd" / "cron.md"

        # Step 1: Write cron.md with two jobs
        cron_md.write_text(
            "# Cron Tasks\n\n"
            "```cron\n"
            "@hourly   /date\n"
            "0 9 * * * /ask daily report\n"
            "```\n",
            encoding="utf-8",
        )

        # Step 2: Parse
        parser = CronParser()
        jobs = parser.parse_file(cron_md)
        assert len(jobs) == 2, f"Expected 2 jobs, got {len(jobs)}"

        for job in jobs:
            assert job.job_id, "job_id should not be empty"
            assert job.command, "command should not be empty"

        # Step 3: Register
        sched = CronScheduler()
        sched.sync_jobs(jobs)
        states = sched.get_all_states()
        assert len(states) == 2, f"Expected 2 states, got {len(states)}"

        # Step 4: Verify state details
        for jid, st in states.items():
            assert st.status.value in ("active", "paused"), f"Unexpected status: {st.status}"
            assert st.next_run is not None, f"Job {jid} has no next_run"

        # Step 5: Inline writeback
        inline_data = {}
        for jid, st in states.items():
            inline_data[jid] = {
                "status": st.status,
                "next_run_str": st.next_run.strftime("%Y-%m-%d %H:%M") if st.next_run else "",
                "raw_line": [j for j in jobs if j.job_id == jid][0].raw_line,
            }
        modified = write_inline_status(cron_md, inline_data)
        assert modified, "Inline status should have modified cron.md"

        content = cron_md.read_text(encoding="utf-8")
        for jid in states:
            assert f"[{jid}]" in content, f"Job ID {jid} annotation missing from cron.md"
            assert "✅" in content or "⏸" in content, "Status icon missing"


# ═════════════════════════════════════════════════════════════════════
# Scenario 3: Notification pipeline
# ═════════════════════════════════════════════════════════════════════


class TestPoNotification:
    """PO: send notifications → verify notification.md format."""

    def test_notification_pipeline(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        notif_path = ws / "chatmd" / "notification.md"

        mgr = NotificationManager()
        mgr.add_channel(FileChannel(notif_path))
        mgr.add_channel(SystemChannel(enabled=False))

        # Send error notification with actions
        mgr.notify(
            title="Cron task failed",
            body="Job `cron-a1b2` command `/sync` exited with error",
            level="error",
            source="cron",
            actions=["/cron run cron-a1b2", "/cron history cron-a1b2"],
        )

        # Send warning
        mgr.notify(
            title="Cron auto-paused",
            body="Job `cron-c3d4` paused after 5 consecutive failures",
            level="warning",
            source="cron",
        )

        # Send info
        mgr.notify(
            title="Missed jobs detected",
            body="2 jobs were missed during downtime",
            level="info",
            source="cron",
        )

        assert notif_path.exists(), "notification.md was not created"
        content = notif_path.read_text(encoding="utf-8")

        # Verify icons
        assert "❌" in content, "Error icon missing"
        assert "⚠️" in content, "Warning icon missing"
        assert "ℹ️" in content, "Info icon missing"

        # Verify titles
        assert "Cron task failed" in content, "Error title missing"
        assert "Cron auto-paused" in content, "Warning title missing"
        assert "Missed jobs detected" in content, "Info title missing"

        # Verify actions
        assert "/cron run cron-a1b2" in content, "Action command missing"


# ═════════════════════════════════════════════════════════════════════
# Scenario 4: /cron skill full subcommand flow
# ═════════════════════════════════════════════════════════════════════


class TestPoCronSkillCommands:
    """PO: /cron add → list → pause → resume → run → test → validate → history → remove."""

    def test_full_cron_management(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        cron_md = ws / "chatmd" / "cron.md"
        cron_md.write_text("# Cron\n\n```cron\n```\n", encoding="utf-8")

        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_md)
        ctx = _ctx(ws)

        # 1. Add a job
        r = skill.execute("add @hourly /date", {}, ctx)
        assert r.success, f"/cron add failed: {r.error}"
        content = cron_md.read_text(encoding="utf-8")
        assert "@hourly" in content, "cron.md missing @hourly after add"

        # Re-parse and sync to scheduler
        jobs = CronParser().parse_file(cron_md)
        sched.sync_jobs(jobs)
        assert len(sched.get_all_states()) >= 1, "No jobs registered after add"
        jid = list(sched.get_all_states().keys())[0]

        # 2. List
        r = skill.execute("", {}, ctx)
        assert r.success, f"/cron list failed: {r.error}"
        assert jid in r.output, f"Job {jid} not in list output"

        # 3. Status
        r = skill.execute("status", {}, ctx)
        assert r.success, f"/cron status failed: {r.error}"

        # 4. Next
        r = skill.execute("next", {}, ctx)
        assert r.success, f"/cron next failed: {r.error}"

        # 5. Pause
        r = skill.execute(f"pause {jid}", {}, ctx)
        assert r.success, f"/cron pause failed: {r.error}"
        assert sched.get_state(jid).status.value == "paused", "Job should be paused"

        # 6. Resume
        r = skill.execute(f"resume {jid}", {}, ctx)
        assert r.success, f"/cron resume failed: {r.error}"
        assert sched.get_state(jid).status.value == "active", "Job should be active"

        # 7. Run (manual trigger)
        r = skill.execute(f"run {jid}", {}, ctx)
        assert r.success, f"/cron run failed: {r.error}"

        # 8. Test
        r = skill.execute(f"test {jid}", {}, ctx)
        assert r.success, f"/cron test failed: {r.error}"

        # 9. Validate
        r = skill.execute("validate", {}, ctx)
        assert r.success, f"/cron validate failed: {r.error}"

        # 10. History
        r = skill.execute("history", {}, ctx)
        assert r.success, f"/cron history failed: {r.error}"

        # 11. Remove
        r = skill.execute(f"remove {jid}", {}, ctx)
        assert r.success, f"/cron remove failed: {r.error}"
        assert sched.get_state(jid) is None, "Job should be removed"


# ═════════════════════════════════════════════════════════════════════
# Scenario 5: Safety blacklist
# ═════════════════════════════════════════════════════════════════════


class TestPoSafetyBlacklist:
    """PO: dangerous commands rejected by /cron add."""

    def test_dangerous_commands_rejected(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        cron_md = ws / "chatmd" / "cron.md"
        cron_md.write_text("# Cron\n", encoding="utf-8")

        sched = CronScheduler()
        skill = CronSkill(cron_scheduler=sched)
        skill.set_cron_file(cron_md)
        ctx = _ctx(ws)

        # /upload is dangerous
        r = skill.execute("add @hourly /upload", {}, ctx)
        assert not r.success, "/upload should be rejected"

        # /new is dangerous
        r = skill.execute("add @hourly /new", {}, ctx)
        assert not r.success, "/new should be rejected"

        # /upgrade is dangerous
        r = skill.execute("add @hourly /upgrade", {}, ctx)
        assert not r.success, "/upgrade should be rejected"

        # /date is safe — should succeed
        r = skill.execute("add @hourly /date", {}, ctx)
        assert r.success, f"/date should be allowed: {r.error}"


# ═════════════════════════════════════════════════════════════════════
# Scenario 6: Auto-pause on consecutive failures
# ═════════════════════════════════════════════════════════════════════


class TestPoAutoPause:
    """PO: consecutive failures > threshold → auto pause."""

    def test_auto_pause_triggers(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        cron_md = ws / "chatmd" / "cron.md"
        cron_md.write_text(
            "# Cron\n\n```cron\n@hourly /sync\n```\n",
            encoding="utf-8",
        )

        sched = CronScheduler()
        jobs = CronParser().parse_file(cron_md)
        sched.sync_jobs(jobs)
        jid = jobs[0].job_id

        # Below threshold: should NOT pause
        sched.get_state(jid).consecutive_failures = 4
        paused = auto_pause_on_failures(sched, max_failures=5)
        assert jid not in paused, "Should NOT pause at 4 failures (threshold=5)"

        # Above threshold: SHOULD pause
        sched.get_state(jid).consecutive_failures = 6
        paused = auto_pause_on_failures(sched, max_failures=5)
        assert jid in paused, "Should pause at 6 failures (threshold=5)"


# ═════════════════════════════════════════════════════════════════════
# Scenario 7: Cron persistence
# ═════════════════════════════════════════════════════════════════════


class TestPoCronPersistence:
    """PO: save state → new scheduler → restore → verify data consistency."""

    def test_persist_and_restore(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        state_path = ws / ".chatmd" / "state" / "cron_state.json"
        cron_md = ws / "chatmd" / "cron.md"
        cron_md.write_text(
            "# Cron\n\n```cron\n@hourly /date\n0 9 * * * /ask daily\n```\n",
            encoding="utf-8",
        )

        # Parse and register
        jobs = CronParser().parse_file(cron_md)
        sched1 = CronScheduler()
        sched1.sync_jobs(jobs)

        # Modify state
        j1, j2 = jobs[0].job_id, jobs[1].job_id
        sched1.get_state(j1).run_count = 42
        sched1.get_state(j2).consecutive_failures = 3

        # Save
        save_cron_state(state_path, sched1.get_all_states())
        assert state_path.exists(), "cron_state.json was not created"

        # New scheduler + restore
        sched2 = CronScheduler()
        sched2.sync_jobs(jobs)
        loaded = load_cron_state(state_path)
        restore_scheduler_state(sched2, loaded)

        # Verify
        assert sched2.get_state(j1).run_count == 42, \
            f"Expected run_count=42, got {sched2.get_state(j1).run_count}"
        assert sched2.get_state(j2).consecutive_failures == 3, \
            f"Expected failures=3, got {sched2.get_state(j2).consecutive_failures}"


# ═════════════════════════════════════════════════════════════════════
# Scenario 8: /help three levels
# ═════════════════════════════════════════════════════════════════════


class TestPoHelpRefactored:
    """PO: /help → /help <group> → /help <cmd> → /help nonexistent."""

    def test_help_three_levels(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        agent = Agent(ws)
        help_skill = agent.router.get_skill("help")
        ctx = _ctx(ws)

        # ── Level 1: Overview ──
        r = help_skill.execute("", {}, ctx)
        assert r.success, f"/help overview failed: {r.error}"
        # Should show group names
        assert "Date & Time" in r.output, "Overview missing 'Date & Time' group"
        # Should have hint
        assert "/help" in r.output, "Overview missing '/help <group>' hint"

        # ── Level 2: Group detail ──
        r = help_skill.execute("datetime", {}, ctx)
        assert r.success, f"/help datetime failed: {r.error}"
        assert "`/date`" in r.output, "Group detail missing /date command"

        # ── Level 3: Single command detail ──
        r = help_skill.execute("date", {}, ctx)
        assert r.success, f"/help date failed: {r.error}"
        assert "## /date" in r.output, "Command detail missing ## /date header"

        # ── Nonexistent ──
        r = help_skill.execute("nonexistent_xyz", {}, ctx)
        assert not r.success, "/help nonexistent should fail"


# ═════════════════════════════════════════════════════════════════════
# Scenario 9: /confirm skill flow (R-040)
# ═════════════════════════════════════════════════════════════════════


class TestPoConfirmSkillFlow:
    """PO: /confirm → list → confirm by ID → nothing pending."""

    def test_confirm_full_flow(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        ctx = _ctx(ws)

        cw = ConfirmationWindow(enabled=True, commands=["/sync", "/new"])
        skill = ConfirmSkill(confirmation_window=cw)

        # 1. Nothing pending initially
        r = skill.execute("", {}, ctx)
        assert r.success, f"/confirm empty failed: {r.error}"
        assert "pending" in r.output.lower() or "confirm" in r.output.lower()

        # 2. Add two pending confirmations
        executed = []
        p1 = cw.request_confirmation(
            command_text="/sync",
            source_file=ws / "chatmd" / "chat.md",
            source_line=5,
            callback=lambda: executed.append("sync"),
        )
        cw.request_confirmation(
            command_text="/new session",
            source_file=ws / "chatmd" / "chat.md",
            source_line=10,
            callback=lambda: executed.append("new"),
        )

        # 3. List pending — should show both
        r = skill.execute("list", {}, ctx)
        assert r.success, f"/confirm list failed: {r.error}"
        assert "/sync" in r.output, "Missing /sync in list"
        assert "/new" in r.output, "Missing /new in list"

        # 4. Confirm specific by ID
        r = skill.execute(f"#{p1.confirm_id}", {}, ctx)
        assert r.success, f"/confirm by ID failed: {r.error}"
        assert executed == ["sync"], f"Expected sync executed, got {executed}"

        # 5. Confirm latest (should be p2)
        r = skill.execute("", {}, ctx)
        assert r.success
        assert executed == ["sync", "new"], f"Expected both executed, got {executed}"

        # 6. Cancel flow
        p3 = cw.request_confirmation(
            command_text="/upload test.png",
            source_file=ws / "chatmd" / "chat.md",
            source_line=15,
            callback=lambda: executed.append("upload"),
        )
        assert cw.cancel(p3.confirm_id), "Cancel should succeed"
        assert len(cw.list_pending()) == 0, "Should have no pending after cancel"

    def test_confirm_marker_format(self, tmp_path: Path) -> None:
        """Confirmation marker contains command name and ID."""
        cw = ConfirmationWindow(enabled=True, commands=["/sync"])
        marker = cw.confirmation_marker("confirm-42", "/sync")
        assert "confirm-42" in marker
        assert "/sync" in marker
        assert "/confirm" in marker
        assert "auto-execute" not in marker


# ═════════════════════════════════════════════════════════════════════
# Scenario 10: Confirmation gate — Agent integration
# ═════════════════════════════════════════════════════════════════════


class TestPoConfirmationGate:
    """PO: Agent intercepts commands in confirm.commands list."""

    def test_agent_has_confirmation_window(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        agent = Agent(ws)
        assert hasattr(agent, "_confirmation_window")
        assert isinstance(agent._confirmation_window, ConfirmationWindow)

    def test_agent_registers_confirm_skill(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        agent = Agent(ws)
        confirm_skill = agent.router.get_skill("confirm")
        assert confirm_skill is not None, "/confirm skill not registered"
        assert confirm_skill.name == "confirm"

    def test_agent_confirm_aliases(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        agent = Agent(ws)
        # /y and /yes should route to confirm skill via aliases
        from chatmd.engine.parser import Parser
        parser = Parser()
        for alias in ("y", "yes"):
            cmds = parser.parse_lines([f"/{alias}"])
            assert len(cmds) == 1, f"/{alias} not parsed"
            skill, _ = agent.router.route(cmds[0])
            assert skill.name == "confirm", f"/{alias} should resolve to confirm"

    def test_confirm_config_from_init(self, tmp_path: Path) -> None:
        """Default init workspace has trigger.confirm in agent.yaml."""
        ws = _init_full_workspace(tmp_path)
        cfg = _read_yaml(ws / ".chatmd" / "agent.yaml")
        confirm = cfg.get("trigger", {}).get("confirm", {})
        assert "enabled" in confirm, "trigger.confirm.enabled missing"
        assert "commands" in confirm, "trigger.confirm.commands missing"
        assert isinstance(confirm["commands"], list)

    def test_needs_confirmation_disabled_by_default(self, tmp_path: Path) -> None:
        """Default config has confirm.enabled=false, no commands intercepted."""
        ws = _init_full_workspace(tmp_path)
        agent = Agent(ws)
        assert not agent._confirmation_window.enabled
        assert not agent._confirmation_window.needs_confirmation("/sync")


# ═════════════════════════════════════════════════════════════════════
# Scenario 11: Custom skill plugin loading
# ═════════════════════════════════════════════════════════════════════


class TestPoCustomSkillPlugin:
    """PO: write a custom skill → auto-discover → load → execute."""

    def test_auto_discover_custom_skill(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        skills_dir = ws / ".chatmd" / "skills"
        skills_dir.mkdir(exist_ok=True)

        # Write a minimal custom skill
        skill_code = (
            "from chatmd.skills.base import Skill, SkillContext, SkillResult\n\n"
            "class PingSkill(Skill):\n"
            "    name = 'ping'\n"
            "    description = 'ping'\n"
            "    category = 'custom'\n"
            "    aliases = []\n\n"
            "    def execute(self, input_text, args, context):\n"
            "        return SkillResult(success=True, output='pong')\n"
        )
        (skills_dir / "ping_skill.py").write_text(skill_code, encoding="utf-8")

        # Load with auto-discover
        config = load_skills_config(ws / ".chatmd")
        assert config.discover == "auto"

        ctx = SkillContext(
            source_file=ws / "chatmd" / "chat.md",
            source_line=1,
            workspace=ws,
        )
        skills = load_plugin_skills(skills_dir, config, context=ctx)
        assert len(skills) >= 1, f"Expected at least 1 plugin, got {len(skills)}"

        ping = [s for s in skills if s.name == "ping"]
        assert len(ping) == 1, "PingSkill not found in loaded plugins"

        # Execute
        r = ping[0].execute("", {}, ctx)
        assert r.success
        assert r.output == "pong"

    def test_manual_mode_skips_unlisted(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        skills_dir = ws / ".chatmd" / "skills"
        skills_dir.mkdir(exist_ok=True)

        # Write a skill
        skill_code = (
            "from chatmd.skills.base import Skill, SkillContext, SkillResult\n\n"
            "class FooSkill(Skill):\n"
            "    name = 'foo'\n"
            "    description = 'foo'\n"
            "    category = 'custom'\n"
            "    aliases = []\n\n"
            "    def execute(self, input_text, args, context):\n"
            "        return SkillResult(success=True, output='bar')\n"
        )
        (skills_dir / "foo_skill.py").write_text(skill_code, encoding="utf-8")

        # Write skills.yaml with manual mode, no plugins listed
        skills_yaml = {"discover": "manual", "plugins": {}}
        with open(ws / ".chatmd" / "skills.yaml", "w", encoding="utf-8") as f:
            yaml.dump(skills_yaml, f)

        config = load_skills_config(ws / ".chatmd")
        assert config.discover == "manual"

        ctx = SkillContext(
            source_file=ws / "chatmd" / "chat.md",
            source_line=1,
            workspace=ws,
        )
        skills = load_plugin_skills(skills_dir, config, context=ctx)
        assert len(skills) == 0, "Manual mode with no plugins should load nothing"


# ═════════════════════════════════════════════════════════════════════
# Scenario 12: /notify skill
# ═════════════════════════════════════════════════════════════════════


class TestPoNotifySkill:
    """PO: /notify command → sends notification via NotificationManager."""

    def test_notify_via_agent(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        agent = Agent(ws)
        ctx = _ctx(ws)

        notify_skill = agent.router.get_skill("notify")
        assert notify_skill is not None, "/notify skill not registered"

        r = notify_skill.execute("Test reminder", {}, ctx)
        assert r.success, f"/notify failed: {r.error}"

        # Verify notification.md was written
        notif_path = ws / "chatmd" / "notification.md"
        assert notif_path.exists(), "notification.md not created"
        content = notif_path.read_text(encoding="utf-8")
        assert "Test reminder" in content, "Notification message missing"

    def test_notify_empty_message(self, tmp_path: Path) -> None:
        ws = _init_full_workspace(tmp_path)
        agent = Agent(ws)
        ctx = _ctx(ws)

        notify_skill = agent.router.get_skill("notify")
        r = notify_skill.execute("", {}, ctx)
        assert not r.success, "/notify with empty message should fail"
