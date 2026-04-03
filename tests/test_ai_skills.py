"""Tests for AI skills — /ask, /translate."""

from pathlib import Path

from chatmd.providers.base import AIProvider
from chatmd.skills.ai import ChatSkill, TranslateSkill
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


class TestChatSkill:
    def test_success(self, tmp_path):
        skill = ChatSkill(provider=_MockProvider("Hello!"))
        result = skill.execute("Hi", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "Hello!"

    def test_no_provider(self, tmp_path):
        skill = ChatSkill(provider=None)
        result = skill.execute("Hi", {}, _ctx(tmp_path))
        assert not result.success
        assert "not configured" in result.error

    def test_empty_input(self, tmp_path):
        skill = ChatSkill(provider=_MockProvider())
        result = skill.execute("", {}, _ctx(tmp_path))
        assert not result.success
        assert "Please enter" in result.error

    def test_provider_failure(self, tmp_path):
        skill = ChatSkill(provider=_FailProvider())
        result = skill.execute("Hello", {}, _ctx(tmp_path))
        assert not result.success
        assert "timeout" in result.error

    def test_set_provider(self, tmp_path):
        skill = ChatSkill()
        assert skill._provider is None
        provider = _MockProvider("late init")
        skill.set_provider(provider)
        result = skill.execute("Hi", {}, _ctx(tmp_path))
        assert result.success
        assert result.output == "late init"


class TestTranslateSkill:
    def test_success_with_positional(self, tmp_path):
        skill = TranslateSkill(provider=_MockProvider("こんにちは"))
        result = skill.execute("Hello", {"_positional": "日文"}, _ctx(tmp_path))
        assert result.success
        assert result.output == "こんにちは"

    def test_success_with_named_param(self, tmp_path):
        skill = TranslateSkill(provider=_MockProvider("Bonjour"))
        result = skill.execute("Hello", {"lang": "法文"}, _ctx(tmp_path))
        assert result.success

    def test_default_target_language(self, tmp_path):
        skill = TranslateSkill(provider=_MockProvider("Hello"))
        result = skill.execute("你好", {}, _ctx(tmp_path))
        assert result.success
        # Default is 英文

    def test_no_provider(self, tmp_path):
        skill = TranslateSkill(provider=None)
        result = skill.execute("Hello", {}, _ctx(tmp_path))
        assert not result.success

    def test_empty_input(self, tmp_path):
        skill = TranslateSkill(provider=_MockProvider())
        result = skill.execute("", {}, _ctx(tmp_path))
        assert not result.success
        assert "Please enter" in result.error

    def test_provider_failure(self, tmp_path):
        skill = TranslateSkill(provider=_FailProvider())
        result = skill.execute("Hello", {"_positional": "日文"}, _ctx(tmp_path))
        assert not result.success
