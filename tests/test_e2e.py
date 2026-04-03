"""End-to-end integration tests — verify full pipeline from parse to output."""

from pathlib import Path

from chatmd.engine.parser import CommandType, Parser
from chatmd.engine.router import Router
from chatmd.infra.file_writer import FileWriter
from chatmd.skills.base import SkillContext
from chatmd.skills.builtin import register_builtin_skills
from chatmd.watcher.suffix_trigger import SuffixTrigger


class TestParseRouteExecute:
    """Test the full parse → route → execute pipeline."""

    def test_slash_command_pipeline(self):
        parser = Parser()
        router = Router()
        register_builtin_skills(router)

        lines = ["/help"]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.SLASH_CMD

        skill, resolved = router.route(cmds[0])
        assert skill.name == "help"

        ctx = SkillContext(source_file=None, source_line=1, workspace=Path("."))
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success
        assert len(result.output) > 0

    def test_date_command_pipeline(self):
        parser = Parser()
        router = Router()
        register_builtin_skills(router)

        cmds = parser.parse_lines(["/date"])
        skill, resolved = router.route(cmds[0])
        ctx = SkillContext(source_file=None, source_line=1, workspace=Path("."))
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success
        # Date should contain year
        assert "202" in result.output

    def test_alias_resolution_pipeline(self):
        parser = Parser()
        router = Router()
        register_builtin_skills(router)
        router.register_aliases({"d": "date"})

        cmds = parser.parse_lines(["/d"])
        skill, resolved = router.route(cmds[0])
        assert skill.name == "date"

    def test_suffix_trigger_pipeline(self):
        parser = Parser()
        trigger = SuffixTrigger(marker=";", enabled=True)
        parser.set_suffix_trigger(trigger)
        router = Router()
        register_builtin_skills(router)

        cmds = parser.parse_lines(["/date;"])
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.SLASH_CMD
        assert cmds[0].command == "date"

        skill, resolved = router.route(cmds[0])
        ctx = SkillContext(source_file=None, source_line=1, workspace=Path("."))
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success


class TestFileWriterIntegration:
    """Test FileWriter with real files."""

    def test_write_result_to_file(self, tmp_path):
        fw = FileWriter()
        md_file = tmp_path / "test.md"
        md_file.write_text("/date\n", encoding="utf-8")

        fw.write_result(md_file, 1, "/date", "> 2026-03-30")
        content = md_file.read_text(encoding="utf-8")
        assert "2026-03-30" in content

    def test_agent_write_filtering(self, tmp_path):
        fw = FileWriter()
        md_file = tmp_path / "test.md"
        md_file.write_text("hello\n", encoding="utf-8")

        fw.write_result(md_file, 1, "hello", "> result")
        # During write, file should be marked as agent write
        # After write completes, it should no longer be
        assert not fw.is_agent_write(md_file)


class TestCustomSkillIntegration:
    """Test custom YAML/Python skill loading and execution."""

    def test_yaml_skill_in_router(self, tmp_path):
        from chatmd.skills.loader import load_yaml_skills

        (tmp_path / "greet.yaml").write_text(
            'name: greet\ndescription: "Greet user"\ntemplate: "Hi, {{input}}!"',
            encoding="utf-8",
        )
        skills = load_yaml_skills(tmp_path)
        router = Router()
        for s in skills:
            router.register(s)

        parser = Parser()
        cmds = parser.parse_lines(["/greet World"])
        skill, resolved = router.route(cmds[0])
        ctx = SkillContext(source_file=None, source_line=1, workspace=Path("."))
        result = skill.execute(resolved.input_text, resolved.args, ctx)
        assert result.success
        assert result.output == "Hi, World!"


class TestMultiLineAtAi:
    """Test multi-line @ai{} block parsing end-to-end."""

    def test_multi_line_block_parsed(self):
        parser = Parser()
        lines = [
            "some text above",
            "@ai{",
            "translate this:",
            "Hello World",
            "}",
            "some text below",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 1
        assert cmds[0].type == CommandType.AT_AI
        assert "Hello World" in cmds[0].input_text


class TestProtectedRegions:
    """Verify commands in code blocks and blockquotes are not parsed."""

    def test_code_fence_protects_commands(self):
        parser = Parser()
        lines = [
            "```python",
            "/date",
            "/help",
            "```",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 0

    def test_blockquote_protects_commands(self):
        parser = Parser()
        cmds = parser.parse_lines(["> /date"])
        assert len(cmds) == 0

    def test_normal_command_outside_protection(self):
        parser = Parser()
        lines = [
            "```",
            "/date inside fence",
            "```",
            "/date",
        ]
        cmds = parser.parse_lines(lines)
        assert len(cmds) == 1
        assert cmds[0].command == "date"
