"""Skill loaders — load custom Skills from YAML definitions and Python modules."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

import yaml

from chatmd.skills.base import Skill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


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
