"""ChatMD CLI entry point using Click."""

from __future__ import annotations

import io
import os
import sys

import click

from chatmd import __version__


def _ensure_utf8_stdout() -> None:
    """Reconfigure stdout/stderr to UTF-8 on Windows to avoid GBK encoding errors."""
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        else:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace"
            )
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        else:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding="utf-8", errors="replace"
            )


_ensure_utf8_stdout()


@click.group()
@click.version_option(version=__version__, prog_name="chatmd")
def main() -> None:
    """ChatMD — A local-first, text-driven personal AI Agent engine."""


@main.command()
@click.argument("path", type=click.Path())
@click.option("--no-git", is_flag=True, default=False, help="Skip Git initialization.")
def init(path: str, no_git: bool) -> None:
    """Initialize a ChatMD workspace at PATH."""
    from chatmd.commands.init_workspace import run_init

    run_init(path, no_git=no_git)


@main.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
@click.option(
    "--daemon",
    "-d",
    is_flag=True,
    default=False,
    help="Run Agent in the background (detached process).",
)
def start(workspace: str, daemon: bool) -> None:
    """Start the ChatMD Agent."""
    from chatmd.commands.agent_lifecycle import run_start, run_start_daemon

    if daemon:
        run_start_daemon(workspace)
    else:
        run_start(workspace)


@main.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def stop(workspace: str) -> None:
    """Stop the ChatMD Agent."""
    from chatmd.commands.agent_lifecycle import run_stop

    run_stop(workspace)


@main.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def status(workspace: str) -> None:
    """Show Agent status."""
    from chatmd.commands.agent_lifecycle import run_status

    run_status(workspace)


@main.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def restart(workspace: str) -> None:
    """Restart the ChatMD Agent (stop + start daemon)."""
    from chatmd.commands.agent_lifecycle import run_restart

    run_restart(workspace)


@main.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
@click.option("--full", is_flag=True, default=False, help="Upgrade to full workspace mode.")
def upgrade(workspace: str, full: bool) -> None:
    """Upgrade an existing ChatMD workspace."""
    from chatmd.commands.upgrade import run_upgrade

    run_upgrade(workspace, full=full)


@main.command()
@click.argument("mode", type=click.Choice(["suffix", "save"]), required=False)
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def mode(mode: str | None, workspace: str) -> None:
    """Show or switch trigger mode (suffix / save)."""
    from chatmd.commands.mode import run_mode

    run_mode(workspace, mode)


@main.group()
def service() -> None:
    """Manage system service (auto-start on boot)."""


@service.command("install")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def service_install(workspace: str) -> None:
    """Install ChatMD Agent as a system service."""
    from chatmd.commands.service import run_service_install

    run_service_install(workspace)


@service.command("uninstall")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=None,
    help="Workspace directory. Omit to use --all.",
)
@click.option(
    "--all",
    "uninstall_all",
    is_flag=True,
    default=False,
    help="Uninstall all ChatMD services.",
)
def service_uninstall(workspace: str | None, uninstall_all: bool) -> None:
    """Uninstall ChatMD Agent system service."""
    if uninstall_all:
        from chatmd.commands.service import run_service_uninstall_all
        run_service_uninstall_all()
    elif workspace:
        from chatmd.commands.service import run_service_uninstall
        run_service_uninstall(workspace)
    else:
        # Default: uninstall current dir workspace
        from chatmd.commands.service import run_service_uninstall
        run_service_uninstall(".")


@service.command("status")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=None,
    help="Workspace directory. Omit to list all services.",
)
def service_status(workspace: str | None) -> None:
    """Show ChatMD Agent system service status."""
    from chatmd.commands.service import run_service_status

    run_service_status(workspace)
