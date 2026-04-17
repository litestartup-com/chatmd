"""Tests for confirmation window + /confirm skill (R-040 — explicit /confirm, no timer)."""

from __future__ import annotations

from pathlib import Path

from chatmd.engine.confirm import ConfirmationWindow
from chatmd.i18n import t
from chatmd.skills.base import SkillContext
from chatmd.skills.confirm import ConfirmSkill


class TestNeedsConfirmation:
    """needs_confirmation() checks enabled flag + commands list."""

    def test_disabled_never_needs_confirmation(self):
        cw = ConfirmationWindow(enabled=False, commands=["/sync", "/upload"])
        assert not cw.needs_confirmation("/sync")
        assert not cw.needs_confirmation("/upload")

    def test_enabled_only_listed_commands(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync", "/upload"])
        assert cw.needs_confirmation("/sync")
        assert cw.needs_confirmation("/upload")
        assert not cw.needs_confirmation("/date")
        assert not cw.needs_confirmation("/help")

    def test_enabled_empty_commands_list(self):
        cw = ConfirmationWindow(enabled=True, commands=[])
        assert not cw.needs_confirmation("/sync")

    def test_default_disabled(self):
        cw = ConfirmationWindow()
        assert not cw.enabled
        assert not cw.needs_confirmation("/anything")


class TestRequestAndCancel:
    """request_confirmation() creates pending; cancel() removes it."""

    def test_request_creates_pending(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync"])
        pending = cw.request_confirmation(
            command_text="/sync",
            source_file=None,
            source_line=1,
            callback=lambda: None,
        )
        assert pending.confirm_id.startswith("confirm-")
        assert len(cw.list_pending()) == 1

    def test_cancel_removes_pending(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync"])
        called = []
        pending = cw.request_confirmation(
            command_text="/sync",
            source_file=None,
            source_line=1,
            callback=lambda: called.append(True),
        )
        assert cw.cancel(pending.confirm_id)
        assert called == []
        assert len(cw.list_pending()) == 0

    def test_cancel_nonexistent(self):
        cw = ConfirmationWindow()
        assert not cw.cancel("nonexistent-id")

    def test_cancel_all(self):
        cw = ConfirmationWindow(enabled=True, commands=["/a", "/b", "/c"])
        for i in range(3):
            cw.request_confirmation(
                command_text=f"/cmd{i}",
                source_file=None,
                source_line=i,
                callback=lambda: None,
            )
        assert len(cw.list_pending()) == 3
        cancelled = cw.cancel_all()
        assert cancelled == 3
        assert len(cw.list_pending()) == 0


class TestConfirmExecution:
    """confirm() executes the pending command callback."""

    def test_confirm_by_id(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync"])
        called = []
        pending = cw.request_confirmation(
            command_text="/sync",
            source_file=None,
            source_line=1,
            callback=lambda: called.append(True),
        )
        result = cw.confirm(pending.confirm_id)
        assert result is not None
        assert result.command_text == "/sync"
        assert called == [True]
        assert len(cw.list_pending()) == 0

    def test_confirm_latest_when_no_id(self):
        cw = ConfirmationWindow(enabled=True, commands=["/a", "/b"])
        calls = []
        cw.request_confirmation(
            command_text="/a", source_file=None, source_line=1,
            callback=lambda: calls.append("a"),
        )
        cw.request_confirmation(
            command_text="/b", source_file=None, source_line=2,
            callback=lambda: calls.append("b"),
        )
        result = cw.confirm()  # No ID → confirm latest (/b)
        assert result is not None
        assert result.command_text == "/b"
        assert calls == ["b"]
        assert len(cw.list_pending()) == 1  # /a still pending

    def test_confirm_nothing_pending(self):
        cw = ConfirmationWindow(enabled=True)
        result = cw.confirm()
        assert result is None

    def test_no_auto_execute(self):
        """Commands never auto-execute — they stay pending indefinitely."""
        cw = ConfirmationWindow(enabled=True, commands=["/sync"])
        called = []
        cw.request_confirmation(
            command_text="/sync",
            source_file=None,
            source_line=1,
            callback=lambda: called.append(True),
        )
        # Without calling confirm(), callback is never invoked
        assert called == []
        assert len(cw.list_pending()) == 1


class TestGetAndList:
    """get_pending() and list_pending() lookups."""

    def test_get_pending(self):
        cw = ConfirmationWindow(enabled=True, commands=["/test"])
        pending = cw.request_confirmation(
            command_text="/test",
            source_file=None,
            source_line=1,
            callback=lambda: None,
        )
        found = cw.get_pending(pending.confirm_id)
        assert found is not None
        assert found.command_text == "/test"
        cw.cancel_all()

    def test_get_pending_not_found(self):
        cw = ConfirmationWindow()
        assert cw.get_pending("nonexistent") is None


class TestConfirmationMarker:
    """confirmation_marker() generates the prompt line."""

    def test_marker_contains_command_and_id(self):
        cw = ConfirmationWindow(enabled=True)
        marker = cw.confirmation_marker("confirm-1", "/sync")
        assert "confirm-1" in marker
        assert "/sync" in marker
        assert "/confirm" in marker

    def test_marker_no_delay_reference(self):
        """New design has no timer/delay concept."""
        cw = ConfirmationWindow(enabled=True)
        marker = cw.confirmation_marker("confirm-1", "/sync")
        assert "auto-execute" not in marker
        assert "delay" not in marker.lower()


class TestEnabledSetter:
    """enabled property can be toggled."""

    def test_toggle_enabled(self):
        cw = ConfirmationWindow(enabled=False)
        assert not cw.enabled
        cw.enabled = True
        assert cw.enabled
        assert cw.needs_confirmation("/sync") is False  # empty commands

    def test_commands_property(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync", "/upload"])
        assert cw.commands == {"/sync", "/upload"}


# ── ConfirmSkill tests ──────────────────────────────────────────────────


def _make_context() -> SkillContext:
    return SkillContext(
        source_file=Path("/tmp/chat.md"),
        source_line=1,
        workspace=Path("/tmp"),
    )


class TestConfirmSkillExecute:
    """ConfirmSkill.execute() dispatches to ConfirmationWindow."""

    def test_confirm_latest(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync"])
        called = []
        cw.request_confirmation(
            command_text="/sync",
            source_file=Path("/tmp/chat.md"),
            source_line=1,
            callback=lambda: called.append(True),
        )
        skill = ConfirmSkill(confirmation_window=cw)
        result = skill.execute("", {}, _make_context())
        assert result.success
        assert called == [True]
        assert result.output == t("confirm.accepted_placeholder")

    def test_confirm_by_id(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync"])
        called = []
        pending = cw.request_confirmation(
            command_text="/sync",
            source_file=Path("/tmp/chat.md"),
            source_line=1,
            callback=lambda: called.append(True),
        )
        skill = ConfirmSkill(confirmation_window=cw)
        result = skill.execute(f"#{pending.confirm_id}", {}, _make_context())
        assert result.success
        assert called == [True]

    def test_confirm_nothing_pending(self):
        cw = ConfirmationWindow(enabled=True)
        skill = ConfirmSkill(confirmation_window=cw)
        result = skill.execute("", {}, _make_context())
        assert result.success
        assert "pending" in result.output.lower() or "confirm" in result.output.lower()

    def test_confirm_no_window(self):
        skill = ConfirmSkill(confirmation_window=None)
        result = skill.execute("", {}, _make_context())
        assert not result.success

    def test_confirm_list(self):
        cw = ConfirmationWindow(enabled=True, commands=["/sync", "/upload"])
        cw.request_confirmation(
            command_text="/sync",
            source_file=Path("/tmp/chat.md"),
            source_line=1,
            callback=lambda: None,
        )
        cw.request_confirmation(
            command_text="/upload img.png",
            source_file=Path("/tmp/chat.md"),
            source_line=3,
            callback=lambda: None,
        )
        skill = ConfirmSkill(confirmation_window=cw)
        result = skill.execute("list", {}, _make_context())
        assert result.success
        assert "/sync" in result.output
        assert "/upload" in result.output

    def test_confirm_list_empty(self):
        cw = ConfirmationWindow(enabled=True)
        skill = ConfirmSkill(confirmation_window=cw)
        result = skill.execute("list", {}, _make_context())
        assert result.success


class TestConfirmSkillMeta:
    """ConfirmSkill metadata."""

    def test_name(self):
        skill = ConfirmSkill()
        assert skill.name == "confirm"

    def test_aliases(self):
        skill = ConfirmSkill()
        assert "y" in skill.aliases
        assert "yes" in skill.aliases

    def test_category(self):
        skill = ConfirmSkill()
        assert skill.category == "builtin"

    def test_set_confirmation_window(self):
        skill = ConfirmSkill()
        cw = ConfirmationWindow(enabled=True)
        skill.set_confirmation_window(cw)
        assert skill._cw is cw


class TestConfirmConfig:
    """trigger.confirm config defaults."""

    def test_default_config_has_confirm(self):
        from chatmd.infra.config import _DEFAULT_AGENT_CONFIG
        confirm = _DEFAULT_AGENT_CONFIG["trigger"]["confirm"]
        assert confirm["enabled"] is False
        assert isinstance(confirm["commands"], list)
        assert "/sync" in confirm["commands"]

    def test_init_workspace_config_has_confirm(self):
        from chatmd.commands.init_workspace import _DEFAULT_AGENT_YAML
        confirm = _DEFAULT_AGENT_YAML["trigger"]["confirm"]
        assert confirm["enabled"] is False
        assert "/sync" in confirm["commands"]
        assert "/upload" in confirm["commands"]
        assert "/new" in confirm["commands"]
