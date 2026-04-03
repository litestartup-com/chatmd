"""ChatMD custom exceptions."""


class ChatMDError(Exception):
    """Base exception for all ChatMD errors."""


class WorkspaceError(ChatMDError):
    """Workspace-related errors (init, not found, etc.)."""


class ConfigError(ChatMDError):
    """Configuration loading or validation errors."""


class ParseError(ChatMDError):
    """Command parsing errors."""


class RouteError(ChatMDError):
    """Command routing errors (skill not found, etc.)."""


class SkillError(ChatMDError):
    """Skill execution errors."""


class FileWriteError(ChatMDError):
    """File write operation errors."""


class AgentError(ChatMDError):
    """Agent lifecycle errors."""
