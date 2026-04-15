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

    def test_already_bound(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """Should return warning when user already has active binding."""
        provider.bind_status.return_value = {
            "success": True,
            "status": "active",
            "platform": "telegram",
            "repo_url_masked": "https://github.com/u***/r***.git",
            "bound_at": "2026-04-14T10:30:00",
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is False
        assert "active" in result.output.lower() or "绑定" in result.output
        provider.bind_initiate.assert_not_called()

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

    def test_bind_status_failure_proceeds(
        self, context: SkillContext, provider: MagicMock,
    ) -> None:
        """If bind_status fails, should proceed to initiate anyway."""
        provider.bind_status.return_value = {
            "success": False,
            "error": "Network error",
        }
        skill = BindSkill(provider=provider)
        with patch(
            "chatmd.skills.bind.get_git_remote_url",
            return_value="https://github.com/user/repo.git",
        ):
            result = skill.execute("ghp_xxx", {}, context)

        assert result.success is True
        provider.bind_initiate.assert_called_once()
