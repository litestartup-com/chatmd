"""Tests for Skill hot-reload."""

from chatmd.engine.router import Router
from chatmd.skills.hot_reload import SkillReloader


class TestSkillReloader:
    def test_load_yaml_skills(self, tmp_path):
        (tmp_path / "greet.yaml").write_text(
            'name: greet\ntemplate: "Hello {{input}}"',
            encoding="utf-8",
        )
        router = Router()
        reloader = SkillReloader(tmp_path, router)
        count = reloader.load_all()
        assert count == 1
        assert "greet" in reloader.get_loaded_names()
        assert router.get_skill("greet") is not None

    def test_load_python_skills(self, tmp_path):
        code = '''
from chatmd.skills.base import Skill, SkillContext, SkillResult

class PingSkill(Skill):
    name = "ping"
    description = "Pong"
    category = "custom"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output="pong")
'''
        (tmp_path / "ping.py").write_text(code, encoding="utf-8")
        router = Router()
        reloader = SkillReloader(tmp_path, router)
        count = reloader.load_all()
        assert count == 1
        assert router.get_skill("ping") is not None

    def test_reload_clears_and_reloads(self, tmp_path):
        (tmp_path / "a.yaml").write_text(
            'name: alpha\ntemplate: "A"', encoding="utf-8",
        )
        router = Router()
        reloader = SkillReloader(tmp_path, router)
        reloader.load_all()
        assert reloader.loaded_count == 1

        # Add another skill and reload
        (tmp_path / "b.yaml").write_text(
            'name: beta\ntemplate: "B"', encoding="utf-8",
        )
        count = reloader.reload()
        assert count == 2
        assert "alpha" in reloader.get_loaded_names()
        assert "beta" in reloader.get_loaded_names()

    def test_nonexistent_dir(self, tmp_path):
        router = Router()
        reloader = SkillReloader(tmp_path / "nope", router)
        assert reloader.load_all() == 0
        assert reloader.loaded_count == 0
