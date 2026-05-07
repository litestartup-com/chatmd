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
@click.option(
    "--profile",
    type=click.Choice(["basic", "personal", "twin"]),
    default="basic",
    show_default=True,
    help="Workspace profile to initialize.",
)
@click.option(
    "--language",
    type=click.Choice(["en", "cn"]),
    default="en",
    show_default=True,
    help="Initial content language.",
)
def init(path: str, no_git: bool, profile: str, language: str) -> None:
    """Initialize a ChatMD workspace at PATH."""
    from chatmd.commands.init_workspace import run_init

    run_init(path, no_git=no_git, profile=profile, language=language)


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


@service.command("start")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def service_start(workspace: str) -> None:
    """Start the ChatMD Agent system service."""
    from chatmd.commands.service import run_service_start

    run_service_start(workspace)


@service.command("stop")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def service_stop(workspace: str) -> None:
    """Stop the ChatMD Agent system service (does not uninstall)."""
    from chatmd.commands.service import run_service_stop

    run_service_stop(workspace)


@service.command("restart")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def service_restart(workspace: str) -> None:
    """Restart the ChatMD Agent system service."""
    from chatmd.commands.service import run_service_restart

    run_service_restart(workspace)


@main.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
@click.option(
    "--category",
    "-c",
    "categories",
    multiple=True,
    help="Only run checks in the given category (repeatable).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show per-check details and enable opt-in smoke tests.",
)
@click.option(
    "--no-network",
    is_flag=True,
    default=False,
    help="Skip checks that require network access.",
)
def doctor(
    workspace: str,
    categories: tuple[str, ...],
    verbose: bool,
    no_network: bool,
) -> None:
    """Run environment and workspace health checks."""
    from chatmd.commands.doctor import run_doctor

    exit_code = run_doctor(
        workspace,
        categories=categories,
        verbose=verbose,
        no_network=no_network,
    )
    sys.exit(exit_code)


@main.group("config")
def config_group() -> None:
    """View and modify ChatMD configuration."""


@config_group.command("list")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def config_list(workspace: str) -> None:
    """List all configuration values."""
    from chatmd.commands.config_cmd import run_config_list

    run_config_list(workspace)


@config_group.command("get")
@click.argument("key")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def config_get(key: str, workspace: str) -> None:
    """Get a configuration value by key."""
    from chatmd.commands.config_cmd import run_config_get

    run_config_get(workspace, key)


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def config_set(key: str, value: str, workspace: str) -> None:
    """Set a configuration value."""
    from chatmd.commands.config_cmd import run_config_set

    run_config_set(workspace, key, value)


@config_group.command("init")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    default=".",
    help="Workspace directory (default: current dir).",
)
def config_init(workspace: str) -> None:
    """Interactive configuration wizard."""
    from chatmd.commands.config_cmd import run_config_init

    run_config_init(workspace)
