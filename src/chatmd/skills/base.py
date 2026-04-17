"""Skill base classes and data structures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from chatmd.i18n import t

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class SkillResult:
    """Result returned by a Skill execution.

    Fields:
        success: True if the skill completed its intended operation.
        output: Text to write back to the markdown file.
        error: Error message when success=False AND the failure is a real error.
        metadata: Optional structured data (bind_code, task_id, etc.).
        informational: True when success=False is used purely as control flow
            (e.g. "already bound", "missing token" help) and should not be
            audited as a failure. Defaults to False.
    """

    success: bool
    output: str
    error: str | None = None
    metadata: dict | None = None
    informational: bool = False


@dataclass
class ParamDef:
    """Parameter definition for a Skill."""

    name: str
    type: str = "string"
    required: bool = False
    default: str | None = None
    position: int | None = None
    choices: list[str] | None = None
    description: str = ""


@dataclass
class SkillContext:
    """Execution context injected by the Agent engine."""

    source_file: Path
    source_line: int
    workspace: Path
    interaction_root: Path | None = None


class Skill(ABC):
    """Base class for all Skills."""

    name: str = ""
    description: str = ""
    category: str = "general"
    requires_network: bool = False
    is_async: bool = False
    is_dangerous: bool = False
    aliases: list[str] = []
    params_schema: list[ParamDef] = []

    def configure(self, config: dict, context: SkillContext) -> None:
        """Optional lifecycle hook — called after instantiation, before registration.

        Args:
            config: Plugin-specific config from skills.yaml.
            context: Workspace context (workspace path, interaction_root, etc.).
        """

    def teardown(self) -> None:
        """Optional cleanup hook — called when skill is unloaded/disabled."""

    @abstractmethod
    def execute(self, input_text: str, args: dict, context: SkillContext) -> SkillResult:
        """Execute the skill and return a result."""
        ...

    def help(self) -> str:
        """Return usage help text (called by /help <command>)."""
        key = f"skill.{self.name}.description"
        localized = t(key)
        # If t() returns the key itself, no i18n entry exists — use raw description
        return localized if localized != key else self.description
