"""Tests for KernelGate output filtering and audit."""

from chatmd.security.kernel_gate import KernelGate
from chatmd.skills.base import Skill, SkillResult


class _FakeAISkill(Skill):
    name = "ask"
    category = "ai"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output=input_text)


class _FakeBuiltinSkill(Skill):
    name = "date"
    category = "builtin"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output="2026-03-30")


class TestCommandEscaping:
    """Test that slash commands in AI output are escaped."""

    def test_escapes_slash_commands(self):
        gate = KernelGate()
        skill = _FakeAISkill()
        result = SkillResult(success=True, output="Try running /date to get today's date")
        filtered = gate.process_output(skill, result)
        assert "\\/date" in filtered.output
        assert filtered.output.startswith("Try running \\/date")

    def test_escapes_multiple_commands(self):
        gate = KernelGate()
        skill = _FakeAISkill()
        result = SkillResult(
            success=True,
            output="Use /help for help\nOr /translate for translation",
        )
        filtered = gate.process_output(skill, result)
        assert "\\/help" in filtered.output
        assert "\\/translate" in filtered.output

    def test_no_escape_for_builtin(self):
        gate = KernelGate()
        skill = _FakeBuiltinSkill()
        result = SkillResult(success=True, output="/date is a command")
        filtered = gate.process_output(skill, result)
        # Builtin skills are not filtered
        assert filtered.output == "/date is a command"

    def test_no_escape_when_no_commands(self):
        gate = KernelGate()
        skill = _FakeAISkill()
        result = SkillResult(success=True, output="Hello, no commands here!")
        filtered = gate.process_output(skill, result)
        assert filtered.output == "Hello, no commands here!"

    def test_failed_result_not_filtered(self):
        gate = KernelGate()
        skill = _FakeAISkill()
        result = SkillResult(success=False, output="", error="/date caused error")
        filtered = gate.process_output(skill, result)
        assert filtered.error == "/date caused error"


class TestAudit:
    """Test audit logging."""

    def test_audit_records_success(self):
        gate = KernelGate()
        skill = _FakeBuiltinSkill()
        result = SkillResult(success=True, output="ok")
        gate.process_output(skill, result)

        audit = gate.get_recent_audit()
        assert len(audit) == 1
        assert audit[0]["skill"] == "date"
        assert audit[0]["success"] is True

    def test_audit_records_failure(self):
        gate = KernelGate()
        skill = _FakeAISkill()
        result = SkillResult(success=False, output="", error="timeout")
        gate.process_output(skill, result)

        audit = gate.get_recent_audit()
        assert len(audit) == 1
        assert audit[0]["success"] is False
        assert audit[0]["error"] == "timeout"

    def test_audit_limits_entries(self):
        gate = KernelGate()
        skill = _FakeBuiltinSkill()
        result = SkillResult(success=True, output="ok")

        for _ in range(1100):
            gate.process_output(skill, result)

        audit = gate.get_recent_audit(count=1000)
        # After exceeding 1000, trimmed to 500, then more entries added
        # Total should be much less than 1100
        assert len(audit) < 1100
