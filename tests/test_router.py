"""Tests for the command router."""

import pytest

from chatmd.engine.parser import CommandType, ParsedCommand
from chatmd.engine.router import Router
from chatmd.exceptions import RouteError
from chatmd.skills.base import Skill, SkillContext, SkillResult


class _MockSkill(Skill):
    """A simple mock skill for testing."""

    def __init__(self, name: str, aliases: list[str] | None = None):
        self.name = name
        self.description = f"Mock {name}"
        self.category = "test"
        self.aliases = aliases or []

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output=f"{self.name}: {input_text}")


class TestRouterRegistration:
    """Test skill registration and lookup."""

    def test_register_and_get(self):
        router = Router()
        skill = _MockSkill("date")
        router.register(skill)
        assert router.get_skill("date") is skill

    def test_list_skills(self):
        router = Router()
        router.register(_MockSkill("date"))
        router.register(_MockSkill("help"))
        assert len(router.list_skills()) == 2

    def test_alias_registration(self):
        router = Router()
        router.register(_MockSkill("translate", aliases=["tran", "t"]))
        cmd = ParsedCommand(type=CommandType.SLASH_CMD, command="tran")
        skill, _ = router.route(cmd)
        assert skill.name == "translate"


class TestRouterRouting:
    """Test command routing logic."""

    def test_direct_match(self):
        router = Router()
        router.register(_MockSkill("date"))
        cmd = ParsedCommand(type=CommandType.SLASH_CMD, command="date")
        skill, resolved = router.route(cmd)
        assert skill.name == "date"

    def test_alias_resolve(self):
        router = Router()
        router.register(_MockSkill("translate", aliases=["t"]))
        cmd = ParsedCommand(type=CommandType.SLASH_CMD, command="t")
        skill, resolved = router.route(cmd)
        assert skill.name == "translate"

    def test_user_alias_with_params(self):
        router = Router()
        router.register(_MockSkill("translate"))
        router.register_aliases({"en": "translate(English)"})
        cmd = ParsedCommand(type=CommandType.SLASH_CMD, command="en")
        skill, resolved = router.route(cmd)
        assert skill.name == "translate"
        assert resolved.args.get("_positional") == "English"

    def test_unknown_command_raises(self):
        router = Router()
        router.register(_MockSkill("date"))
        cmd = ParsedCommand(type=CommandType.SLASH_CMD, command="nonexistent")
        with pytest.raises(RouteError, match="Unknown command"):
            router.route(cmd)

    def test_fuzzy_suggestion(self):
        router = Router()
        router.register(_MockSkill("translate"))
        cmd = ParsedCommand(type=CommandType.SLASH_CMD, command="tranlate")
        with pytest.raises(RouteError, match="translate"):
            router.route(cmd)


class TestOpenChatRouting:
    """Test OPEN_CHAT routing."""

    def test_routes_to_ask_skill(self):
        router = Router()
        router.register(_MockSkill("ask"))
        cmd = ParsedCommand(type=CommandType.OPEN_CHAT, input_text="Hello")
        skill, _ = router.route(cmd)
        assert skill.name == "ask"

    def test_no_chat_skill_raises(self):
        router = Router()
        router.register(_MockSkill("date"))
        cmd = ParsedCommand(type=CommandType.OPEN_CHAT, input_text="Hello")
        with pytest.raises(RouteError, match="No chat skill"):
            router.route(cmd)


class TestAtAiRouting:
    """Test AT_AI routing — @ai{} commands route to ask/chat skill."""

    def test_at_ai_routes_to_ask_skill(self):
        router = Router()
        router.register(_MockSkill("ask"))
        cmd = ParsedCommand(type=CommandType.AT_AI, input_text="翻译成英文")
        skill, _ = router.route(cmd)
        assert skill.name == "ask"

    def test_at_ai_no_chat_skill_raises(self):
        router = Router()
        router.register(_MockSkill("date"))
        cmd = ParsedCommand(type=CommandType.AT_AI, input_text="翻译成英文")
        with pytest.raises(RouteError, match="No chat skill"):
            router.route(cmd)
