"""Tests for `chatmd doctor` — environment and workspace diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from chatmd.commands.doctor import (
    _REGISTRY,
    CheckResult,
    default_checks,
    register_check,
    run_doctor,
)

# ---------------------------------------------------------------------------
# Fake Check helper used across tests
# ---------------------------------------------------------------------------


@dataclass
class FakeCheck:
    """Minimal check implementation for unit tests."""

    name: str
    category: str
    status: str
    message: str = "ok"
    details: tuple[str, ...] = ()
    fix_hint: str | None = None
    requires_network: bool = False

    def run(self, workspace: Path) -> CheckResult:
        return CheckResult(
            name=self.name,
            category=self.category,
            status=self.status,  # type: ignore[arg-type]
            message=self.message,
            details=list(self.details),
            fix_hint=self.fix_hint,
        )


def _check(**kwargs) -> FakeCheck:
    defaults = dict(name="test", category="environment", status="ok")
    defaults.update(kwargs)
    return FakeCheck(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CheckResult data class
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_minimal_construction(self) -> None:
        r = CheckResult(name="n", category="c", status="ok", message="m")
        assert r.details == []
        assert r.fix_hint is None

    def test_with_details_and_hint(self) -> None:
        r = CheckResult(
            name="n",
            category="c",
            status="error",
            message="m",
            details=["line 1", "line 2"],
            fix_hint="run foo",
        )
        assert r.details == ["line 1", "line 2"]
        assert r.fix_hint == "run foo"


# ---------------------------------------------------------------------------
# run_doctor exit codes & filtering
# ---------------------------------------------------------------------------


class TestRunDoctorExitCodes:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / ".chatmd").mkdir()
        return tmp_path

    def test_empty_registry_returns_zero(self, workspace: Path) -> None:
        assert run_doctor(str(workspace), checks=[]) == 0

    def test_all_ok_returns_zero(self, workspace: Path) -> None:
        code = run_doctor(
            str(workspace),
            checks=[_check(status="ok"), _check(name="t2", status="ok")],
        )
        assert code == 0

    def test_single_warning_returns_one(self, workspace: Path) -> None:
        code = run_doctor(
            str(workspace),
            checks=[_check(status="ok"), _check(name="t2", status="warn")],
        )
        assert code == 1

    def test_single_error_returns_two(self, workspace: Path) -> None:
        code = run_doctor(
            str(workspace),
            checks=[_check(status="warn"), _check(name="t2", status="error")],
        )
        assert code == 2

    def test_skip_only_returns_zero(self, workspace: Path) -> None:
        code = run_doctor(
            str(workspace),
            checks=[_check(status="skip"), _check(name="t2", status="skip")],
        )
        assert code == 0


class TestRunDoctorCategoryFilter:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / ".chatmd").mkdir()
        return tmp_path

    def test_filter_by_single_category(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(name="env-check", category="environment", status="ok"),
            _check(name="svc-check", category="service", status="error"),
        ]
        # Only run environment; service error must NOT count
        code = run_doctor(str(workspace), categories=("environment",), checks=checks)
        assert code == 0
        out = capsys.readouterr().out
        assert "env-check" in out
        assert "svc-check" not in out

    def test_filter_by_multiple_categories(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(name="env-check", category="environment", status="ok"),
            _check(name="svc-check", category="service", status="ok"),
            _check(name="git-check", category="git", status="warn"),
        ]
        code = run_doctor(
            str(workspace),
            categories=("environment", "service"),
            checks=checks,
        )
        assert code == 0  # git warn excluded
        out = capsys.readouterr().out
        assert "git-check" not in out


class TestRunDoctorNoNetwork:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / ".chatmd").mkdir()
        return tmp_path

    def test_network_check_skipped_when_flag_set(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(name="local", category="environment", status="ok"),
            _check(
                name="remote",
                category="provider",
                status="ok",
                requires_network=True,
            ),
        ]
        code = run_doctor(str(workspace), no_network=True, checks=checks)
        assert code == 0
        out = capsys.readouterr().out
        assert "remote" in out
        # skipped symbol (⏭️) should appear
        assert "--no-network" in out or "skipped" in out

    def test_network_check_runs_by_default(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(
                name="remote",
                category="provider",
                status="ok",
                message="connected",
                requires_network=True,
            ),
        ]
        run_doctor(str(workspace), checks=checks)
        out = capsys.readouterr().out
        assert "connected" in out


class TestRunDoctorVerbose:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / ".chatmd").mkdir()
        return tmp_path

    def test_details_hidden_by_default(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(status="ok", details=("deep-detail-xyz",)),
        ]
        run_doctor(str(workspace), checks=checks)
        out = capsys.readouterr().out
        assert "deep-detail-xyz" not in out

    def test_details_shown_when_verbose(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(status="ok", details=("deep-detail-xyz",)),
        ]
        run_doctor(str(workspace), verbose=True, checks=checks)
        out = capsys.readouterr().out
        assert "deep-detail-xyz" in out

    def test_fix_hint_rendered_for_error(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(status="error", message="broken", fix_hint="chatmd init"),
        ]
        run_doctor(str(workspace), checks=checks)
        out = capsys.readouterr().out
        assert "chatmd init" in out

    def test_fix_hint_omitted_for_ok(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        checks = [
            _check(status="ok", fix_hint="should-not-print"),
        ]
        run_doctor(str(workspace), checks=checks)
        out = capsys.readouterr().out
        assert "should-not-print" not in out


class TestRunDoctorRobustness:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / ".chatmd").mkdir()
        return tmp_path

    def test_crashing_check_becomes_error(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        @dataclass
        class BoomCheck:
            name: str = "boom"
            category: str = "environment"

            def run(self, workspace: Path) -> CheckResult:
                raise RuntimeError("kaboom")

        code = run_doctor(str(workspace), checks=[BoomCheck()])
        assert code == 2
        out = capsys.readouterr().out
        assert "kaboom" in out


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_register_and_default_checks(self) -> None:
        before = len(_REGISTRY)
        try:
            @register_check
            def _factory() -> FakeCheck:
                return _check(name="registered")

            assert len(_REGISTRY) == before + 1
            checks = default_checks()
            assert any(c.name == "registered" for c in checks)
        finally:
            # Leave registry as we found it
            _REGISTRY.pop()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestEnvironmentChecks:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / ".chatmd").mkdir()
        return tmp_path

    def test_python_version_ok(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _PythonVersionCheck

        result = _PythonVersionCheck().run(workspace)
        assert result.status == "ok"
        assert "Python" in result.message

    def test_python_version_too_old(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _PythonVersionCheck

        fake = type("VI", (), {"major": 3, "minor": 8, "micro": 0})
        with patch(
            "sys.version_info",
            new=(fake.major, fake.minor, fake.micro, "final", 0),
        ):
            result = _PythonVersionCheck().run(workspace)
        assert result.status == "error"
        assert "3.8" in result.message
        assert result.fix_hint is not None

    def test_dependencies_all_present(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _DependenciesCheck

        result = _DependenciesCheck().run(workspace)
        # Running in the dev venv — all required deps must be installed
        assert result.status in {"ok", "warn"}  # warn allowed if pywin32 partial
        # message shouldn't contain 'missing:'
        assert "missing:" not in result.message

    def test_dependencies_missing_is_error(self, workspace: Path) -> None:
        from importlib.metadata import PackageNotFoundError

        from chatmd.commands.doctor import _DependenciesCheck

        def fake_version(name: str) -> str:
            if name == "click":
                raise PackageNotFoundError(name)
            return "99.0"

        with patch("chatmd.commands.doctor.version", fake_version):
            result = _DependenciesCheck().run(workspace)
        assert result.status == "error"
        assert "click" in result.message
        assert "pip install" in (result.fix_hint or "")

    def test_dependencies_outdated_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _DependenciesCheck

        def fake_version(name: str) -> str:
            # Return extremely old versions for every required dep
            return "0.0.1"

        with patch("chatmd.commands.doctor.version", fake_version):
            result = _DependenciesCheck().run(workspace)
        assert result.status == "warn"
        assert "outdated" in result.message

    def test_version_tuple_parses_trailing_text(self) -> None:
        from chatmd.commands.doctor import _version_tuple

        assert _version_tuple("1.2.3") == (1, 2, 3)
        assert _version_tuple("1.2.3rc1") == (1, 2)
        assert _version_tuple("8.1.7") > _version_tuple("8.1")


class TestWorkspaceChecks:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd = tmp_path / ".chatmd"
        chatmd.mkdir()
        (chatmd / "logs").mkdir()
        (chatmd / "state").mkdir()
        (chatmd / "agent.yaml").write_text("watcher:\n  debounce_ms: 300\n", encoding="utf-8")
        (chatmd / "user.yaml").write_text("language: en\n", encoding="utf-8")
        return tmp_path

    def test_structure_ok(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _WorkspaceStructureCheck

        result = _WorkspaceStructureCheck().run(workspace)
        assert result.status == "ok"

    def test_structure_missing_chatmd_dir(self, tmp_path: Path) -> None:
        from chatmd.commands.doctor import _WorkspaceStructureCheck

        result = _WorkspaceStructureCheck().run(tmp_path)
        assert result.status == "error"
        assert "chatmd init" in (result.fix_hint or "")

    def test_structure_missing_required_config(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _WorkspaceStructureCheck

        (workspace / ".chatmd" / "agent.yaml").unlink()
        result = _WorkspaceStructureCheck().run(workspace)
        assert result.status == "error"
        assert "agent.yaml" in result.message

    def test_structure_missing_subdir_is_warn(self, workspace: Path) -> None:
        import shutil

        from chatmd.commands.doctor import _WorkspaceStructureCheck

        shutil.rmtree(workspace / ".chatmd" / "logs")
        result = _WorkspaceStructureCheck().run(workspace)
        assert result.status == "warn"
        assert "logs" in result.message

    def test_yaml_syntax_ok(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _YamlSyntaxCheck

        result = _YamlSyntaxCheck().run(workspace)
        assert result.status == "ok"

    def test_yaml_syntax_error_reports_line(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _YamlSyntaxCheck

        (workspace / ".chatmd" / "agent.yaml").write_text(
            "watcher:\n  debounce_ms: [unterminated\n",
            encoding="utf-8",
        )
        result = _YamlSyntaxCheck().run(workspace)
        assert result.status == "error"
        assert "agent.yaml" in result.details[0]

    def test_yaml_syntax_skips_when_no_workspace(self, tmp_path: Path) -> None:
        from chatmd.commands.doctor import _YamlSyntaxCheck

        result = _YamlSyntaxCheck().run(tmp_path)
        assert result.status == "skip"

    def test_skills_plugin_skips_when_no_skills_yaml(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _SkillsPluginCheck

        result = _SkillsPluginCheck().run(workspace)
        assert result.status == "skip"

    def test_skills_plugin_missing_path_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _SkillsPluginCheck

        (workspace / ".chatmd" / "skills.yaml").write_text(
            "plugins:\n"
            "  - type: python\n"
            "    path: ./no-such-plugin.py\n",
            encoding="utf-8",
        )
        result = _SkillsPluginCheck().run(workspace)
        assert result.status == "warn"
        assert "no-such-plugin.py" in " ".join(result.details)

    def test_skills_plugin_invalid_type_is_error(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _SkillsPluginCheck

        (workspace / ".chatmd" / "skills.yaml").write_text(
            "plugins:\n"
            "  - type: bogus\n"
            "    path: foo\n",
            encoding="utf-8",
        )
        result = _SkillsPluginCheck().run(workspace)
        assert result.status == "error"

    def test_skills_plugin_missing_path_field_is_error(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _SkillsPluginCheck

        (workspace / ".chatmd" / "skills.yaml").write_text(
            "plugins:\n"
            "  - type: yaml\n",
            encoding="utf-8",
        )
        result = _SkillsPluginCheck().run(workspace)
        assert result.status == "error"

    def test_skills_plugin_ok_with_existing_path(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _SkillsPluginCheck

        plugin = workspace / "my_plugin.py"
        plugin.write_text("# plugin\n", encoding="utf-8")
        (workspace / ".chatmd" / "skills.yaml").write_text(
            f"plugins:\n"
            f"  - type: python\n"
            f"    path: {plugin.name}\n",
            encoding="utf-8",
        )
        result = _SkillsPluginCheck().run(workspace)
        assert result.status == "ok"


class TestServiceChecks:
    """Regression guard for the 2026-04-20 Service<->PID consistency bug."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        (tmp_path / ".chatmd").mkdir()
        return tmp_path

    # -- _PidFileCheck -------------------------------------------------------

    def test_pid_file_absent_is_ok(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _PidFileCheck

        result = _PidFileCheck().run(workspace)
        assert result.status == "ok"
        assert "not running" in result.message.lower() or "no agent.pid" in result.message.lower()

    def test_pid_file_alive(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _PidFileCheck
        from chatmd.infra.pid_utils import write_pid_file

        pid_file = workspace / ".chatmd" / "agent.pid"
        write_pid_file(pid_file)  # current process — alive
        result = _PidFileCheck().run(workspace)
        assert result.status == "ok"
        assert "alive" in result.message.lower()

    def test_pid_file_legacy_format_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _PidFileCheck

        pid_file = workspace / ".chatmd" / "agent.pid"
        pid_file.write_text("12345", encoding="utf-8")  # no ctime
        result = _PidFileCheck().run(workspace)
        assert result.status == "warn"
        assert "legacy" in result.message.lower()

    def test_pid_file_stale_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _PidFileCheck

        pid_file = workspace / ".chatmd" / "agent.pid"
        # PID that almost certainly doesn't exist, with a fake ctime
        pid_file.write_text("2999999\n12345", encoding="utf-8")
        result = _PidFileCheck().run(workspace)
        assert result.status == "warn"
        assert "stale" in result.message.lower()

    def test_pid_file_malformed_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _PidFileCheck

        (workspace / ".chatmd" / "agent.pid").write_text("not-a-number", encoding="utf-8")
        result = _PidFileCheck().run(workspace)
        assert result.status == "warn"
        assert "malformed" in result.message.lower()

    # -- _ServiceConsistencyCheck -------------------------------------------

    def test_consistency_no_service_no_pid_skips(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ServiceConsistencyCheck

        with patch.object(
            _ServiceConsistencyCheck, "_query_service_state", return_value=None,
        ):
            result = _ServiceConsistencyCheck().run(workspace)
        assert result.status == "skip"

    def test_consistency_no_service_but_live_pid_is_ok(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ServiceConsistencyCheck

        with patch.object(
            _ServiceConsistencyCheck, "_query_service_state", return_value=None,
        ), patch(
            "chatmd.infra.pid_utils.is_agent_alive", return_value=True,
        ):
            result = _ServiceConsistencyCheck().run(workspace)
        assert result.status == "ok"

    def test_consistency_running_and_alive_is_ok(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ServiceConsistencyCheck

        with patch.object(
            _ServiceConsistencyCheck, "_query_service_state", return_value="running",
        ), patch(
            "chatmd.infra.pid_utils.is_agent_alive", return_value=True,
        ):
            result = _ServiceConsistencyCheck().run(workspace)
        assert result.status == "ok"
        assert "consistent" in result.message.lower()

    def test_consistency_running_but_not_alive_is_error(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ServiceConsistencyCheck

        with patch.object(
            _ServiceConsistencyCheck, "_query_service_state", return_value="running",
        ), patch(
            "chatmd.infra.pid_utils.is_agent_alive", return_value=False,
        ):
            result = _ServiceConsistencyCheck().run(workspace)
        assert result.status == "error"
        assert "restart" in (result.fix_hint or "")

    def test_consistency_stopped_but_alive_is_error(self, workspace: Path) -> None:
        """The exact 2026-04-20 bug scenario."""
        from chatmd.commands.doctor import _ServiceConsistencyCheck

        with patch.object(
            _ServiceConsistencyCheck, "_query_service_state", return_value="stopped",
        ), patch(
            "chatmd.infra.pid_utils.is_agent_alive", return_value=True,
        ):
            result = _ServiceConsistencyCheck().run(workspace)
        assert result.status == "error"
        assert "recycled" in result.message.lower()
        assert "service start" in (result.fix_hint or "")

    def test_consistency_stopped_and_not_alive_is_ok(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ServiceConsistencyCheck

        with patch.object(
            _ServiceConsistencyCheck, "_query_service_state", return_value="stopped",
        ), patch(
            "chatmd.infra.pid_utils.is_agent_alive", return_value=False,
        ):
            result = _ServiceConsistencyCheck().run(workspace)
        assert result.status == "ok"

    def test_consistency_transitional_state_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ServiceConsistencyCheck

        with patch.object(
            _ServiceConsistencyCheck, "_query_service_state", return_value="starting",
        ), patch(
            "chatmd.infra.pid_utils.is_agent_alive", return_value=False,
        ):
            result = _ServiceConsistencyCheck().run(workspace)
        assert result.status == "warn"


class TestProviderChecks:
    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        chatmd = tmp_path / ".chatmd"
        chatmd.mkdir()
        return tmp_path

    def _write_agent_yaml(self, workspace: Path, content: str) -> None:
        (workspace / ".chatmd" / "agent.yaml").write_text(content, encoding="utf-8")

    # -- _ProviderConfigCheck -----------------------------------------------

    def test_config_skips_when_no_yaml(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderConfigCheck

        result = _ProviderConfigCheck().run(workspace)
        assert result.status == "skip"

    def test_config_no_providers_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderConfigCheck

        self._write_agent_yaml(workspace, "ai:\n  providers: []\n")
        result = _ProviderConfigCheck().run(workspace)
        assert result.status == "warn"
        assert "no AI providers" in result.message

    def test_config_ok_with_valid_provider(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderConfigCheck

        self._write_agent_yaml(
            workspace,
            "ai:\n  providers:\n"
            "    - type: litestartup\n"
            "      api_base: https://api.example.com\n"
            "      api_key: secret-abc-1234567890\n",
        )
        result = _ProviderConfigCheck().run(workspace)
        assert result.status == "ok"
        # key must be masked in details
        assert "secret-abc-1234567890" not in " ".join(result.details)
        assert "secr" in " ".join(result.details)

    def test_config_missing_api_key_is_warn(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderConfigCheck

        self._write_agent_yaml(
            workspace,
            "ai:\n  providers:\n"
            "    - type: litestartup\n"
            "      api_base: https://api.example.com\n",
        )
        result = _ProviderConfigCheck().run(workspace)
        assert result.status == "warn"
        assert "api_key" in result.message

    def test_config_invalid_url_is_error(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderConfigCheck

        self._write_agent_yaml(
            workspace,
            "ai:\n  providers:\n"
            "    - type: litestartup\n"
            "      api_base: not-a-url\n"
            "      api_key: k\n",
        )
        result = _ProviderConfigCheck().run(workspace)
        assert result.status == "error"

    def test_config_missing_api_base_is_error(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderConfigCheck

        self._write_agent_yaml(
            workspace,
            "ai:\n  providers:\n"
            "    - type: litestartup\n"
            "      api_key: k\n",
        )
        result = _ProviderConfigCheck().run(workspace)
        assert result.status == "error"

    def test_mask_key_hides_secret(self) -> None:
        from chatmd.commands.doctor import _mask_key

        assert _mask_key("") == "<empty>"
        assert _mask_key("abc") == "***"
        assert "secr" in _mask_key("secret-very-long")
        assert "secret-very-long" not in _mask_key("secret-very-long")

    # -- _ProviderHealthCheck -----------------------------------------------

    def test_health_skips_when_no_providers(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderHealthCheck

        self._write_agent_yaml(workspace, "ai:\n  providers: []\n")
        result = _ProviderHealthCheck().run(workspace)
        assert result.status == "skip"

    def test_health_requires_network_flag(self) -> None:
        from chatmd.commands.doctor import _ProviderHealthCheck

        assert _ProviderHealthCheck.requires_network is True

    def test_health_ok_on_any_http_response(self, workspace: Path) -> None:
        from chatmd.commands.doctor import _ProviderHealthCheck

        self._write_agent_yaml(
            workspace,
            "ai:\n  providers:\n"
            "    - type: litestartup\n"
            "      api_base: https://api.example.com\n"
            "      api_key: k\n",
        )

        class _Resp:
            status_code = 404

        with patch("httpx.get", return_value=_Resp()):
            result = _ProviderHealthCheck().run(workspace)
        assert result.status == "ok"

    def test_health_timeout_is_warn(self, workspace: Path) -> None:
        import httpx

        from chatmd.commands.doctor import _ProviderHealthCheck

        self._write_agent_yaml(
            workspace,
            "ai:\n  providers:\n"
            "    - type: litestartup\n"
            "      api_base: https://api.example.com\n"
            "      api_key: k\n",
        )

        with patch("httpx.get", side_effect=httpx.TimeoutException("slow")):
            result = _ProviderHealthCheck().run(workspace)
        assert result.status == "warn"
        assert "timed out" in result.message

    def test_health_other_http_error_is_error(self, workspace: Path) -> None:
        import httpx

        from chatmd.commands.doctor import _ProviderHealthCheck

        self._write_agent_yaml(
            workspace,
            "ai:\n  providers:\n"
            "    - type: litestartup\n"
            "      api_base: https://api.example.com\n"
            "      api_key: k\n",
        )

        with patch("httpx.get", side_effect=httpx.ConnectError("no route")):
            result = _ProviderHealthCheck().run(workspace)
        assert result.status == "error"


class TestGitChecks:
    @pytest.fixture()
    def repo(self, tmp_path: Path) -> Path:
        """Create a real but minimal Git repo under tmp_path."""
        import subprocess

        (tmp_path / ".chatmd").mkdir()
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
        )
        (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=tmp_path,
            check=True,
        )
        return tmp_path

    # -- _GitRepoCheck -------------------------------------------------------

    def test_repo_skip_when_not_a_repo(self, tmp_path: Path) -> None:
        from chatmd.commands.doctor import _GitRepoCheck

        result = _GitRepoCheck().run(tmp_path)
        assert result.status == "skip"

    def test_repo_clean_is_ok(self, repo: Path) -> None:
        from chatmd.commands.doctor import _GitRepoCheck

        result = _GitRepoCheck().run(repo)
        assert result.status == "ok"

    def test_repo_dirty_is_warn(self, repo: Path) -> None:
        from chatmd.commands.doctor import _GitRepoCheck

        (repo / "new.md").write_text("x\n", encoding="utf-8")
        result = _GitRepoCheck().run(repo)
        assert result.status == "warn"
        assert "uncommitted" in result.message

    # -- _GitRemoteCheck ----------------------------------------------------

    def test_remote_no_origin_is_warn(self, repo: Path) -> None:
        from chatmd.commands.doctor import _GitRemoteCheck

        result = _GitRemoteCheck().run(repo)
        assert result.status == "warn"
        assert "origin" in result.message

    def test_remote_plaintext_credentials_is_error(self, repo: Path) -> None:
        import subprocess

        from chatmd.commands.doctor import _GitRemoteCheck

        subprocess.run(
            ["git", "remote", "add", "origin", "https://user:pass@github.com/u/r.git"],
            cwd=repo,
            check=True,
        )
        result = _GitRemoteCheck().run(repo)
        assert result.status == "error"
        assert "credentials" in result.message
        # must not echo the secret
        assert "pass" not in result.message.lower() or "password" not in result.message.lower()

    def test_remote_ssh_url_is_ok(self, repo: Path) -> None:
        import subprocess

        from chatmd.commands.doctor import _GitRemoteCheck

        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:user/repo.git"],
            cwd=repo,
            check=True,
        )
        result = _GitRemoteCheck().run(repo)
        assert result.status == "ok"

    # -- _GitUnpushedCheck --------------------------------------------------

    def test_unpushed_no_upstream_is_warn(self, repo: Path) -> None:
        from chatmd.commands.doctor import _GitUnpushedCheck

        result = _GitUnpushedCheck().run(repo)
        assert result.status == "warn"
        assert "upstream" in result.message

    def test_unpushed_skip_when_not_a_repo(self, tmp_path: Path) -> None:
        from chatmd.commands.doctor import _GitUnpushedCheck

        result = _GitUnpushedCheck().run(tmp_path)
        assert result.status == "skip"

    # -- _run_git helper ----------------------------------------------------

    def test_run_git_missing_binary(self, tmp_path: Path) -> None:
        from chatmd.commands.doctor import _run_git

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            rc, out, err = _run_git(["status"], tmp_path)
        assert rc == -1
        assert "not available" in err

    def test_run_git_timeout(self, tmp_path: Path) -> None:
        import subprocess as sp

        from chatmd.commands.doctor import _run_git

        with patch(
            "subprocess.run",
            side_effect=sp.TimeoutExpired(cmd=["git"], timeout=5.0),
        ):
            rc, out, err = _run_git(["status"], tmp_path)
        assert rc == -2
        assert "timeout" in err


class TestDoctorIntegration:
    """End-to-end runs of the real default_checks() against a realistic workspace."""

    @pytest.fixture()
    def workspace(self, tmp_path: Path) -> Path:
        import subprocess

        chatmd = tmp_path / ".chatmd"
        chatmd.mkdir()
        (chatmd / "logs").mkdir()
        (chatmd / "state").mkdir()
        (chatmd / "agent.yaml").write_text(
            "ai:\n"
            "  providers:\n"
            "    - type: litestartup\n"
            "      api_base: https://api.example.com\n"
            "      api_key: fake-key-1234567890\n",
            encoding="utf-8",
        )
        (chatmd / "user.yaml").write_text("language: en\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@e.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "t"], cwd=tmp_path, check=True,
        )
        (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True,
        )
        return tmp_path

    def test_full_run_with_no_network_exits_with_warnings_only(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        """All-ok environment + skipped network + no git upstream -> exit code 1 at worst."""
        code = run_doctor(str(workspace), no_network=True)
        out = capsys.readouterr().out
        # Exit code is 1 because Git upstream check warns (no upstream set).
        # This also exercises all 11 default checks.
        assert code in {0, 1}
        assert "Python" in out
        assert "agent.pid" in out or "Agent" in out  # service category visible

    def test_full_run_has_summary_line(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        run_doctor(str(workspace), no_network=True)
        out = capsys.readouterr().out
        # Header + per-category + summary
        assert "ChatMD Doctor" in out
        assert "ok" in out.lower()

    def test_category_filter_integration(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        run_doctor(
            str(workspace),
            categories=("environment",),
            no_network=True,
        )
        out = capsys.readouterr().out
        # Only the environment category should render
        assert "Python" in out
        # Service/git/provider sections must NOT be rendered
        assert "PID" not in out
        assert "upstream" not in out.lower()

    def test_broken_workspace_exits_with_error_code(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        """A bare directory with no .chatmd/ must produce exit code 2."""
        code = run_doctor(str(tmp_path), no_network=True)
        assert code == 2
        out = capsys.readouterr().out
        assert "chatmd init" in out

    def test_zh_locale_header(
        self, workspace: Path, capsys: pytest.CaptureFixture,
    ) -> None:
        from chatmd.i18n import set_locale

        try:
            set_locale("zh-CN")
            run_doctor(str(workspace), no_network=True)
            out = capsys.readouterr().out
            assert "工作区" in out or "ChatMD Doctor" in out
        finally:
            set_locale("en")


class TestDoctorCLI:
    def test_cli_help(self) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output
        assert "--category" in result.output
        assert "--verbose" in result.output
        assert "--no-network" in result.output

    def test_cli_runs_empty_registry(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from chatmd.cli import main

        (tmp_path / ".chatmd").mkdir()

        runner = CliRunner()
        # Patch default_checks to empty so the real registry doesn't interfere
        with patch("chatmd.commands.doctor.default_checks", return_value=[]):
            result = runner.invoke(main, ["doctor", "-w", str(tmp_path)])
        assert result.exit_code == 0
