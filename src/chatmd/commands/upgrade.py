"""chatmd upgrade — run config migrations and ensure directory structure."""

from __future__ import annotations

from pathlib import Path

import click

from chatmd.commands.init_workspace import _build_welcome_chat_md
from chatmd.commands.migrations import run_migrations
from chatmd.i18n import t


def run_upgrade(path_str: str, *, full: bool = False) -> None:
    """Upgrade an existing workspace.

    ``--full`` ensures the chatmd/ directory structure is complete
    (creates ``chat.md``, ``chat/``, ``notification.md`` if missing).
    """
    workspace = Path(path_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("upgrade.not_workspace"))
        return

    # Always run config migrations
    messages = run_migrations(workspace)
    for msg in messages:
        click.echo(msg)

    if full:
        _ensure_structure(workspace)
    elif not messages:
        click.echo(t("upgrade.specify_option"))
        click.echo(t("upgrade.full_option"))


def _ensure_structure(workspace: Path) -> None:
    """Ensure chatmd/ directory structure is complete."""
    interact_root = workspace / "chatmd"
    interact_root.mkdir(parents=True, exist_ok=True)

    created: list[str] = []

    chat_md = interact_root / "chat.md"
    if not chat_md.exists():
        chat_md.write_text(_build_welcome_chat_md(), encoding="utf-8")
        created.append("chat.md")

    chat_dir = interact_root / "chat"
    if not chat_dir.exists():
        chat_dir.mkdir(exist_ok=True)
        created.append("chat/")

    notif_md = interact_root / "notification.md"
    if not notif_md.exists():
        notif_md.write_text(
            f"# {t('init.notification_title')}\n\n"
            f"> {t('init.notification_subtitle')}\n\n---\n\n",
            encoding="utf-8",
        )
        created.append("notification.md")

    cron_md = interact_root / "cron.md"
    if not cron_md.exists():
        cron_md.write_text(
            "# Cron Tasks\n\n```cron\n@every 5m /sync\n```\n",
            encoding="utf-8",
        )
        created.append("cron.md")

    if created:
        click.echo(t("upgrade.done", items=", ".join(created)))
    else:
        click.echo(t("upgrade.already_full"))
