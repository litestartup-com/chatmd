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
    "version": "0.2.8",
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
        "confirm": {
            "enabled": False,
            "commands": ["/sync", "/upload", "/new", "/upgrade", "/notify"],
        },
    },
    "watcher": {
        "debounce_ms": 300,
        "watch_dirs": ["chatmd/"],
        "ignore_patterns": ["_index.md"],
    },
    "commands": {"prefix": "/"},
    "async": {"max_concurrent": 3, "timeout": 60},
    "sync": {"mode": "git"},
    "logging": {"level": "INFO", "audit": True},
    "cron": {"enabled": True, "cron_file": "cron.md"},
    "notification": {
        "enabled": True,
        "notification_file": "notification.md",
        "system_notify": False,
    },
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
# ChatMD config (may contain API keys — use agent.yaml.example as template)
.chatmd/agent.yaml
.chatmd/user.yaml

# ChatMD runtime (do not sync — causes merge conflicts)
.chatmd/agent.pid
.chatmd/stop.signal
.chatmd/state/
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


def _write_yaml(path: Path, data: dict) -> None:
    """Write a dict to a YAML file with UTF-8 encoding."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def run_init(path_str: str, *, no_git: bool = False) -> None:
    """Execute the ``chatmd init`` command."""
    workspace = Path(path_str).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    chatmd_dir = workspace / ".chatmd"
    chatmd_dir.mkdir(exist_ok=True)

    # Write config files (gitignored — contain real keys)
    _write_yaml(chatmd_dir / "agent.yaml", _DEFAULT_AGENT_YAML)
    _write_yaml(chatmd_dir / "user.yaml", _DEFAULT_USER_YAML)

    # Write example configs (committed to git — safe templates for collaborators)
    example_agent = chatmd_dir / "agent.yaml.example"
    if not example_agent.exists():
        _write_yaml(example_agent, _DEFAULT_AGENT_YAML)
    example_user = chatmd_dir / "user.yaml.example"
    if not example_user.exists():
        _write_yaml(example_user, _DEFAULT_USER_YAML)

    # Create .chatmd subdirectories
    for sub in ("skills", "memory", "logs", "history", "state"):
        (chatmd_dir / sub).mkdir(exist_ok=True)

    # Create interaction directory (chatmd/)
    interact_root = workspace / "chatmd"
    interact_root.mkdir(parents=True, exist_ok=True)

    # Create chat.md
    chat_md = interact_root / "chat.md"
    if not chat_md.exists():
        chat_md.write_text(_build_welcome_chat_md(), encoding="utf-8")

    # Create chat/ directory
    chat_dir = interact_root / "chat"
    chat_dir.mkdir(exist_ok=True)

    # Create notification.md
    notif_md = interact_root / "notification.md"
    if not notif_md.exists():
        notif_md.write_text(
            f"# {t('init.notification_title')}\n\n"
            f"> {t('init.notification_subtitle')}\n\n---\n\n",
            encoding="utf-8",
        )

    # Create cron.md with /sync job if git sync is enabled
    cron_md = interact_root / "cron.md"
    if not cron_md.exists():
        cron_md.write_text(
            "# Cron Tasks\n\n```cron\n@every 5m /sync\n```\n",
            encoding="utf-8",
        )

    # Git init
    if not no_git:
        _init_git(workspace)

    click.echo(t("init.workspace_created", workspace=workspace))
    click.echo(t("init.run_start"))
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
