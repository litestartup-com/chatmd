"""Tests for chatmd.skills.bind — /bind Skill full flow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chatmd.skills.base import SkillContext
from chatmd.skills.bind import BindSkill


@pytest.fixture()
def context(tmp_path: Path) -> SkillContext:
    """Minimal SkillContext for testing."""
    return SkillContext(
        source_file=tmp_path / "chat.md",
        source_line=1,
        workspace=tmp_path,
    )


@pytest.fixture()
def provider() -> MagicMock:
    """Mock LiteStartupProvider."""
    mock = MagicMock()
    mock.bind_status.return_value = {"success": True, "status": "none"}
    mock.bind_initiate.return_value = {
        "success": True,
        "bind_code": "482916",
        "expires_in": 300,
        "bot_username": "@ChatMDBot",
        "bot_deep_link": "https://t.me/ChatMDBot",
    }
    return mock


class TestBindSkill:
    """Tests for the /bind skill."""

    def test_skill_metadata(self) -> None:
        """Check skill name and category."""
        skill = BindSkill()
        assert skill.name == "bind"
        assert skill.category == "general"
        assert skill.requires_network is True

    def test_no_provider_error(self, context: SkillContext) -> None:
        """Should fail when no provider is configured."""
        skill = BindSkill(provider=None)
        result = skill.execute("some_token", {}, context)
        assert result.success is False
        assert result.error is not None

    def test_no_token_shows_help(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Empty input should show token help, not call API."""
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("", {}, context)
        assert result.success is False
        assert "token" in result.output.lower() or "Token" in result.output
        provider.bind_initiate.assert_not_called()

    def test_no_git_remote_error(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Should fail when workspace has no git remote."""
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value=None,
        ):
            result = skill.execute("ghp_xxx", {}, context)
        assert result.success is False
        assert result.error is not None

    def test_successful_bind(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Full success: token provided, remote found, API returns code."""
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is True
        assert "482916" in result.output
        assert result.metadata is not None
        assert result.metadata["bind_code"] == "482916"
        provider.bind_initiate.assert_called_once()
        call_kwargs = provider.bind_initiate.call_args[1]
        assert call_kwargs["repo_url"] == "https://github.com/user/repo.git"
        assert call_kwargs["git_token"] == "ghp_xxx"
        assert call_kwargs["platform"] == "telegram"
        assert "timezone" in call_kwargs
        assert isinstance(call_kwargs["timezone"], str)
        assert len(call_kwargs["timezone"]) > 0

    def test_ssh_url_converted(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """SSH remote should be auto-converted to HTTPS."""
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="git@github.com:user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is True
        provider.bind_initiate.assert_called_once()
        call_kwargs = provider.bind_initiate.call_args[1]
        assert call_kwargs["repo_url"] == "https://github.com/user/repo.git"

    def test_active_binding_for_other_repo_proceeds_to_initiate(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Multi-repo regression (T-R083 / T-123.2): an existing active binding
        for a *different* repo on the same account must NOT short-circuit
        the new bind — the server is the only authority on duplicate detection
        (it returns code 1003 only when the SAME repo_url is bound twice).

        Before the hotfix, bind.py used to check bind_status() and abort if
        any binding was active, even when the user was binding a brand-new
        repo under the same git_token. This test guards against regressing
        to that single-binding behavior.
        """
        provider.bind_status.return_value = {
            "success": True,
            "status": "active",
            "platform": "telegram",
            "repo_url_masked": "https://github.com/u***/other-repo.git",
            "bound_at": "2026-04-14T10:30:00",
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is True
        provider.bind_initiate.assert_called_once()

    def test_api_error_invalid_repo(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Should handle API error code 1001."""
        provider.bind_initiate.return_value = {
            "success": False,
            "error": "Invalid repo URL format",
            "code": 1001,
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is False
        assert result.error is not None

    def test_api_error_rate_limited(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Should handle API error code 3001."""
        provider.bind_initiate.return_value = {
            "success": False,
            "error": "Too many requests",
            "code": 3001,
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is False

    def test_api_error_unauthorized(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Should handle API error code 2001."""
        provider.bind_initiate.return_value = {
            "success": False,
            "error": "Unauthorized",
            "code": 2001,
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is False

    def test_set_provider_injection(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """set_provider should inject the provider after construction."""
        skill = BindSkill(provider=None)
        skill.set_provider(provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)
        assert result.success is True

    def test_help_text_property(self) -> None:
        """help_text should return non-empty string."""
        skill = BindSkill()
        text = skill.help_text
        assert isinstance(text, str)
        assert len(text) > 0

    def test_bind_status_is_not_called_anymore(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """T-R083 / T-123.2: bind.py no longer pre-checks bind_status().

        The status pre-check was a v0.2.x single-binding-era optimization.
        Under the multi-repo model the server is the only authority on
        duplicate detection (via findByUserAndRepo → 1003), so the client
        sends initiate unconditionally. This test guards against re-adding
        the pre-check, which would re-introduce Bug C (single-binding guard
        that blocks legitimate second-repo binds).
        """
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is True
        provider.bind_status.assert_not_called()
        provider.bind_initiate.assert_called_once()

    def test_missing_token_help_is_informational(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """'Missing token' help must be marked informational, not a real failure."""
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("", {}, context)
        assert result.success is False
        assert result.informational is True
        assert result.error is None

    def test_unknown_error_exposes_code_and_raw(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Unknown bind error must expose server code + raw response for diagnosis."""
        provider.bind_initiate.return_value = {
            "success": False,
            "code": 9999,
            # No 'error' field — exercises the 'unknown' fallback path
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is False
        assert result.informational is False  # this IS a real error
        assert result.error is not None
        # Diagnostic details must be surfaced
        assert "9999" in result.error
        assert "raw=" in result.error

    def test_unknown_error_without_code_still_useful(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Empty server response still gives a diagnosable message."""
        provider.bind_initiate.return_value = {"success": False}
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is False
        assert result.error is not None
        assert "n/a" in result.error  # code=n/a shown when not provided

    def test_server_error_includes_code_suffix(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Server error with code but outside code_map must show the code for debugging."""
        provider.bind_initiate.return_value = {
            "success": False,
            "error": "Something broke on the server",
            "code": 5000,
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is False
        assert result.error is not None
        assert "5000" in result.error
        assert "Something broke" in result.error

    # ── T-125 option B: alias propagation regression ─────────────────────

    def test_bind_passes_derived_repo_alias_to_provider(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """T-125: bind.py must derive a repo_alias and forward it to the
        provider so the server can persist a user-friendly handle for
        ``/use`` from Telegram. We patch ``derive_repo_alias`` to return
        a known value and assert it lands in provider.bind_initiate's
        kwargs verbatim.
        """
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ), patch(
            "chatmd.skills.bind.derive_repo_alias",
            return_value="my-cool-repo",
        ):
            skill.execute("ghp_xxx", {}, context)

        provider.bind_initiate.assert_called_once()
        call_kwargs = provider.bind_initiate.call_args[1]
        assert call_kwargs.get("repo_alias") == "my-cool-repo", (
            "bind.py must forward the derived repo_alias to provider.bind_initiate"
        )

    def test_bind_forwards_empty_repo_alias_when_derivation_fails(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """T-125: when derive_repo_alias returns "" (everything fell
        through), we must still pass it as ``repo_alias=""`` so the
        provider can omit the payload key. The server then synthesises
        an effective_alias from the repo URL on its side -- the user
        is never wedged.
        """
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ), patch(
            "chatmd.skills.bind.derive_repo_alias",
            return_value="",
        ):
            skill.execute("ghp_xxx", {}, context)

        provider.bind_initiate.assert_called_once()
        call_kwargs = provider.bind_initiate.call_args[1]
        # Empty string is the contract value for "let server fall back".
        assert call_kwargs.get("repo_alias") == ""


# ════════════════════════════════════════════════════════════════════════════
# T-R083 / T-126: `/bind status` sub-command (multi-repo listing)
# ════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def list_provider() -> MagicMock:
    """Provider mock with bind_list pre-configured (T-126)."""
    mock = MagicMock()
    mock.bind_list.return_value = {
        "success": True,
        "count": 2,
        "repos": [
            {
                "id": 5,
                "repo_alias": "note-kaka",
                "effective_alias": "note-kaka",
                "repo_url_masked": "github.com/me/note-kaka",
                "is_active": True,
                "bound_at": "2026-04-27 12:00:00",
                "updated_at": "2026-04-28 09:00:00",
            },
            {
                "id": 6,
                "repo_alias": None,
                "effective_alias": "chatmd-test",
                "repo_url_masked": "github.com/me/chatmd-test",
                "is_active": False,
                "bound_at": "2026-04-28 18:00:00",
                "updated_at": "2026-04-28 18:00:00",
            },
        ],
    }
    return mock


class TestBindStatusSubcommand:
    """T-R083 / T-126: `/bind status` lists every visible binding.

    The skill layer must:
    - Recognise `status` as a sub-command (not a token).
    - Render alias + masked URL per row.
    - Mark the active row with ✅ and the workspace-matching row with ▶.
    - Show a friendly empty-state when count=0.
    - Surface list-call errors via the dedicated _list_error path.
    """

    def test_bind_status_dispatches_to_list_not_initiate(
        self, context: SkillContext, list_provider: MagicMock,
    ) -> None:
        """`/bind status` must not call bind_initiate even though it has
        non-empty input -- the sub-command parser short-circuits first.
        """
        skill = BindSkill(provider=list_provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="",
        ):
            skill.execute("status", {}, context)

        list_provider.bind_list.assert_called_once_with(platform="telegram")
        list_provider.bind_initiate.assert_not_called()

    def test_bind_status_renders_two_repos_with_aliases(
        self, context: SkillContext, list_provider: MagicMock,
    ) -> None:
        """Both rows must show their effective alias + masked URL."""
        skill = BindSkill(provider=list_provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="",
        ):
            result = skill.execute("status", {}, context)

        assert result.success is True
        assert "note-kaka" in result.output
        assert "chatmd-test" in result.output  # effective_alias for NULL row
        assert "github.com/me/note-kaka" in result.output
        assert "github.com/me/chatmd-test" in result.output

    def test_bind_status_marks_active_row_with_check(
        self, context: SkillContext, list_provider: MagicMock,
    ) -> None:
        """The is_active=True row must render with the ✅ marker."""
        skill = BindSkill(provider=list_provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="",
        ):
            result = skill.execute("status", {}, context)

        # The active row carries 'note-kaka' -- find that line and
        # confirm it has the marker.
        active_line = next(
            line for line in result.output.splitlines()
            if "note-kaka" in line
        )
        assert "✅" in active_line

    def test_bind_status_marks_current_workspace_with_arrow(
        self, context: SkillContext, list_provider: MagicMock,
    ) -> None:
        """A row whose masked URL matches the workspace remote gets ▶."""
        skill = BindSkill(provider=list_provider)
        # workspace remote points at chatmd-test (the inactive row),
        # so the ▶ should land on that line, not on note-kaka.
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/me/chatmd-test.git",
        ):
            result = skill.execute("status", {}, context)

        chatmd_line = next(
            line for line in result.output.splitlines()
            if "chatmd-test" in line
        )
        note_kaka_line = next(
            line for line in result.output.splitlines()
            if "note-kaka" in line
        )
        assert "▶" in chatmd_line
        assert "▶" not in note_kaka_line

    def test_bind_status_empty_emits_friendly_hint(
        self, context: SkillContext, list_provider: MagicMock,
    ) -> None:
        """count=0 must show an empty-state hint, not a confused blank."""
        list_provider.bind_list.return_value = {
            "success": True, "count": 0, "repos": [],
        }
        skill = BindSkill(provider=list_provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="",
        ):
            result = skill.execute("status", {}, context)

        assert result.success is True
        assert result.informational is True
        # Empty state should mention how to create a binding.
        assert "/bind" in result.output

    def test_bind_status_propagates_list_error(
        self, context: SkillContext, list_provider: MagicMock,
    ) -> None:
        """A failed bind_list call must yield a real error, not a blank list."""
        list_provider.bind_list.return_value = {
            "success": False,
            "error": "Network unreachable",
            "code": None,
        }
        skill = BindSkill(provider=list_provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="",
        ):
            result = skill.execute("status", {}, context)

        assert result.success is False
        assert result.error is not None
        assert "Network unreachable" in result.error

    def test_bind_status_handles_workspace_without_remote(
        self, context: SkillContext, list_provider: MagicMock,
    ) -> None:
        """No git remote should still render the list (just no ▶ marker
        on any data row -- the legend footer is allowed to mention it).

        This is the case where the user runs `/bind status` from a
        non-git directory but is still authenticated -- the list itself
        is useful (they can see what's bound elsewhere).
        """
        skill = BindSkill(provider=list_provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value=None,
        ):
            result = skill.execute("status", {}, context)

        assert result.success is True
        assert "note-kaka" in result.output
        # No data row may carry the ▶ marker -- check only the lines
        # that mention an alias, ignoring header/footer/legend.
        data_lines = [
            line for line in result.output.splitlines()
            if "note-kaka" in line or "chatmd-test" in line
        ]
        assert data_lines, "expected at least two data rows"
        for line in data_lines:
            assert "▶" not in line, (
                f"data row leaked workspace marker: {line!r}"
            )
