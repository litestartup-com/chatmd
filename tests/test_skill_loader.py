"""Tests for YAML and Python skill loaders."""

from chatmd.skills.base import SkillContext
from chatmd.skills.loader import YAMLSkill, load_python_skills, load_yaml_skills


class TestYAMLSkill:
    def test_basic_template(self):
        skill = YAMLSkill({
            "name": "greet",
            "description": "Say hello",
            "template": "Hello, {{input}}!",
        })
        ctx = SkillContext(source_file=None, source_line=0, workspace=None)
        result = skill.execute("World", {}, ctx)
        assert result.success
        assert result.output == "Hello, World!"

    def test_named_args_in_template(self):
        skill = YAMLSkill({
            "name": "format",
            "template": "{{name}} says {{input}}",
        })
        ctx = SkillContext(source_file=None, source_line=0, workspace=None)
        result = skill.execute("hi", {"name": "Alice"}, ctx)
        assert result.output == "Alice says hi"

    def test_category_default(self):
        skill = YAMLSkill({"name": "test"})
        assert skill.category == "custom"

    def test_aliases(self):
        skill = YAMLSkill({
            "name": "greet",
            "aliases": ["hi", "hello"],
        })
        assert skill.aliases == ["hi", "hello"]


class TestLoadYAMLSkills:
    def test_load_from_directory(self, tmp_path):
        (tmp_path / "greet.yaml").write_text(
            'name: greet\ntemplate: "Hello {{input}}"',
            encoding="utf-8",
        )
        (tmp_path / "bye.yml").write_text(
            'name: bye\ntemplate: "Goodbye {{input}}"',
            encoding="utf-8",
        )
        skills = load_yaml_skills(tmp_path)
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"greet", "bye"}

    def test_skip_invalid(self, tmp_path):
        (tmp_path / "bad.yaml").write_text("not_a_skill: true", encoding="utf-8")
        skills = load_yaml_skills(tmp_path)
        assert len(skills) == 0

    def test_nonexistent_dir(self, tmp_path):
        skills = load_yaml_skills(tmp_path / "nope")
        assert skills == []


class TestLoadPythonSkills:
    def test_load_python_skill(self, tmp_path):
        code = '''
from chatmd.skills.base import Skill, SkillContext, SkillResult

class EchoSkill(Skill):
    name = "echo"
    description = "Echo input"
    category = "custom"

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output=input_text)
'''
        (tmp_path / "echo.py").write_text(code, encoding="utf-8")
        skills = load_python_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "echo"

    def test_skip_underscore_files(self, tmp_path):
        (tmp_path / "_private.py").write_text("x = 1", encoding="utf-8")
        skills = load_python_skills(tmp_path)
        assert skills == []

    def test_nonexistent_dir(self, tmp_path):
        skills = load_python_skills(tmp_path / "nope")
        assert skills == []

    def test_bad_python_file(self, tmp_path):
        (tmp_path / "bad.py").write_text("raise SyntaxError", encoding="utf-8")
        skills = load_python_skills(tmp_path)
        assert skills == []
