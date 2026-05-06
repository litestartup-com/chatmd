"""Tests for chatmd.skills.unbind — /unbind Skill (T-R083 / T-126)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chatmd.skills.base import SkillContext
from chatmd.skills.unbind import UnbindSkill


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
    """Mock LiteStartupProvider with bind_list + bind_unbind ready.

    The default list response carries two rows so we can exercise the
    workspace-match resolution and the active-promotion path. Each test
    can override the per-call behaviour via ``provider.bind_unbind.return_value``
    or ``provider.bind_list.return_value``.
    """
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
            },
            {
                "id": 6,
                "repo_alias": None,
                "effective_alias": "chatmd-test",
                "repo_url_masked": "github.com/me/chatmd-test",
                "is_active": False,
            },
        ],
    }
    mock.bind_unbind.return_value = {
        "success": True,
        "deleted": {"id": 6, "repo_alias": None},
        "deleted_uuid": "uuid-6",
        "new_active": None,
        "remaining_count": 1,
    }
    return mock


# ════════════════════════════════════════════════════════════════════════════
# Skill metadata + provider injection
# ════════════════════════════════════════════════════════════════════════════


class TestUnbindSkillMetadata:
    """Skill registration surface."""

    def test_skill_name_and_category(self) -> None:
        skill = UnbindSkill()
        assert skill.name == "unbind"
        assert skill.category == "general"
        assert skill.requires_network is True

    def test_no_provider_error(self, context: SkillContext) -> None:
        skill = UnbindSkill(provider=None)
        result = skill.execute("anything", {}, context)
        assert result.success is False
        assert result.error is not None

    def test_set_provider_injection(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        skill = UnbindSkill(provider=None)
        skill.set_provider(provider)
        result = skill.execute("--all", {}, context)
        # bind_unbind(all=True) is the path we expect
        assert result.success is True

    def test_help_text_property(self) -> None:
        skill = UnbindSkill()
        text = skill.help_text
        assert isinstance(text, str)
        assert len(text) > 0


# ════════════════════════════════════════════════════════════════════════════
# Mode 1: /unbind --all
# ════════════════════════════════════════════════════════════════════════════


class TestUnbindAll:
    """`/unbind --all` wipes every binding for the user."""

    def test_dispatches_with_all_true(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        provider.bind_unbind.return_value = {
            "success": True,
            "deleted_count": 2,
            "deleted": [
                {"id": 5, "repo_alias": "note-kaka", "effective_alias": "note-kaka"},
                {"id": 6, "repo_alias": None, "effective_alias": "chatmd-test"},
            ],
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("--all", {}, context)

        provider.bind_unbind.assert_called_once_with(
            all=True, platform="telegram",
        )
        assert result.success is True
        assert "2" in result.output
        assert "note-kaka" in result.output
        assert "chatmd-test" in result.output  # effective_alias for NULL row

    def test_short_flag_dash_a(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """`/unbind -a` is also a recognised wipe-all flag."""
        provider.bind_unbind.return_value = {
            "success": True, "deleted_count": 0, "deleted": [],
        }
        skill = UnbindSkill(provider=provider)
        skill.execute("-a", {}, context)
        provider.bind_unbind.assert_called_once_with(
            all=True, platform="telegram",
        )

    def test_empty_wipe_emits_friendly_message(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """`/unbind --all` when no bindings exist must say so kindly,
        not raise / show a "0 binding(s)" awkward summary.
        """
        provider.bind_unbind.return_value = {
            "success": True, "deleted_count": 0, "deleted": [],
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("--all", {}, context)

        assert result.success is True
        assert result.informational is True


# ════════════════════════════════════════════════════════════════════════════
# Mode 2: /unbind <alias>
# ════════════════════════════════════════════════════════════════════════════


class TestUnbindByAlias:
    """`/unbind <alias>` removes the addressed binding."""

    def test_dispatches_with_alias(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        skill = UnbindSkill(provider=provider)
        skill.execute("note-kaka", {}, context)

        provider.bind_unbind.assert_called_once_with(
            alias="note-kaka", platform="telegram",
        )
        # The list pre-fetch must NOT be called when an explicit alias
        # is supplied -- we trust the user's input.
        provider.bind_list.assert_not_called()

    def test_success_renders_remaining_and_no_new_active(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        provider.bind_unbind.return_value = {
            "success": True,
            "deleted": {"id": 6, "repo_alias": "stale"},
            "deleted_uuid": "uuid-6",
            "new_active": None,
            "remaining_count": 1,
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("stale", {}, context)

        assert result.success is True
        assert "stale" in result.output
        assert "1" in result.output  # remaining count

    def test_success_with_new_active_emits_promotion_hint(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Removing the active binding must surface the new active alias."""
        provider.bind_unbind.return_value = {
            "success": True,
            "deleted": {"id": 5, "repo_alias": "note-kaka"},
            "deleted_uuid": "uuid-5",
            "new_active": {
                "id": 6,
                "repo_alias": None,
                "effective_alias": "chatmd-test",
            },
            "remaining_count": 1,
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("note-kaka", {}, context)

        assert result.success is True
        # The user must see what got promoted -- they'll need it for /use.
        assert "chatmd-test" in result.output

    def test_alias_not_found_returns_friendly_error(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Server code 4040 must map to a user-facing alias-not-found message."""
        provider.bind_unbind.return_value = {
            "success": False,
            "error": "Alias 'nope' not found",
            "code": 4040,
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("nope", {}, context)

        assert result.success is False
        assert result.error is not None
        # The friendly message includes the alias and points at /bind status.
        assert "nope" in result.error
        assert "/bind status" in result.error


# ════════════════════════════════════════════════════════════════════════════
# Mode 3: /unbind  (no arg) — workspace-derived alias
# ════════════════════════════════════════════════════════════════════════════


class TestUnbindCurrentWorkspace:
    """`/unbind` (no args) auto-resolves the alias from `git remote origin`."""

    def test_workspace_match_unbinds_correct_alias(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Given a workspace pointing at chatmd-test, the skill must:
        1) call bind_list, 2) find the matching row, 3) call bind_unbind
        with that row's alias (effective_alias since repo_alias is NULL).
        """
        skill = UnbindSkill(provider=provider)
        with patch(
            "chatmd.skills.unbind.get_git_remote_url",
            return_value="https://github.com/me/chatmd-test.git",
        ):
            result = skill.execute("", {}, context)

        provider.bind_list.assert_called_once_with(platform="telegram")
        provider.bind_unbind.assert_called_once_with(
            alias="chatmd-test", platform="telegram",
        )
        assert result.success is True

    def test_no_git_remote_yields_clear_error(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        skill = UnbindSkill(provider=provider)
        with patch(
            "chatmd.skills.unbind.get_git_remote_url",
            return_value=None,
        ):
            result = skill.execute("", {}, context)

        assert result.success is False
        assert result.error is not None
        # We never even reach the network in this branch.
        provider.bind_list.assert_not_called()
        provider.bind_unbind.assert_not_called()

    def test_workspace_with_no_matching_binding_guides_user(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """If list contains zero rows matching the workspace URL, the
        error must point at /bind status + /unbind <alias> rather than
        leaving the user stuck.
        """
        provider.bind_list.return_value = {
            "success": True,
            "count": 1,
            "repos": [
                {
                    "id": 5,
                    "repo_alias": "note-kaka",
                    "effective_alias": "note-kaka",
                    "repo_url_masked": "github.com/me/note-kaka",
                    "is_active": True,
                },
            ],
        }
        skill = UnbindSkill(provider=provider)
        with patch(
            "chatmd.skills.unbind.get_git_remote_url",
            return_value="https://github.com/me/some-other-repo.git",
        ):
            result = skill.execute("", {}, context)

        assert result.success is False
        assert result.error is not None
        assert "/bind status" in result.error
        provider.bind_unbind.assert_not_called()

    def test_list_failure_short_circuits_with_error(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """If the pre-fetch list call fails, we must not blindly call
        unbind -- and the error must surface clearly.
        """
        provider.bind_list.return_value = {
            "success": False,
            "error": "Network down",
            "code": None,
        }
        skill = UnbindSkill(provider=provider)
        with patch(
            "chatmd.skills.unbind.get_git_remote_url",
            return_value="https://github.com/me/anything.git",
        ):
            result = skill.execute("", {}, context)

        assert result.success is False
        assert "Network down" in result.error
        provider.bind_unbind.assert_not_called()


# ════════════════════════════════════════════════════════════════════════════
# Auth / rate-limit cross-cutting paths
# ════════════════════════════════════════════════════════════════════════════


class TestUnbindAuthErrors:
    """Auth / rate limit translation across both alias and --all modes."""

    def test_unauthorized_error_2001(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        provider.bind_unbind.return_value = {
            "success": False,
            "error": "Unauthorized",
            "code": 2001,
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("anything", {}, context)
        assert result.success is False
        assert result.error is not None

    def test_rate_limited_error_3001(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        provider.bind_unbind.return_value = {
            "success": False,
            "error": "Too many requests",
            "code": 3001,
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("anything", {}, context)
        assert result.success is False
        assert result.error is not None

    def test_unknown_error_includes_detail_and_code(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Unmapped error codes must still surface server detail + code
        so users have something to grep for in support tickets.
        """
        provider.bind_unbind.return_value = {
            "success": False,
            "error": "Database unavailable",
            "code": 5001,
        }
        skill = UnbindSkill(provider=provider)
        result = skill.execute("anything", {}, context)

        assert result.success is False
        assert "Database unavailable" in result.error
        assert "5001" in result.error
