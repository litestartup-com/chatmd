"""Tests for AI writing skills — /rewrite /expand /polish /summary /tag /title (T-039)."""

from pathlib import Path

from chatmd.providers.base import AIProvider
from chatmd.skills.ai import (
    ExpandSkill,
    PolishSkill,
    RewriteSkill,
    SummarySkill,
    TagSkill,
    TitleSkill,
    register_ai_skills,
)
from chatmd.skills.base import SkillContext


def _ctx(tmp_path: Path) -> SkillContext:
    return SkillContext(source_file=tmp_path / "chat.md", source_line=1, workspace=tmp_path)


class _MockProvider(AIProvider):
    name = "mock"

    def __init__(self, response: str = "mock response"):
        self._response = response

    def chat(self, messages: list[dict], **kwargs) -> str:
        return self._response


class _FailProvider(AIProvider):
    name = "fail"

    def chat(self, messages: list[dict], **kwargs) -> str:
        raise RuntimeError("AI API request timeout (60s)")


# ── Shared test patterns for all prompt-driven skills ────────────────────


_SKILL_CLASSES = [
    RewriteSkill,
    ExpandSkill,
    PolishSkill,
    SummarySkill,
    TagSkill,
    TitleSkill,
]


class TestWritingSkillsCommon:
    """Common behaviour shared by all prompt-driven AI writing skills."""

    def test_success(self, tmp_path):
        for cls in _SKILL_CLASSES:
            skill = cls(provider=_MockProvider("improved text"))
            result = skill.execute("Hello world", {}, _ctx(tmp_path))
            assert result.success, f"{cls.name} should succeed"
            assert result.output == "improved text"

    def test_no_provider(self, tmp_path):
        for cls in _SKILL_CLASSES:
            skill = cls(provider=None)
            result = skill.execute("Hello", {}, _ctx(tmp_path))
            assert not result.success, f"{cls.name} should fail without provider"
            assert "not configured" in result.error

    def test_empty_input(self, tmp_path):
        for cls in _SKILL_CLASSES:
            skill = cls(provider=_MockProvider())
            result = skill.execute("", {}, _ctx(tmp_path))
            assert not result.success, f"{cls.name} should fail on empty input"
            assert result.error  # Non-empty error message

    def test_whitespace_only_input(self, tmp_path):
        for cls in _SKILL_CLASSES:
            skill = cls(provider=_MockProvider())
            result = skill.execute("   \n  ", {}, _ctx(tmp_path))
            assert not result.success, f"{cls.name} should fail on whitespace-only"

    def test_provider_failure(self, tmp_path):
        for cls in _SKILL_CLASSES:
            skill = cls(provider=_FailProvider())
            result = skill.execute("Hello", {}, _ctx(tmp_path))
            assert not result.success, f"{cls.name} should fail on provider error"
            assert "timeout" in result.error

    def test_set_provider(self, tmp_path):
        for cls in _SKILL_CLASSES:
            skill = cls()
            assert skill._provider is None
            skill.set_provider(_MockProvider("late"))
            result = skill.execute("Hi", {}, _ctx(tmp_path))
            assert result.success, f"{cls.name} set_provider should work"
            assert result.output == "late"


# ── Skill-specific attribute tests ───────────────────────────────────────


class TestRewriteSkill:
    def test_attributes(self):
        skill = RewriteSkill()
        assert skill.name == "rewrite"
        assert skill.category == "ai"
        assert skill.is_async is True
        assert "rw" in skill.aliases

    def test_prompt_contains_input(self, tmp_path):
        """The prompt sent to the provider should contain the user text."""
        captured = {}

        class _CaptureProvider(AIProvider):
            name = "capture"

            def chat(self, messages: list[dict], **kwargs) -> str:
                captured["prompt"] = messages[0]["content"]
                return "result"

        skill = RewriteSkill(provider=_CaptureProvider())
        skill.execute("test text here", {}, _ctx(tmp_path))
        assert "test text here" in captured["prompt"]


class TestExpandSkill:
    def test_attributes(self):
        skill = ExpandSkill()
        assert skill.name == "expand"
        assert "exp" in skill.aliases


class TestPolishSkill:
    def test_attributes(self):
        skill = PolishSkill()
        assert skill.name == "polish"
        assert "pol" in skill.aliases


class TestSummarySkill:
    def test_attributes(self):
        skill = SummarySkill()
        assert skill.name == "summary"
        assert "sum" in skill.aliases


class TestTagSkill:
    def test_attributes(self):
        skill = TagSkill()
        assert skill.name == "tag"
        assert skill.aliases == []


class TestTitleSkill:
    def test_attributes(self):
        skill = TitleSkill()
        assert skill.name == "title"
        assert skill.aliases == []


# ── Registration test ────────────────────────────────────────────────────


class TestRegistration:
    def test_register_ai_skills_includes_writing_skills(self):
        """register_ai_skills should register all 8 AI skills (ask + translate + 6 writing)."""
        from chatmd.engine.router import Router

        router = Router()
        register_ai_skills(router, provider=_MockProvider())

        expected = ["ask", "translate", "rewrite", "expand", "polish", "summary", "tag", "title"]
        for name in expected:
            assert router.get_skill(name) is not None, f"Skill '{name}' not registered"

    def test_aliases_registered(self):
        """Aliases should be resolvable via route."""
        from chatmd.engine.parser import CommandType, ParsedCommand
        from chatmd.engine.router import Router

        router = Router()
        register_ai_skills(router, provider=_MockProvider())

        # Test /rw alias resolves to rewrite
        cmd = ParsedCommand(
            type=CommandType.SLASH_CMD,
            command="rw",
            input_text="hello",
        )
        skill, resolved = router.route(cmd)
        assert skill.name == "rewrite"

        # Test /sum alias resolves to summary
        cmd2 = ParsedCommand(
            type=CommandType.SLASH_CMD,
            command="sum",
            input_text="hello",
        )
        skill2, _ = router.route(cmd2)
        assert skill2.name == "summary"
