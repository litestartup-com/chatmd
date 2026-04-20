"""`chatmd doctor` — environment and workspace diagnostics.

The *doctor* subcommand runs a series of read-only health checks against a
workspace and reports any inconsistencies that would prevent the Agent from
working correctly (wrong Python version, missing dependencies, corrupted
config, stale PID files, unreachable AI provider, etc.).

Design goals
------------
1. **Zero side effects** — doctor only observes; it never mutates disk state,
   starts/stops services, or calls APIs that cost money (unless ``-v`` opts
   in to smoke tests).
2. **Composable** — each check is a pure ``Check`` object producing a
   :class:`CheckResult`.  Checks are grouped by ``category`` so users can
   filter with ``--category``.
3. **Extensible** — future plugins or custom checks can register via
   :func:`register_check`; internally the doctor builds its list by calling
   :func:`default_checks`.
4. **Stable exit codes** — 0 when everything is ok, 1 when warnings exist,
   2 when any error exists.  CI pipelines can branch on these.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal, Protocol

import click

from chatmd.i18n import t

Status = Literal["ok", "warn", "error", "skip"]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Outcome of a single health check.

    Attributes:
        name: Short human-readable label (e.g. "Python version").
        category: Grouping key used by ``--category``.
        status: One of ``ok`` / ``warn`` / ``error`` / ``skip``.
        message: One-line summary shown always.
        details: Multi-line details shown only in verbose mode.
        fix_hint: Optional actionable command the user can copy-paste.
    """

    name: str
    category: str
    status: Status
    message: str
    details: list[str] = field(default_factory=list)
    fix_hint: str | None = None


class Check(Protocol):
    """Protocol for a single doctor check.

    Implementations can be any callable with matching signature; they don't
    have to be classes.  The ``run`` is expected to be side-effect free.
    """

    name: str
    category: str

    def run(self, workspace: Path) -> CheckResult: ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


CheckFactory = Callable[[], Check]
_REGISTRY: list[CheckFactory] = []


def register_check(factory: CheckFactory) -> CheckFactory:
    """Register a check factory.  Decorator-friendly."""
    _REGISTRY.append(factory)
    return factory


def default_checks() -> list[Check]:
    """Return the current list of registered checks."""
    return [factory() for factory in _REGISTRY]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_STATUS_SYMBOL: dict[Status, str] = {
    "ok": "✅",
    "warn": "⚠️ ",
    "error": "❌",
    "skip": "⏭️ ",
}


def _render_result(result: CheckResult, *, verbose: bool) -> None:
    symbol = _STATUS_SYMBOL[result.status]
    click.echo(f"  {symbol} {result.name}: {result.message}")
    if verbose and result.details:
        for line in result.details:
            click.echo(f"       {line}")
    if result.fix_hint and result.status in {"warn", "error"}:
        click.echo(f"       {t('doctor.fix_hint_label')} {result.fix_hint}")


def _render_summary(results: list[CheckResult]) -> None:
    ok = sum(1 for r in results if r.status == "ok")
    warn = sum(1 for r in results if r.status == "warn")
    err = sum(1 for r in results if r.status == "error")
    skip = sum(1 for r in results if r.status == "skip")
    click.echo("")
    click.echo(
        t(
            "doctor.summary",
            ok=ok,
            warn=warn,
            error=err,
            skip=skip,
        )
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_doctor(
    workspace_str: str,
    *,
    categories: tuple[str, ...] = (),
    verbose: bool = False,
    no_network: bool = False,
    checks: list[Check] | None = None,
) -> int:
    """Run all applicable checks against *workspace_str* and return an exit code.

    Exit codes:
        0 — all checks ok (or skipped)
        1 — at least one warning, no errors
        2 — at least one error
    """
    workspace = Path(workspace_str).resolve()

    click.echo(t("doctor.header", workspace=workspace))

    registry = checks if checks is not None else default_checks()

    if categories:
        registry = [c for c in registry if c.category in categories]

    # Group checks by category to emit a section header per group
    results: list[CheckResult] = []
    grouped: dict[str, list[Check]] = {}
    for check in registry:
        grouped.setdefault(check.category, []).append(check)

    for category, group in grouped.items():
        click.echo("")
        click.echo(t(f"doctor.category.{category}"))
        for check in group:
            # Checks can opt into the no-network flag by accepting an extra
            # attribute ``requires_network``; if True and no_network is set
            # we short-circuit to a skip result.
            requires_network = getattr(check, "requires_network", False)
            if no_network and requires_network:
                result = CheckResult(
                    name=check.name,
                    category=check.category,
                    status="skip",
                    message=t("doctor.skipped_no_network"),
                )
            else:
                try:
                    result = check.run(workspace)
                except Exception as exc:  # pragma: no cover - defensive
                    result = CheckResult(
                        name=check.name,
                        category=check.category,
                        status="error",
                        message=t("doctor.check_crashed", error=str(exc)),
                    )
            results.append(result)
            _render_result(result, verbose=verbose)

    _render_summary(results)

    if any(r.status == "error" for r in results):
        return 2
    if any(r.status == "warn" for r in results):
        return 1
    return 0


# ===========================================================================
# Built-in checks
# ===========================================================================


# ---------------------------------------------------------------------------
# Environment: Python version & required dependencies
# ---------------------------------------------------------------------------


# Keep in sync with pyproject.toml [project] dependencies.
# Tuple: (distribution_name, minimum_version).  ``None`` minimum means only
# existence is required.
_REQUIRED_DEPS: tuple[tuple[str, str | None], ...] = (
    ("click", "8.1"),
    ("watchdog", "3.0"),
    ("pyyaml", "6.0"),
    ("httpx", "0.25"),
)

# Windows-only optional dependency.
_WIN_OPTIONAL_DEPS: tuple[tuple[str, str | None], ...] = (
    ("pywin32", "306"),
)

# Minimum supported Python, must match pyproject ``requires-python``.
_MIN_PYTHON: tuple[int, int] = (3, 10)


def _version_tuple(s: str) -> tuple[int, ...]:
    """Parse a dotted version string into a comparable tuple of ints.

    Trailing non-integer segments (e.g. ``rc1``) are ignored.
    """
    parts: list[int] = []
    for seg in s.split("."):
        try:
            parts.append(int(seg))
        except ValueError:
            break
    return tuple(parts)


class _PythonVersionCheck:
    name = "Python version"
    category = "environment"

    def run(self, workspace: Path) -> CheckResult:
        import sys

        vi = sys.version_info
        current = (vi[0], vi[1])
        micro = vi[2] if len(vi) > 2 else 0
        current_str = f"{current[0]}.{current[1]}.{micro}"
        minimum = _MIN_PYTHON
        if current < minimum:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"Python {current_str} < required {minimum[0]}.{minimum[1]}",
                fix_hint=f"Install Python {minimum[0]}.{minimum[1]} or newer",
            )
        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"Python {current_str}",
        )


class _DependenciesCheck:
    name = "Required dependencies"
    category = "environment"

    def run(self, workspace: Path) -> CheckResult:
        import sys

        required = list(_REQUIRED_DEPS)
        optional_note: list[str] = []

        # Windows-specific optional deps
        if sys.platform == "win32":
            for dist, min_v in _WIN_OPTIONAL_DEPS:
                try:
                    found = version(dist)
                    if min_v and _version_tuple(found) < _version_tuple(min_v):
                        optional_note.append(
                            f"{dist} {found} < {min_v} (Windows Service may misbehave)"
                        )
                except PackageNotFoundError:
                    optional_note.append(
                        f"{dist} not installed (Windows Service unavailable)"
                    )

        missing: list[str] = []
        outdated: list[str] = []
        ok_list: list[str] = []

        for dist, min_v in required:
            try:
                found = version(dist)
            except PackageNotFoundError:
                missing.append(dist)
                continue
            if min_v and _version_tuple(found) < _version_tuple(min_v):
                outdated.append(f"{dist} {found} < {min_v}")
            else:
                ok_list.append(f"{dist} {found}")

        if missing:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"missing: {', '.join(missing)}",
                details=ok_list,
                fix_hint=f"pip install {' '.join(missing)}",
            )
        if outdated:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message=f"outdated: {', '.join(outdated)}",
                details=ok_list + optional_note,
                fix_hint="pip install --upgrade chatmd",
            )

        details = ok_list + optional_note
        # Optional-only warnings (e.g. missing pywin32 on Windows)
        if optional_note:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message="; ".join(optional_note),
                details=ok_list,
                fix_hint="pip install 'chatmd[win-service]'" if sys.platform == "win32" else None,
            )

        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"{len(ok_list)} packages ok",
            details=details,
        )


# ---------------------------------------------------------------------------
# Workspace: directory structure & YAML config sanity
# ---------------------------------------------------------------------------


_REQUIRED_CONFIG_FILES: tuple[str, ...] = ("agent.yaml", "user.yaml")
_OPTIONAL_CONFIG_FILES: tuple[str, ...] = ("skills.yaml",)
_EXPECTED_SUBDIRS: tuple[str, ...] = ("logs", "state")


class _WorkspaceStructureCheck:
    name = "Workspace structure"
    category = "workspace"

    def run(self, workspace: Path) -> CheckResult:
        chatmd_dir = workspace / ".chatmd"
        if not chatmd_dir.is_dir():
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"{chatmd_dir} not found",
                fix_hint="chatmd init .",
            )

        missing_files = [
            name
            for name in _REQUIRED_CONFIG_FILES
            if not (chatmd_dir / name).is_file()
        ]
        missing_dirs = [
            name
            for name in _EXPECTED_SUBDIRS
            if not (chatmd_dir / name).is_dir()
        ]

        if missing_files:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"missing config: {', '.join(missing_files)}",
                fix_hint="chatmd upgrade --full",
            )
        if missing_dirs:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message=f"missing subdirs: {', '.join(missing_dirs)}",
                details=[f"expected {chatmd_dir / d}/" for d in missing_dirs],
                fix_hint="chatmd upgrade --full",
            )

        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"{chatmd_dir} complete",
        )


class _YamlSyntaxCheck:
    name = "YAML configuration syntax"
    category = "workspace"

    def run(self, workspace: Path) -> CheckResult:
        import yaml

        chatmd_dir = workspace / ".chatmd"
        if not chatmd_dir.is_dir():
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message=".chatmd/ not present",
            )

        errors: list[str] = []
        ok_count = 0
        candidates = list(_REQUIRED_CONFIG_FILES) + list(_OPTIONAL_CONFIG_FILES)

        for name in candidates:
            fp = chatmd_dir / name
            if not fp.is_file():
                continue
            try:
                with open(fp, encoding="utf-8") as fh:
                    yaml.safe_load(fh)
                ok_count += 1
            except yaml.YAMLError as exc:
                mark = getattr(exc, "problem_mark", None)
                if mark is not None:
                    errors.append(f"{name}:{mark.line + 1}: {exc.problem}")
                else:
                    errors.append(f"{name}: {exc}")
            except OSError as exc:
                errors.append(f"{name}: {exc}")

        if errors:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"{len(errors)} file(s) invalid",
                details=errors,
                fix_hint="Fix YAML syntax or restore from git",
            )
        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"{ok_count} YAML file(s) valid",
        )


class _SkillsPluginCheck:
    name = "Skill plugins"
    category = "workspace"

    def run(self, workspace: Path) -> CheckResult:
        import yaml

        chatmd_dir = workspace / ".chatmd"
        skills_yaml = chatmd_dir / "skills.yaml"
        if not skills_yaml.is_file():
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="no skills.yaml (built-in skills only)",
            )

        try:
            with open(skills_yaml, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except (yaml.YAMLError, OSError) as exc:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"skills.yaml unreadable: {exc}",
            )

        plugins = data.get("plugins") or []
        if not isinstance(plugins, list):
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message="skills.yaml `plugins` must be a list",
            )

        warnings: list[str] = []
        errors: list[str] = []
        ok_count = 0

        for idx, plugin in enumerate(plugins):
            if not isinstance(plugin, dict):
                errors.append(f"plugins[{idx}] is not a mapping")
                continue

            ptype = plugin.get("type")
            if ptype not in {"yaml", "python"}:
                errors.append(
                    f"plugins[{idx}] has invalid type {ptype!r} (expected yaml/python)"
                )
                continue

            path = plugin.get("path")
            if not path:
                errors.append(f"plugins[{idx}] missing `path`")
                continue

            resolved = (workspace / path).resolve() if not Path(path).is_absolute() else Path(path)
            if not resolved.exists():
                warnings.append(f"plugins[{idx}] path not found: {path}")
                continue

            ok_count += 1

        if errors:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"{len(errors)} plugin error(s)",
                details=errors + warnings,
                fix_hint="Review .chatmd/skills.yaml",
            )
        if warnings:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message=f"{len(warnings)} missing plugin path(s)",
                details=warnings,
            )
        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"{ok_count} plugin(s) registered",
        )


# ---------------------------------------------------------------------------
# Service: PID file + SCM/systemd/launchd cross-check
#
# This is the direct diagnostic companion to the 2026-04-20 bug fix where
# `chatmd status` could report "running" while the Windows Service Control
# Manager reported "stopped" (PID recycled by the OS).  The checks below
# reveal any mismatch so users can self-diagnose the issue next time.
# ---------------------------------------------------------------------------


class _PidFileCheck:
    name = "PID file"
    category = "service"

    def run(self, workspace: Path) -> CheckResult:
        from chatmd.infra.pid_utils import is_agent_alive, read_pid_file

        pid_file = workspace / ".chatmd" / "agent.pid"
        if not pid_file.exists():
            return CheckResult(
                name=self.name,
                category=self.category,
                status="ok",
                message="no agent.pid (Agent not running)",
            )

        parsed = read_pid_file(pid_file)
        if parsed is None:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message="agent.pid is malformed",
                fix_hint="chatmd status  # (will auto-clean)",
            )

        pid, ctime = parsed
        if ctime is None:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message=f"agent.pid is legacy format (PID {pid}, no create-time)",
                fix_hint="chatmd restart  # regenerate in new format",
            )

        if is_agent_alive(pid_file):
            return CheckResult(
                name=self.name,
                category=self.category,
                status="ok",
                message=f"Agent is alive (PID {pid})",
            )
        return CheckResult(
            name=self.name,
            category=self.category,
            status="warn",
            message=f"agent.pid stale (PID {pid} reused or dead)",
            fix_hint="chatmd status  # (will auto-clean the stale PID file)",
        )


class _ServiceConsistencyCheck:
    """Cross-check SCM / systemd / launchd state against agent.pid liveness.

    This is the canonical regression guard for the 2026-04-20 bug.
    """

    name = "Service \u21c4 PID consistency"
    category = "service"

    def run(self, workspace: Path) -> CheckResult:
        from chatmd.infra.pid_utils import is_agent_alive

        pid_file = workspace / ".chatmd" / "agent.pid"
        pid_alive = is_agent_alive(pid_file)
        svc_state = self._query_service_state(workspace)

        if svc_state is None:
            # No installed service — inconsistency is only possible when a
            # daemon / foreground agent forgot to clean its pid file.
            if pid_alive:
                return CheckResult(
                    name=self.name,
                    category=self.category,
                    status="ok",
                    message="no service installed; foreground/daemon agent alive",
                )
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="no service installed; no running agent",
            )

        # Service exists; compare to pid state
        if svc_state == "running" and pid_alive:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="ok",
                message="service running and PID alive (consistent)",
            )
        if svc_state == "running" and not pid_alive:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message="service reports running but Agent is not responding",
                fix_hint="chatmd service restart",
            )
        if svc_state == "stopped" and pid_alive:
            # The exact failure mode fixed on 2026-04-20
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=(
                    "service stopped but agent.pid reports alive "
                    "(PID likely recycled by the OS)"
                ),
                details=[
                    "This is the scenario fixed by v0.2.10's pid_utils.",
                    "If you are on v0.2.10+ this should not happen; please report.",
                ],
                fix_hint="chatmd service start",
            )
        if svc_state == "stopped" and not pid_alive:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="ok",
                message="service stopped and no live PID (consistent)",
            )

        # Any transitional state (starting, stopping, paused, …)
        return CheckResult(
            name=self.name,
            category=self.category,
            status="warn",
            message=f"service state `{svc_state}`; retry after it settles",
        )

    @staticmethod
    def _query_service_state(workspace: Path) -> str | None:
        """Return the installed service's state, or None if not installed."""
        import sys

        if sys.platform == "win32":
            try:
                from chatmd.commands.service import (
                    _check_pywin32,
                    _status_windows,
                )
            except Exception:
                return None
            if not _check_pywin32():
                return None
            try:
                state = _status_windows(workspace)
            except Exception:
                return None
            if state == "not installed":
                return None
            return state
        if sys.platform == "linux":
            from chatmd.commands.service import _status_systemd

            try:
                state = _status_systemd(workspace)
            except Exception:
                return None
            if not state or state in {"unknown", "inactive", "failed"}:
                # `inactive` for systemd = stopped; `failed` = crashed.
                # `unknown` typically means unit file isn't installed.
                return (
                    None
                    if state == "unknown"
                    else "stopped"
                )
            if state == "active":
                return "running"
            return state
        if sys.platform == "darwin":
            from chatmd.commands.service import _status_launchd

            try:
                state = _status_launchd(workspace)
            except Exception:
                return None
            if state == "not loaded":
                return None
            if state == "running":
                return "running"
            return state
        return None


# ---------------------------------------------------------------------------
# Provider: config sanity + (optional) connectivity
# ---------------------------------------------------------------------------


def _mask_key(key: str) -> str:
    """Hide all but the first four characters of an API key."""
    if not key:
        return "<empty>"
    if len(key) <= 4:
        return "*" * len(key)
    return f"{key[:4]}…({len(key)} chars)"


def _load_agent_config(workspace: Path) -> dict | None:
    """Load ``.chatmd/agent.yaml`` without side effects.  Returns None on error."""
    import yaml

    fp = workspace / ".chatmd" / "agent.yaml"
    if not fp.is_file():
        return None
    try:
        with open(fp, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (yaml.YAMLError, OSError):
        return None
    return data if isinstance(data, dict) else None


class _ProviderConfigCheck:
    name = "Provider configuration"
    category = "provider"

    def run(self, workspace: Path) -> CheckResult:
        cfg = _load_agent_config(workspace)
        if cfg is None:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="agent.yaml not readable (see Workspace checks)",
            )

        providers = ((cfg.get("ai") or {}).get("providers")) or []
        if not isinstance(providers, list) or not providers:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message="no AI providers configured in agent.yaml",
                fix_hint="Edit .chatmd/agent.yaml and add an `ai.providers` entry",
            )

        errors: list[str] = []
        warnings: list[str] = []
        details: list[str] = []

        for idx, p in enumerate(providers):
            if not isinstance(p, dict):
                errors.append(f"providers[{idx}] is not a mapping")
                continue
            ptype = p.get("type", "?")
            api_base = p.get("api_base") or p.get("api_url") or ""
            api_key = p.get("api_key") or ""

            if not api_base:
                errors.append(f"providers[{idx}] ({ptype}) missing api_base/api_url")
                continue

            if not api_key:
                warnings.append(
                    f"providers[{idx}] ({ptype}) has no api_key — AI calls will fail"
                )

            # Cheap URL sanity check
            from urllib.parse import urlparse

            parsed = urlparse(api_base)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(
                    f"providers[{idx}] invalid api_base: {api_base!r}"
                )
                continue

            details.append(
                f"providers[{idx}] {ptype} @ {api_base} (key={_mask_key(api_key)})"
            )

        if errors:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"{len(errors)} provider config error(s)",
                details=errors + warnings + details,
                fix_hint="Review .chatmd/agent.yaml `ai.providers`",
            )
        if warnings:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message="; ".join(warnings),
                details=details,
            )
        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"{len(providers)} provider(s) configured",
            details=details,
        )


class _ProviderHealthCheck:
    """Best-effort TCP/HTTP reachability probe for each provider's base URL.

    Does NOT call paid endpoints; only a HEAD/GET to the base URL with a
    short timeout.  Opt-out via ``--no-network``.
    """

    name = "Provider reachability"
    category = "provider"
    requires_network = True

    _TIMEOUT = 5.0

    def run(self, workspace: Path) -> CheckResult:
        import httpx

        cfg = _load_agent_config(workspace)
        if cfg is None:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="agent.yaml not readable",
            )
        providers = ((cfg.get("ai") or {}).get("providers")) or []
        if not providers:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="no providers to probe",
            )

        results: list[str] = []
        errors: list[str] = []
        timeouts: list[str] = []
        ok_count = 0

        for idx, p in enumerate(providers):
            if not isinstance(p, dict):
                continue
            api_base = (p.get("api_base") or p.get("api_url") or "").rstrip("/")
            if not api_base:
                continue

            label = f"providers[{idx}] {api_base}"
            try:
                resp = httpx.get(api_base, timeout=self._TIMEOUT)
            except httpx.TimeoutException:
                timeouts.append(f"{label} (timeout {self._TIMEOUT}s)")
                continue
            except httpx.HTTPError as exc:
                errors.append(f"{label} — {exc}")
                continue
            # Any HTTP response (even 404) proves TCP/TLS reachability
            results.append(f"{label} → HTTP {resp.status_code}")
            ok_count += 1

        if errors:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"{len(errors)} provider(s) unreachable",
                details=errors + timeouts + results,
                fix_hint="Check network / proxy / firewall",
            )
        if timeouts:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message=f"{len(timeouts)} provider(s) timed out",
                details=timeouts + results,
            )
        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"{ok_count} provider(s) reachable",
            details=results,
        )


# ---------------------------------------------------------------------------
# Git: repository health
# ---------------------------------------------------------------------------


def _run_git(
    args: list[str],
    cwd: Path,
    timeout: float = 5.0,
) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr).

    Returns ``(-1, "", "git not available")`` when git is not on PATH.
    """
    import subprocess

    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        return -1, "", "git not available"
    except subprocess.TimeoutExpired:
        return -2, "", f"timeout after {timeout}s"
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


class _GitRepoCheck:
    name = "Git repository"
    category = "git"

    def run(self, workspace: Path) -> CheckResult:
        if not (workspace / ".git").is_dir():
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="not a Git repository",
            )

        rc, out, err = _run_git(["status", "--porcelain"], workspace)
        if rc == -1:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message="git command not found on PATH",
            )
        if rc != 0:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"git status failed: {err or 'rc=' + str(rc)}",
            )
        if out:
            dirty_lines = out.splitlines()
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message=f"{len(dirty_lines)} uncommitted change(s)",
                details=dirty_lines[:10],
            )
        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message="working tree clean",
        )


class _GitRemoteCheck:
    name = "Git remote"
    category = "git"

    def run(self, workspace: Path) -> CheckResult:
        from chatmd.infra.git_utils import get_git_remote_url

        if not (workspace / ".git").is_dir():
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="not a Git repository",
            )

        url = get_git_remote_url(workspace)
        if not url:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message="no `origin` remote configured",
            )

        # Security: reject URLs with embedded credentials
        import re

        if re.match(r"^https?://[^@/]+@", url):
            # Strip credentials before echoing
            from chatmd.infra.git_utils import mask_repo_url

            return CheckResult(
                name=self.name,
                category=self.category,
                status="error",
                message=f"remote URL contains plaintext credentials: {mask_repo_url(url)}",
                fix_hint=(
                    "git remote set-url origin <ssh-or-token-helper-url> "
                    "(avoid embedding passwords in URL)"
                ),
            )

        return CheckResult(
            name=self.name,
            category=self.category,
            status="ok",
            message=f"origin → {url}",
        )


class _GitUnpushedCheck:
    name = "Git unpushed commits"
    category = "git"

    def run(self, workspace: Path) -> CheckResult:
        if not (workspace / ".git").is_dir():
            return CheckResult(
                name=self.name,
                category=self.category,
                status="skip",
                message="not a Git repository",
            )

        # Upstream tracking branch: `git rev-parse --abbrev-ref @{u}`
        rc, out, err = _run_git(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            workspace,
        )
        if rc != 0:
            # No upstream (common for single-user workspaces)
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message="no upstream tracking branch set",
                fix_hint="git push -u origin <branch>",
            )

        upstream = out.strip()
        rc, out, err = _run_git(["log", f"{upstream}..HEAD", "--oneline"], workspace)
        if rc != 0:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="warn",
                message=f"git log failed: {err or 'rc=' + str(rc)}",
            )

        if not out:
            return CheckResult(
                name=self.name,
                category=self.category,
                status="ok",
                message=f"up to date with {upstream}",
            )
        commits = out.splitlines()
        return CheckResult(
            name=self.name,
            category=self.category,
            status="warn",
            message=f"{len(commits)} unpushed commit(s)",
            details=commits[:10],
            fix_hint=f"git push origin {upstream.split('/', 1)[-1]}",
        )


# Register built-in checks in display order
register_check(lambda: _PythonVersionCheck())
register_check(lambda: _DependenciesCheck())
register_check(lambda: _WorkspaceStructureCheck())
register_check(lambda: _YamlSyntaxCheck())
register_check(lambda: _SkillsPluginCheck())
register_check(lambda: _PidFileCheck())
register_check(lambda: _ServiceConsistencyCheck())
register_check(lambda: _ProviderConfigCheck())
register_check(lambda: _ProviderHealthCheck())
register_check(lambda: _GitRepoCheck())
register_check(lambda: _GitRemoteCheck())
register_check(lambda: _GitUnpushedCheck())
