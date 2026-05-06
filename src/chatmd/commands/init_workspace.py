"""chatmd init — workspace initialization command."""

from __future__ import annotations

import subprocess
from copy import deepcopy
from pathlib import Path

import click
import yaml

from chatmd.i18n import set_locale, t


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


_ALLOWED_PROFILES = {"basic", "personal", "twin"}
_ALLOWED_LANGUAGES = {"en", "cn"}
_BASIC_INTERACTION_ROOT = "chatmd"
_PROFILE_INTERACTION_ROOT = "A-ChatMD"

_PERSONAL_ROOTS: dict[str, str] = {
    "agent": "A-ChatMD",
    "dashboard": "B-Dashboard",
    "inbox": "C-Inbox",
    "daily": "D-Daily",
    "projects": "E-Projects",
    "notes": "K-Notes",
    "resources": "L-Resources",
    "archive": "Z-Archive",
}

_TWIN_EXTRA_ROOTS: dict[str, str] = {
    "people": "F-People",
    "goals": "G-Goals",
    "habits": "H-Habits",
    "decisions": "I-Decisions",
    "health": "J-Health",
}

_DEFAULT_AGENT_YAML: dict = {
    "version": "0.2.9",
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


def _write_text_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _build_agent_yaml(interaction_root: str) -> dict:
    data = deepcopy(_DEFAULT_AGENT_YAML)
    data["watcher"]["watch_dirs"] = [f"{interaction_root}/"]
    return data


def _build_user_yaml(language: str) -> dict:
    data = deepcopy(_DEFAULT_USER_YAML)
    data["language"] = language
    return data


def _write_core_configs(chatmd_dir: Path, agent_yaml: dict, user_yaml: dict) -> None:
    _write_yaml(chatmd_dir / "agent.yaml", agent_yaml)
    _write_yaml(chatmd_dir / "user.yaml", user_yaml)

    example_agent = chatmd_dir / "agent.yaml.example"
    if not example_agent.exists():
        _write_yaml(example_agent, agent_yaml)
    example_user = chatmd_dir / "user.yaml.example"
    if not example_user.exists():
        _write_yaml(example_user, user_yaml)


def _create_runtime_dirs(chatmd_dir: Path) -> None:
    for sub in ("skills", "memory", "logs", "history", "state"):
        (chatmd_dir / sub).mkdir(exist_ok=True)


def _create_agent_workspace(workspace: Path, interaction_root: str) -> None:
    interact_root = workspace / interaction_root
    interact_root.mkdir(parents=True, exist_ok=True)

    _write_text_if_missing(interact_root / "README.md", t("init.interaction.readme"))
    _write_text_if_missing(interact_root / "chat.md", _build_welcome_chat_md())
    (interact_root / "chat").mkdir(exist_ok=True)
    _write_text_if_missing(
        interact_root / "notification.md",
        f"# {t('init.notification_title')}\n\n"
        f"> {t('init.notification_subtitle')}\n\n---\n\n",
    )
    _write_text_if_missing(
        interact_root / "cron.md",
        "# Cron Tasks\n\n```cron\n@every 5m /sync\n```\n",
    )


def _build_roots(profile: str) -> dict[str, str]:
    roots = dict(_PERSONAL_ROOTS)
    if profile == "twin":
        roots.update(_TWIN_EXTRA_ROOTS)
    return roots


def _build_kb_yaml(profile: str, language: str, roots: dict[str, str]) -> dict:
    return {
        "version": "0.1",
        "profile": profile,
        "language": language,
        "index_style": {
            "top_level": "letter",
            "secondary": "number",
        },
        "roots": roots,
        "entrypoints": {
            "chat": "A-ChatMD/chat.md",
            "cron": "A-ChatMD/cron.md",
            "notification": "A-ChatMD/notification.md",
        },
        "write_targets": {
            "inbox": "C-Inbox",
            "attachments": "C-Inbox/02-Assets",
            "ai_conversations": "C-Inbox/ai_conversations.md",
            "daily": "D-Daily/01-Daily-Notes",
            "reports": "D-Daily/03-Reports",
        },
        "enabled_modules": list(roots.keys()),
    }


def _build_privacy_yaml(profile: str) -> dict:
    sensitive_roots: list[dict[str, str]] = []
    if profile == "twin":
        sensitive_roots = [
            {
                "root": "F-People",
                "sync": "exclude_by_default",
                "ai_context": "exclude_by_default",
            },
            {
                "root": "J-Health",
                "sync": "exclude_by_default",
                "ai_context": "exclude_by_default",
            },
        ]
    return {
        "version": "0.1",
        "profile": profile,
        "sensitive_roots": sensitive_roots,
        "sync_policy": {
            "default": "include",
            "sensitive": "exclude_by_default",
        },
        "ai_context_policy": {
            "default": "allow",
            "sensitive": "exclude_by_default",
        },
    }


def _create_profile_dirs(workspace: Path, roots: dict[str, str], profile: str) -> None:
    for root in roots.values():
        (workspace / root).mkdir(parents=True, exist_ok=True)

    for directory in (
        "C-Inbox/02-Assets",
        "D-Daily/01-Daily-Notes",
        "D-Daily/02-Weekly-Reviews",
        "D-Daily/03-Reports",
        "E-Projects/01-Active",
        "E-Projects/02-Someday",
        "K-Notes/01-Ideas",
        "K-Notes/02-Books",
        "K-Notes/03-Meetings",
        "K-Notes/04-Learnings",
        "L-Resources/01-Templates",
        "L-Resources/02-Assets",
        "L-Resources/03-References",
        "L-Resources/04-Tools",
        "Z-Archive/01-Completed",
        "Z-Archive/02-Archived",
    ):
        (workspace / directory).mkdir(parents=True, exist_ok=True)

    if profile == "twin":
        for directory in (
            "F-People/01-Contacts",
            "G-Goals/01-Yearly",
            "H-Habits/01-Trackers",
            "I-Decisions/01-Decision-Logs",
            "J-Health/01-Logs",
        ):
            (workspace / directory).mkdir(parents=True, exist_ok=True)


def _write_profile_files(workspace: Path, profile: str) -> None:
    _write_text_if_missing(workspace / "README.md", t("init.profile.readme"))
    readmes = {
        "C-Inbox/README.md": "init.profile.inbox_readme",
        "E-Projects/README.md": "init.profile.projects_readme",
        "K-Notes/README.md": "init.profile.notes_readme",
        "Z-Archive/README.md": "init.profile.archive_readme",
    }
    if profile == "twin":
        readmes.update({
            "F-People/README.md": "init.profile.people_readme",
            "G-Goals/README.md": "init.profile.goals_readme",
            "H-Habits/README.md": "init.profile.habits_readme",
            "J-Health/README.md": "init.profile.health_readme",
        })
    for relative_path, key in readmes.items():
        _write_text_if_missing(workspace / relative_path, t(key))

    _write_text_if_missing(
        workspace / "B-Dashboard" / "Home.md",
        t("init.profile.dashboard_home"),
    )
    _write_text_if_missing(
        workspace / "B-Dashboard" / "Today.md",
        t("init.profile.dashboard_today"),
    )
    _write_text_if_missing(
        workspace / "B-Dashboard" / "Knowledge-Map.md",
        t("init.profile.knowledge_map"),
    )

    templates = {
        "daily.md": "init.template.daily",
        "note.md": "init.template.note",
        "project.md": "init.template.project",
        "meeting.md": "init.template.meeting",
        "decision.md": "init.template.decision",
        "weekly-review.md": "init.template.weekly_review",
        "report.md": "init.template.report",
        "output.md": "init.template.output",
    }
    if profile == "twin":
        templates.update({
            "person.md": "init.template.person",
            "goal.md": "init.template.goal",
            "habit.md": "init.template.habit",
            "health-log.md": "init.template.health_log",
            "life-review.md": "init.template.life_review",
            "identity.md": "init.template.identity",
            "monthly-review.md": "init.template.monthly_review",
            "quarterly-review.md": "init.template.quarterly_review",
        })
    templates_dir = workspace / "L-Resources" / "01-Templates"
    for filename, key in templates.items():
        _write_text_if_missing(templates_dir / filename, t(key))


def run_init(
    path_str: str,
    *,
    no_git: bool = False,
    profile: str = "basic",
    language: str = "en",
) -> None:
    """Execute the ``chatmd init`` command."""
    if profile not in _ALLOWED_PROFILES:
        raise click.BadParameter(f"Unsupported profile: {profile}")
    if language not in _ALLOWED_LANGUAGES:
        raise click.BadParameter(f"Unsupported language: {language}")

    set_locale(language)
    workspace = Path(path_str).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    chatmd_dir = workspace / ".chatmd"
    chatmd_dir.mkdir(exist_ok=True)

    interaction_root = (
        _BASIC_INTERACTION_ROOT if profile == "basic" else _PROFILE_INTERACTION_ROOT
    )
    _write_core_configs(
        chatmd_dir,
        _build_agent_yaml(interaction_root),
        _build_user_yaml(language),
    )
    _create_runtime_dirs(chatmd_dir)
    _create_agent_workspace(workspace, interaction_root)

    if profile != "basic":
        roots = _build_roots(profile)
        _create_profile_dirs(workspace, roots, profile)
        _write_profile_files(workspace, profile)
        _write_yaml(chatmd_dir / "kb.yaml", _build_kb_yaml(profile, language, roots))
        _write_yaml(chatmd_dir / "privacy.yaml", _build_privacy_yaml(profile))

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
