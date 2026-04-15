"""Tests for network skill ⏳ placeholder (immediate feedback UX).

When a sync skill has ``requires_network = True``, the Agent should write a
⏳ placeholder to the file *before* calling ``skill.execute()``, then replace
it with the final result after execution completes.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from chatmd.engine.parser import CommandType
from chatmd.infra.file_writer import FileWriter
from chatmd.skills.base import Skill, SkillContext, SkillResult

# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------

class _NetworkSkill(Skill):
    """A fake sync skill that requires network."""

    name = "fakenet"
    description = "Fake network skill"
    category = "general"
    requires_network = True
    is_async = False

    def __init__(self, result: SkillResult | None = None, delay: float = 0):
        self._result = result or SkillResult(success=True, output="done")
        self._delay = delay

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        if self._delay:
            time.sleep(self._delay)
        return self._result


class _LocalSkill(Skill):
    """A fake sync skill that does NOT require network."""

    name = "fakelocal"
    description = "Fake local skill"
    category = "general"
    requires_network = False
    is_async = False

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output="local done")


class TestNetworkPlaceholder:
    """Verify ⏳ placeholder behaviour for requires_network skills."""

    def _make_cmd(self, *, command: str = "fakenet", raw_text: str = "/fakenet") -> Any:
        """Build a minimal command-like object."""
        cmd = MagicMock()
        cmd.command = command
        cmd.raw_text = raw_text
        cmd.source_line = 1
        cmd.end_line = 0
        cmd.input_text = ""
        cmd.args = {}
        cmd.type = CommandType.SLASH_CMD
        return cmd

    def test_network_skill_writes_placeholder_before_result(self, tmp_path: Path) -> None:
        """_write_back should be called twice: once for placeholder, once for result."""
        from chatmd.engine.agent import Agent

        # Build a minimal agent
        agent = Agent.__new__(Agent)
        agent._workspace = tmp_path
        agent._parser = MagicMock()
        agent._router = MagicMock()
        agent._file_writer = MagicMock(spec=FileWriter)
        agent._kernel_gate = MagicMock()
        agent._kernel_gate.process_output = MagicMock(side_effect=lambda s, r: r)
        agent._confirmation_window = MagicMock()
        agent._confirmation_window.needs_confirmation = MagicMock(return_value=False)
        agent._scheduler = MagicMock()

        net_skill = _NetworkSkill()
        resolved = MagicMock()
        resolved.input_text = ""
        resolved.args = {}
        resolved.source_line = 1
        resolved.raw_text = "/fakenet"
        agent._router.route = MagicMock(return_value=(net_skill, resolved))

        filepath = tmp_path / "chat.md"
        filepath.write_text("/fakenet\n", encoding="utf-8")

        cmd = self._make_cmd()
        agent._execute_command(cmd, filepath)

        # _write_back should have been called at least twice:
        # 1st call: placeholder (contains ⏳)
        # 2nd call: final result
        write_calls = agent._file_writer.write_result.call_args_list
        assert len(write_calls) >= 2, f"Expected ≥2 write_result calls, got {len(write_calls)}"

        # First write should contain the ⏳ placeholder
        first_args = write_calls[0][0]
        first_new_text = first_args[3] if len(first_args) > 3 else ""
        assert "⏳" in first_new_text, f"First write should contain ⏳: {first_new_text}"

    def test_local_skill_no_placeholder(self, tmp_path: Path) -> None:
        """A skill without requires_network should NOT get a placeholder."""
        from chatmd.engine.agent import Agent

        agent = Agent.__new__(Agent)
        agent._workspace = tmp_path
        agent._parser = MagicMock()
        agent._router = MagicMock()
        agent._file_writer = MagicMock(spec=FileWriter)
        agent._kernel_gate = MagicMock()
        agent._kernel_gate.process_output = MagicMock(side_effect=lambda s, r: r)
        agent._confirmation_window = MagicMock()
        agent._confirmation_window.needs_confirmation = MagicMock(return_value=False)
        agent._scheduler = MagicMock()

        local_skill = _LocalSkill()
        resolved = MagicMock()
        resolved.input_text = ""
        resolved.args = {}
        resolved.source_line = 1
        resolved.raw_text = "/fakelocal"
        agent._router.route = MagicMock(return_value=(local_skill, resolved))

        filepath = tmp_path / "chat.md"
        filepath.write_text("/fakelocal\n", encoding="utf-8")

        cmd = self._make_cmd(command="fakelocal", raw_text="/fakelocal")
        agent._execute_command(cmd, filepath)

        # Only one write_result call (the final result, no placeholder)
        write_calls = agent._file_writer.write_result.call_args_list
        assert len(write_calls) == 1, f"Expected 1 write_result call, got {len(write_calls)}"

    def test_network_skill_error_replaces_placeholder(self, tmp_path: Path) -> None:
        """If a network skill raises, the placeholder should still be replaced with error."""
        from chatmd.engine.agent import Agent

        agent = Agent.__new__(Agent)
        agent._workspace = tmp_path
        agent._parser = MagicMock()
        agent._router = MagicMock()
        agent._file_writer = MagicMock(spec=FileWriter)
        agent._kernel_gate = MagicMock()
        agent._kernel_gate.process_output = MagicMock(side_effect=RuntimeError("boom"))
        agent._confirmation_window = MagicMock()
        agent._confirmation_window.needs_confirmation = MagicMock(return_value=False)
        agent._scheduler = MagicMock()

        net_skill = _NetworkSkill()
        resolved = MagicMock()
        resolved.input_text = ""
        resolved.args = {}
        resolved.source_line = 1
        resolved.raw_text = "/fakenet"
        agent._router.route = MagicMock(return_value=(net_skill, resolved))

        filepath = tmp_path / "chat.md"
        filepath.write_text("/fakenet\n", encoding="utf-8")

        cmd = self._make_cmd()
        agent._execute_command(cmd, filepath)

        # Should still have 2 writes: placeholder + error replacement
        write_calls = agent._file_writer.write_result.call_args_list
        assert len(write_calls) >= 2

        # Last write should contain ❌ error
        last_new_text = write_calls[-1][0][3] if len(write_calls[-1][0]) > 3 else ""
        assert "❌" in last_new_text, f"Error write should contain ❌: {last_new_text}"
