"""Tests for chatmd.infra.git_utils — SSH→HTTPS, platform detection, remote reading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from chatmd.infra.git_utils import (
    detect_git_platform,
    get_git_remote_url,
    get_token_help_url,
    mask_repo_url,
    ssh_to_https,
    strip_url_credentials,
)

# ── ssh_to_https ─────────────────────────────────────────────────────────


class TestSshToHttps:
    """Tests for SSH → HTTPS URL conversion."""

    @pytest.mark.parametrize(
        ("ssh_url", "expected"),
        [
            (
                "git@github.com:user/repo.git",
                "https://github.com/user/repo.git",
            ),
            (
                "git@gitlab.com:user/repo.git",
                "https://gitlab.com/user/repo.git",
            ),
            (
                "git@gitee.com:user/repo.git",
                "https://gitee.com/user/repo.git",
            ),
            (
                "git@bitbucket.org:user/repo.git",
                "https://bitbucket.org/user/repo.git",
            ),
        ],
    )
    def test_ssh_to_https_conversion(
        self, ssh_url: str, expected: str,
    ) -> None:
        assert ssh_to_https(ssh_url) == expected

    def test_ssh_without_dot_git_suffix(self) -> None:
        """SSH URL without .git suffix should still convert."""
        result = ssh_to_https("git@github.com:user/repo")
        assert result == "https://github.com/user/repo.git"

    def test_https_url_unchanged(self) -> None:
        """HTTPS URLs should be returned unchanged."""
        url = "https://github.com/user/repo.git"
        assert ssh_to_https(url) == url

    def test_http_url_unchanged(self) -> None:
        url = "http://gitlab.com/user/repo.git"
        assert ssh_to_https(url) == url

    def test_whitespace_stripped(self) -> None:
        url = "  git@github.com:user/repo.git  "
        assert ssh_to_https(url) == "https://github.com/user/repo.git"

    def test_nested_path(self) -> None:
        """SSH URL with nested group/repo path."""
        url = "git@gitlab.com:org/sub/repo.git"
        assert ssh_to_https(url) == "https://gitlab.com/org/sub/repo.git"


# ── detect_git_platform ──────────────────────────────────────────────────


class TestDetectGitPlatform:
    """Tests for Git platform detection."""

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://github.com/user/repo.git", "github"),
            ("https://gitlab.com/user/repo.git", "gitlab"),
            ("https://gitee.com/user/repo.git", "gitee"),
            ("https://bitbucket.org/user/repo.git", "bitbucket"),
            ("git@github.com:user/repo.git", "github"),
            ("https://self-hosted.example.com/repo.git", "unknown"),
        ],
    )
    def test_detect_platform(self, url: str, expected: str) -> None:
        assert detect_git_platform(url) == expected


# ── get_token_help_url ───────────────────────────────────────────────────


class TestGetTokenHelpUrl:
    """Tests for token help URL lookup."""

    def test_known_platforms(self) -> None:
        assert "github.com" in get_token_help_url("github")
        assert "gitlab.com" in get_token_help_url("gitlab")
        assert "gitee.com" in get_token_help_url("gitee")
        assert "bitbucket.org" in get_token_help_url("bitbucket")

    def test_unknown_platform(self) -> None:
        assert get_token_help_url("unknown") == ""
        assert get_token_help_url("") == ""


# ── get_git_remote_url ───────────────────────────────────────────────────


class TestGetGitRemoteUrl:
    """Tests for reading git remote origin URL."""

    def test_not_a_git_repo(self, tmp_path: Path) -> None:
        """Non-git directory should return None."""
        assert get_git_remote_url(tmp_path) is None

    def test_git_repo_with_remote(self, tmp_path: Path) -> None:
        """Git repo with origin remote should return the URL."""
        (tmp_path / ".git").mkdir()
        mock_url = "https://github.com/user/repo.git\n"
        with patch("chatmd.infra.git_utils.subprocess.run") as mock_run:
            mock_run.return_value.stdout = mock_url
            result = get_git_remote_url(tmp_path)
        assert result == "https://github.com/user/repo.git"

    def test_git_repo_no_remote(self, tmp_path: Path) -> None:
        """Git repo without origin should return None."""
        (tmp_path / ".git").mkdir()
        with patch("chatmd.infra.git_utils.subprocess.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            result = get_git_remote_url(tmp_path)
        assert result is None

    def test_git_not_installed(self, tmp_path: Path) -> None:
        """Missing git binary should return None."""
        (tmp_path / ".git").mkdir()
        with patch("chatmd.infra.git_utils.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            result = get_git_remote_url(tmp_path)
        assert result is None


# ── mask_repo_url ────────────────────────────────────────────────────────


class TestMaskRepoUrl:
    """Tests for repo URL credential stripping and masking."""

    def test_strips_user_pass_credentials(self) -> None:
        url = "https://zxf.0810:Hell0kaka@gitee.com/zxf.0810/chatmd-test.git"
        assert mask_repo_url(url) == "gitee.com/zxf.0810/chatmd-test"

    def test_strips_token_credential(self) -> None:
        url = "https://ghp_xxxxxxxxxxxx@github.com/user/repo.git"
        assert mask_repo_url(url) == "github.com/user/repo"

    def test_plain_https_no_credentials(self) -> None:
        url = "https://github.com/user/repo.git"
        assert mask_repo_url(url) == "github.com/user/repo"

    def test_no_dot_git_suffix(self) -> None:
        url = "https://github.com/user/repo"
        assert mask_repo_url(url) == "github.com/user/repo"

    def test_http_scheme(self) -> None:
        url = "http://user:pass@gitlab.com/org/repo.git"
        assert mask_repo_url(url) == "gitlab.com/org/repo"


# ── strip_url_credentials ────────────────────────────────────────────────


class TestStripUrlCredentials:
    """Tests for stripping credentials while keeping full URL structure."""

    def test_strips_user_pass(self) -> None:
        url = "https://zxf.0810:Hell0kaka@gitee.com/zxf.0810/chatmd-test.git"
        assert strip_url_credentials(url) == "https://gitee.com/zxf.0810/chatmd-test.git"

    def test_strips_token_only(self) -> None:
        url = "https://ghp_xxxxxxxxxxxx@github.com/user/repo.git"
        assert strip_url_credentials(url) == "https://github.com/user/repo.git"

    def test_plain_https_unchanged(self) -> None:
        url = "https://github.com/user/repo.git"
        assert strip_url_credentials(url) == "https://github.com/user/repo.git"

    def test_http_scheme(self) -> None:
        url = "http://user:pass@gitlab.com/org/repo.git"
        assert strip_url_credentials(url) == "http://gitlab.com/org/repo.git"

    def test_preserves_dot_git(self) -> None:
        url = "https://token@github.com/user/repo.git"
        assert strip_url_credentials(url).endswith(".git")
