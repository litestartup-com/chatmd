"""chatmd init — workspace initialization command."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import yaml

from chatmd.i18n import t


def _build_welcome_chat_md() -> str:
    """Build the welcome chat.md content using i18n strings."""
    return (
        f"{t('init.welcome_title')}\n\n"
        f"{t('init.welcome_subtitle')}\n\n"
        "---\n\n"
        f"{t('init.welcome_quickstart_header')}\n\n"
        f"{t('init.welcome_commands_intro')}\n\n"
        "```\n"
        f"{t('init.welcome_help')}\n"
        f"{t('init.welcome_date')}\n"
        f"{t('init.welcome_ask')}\n"
        f"{t('init.welcome_status')}\n"
        "```\n\n"
        f"{t('init.welcome_instruction')}\n\n"
        "---\n\n"
    )

_DEFAULT_AGENT_YAML: dict = {
    "version": "0.1",
    "workspace": {"mode": "full"},
    "ai": {
        "providers": [
            {
                "name": "litestartup",
                "type": "litestartup",
                "api_url": "https://api.litestartup.com/client/v2/ai/chat",
                "api_key": "${LITEAGENT_API_KEY}",
                "model": "default",
                "timeout": 60,
                "is_default": True,
            }
        ],
    },
    "trigger": {
        "signals": [
            {"type": "file_save", "debounce_ms": 800},
            {"type": "suffix", "marker": ";", "enabled": False},
        ],
    },
    "watcher": {
        "debounce_ms": 300,
        "watch_files": ["chat.md"],
        "watch_dirs": ["chat/"],
        "ignore_patterns": ["_index.md"],
    },
    "commands": {"prefix": "/"},
    "async": {"max_concurrent": 3, "timeout": 60},
    "sync": {"mode": "git", "auto_commit": True, "interval": 300},
    "logging": {"level": "INFO", "audit": True},
}

_DEFAULT_USER_YAML: dict = {
    "language": "en",
    "aliases": {
        "en": "translate(English)",
        "jp": "translate(Japanese)",
        "cn": "translate(Chinese)",
        "q": "ask",
    },
}

_GITIGNORE = """\
# ChatMD runtime
.chatmd/state.json
.chatmd/tasks.json
.chatmd/queue.json
.chatmd/logs/
.chatmd/memory/_index.json

# Python
__pycache__/
*.pyc
.venv/
"""


def _resolve_mode(workspace: Path, mode: str | None) -> str:
    """Determine workspace mode — full or assistant."""
    if mode is not None:
        return mode

    has_files = any(workspace.iterdir()) if workspace.exists() else False
    if not has_files:
        return "full"

    # Interactive prompt when directory has existing files
    return click.prompt(
        t("init.mode_prompt"),
        type=click.Choice(["full", "assistant"]),
        default="assistant",
    )


def _write_yaml(path: Path, data: dict) -> None:
    """Write a dict to a YAML file with UTF-8 encoding."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def run_init(path_str: str, *, mode: str | None = None, no_git: bool = False) -> None:
    """Execute the ``chatmd init`` command."""
    workspace = Path(path_str).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    resolved_mode = _resolve_mode(workspace, mode)

    chatmd_dir = workspace / ".chatmd"
    chatmd_dir.mkdir(exist_ok=True)

    # Always create config
    agent_config = _DEFAULT_AGENT_YAML.copy()
    agent_config["workspace"] = {"mode": resolved_mode}
    if resolved_mode == "assistant":
        agent_config["watcher"] = {
            "debounce_ms": 300,
            "watch_files": [],
            "watch_dirs": ["."],
            "ignore_patterns": ["_index.md"],
        }
    _write_yaml(chatmd_dir / "agent.yaml", agent_config)
    _write_yaml(chatmd_dir / "user.yaml", _DEFAULT_USER_YAML)

    # Create subdirectories
    for sub in ("skills", "memory", "logs", "history"):
        (chatmd_dir / sub).mkdir(exist_ok=True)

    if resolved_mode == "full":
        # Create chat.md
        chat_md = workspace / "chat.md"
        if not chat_md.exists():
            chat_md.write_text(_build_welcome_chat_md(), encoding="utf-8")

        # Create chat/ directory
        chat_dir = workspace / "chat"
        chat_dir.mkdir(exist_ok=True)

    # Git init
    if not no_git:
        _init_git(workspace)

    click.echo(t("init.workspace_created", workspace=workspace, mode=resolved_mode))
    click.echo(t("init.run_start"))
    if resolved_mode == "full":
        click.echo(t("init.open_chat"))


def _init_git(workspace: Path) -> None:
    """Initialize a Git repo if not already one."""
    git_dir = workspace / ".git"
    if git_dir.exists():
        return

    try:
        subprocess.run(["git", "init"], cwd=workspace, capture_output=True, check=True)
        gitignore = workspace / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(_GITIGNORE, encoding="utf-8")
    except FileNotFoundError:
        click.echo(t("init.git_not_installed"))
    except subprocess.CalledProcessError as exc:
        click.echo(t("init.git_failed", error=exc))
