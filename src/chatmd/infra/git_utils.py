"""Git utility functions — remote URL reading, SSH→HTTPS conversion, platform detection.

Used by the ``/bind`` skill to automatically resolve the user's Git repository
information for Bot binding.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# SSH → HTTPS conversion: git@host:user/repo.git → https://host/user/repo.git
_SSH_PATTERN = re.compile(r"^git@([^:]+):(.+?)(?:\.git)?$")

# Token help page URLs per platform
_TOKEN_HELP_URLS: dict[str, str] = {
    "github": "https://github.com/settings/tokens?type=beta",
    "gitlab": "https://gitlab.com/-/user_settings/personal_access_tokens",
    "gitee": "https://gitee.com/profile/personal_access_tokens",
    "bitbucket": "https://bitbucket.org/account/settings/app-passwords/",
}


def get_git_remote_url(workspace: Path) -> str | None:
    """Read ``git remote get-url origin`` from *workspace*.

    Returns the remote URL string, or ``None`` if the workspace is not a
    Git repo or has no ``origin`` remote.
    """
    if not (workspace / ".git").is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        return url if url else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def ssh_to_https(url: str) -> str:
    """Convert an SSH Git URL to HTTPS format.

    If the URL is already HTTPS (or not a recognized SSH format), returns
    it unchanged.

    Examples::

        git@github.com:user/repo.git  → https://github.com/user/repo.git
        git@gitee.com:user/repo       → https://gitee.com/user/repo.git
        https://github.com/user/repo.git  → (unchanged)
    """
    match = _SSH_PATTERN.match(url.strip())
    if match:
        host = match.group(1)
        path = match.group(2)
        return f"https://{host}/{path}.git"
    return url.strip()


def strip_url_credentials(url: str) -> str:
    """Remove embedded credentials from a URL, keeping scheme and path intact.

    Examples::

        https://user:pass@gitee.com/user/repo.git → https://gitee.com/user/repo.git
        https://ghp_xxx@github.com/user/repo.git  → https://github.com/user/repo.git
        https://github.com/user/repo.git           → https://github.com/user/repo.git
    """
    return re.sub(r"(https?://)[^@]+@", r"\1", url)


def mask_repo_url(url: str) -> str:
    """Strip embedded credentials and scheme from a repo URL for safe display.

    Examples::

        https://user:pass@gitee.com/user/repo.git → gitee.com/user/repo
        https://github.com/user/repo.git           → github.com/user/repo
    """
    # Remove embedded credentials (user:pass@)
    masked = re.sub(r"https?://[^@]+@", "https://", url)
    # Remove scheme
    masked = re.sub(r"^https?://", "", masked)
    # Remove trailing .git
    masked = re.sub(r"\.git$", "", masked)
    return masked


def detect_git_platform(url: str) -> str:
    """Detect the Git hosting platform from a repository URL.

    Returns one of ``"github"``, ``"gitlab"``, ``"gitee"``,
    ``"bitbucket"``, or ``"unknown"``.
    """
    lower = url.lower()
    if "github.com" in lower:
        return "github"
    if "gitlab.com" in lower:
        return "gitlab"
    if "gitee.com" in lower:
        return "gitee"
    if "bitbucket.org" in lower:
        return "bitbucket"
    return "unknown"


def get_token_help_url(platform: str) -> str:
    """Return the token creation page URL for the given platform.

    Returns an empty string for unknown platforms.
    """
    return _TOKEN_HELP_URLS.get(platform, "")
