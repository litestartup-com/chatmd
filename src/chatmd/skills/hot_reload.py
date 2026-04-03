"""Skill hot-reload — watch .chatmd/skills/ for changes and reload dynamically."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from chatmd.skills.loader import load_python_skills, load_yaml_skills

if TYPE_CHECKING:
    from chatmd.engine.router import Router

logger = logging.getLogger(__name__)


class SkillReloader:
    """Monitors the custom skills directory and reloads on changes.

    Called by the Agent after detecting file changes in ``.chatmd/skills/``.
    Supports both YAML and Python skill files.
    """

    def __init__(self, skills_dir: Path, router: Router) -> None:
        self._skills_dir = skills_dir
        self._router = router
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

        Returns the number of skills loaded.
        """
        logger.info("Reloading custom skills from %s", self._skills_dir)
        self._loaded_names.clear()
        return self.load_all()

    def get_loaded_names(self) -> list[str]:
        """Return names of all currently loaded custom skills."""
        return sorted(self._loaded_names)
