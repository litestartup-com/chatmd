"""chatmd mode — show or switch trigger mode (suffix / save)."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from chatmd.i18n import t


def run_mode(workspace_str: str, mode: str | None) -> None:
    """Show current trigger mode, or switch to *mode* ('suffix' or 'save')."""
    workspace = Path(workspace_str).resolve()
    chatmd_dir = workspace / ".chatmd"

    if not chatmd_dir.is_dir():
        click.echo(t("cli.not_workspace", workspace=workspace))
        sys.exit(1)

    from chatmd.infra.config import Config

    config = Config(workspace)

    if mode is None:
        # Show current mode
        current = config.get_trigger_mode()
        if current == "suffix":
            marker = config.get_suffix_marker()
            click.echo(t("mode.current_suffix", marker=marker))
        else:
            click.echo(t("mode.current_save"))
        return

    # Switch mode
    config.update_trigger_mode(mode)

    if mode == "suffix":
        marker = config.get_suffix_marker()
        click.echo(t("mode.switched_suffix", marker=marker))
    else:
        click.echo(t("mode.switched_save"))
