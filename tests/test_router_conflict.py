"""Tests for Router conflict detection and enhanced fuzzy suggestions."""

from chatmd.engine.router import Router
from chatmd.skills.base import Skill, SkillResult


class _BuiltinSkill(Skill):
    name = "test"
    category = "builtin"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output="builtin")


class _CustomSkill(Skill):
    name = "test"
    category = "custom"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output="custom")


class _AISkill(Skill):
    name = "test"
    category = "ai"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output="ai")


class TestConflictDetection:
    def test_builtin_wins_over_custom(self):
        router = Router()
        router.register(_BuiltinSkill())
        router.register(_CustomSkill())
        skill = router.get_skill("test")
        assert skill.category == "builtin"
        assert len(router.get_conflicts()) == 1

    def test_builtin_wins_over_ai(self):
        router = Router()
        router.register(_BuiltinSkill())
        router.register(_AISkill())
        skill = router.get_skill("test")
        assert skill.category == "builtin"

    def test_higher_priority_replaces(self):
        router = Router()
        router.register(_CustomSkill())
        router.register(_BuiltinSkill())
        skill = router.get_skill("test")
        # builtin (priority 0) should replace custom (priority 20)
        assert skill.category == "builtin"

    def test_no_conflict_different_names(self):
        class SkillA(Skill):
            name = "a"
            category = "builtin"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="a")

        class SkillB(Skill):
            name = "b"
            category = "custom"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="b")

        router = Router()
        router.register(SkillA())
        router.register(SkillB())
        assert len(router.get_conflicts()) == 0


class TestEnhancedFuzzy:
    def test_prefix_match(self):
        class DateSkill(Skill):
            name = "date"
            category = "builtin"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        class TranslateSkill(Skill):
            name = "translate"
            category = "ai"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        router = Router()
        router.register(DateSkill())
        router.register(TranslateSkill())

        # "trans" should match "translate" via prefix
        suggestions = router._fuzzy_suggest("trans")
        assert "translate" in suggestions

    def test_no_duplicates(self):
        class HelpSkill(Skill):
            name = "help"
            category = "builtin"
            aliases = ["h"]
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        router = Router()
        router.register(HelpSkill())

        suggestions = router._fuzzy_suggest("hel")
        # Should not have duplicates
        assert len(suggestions) == len(set(suggestions))
