"""Skill hot-reload — watch .chatmd/skills/ for changes and reload dynamically."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from chatmd.skills.base import SkillContext
from chatmd.skills.loader import (
    load_plugin_skills,
    load_python_skills,
    load_skills_config,
    load_yaml_skills,
)

if TYPE_CHECKING:
    from chatmd.engine.router import Router

logger = logging.getLogger(__name__)


class SkillReloader:
    """Monitors the custom skills directory and reloads on changes.

    Called by the Agent after detecting file changes in ``.chatmd/skills/``.
    Supports both YAML and Python skill files.
    Uses ``skills.yaml`` plugin configuration when available.
    """

    def __init__(
        self,
        skills_dir: Path,
        router: Router,
        chatmd_dir: Path | None = None,
        context: SkillContext | None = None,
    ) -> None:
        self._skills_dir = skills_dir
        self._router = router
        self._chatmd_dir = chatmd_dir or skills_dir.parent
        self._context = context
        self._loaded_names: set[str] = set()

    @property
    def skills_dir(self) -> Path:
        return self._skills_dir

    @property
    def loaded_count(self) -> int:
        return len(self._loaded_names)

    def load_all(self) -> int:
        """Load (or reload) all custom skills from the directory.

        Returns the number of skills loaded.
        """
        if not self._skills_dir.is_dir():
            return 0

        # Use plugin-aware loading if context is available
        if self._context is not None:
            skills_config = load_skills_config(self._chatmd_dir)
            skills = load_plugin_skills(self._skills_dir, skills_config, self._context)
            for skill in skills:
                self._router.register(skill)
                self._loaded_names.add(skill.name)
            logger.info("Loaded %d custom skills from %s", len(skills), self._skills_dir)
            return len(skills)

        # Fallback: legacy loading (no plugin config)
        count = 0

        # Load YAML skills
        for skill in load_yaml_skills(self._skills_dir):
            self._router.register(skill)
            self._loaded_names.add(skill.name)
            count += 1

        # Load Python skills
        for skill in load_python_skills(self._skills_dir):
            self._router.register(skill)
            self._loaded_names.add(skill.name)
            count += 1

        logger.info("Loaded %d custom skills from %s", count, self._skills_dir)
        return count

    def reload(self) -> int:
        """Reload all custom skills (full refresh).

        Calls teardown() on previously loaded skills before reloading.
        Returns the number of skills loaded.
        """
        logger.info("Reloading custom skills from %s", self._skills_dir)
        # Teardown and unregister old skills
        for name in self._loaded_names:
            skill = self._router.get_skill(name)
            if skill is not None:
                try:
                    skill.teardown()
                except Exception as exc:
                    logger.warning("Skill '%s' teardown() failed: %s", name, exc)
            self._router.unregister(name)
        self._loaded_names.clear()
        return self.load_all()

    def get_loaded_names(self) -> list[str]:
        """Return names of all currently loaded custom skills."""
        return sorted(self._loaded_names)
