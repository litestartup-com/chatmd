"""Skill loaders — load custom Skills from YAML definitions and Python modules.

Supports two discovery modes via ``.chatmd/skills.yaml``:

- ``auto`` (default): load all ``.py`` / ``.yaml`` files in ``skills/``
- ``manual``: only load skills explicitly declared and enabled in ``skills.yaml``
"""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from chatmd.skills.base import Skill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skills Plugin Configuration (T-072)
# ---------------------------------------------------------------------------

@dataclass
class PluginEntry:
    """A single plugin declaration from skills.yaml."""

    name: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillsConfig:
    """Parsed representation of ``.chatmd/skills.yaml``."""

    discover: str = "auto"
    plugins: dict[str, PluginEntry] = field(default_factory=dict)


def load_skills_config(chatmd_dir: Path) -> SkillsConfig:
    """Load and parse ``.chatmd/skills.yaml``.

    Returns a default ``SkillsConfig(discover="auto")`` if the file
    does not exist or is invalid.
    """
    config_path = chatmd_dir / "skills.yaml"
    if not config_path.is_file():
        return SkillsConfig()

    try:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("Failed to load skills.yaml: %s", exc)
        return SkillsConfig()

    if not isinstance(raw, dict):
        return SkillsConfig()

    discover = raw.get("discover", "auto")
    if discover not in ("auto", "manual"):
        logger.warning("Invalid discover mode '%s', falling back to 'auto'", discover)
        discover = "auto"

    plugins: dict[str, PluginEntry] = {}
    raw_skills = raw.get("skills", {})
    if isinstance(raw_skills, dict):
        for name, entry in raw_skills.items():
            if not isinstance(entry, dict):
                continue
            plugins[name] = PluginEntry(
                name=name,
                enabled=entry.get("enabled", True),
                config=entry.get("config", {}),
            )

    return SkillsConfig(discover=discover, plugins=plugins)


def load_plugin_skills(
    skills_dir: Path,
    skills_config: SkillsConfig,
    context: SkillContext,
) -> list[Skill]:
    """Load custom skills using the plugin configuration.

    - ``auto`` mode: load all files, then apply ``configure()`` if config exists.
    - ``manual`` mode: only load files matching enabled entries in skills.yaml.

    Calls ``Skill.configure(config, context)`` for each loaded skill.
    """
    if not skills_dir.is_dir():
        return []

    skills: list[Skill] = []

    if skills_config.discover == "manual":
        skills = _load_manual(skills_dir, skills_config, context)
    else:
        skills = _load_auto(skills_dir, skills_config, context)

    return skills


def _load_auto(
    skills_dir: Path,
    skills_config: SkillsConfig,
    context: SkillContext,
) -> list[Skill]:
    """Auto-discover: load all skills, skip explicitly disabled ones."""
    all_yaml = load_yaml_skills(skills_dir)
    all_python = load_python_skills(skills_dir)
    result: list[Skill] = []

    for skill in all_yaml + all_python:
        entry = skills_config.plugins.get(skill.name)
        # Skip explicitly disabled skills
        if entry and not entry.enabled:
            logger.info("Skipping disabled skill: %s", skill.name)
            continue
        config = entry.config if entry else {}
        _configure_skill(skill, config, context)
        result.append(skill)

    return result


def _load_manual(
    skills_dir: Path,
    skills_config: SkillsConfig,
    context: SkillContext,
) -> list[Skill]:
    """Manual mode: only load skills that are declared and enabled."""
    # Build a map of file stem -> path for quick lookup
    available_py: dict[str, Path] = {}
    available_yaml: dict[str, Path] = {}
    for path in sorted(skills_dir.glob("*.py")):
        if not path.name.startswith("_"):
            available_py[path.stem] = path
    for path in sorted(skills_dir.glob("*.y*ml")):
        if path.name != "skills.yaml":
            available_yaml[path.stem] = path

    result: list[Skill] = []

    for name, entry in skills_config.plugins.items():
        if not entry.enabled:
            logger.info("Skipping disabled plugin: %s", name)
            continue

        loaded: list[Skill] = []

        # Try Python first, then YAML
        if name in available_py:
            try:
                loaded = _load_module_skills(available_py[name])
            except Exception as exc:
                logger.warning("Failed to load plugin %s: %s", name, exc)
                continue
        elif name in available_yaml:
            try:
                with open(available_yaml[name], encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict) and "name" in data:
                    loaded = [YAMLSkill(data)]
            except (yaml.YAMLError, OSError) as exc:
                logger.warning("Failed to load YAML plugin %s: %s", name, exc)
                continue
        else:
            logger.warning("Plugin '%s' declared in skills.yaml but no file found", name)
            continue

        for skill in loaded:
            _configure_skill(skill, entry.config, context)
            result.append(skill)

    return result


def _configure_skill(skill: Skill, config: dict, context: SkillContext) -> None:
    """Call skill.configure() safely."""
    try:
        skill.configure(config, context)
    except Exception as exc:
        logger.warning("Skill '%s' configure() failed: %s", skill.name, exc)


# ---------------------------------------------------------------------------
# YAML Skill Loader (T-021)
# ---------------------------------------------------------------------------

class YAMLSkill(Skill):
    """A Skill defined declaratively in a YAML file.

    YAML format::

        name: greet
        description: "Greet the user"
        aliases: [hi, hello]
        category: custom
        template: "Hello, {{input}}! Have a wonderful day 🌞"
    """

    def __init__(self, definition: dict[str, Any]) -> None:
        self.name = definition["name"]
        self.description = definition.get("description", "")
        self.category = definition.get("category", "custom")
        self.aliases = definition.get("aliases", [])
        self._template: str = definition.get("template", "{{input}}")

    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        output = self._template.replace("{{input}}", input_text)
        # Replace named args
        for key, val in args.items():
            output = output.replace(f"{{{{{key}}}}}", str(val))
        return SkillResult(success=True, output=output)


def load_yaml_skills(skills_dir: Path) -> list[YAMLSkill]:
    """Load all YAML skill definitions from a directory.

    Looks for ``*.yaml`` and ``*.yml`` files in the given directory.
    """
    skills: list[YAMLSkill] = []
    if not skills_dir.is_dir():
        return skills

    for path in sorted(skills_dir.glob("*.y*ml")):
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict) or "name" not in data:
                logger.warning("Skipping invalid YAML skill: %s", path)
                continue
            skill = YAMLSkill(data)
            skills.append(skill)
            logger.info("Loaded YAML skill: %s from %s", skill.name, path.name)
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("Failed to load YAML skill %s: %s", path, exc)

    return skills


# ---------------------------------------------------------------------------
# Python Skill Loader (T-022)
# ---------------------------------------------------------------------------

def load_python_skills(skills_dir: Path) -> list[Skill]:
    """Load custom Python skills from ``*.py`` files in the directory.

    Each file should define one or more classes that subclass ``Skill``.
    The loader discovers all ``Skill`` subclasses in the module.
    """
    skills: list[Skill] = []
    if not skills_dir.is_dir():
        return skills

    for path in sorted(skills_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            loaded = _load_module_skills(path)
            skills.extend(loaded)
        except Exception as exc:
            logger.warning("Failed to load Python skill %s: %s", path, exc)

    return skills


def _load_module_skills(path: Path) -> list[Skill]:
    """Import a Python module from path and find all Skill subclasses."""
    module_name = f"chatmd_custom_skill_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        logger.warning("Cannot load module from %s", path)
        return []

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    skills: list[Skill] = []
    for attr_name in dir(module):
        obj = getattr(module, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, Skill)
            and obj is not Skill
            and hasattr(obj, "name")
            and obj.name
        ):
            try:
                instance = obj()
                skills.append(instance)
                logger.info("Loaded Python skill: %s from %s", instance.name, path.name)
            except Exception as exc:
                logger.warning("Failed to instantiate %s from %s: %s", attr_name, path, exc)

    return skills
