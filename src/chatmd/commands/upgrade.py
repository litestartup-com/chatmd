"""chatmd upgrade — upgrade an assistant workspace to full mode."""

from __future__ import annotations

from pathlib import Path

import click

from chatmd.commands.init_workspace import _build_welcome_chat_md
from chatmd.i18n import t


def run_upgrade(path_str: str, *, full: bool = False) -> None:
    """Upgrade an existing workspace.

    ``--full`` converts an assistant-mode workspace to full mode
    (creates ``chat.md`` and ``chat/`` directory).
    """
    workspace = Path(path_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("upgrade.not_workspace"))
        return

    if full:
        _upgrade_to_full(workspace)
    else:
        click.echo(t("upgrade.specify_option"))
        click.echo(t("upgrade.full_option"))


def _upgrade_to_full(workspace: Path) -> None:
    """Convert assistant workspace to full mode."""
    chat_md = workspace / "chat.md"
    chat_dir = workspace / "chat"

    created: list[str] = []

    if not chat_md.exists():
        chat_md.write_text(_build_welcome_chat_md(), encoding="utf-8")
        created.append("chat.md")

    if not chat_dir.exists():
        chat_dir.mkdir(exist_ok=True)
        created.append("chat/")

    # Update agent.yaml mode
    agent_yaml = workspace / ".chatmd" / "agent.yaml"
    if agent_yaml.exists():
        import yaml

        with open(agent_yaml, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        config.setdefault("workspace", {})["mode"] = "full"
        with open(agent_yaml, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        created.append("agent.yaml (mode → full)")

    if created:
        click.echo(t("upgrade.done", items=", ".join(created)))
    else:
        click.echo(t("upgrade.already_full"))
