"""Tests for the skills plugin mechanism (T-074).

Covers:
- SkillsConfig / PluginEntry parsing from skills.yaml
- load_skills_config() with various inputs
- load_plugin_skills() auto and manual modes
- Skill.configure() lifecycle hook
- Skill.teardown() lifecycle hook
- Router.unregister()
- SkillReloader with plugin config
"""

from __future__ import annotations

from pathlib import Path

from chatmd.engine.router import Router
from chatmd.skills.base import Skill, SkillContext, SkillResult
from chatmd.skills.hot_reload import SkillReloader
from chatmd.skills.loader import (
    PluginEntry,
    SkillsConfig,
    load_plugin_skills,
    load_skills_config,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(workspace: Path) -> SkillContext:
    return SkillContext(source_file=workspace, source_line=0, workspace=workspace)


def _write_python_skill(skills_dir: Path, name: str, *, extra_body: str = "") -> None:
    """Write a minimal Python skill file to skills_dir."""
    code = f'''
from chatmd.skills.base import Skill, SkillContext, SkillResult

class {name.title()}Skill(Skill):
    name = "{name}"
    description = "{name} skill"
    category = "custom"
    _configured = False
    _config_data = {{}}
    _torn_down = False

    def configure(self, config, context):
        self._configured = True
        self._config_data = config
        self._workspace = context.workspace

    def teardown(self):
        self._torn_down = True

    def execute(self, input_text, args, context):
        return SkillResult(success=True, output=f"{name}: {{input_text}}")
    {extra_body}
'''
    (skills_dir / f"{name}.py").write_text(code, encoding="utf-8")


def _write_yaml_skill(skills_dir: Path, name: str) -> None:
    """Write a minimal YAML skill file to skills_dir."""
    content = (
        f'name: {name}\ndescription: "{name} yaml skill"\n'
        f'category: custom\ntemplate: "{name}: {{{{input}}}}"\n'
    )
    (skills_dir / f"{name}.yaml").write_text(content, encoding="utf-8")


def _write_skills_yaml(chatmd_dir: Path, content: str) -> None:
    """Write skills.yaml to chatmd_dir."""
    (chatmd_dir / "skills.yaml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: load_skills_config
# ---------------------------------------------------------------------------

class TestLoadSkillsConfig:
    def test_no_file_returns_auto(self, tmp_path):
        cfg = load_skills_config(tmp_path)
        assert cfg.discover == "auto"
        assert cfg.plugins == {}

    def test_empty_file_returns_auto(self, tmp_path):
        (tmp_path / "skills.yaml").write_text("", encoding="utf-8")
        cfg = load_skills_config(tmp_path)
        assert cfg.discover == "auto"

    def test_manual_mode(self, tmp_path):
        _write_skills_yaml(tmp_path, "discover: manual\nskills:\n  foo:\n    enabled: true\n")
        cfg = load_skills_config(tmp_path)
        assert cfg.discover == "manual"
        assert "foo" in cfg.plugins
        assert cfg.plugins["foo"].enabled is True

    def test_disabled_plugin(self, tmp_path):
        _write_skills_yaml(tmp_path, "discover: manual\nskills:\n  bar:\n    enabled: false\n")
        cfg = load_skills_config(tmp_path)
        assert cfg.plugins["bar"].enabled is False

    def test_config_passed_through(self, tmp_path):
        _write_skills_yaml(tmp_path, (
            "discover: manual\n"
            "skills:\n"
            "  daily_note:\n"
            "    enabled: true\n"
            "    config:\n"
            "      enabled_logs: [journal, dudu]\n"
            "      delete_unedited: true\n"
        ))
        cfg = load_skills_config(tmp_path)
        entry = cfg.plugins["daily_note"]
        assert entry.config["enabled_logs"] == ["journal", "dudu"]
        assert entry.config["delete_unedited"] is True

    def test_invalid_discover_falls_back_to_auto(self, tmp_path):
        _write_skills_yaml(tmp_path, "discover: invalid_mode\n")
        cfg = load_skills_config(tmp_path)
        assert cfg.discover == "auto"

    def test_invalid_yaml_returns_default(self, tmp_path):
        (tmp_path / "skills.yaml").write_text(":::bad yaml", encoding="utf-8")
        cfg = load_skills_config(tmp_path)
        assert cfg.discover == "auto"

    def test_non_dict_skills_ignored(self, tmp_path):
        _write_skills_yaml(tmp_path, "discover: manual\nskills:\n  - not_a_dict\n")
        cfg = load_skills_config(tmp_path)
        assert cfg.plugins == {}


# ---------------------------------------------------------------------------
# Tests: load_plugin_skills — auto mode
# ---------------------------------------------------------------------------

class TestAutoMode:
    def test_auto_loads_all(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")
        _write_python_skill(skills_dir, "beta")

        cfg = SkillsConfig(discover="auto")
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        names = {s.name for s in skills}
        assert names == {"alpha", "beta"}

    def test_auto_skips_disabled(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")
        _write_python_skill(skills_dir, "beta")

        cfg = SkillsConfig(
            discover="auto",
            plugins={"beta": PluginEntry(name="beta", enabled=False)},
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        names = {s.name for s in skills}
        assert names == {"alpha"}

    def test_auto_applies_config(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")

        cfg = SkillsConfig(
            discover="auto",
            plugins={"alpha": PluginEntry(name="alpha", config={"key": "val"})},
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        assert len(skills) == 1
        assert skills[0]._config_data == {"key": "val"}

    def test_auto_with_yaml_skills(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_yaml_skill(skills_dir, "greet")
        _write_python_skill(skills_dir, "echo")

        cfg = SkillsConfig(discover="auto")
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        names = {s.name for s in skills}
        assert names == {"greet", "echo"}

    def test_auto_empty_dir(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        cfg = SkillsConfig(discover="auto")
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        assert skills == []

    def test_nonexistent_dir(self, tmp_path):
        cfg = SkillsConfig(discover="auto")
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(tmp_path / "nope", cfg, ctx)
        assert skills == []


# ---------------------------------------------------------------------------
# Tests: load_plugin_skills — manual mode
# ---------------------------------------------------------------------------

class TestManualMode:
    def test_manual_only_loads_enabled(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")
        _write_python_skill(skills_dir, "beta")

        cfg = SkillsConfig(
            discover="manual",
            plugins={
                "alpha": PluginEntry(name="alpha", enabled=True),
                "beta": PluginEntry(name="beta", enabled=False),
            },
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        names = {s.name for s in skills}
        assert names == {"alpha"}

    def test_manual_ignores_undeclared_files(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")
        _write_python_skill(skills_dir, "secret")  # Not declared

        cfg = SkillsConfig(
            discover="manual",
            plugins={"alpha": PluginEntry(name="alpha", enabled=True)},
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        assert len(skills) == 1
        assert skills[0].name == "alpha"

    def test_manual_missing_file_warns(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        cfg = SkillsConfig(
            discover="manual",
            plugins={"ghost": PluginEntry(name="ghost", enabled=True)},
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        assert skills == []

    def test_manual_loads_yaml(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_yaml_skill(skills_dir, "greet")

        cfg = SkillsConfig(
            discover="manual",
            plugins={"greet": PluginEntry(name="greet", enabled=True)},
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        assert len(skills) == 1
        assert skills[0].name == "greet"

    def test_manual_python_takes_priority_over_yaml(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "dual")
        _write_yaml_skill(skills_dir, "dual")

        cfg = SkillsConfig(
            discover="manual",
            plugins={"dual": PluginEntry(name="dual", enabled=True)},
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        # Python is tried first, so the Python skill should be loaded
        assert len(skills) == 1
        assert skills[0].name == "dual"
        assert skills[0].category == "custom"

    def test_manual_passes_config_to_configure(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")

        cfg = SkillsConfig(
            discover="manual",
            plugins={"alpha": PluginEntry(
                name="alpha",
                enabled=True,
                config={"setting": 42},
            )},
        )
        ctx = _make_context(tmp_path)
        skills = load_plugin_skills(skills_dir, cfg, ctx)
        assert skills[0]._config_data == {"setting": 42}
        assert skills[0]._configured is True


# ---------------------------------------------------------------------------
# Tests: Skill.configure / teardown lifecycle
# ---------------------------------------------------------------------------

class TestSkillLifecycle:
    def test_default_configure_is_noop(self):
        """Base Skill.configure() should not raise."""
        class Dummy(Skill):
            name = "dummy"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        d = Dummy()
        ctx = _make_context(Path("/tmp"))
        d.configure({"key": "val"}, ctx)  # Should not raise

    def test_default_teardown_is_noop(self):
        """Base Skill.teardown() should not raise."""
        class Dummy(Skill):
            name = "dummy"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        d = Dummy()
        d.teardown()  # Should not raise


# ---------------------------------------------------------------------------
# Tests: Router.unregister
# ---------------------------------------------------------------------------

class TestRouterUnregister:
    def test_unregister_removes_skill(self):
        router = Router()

        class Foo(Skill):
            name = "foo"
            aliases = ["f"]
            category = "custom"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        router.register(Foo())
        assert router.get_skill("foo") is not None

        removed = router.unregister("foo")
        assert removed is True
        assert router.get_skill("foo") is None

    def test_unregister_removes_aliases(self):
        router = Router()

        class Foo(Skill):
            name = "foo"
            aliases = ["f", "fo"]
            category = "custom"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        router.register(Foo())
        # Aliases should resolve
        assert "f" in router._aliases
        assert "fo" in router._aliases

        router.unregister("foo")
        assert "f" not in router._aliases
        assert "fo" not in router._aliases

    def test_unregister_nonexistent_returns_false(self):
        router = Router()
        assert router.unregister("nonexistent") is False

    def test_unregister_does_not_affect_other_skills(self):
        router = Router()

        class Foo(Skill):
            name = "foo"
            category = "custom"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        class Bar(Skill):
            name = "bar"
            category = "custom"
            def execute(self, input_text, args, context):
                return SkillResult(success=True, output="")

        router.register(Foo())
        router.register(Bar())

        router.unregister("foo")
        assert router.get_skill("foo") is None
        assert router.get_skill("bar") is not None


# ---------------------------------------------------------------------------
# Tests: SkillReloader with plugin config
# ---------------------------------------------------------------------------

class TestSkillReloaderPlugin:
    def test_reload_calls_teardown(self, tmp_path):
        chatmd_dir = tmp_path
        skills_dir = chatmd_dir / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")

        router = Router()
        ctx = _make_context(tmp_path)
        reloader = SkillReloader(skills_dir, router, chatmd_dir=chatmd_dir, context=ctx)

        count = reloader.load_all()
        assert count == 1
        assert "alpha" in reloader.get_loaded_names()

        # Skill should be registered
        skill = router.get_skill("alpha")
        assert skill is not None

        # Reload — should teardown old skill, unregister, then reload
        count2 = reloader.reload()
        assert count2 == 1

    def test_reloader_respects_skills_yaml(self, tmp_path):
        chatmd_dir = tmp_path
        skills_dir = chatmd_dir / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")
        _write_python_skill(skills_dir, "beta")
        _write_skills_yaml(chatmd_dir, (
            "discover: manual\n"
            "skills:\n"
            "  alpha:\n"
            "    enabled: true\n"
        ))

        router = Router()
        ctx = _make_context(tmp_path)
        reloader = SkillReloader(skills_dir, router, chatmd_dir=chatmd_dir, context=ctx)

        count = reloader.load_all()
        assert count == 1
        assert reloader.get_loaded_names() == ["alpha"]

    def test_reloader_legacy_fallback(self, tmp_path):
        """Without context, falls back to legacy loading."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_python_skill(skills_dir, "alpha")

        router = Router()
        reloader = SkillReloader(skills_dir, router)  # No context

        count = reloader.load_all()
        assert count == 1
