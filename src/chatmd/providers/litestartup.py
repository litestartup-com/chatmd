"""LiteStartup unified provider — single API key, multiple endpoints.

Centralizes authentication and endpoint routing for all LiteStartup services:
- AI chat:  POST /client/v2/ai/chat
- Upload:   POST /client/v2/upload
- Publish:  POST /client/v2/publish
- (future)  notify, subscribe, etc.

Backward compatible with the old ``ai.providers[].api_url`` config format.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60

# Default endpoint paths (relative to api_base)
_DEFAULT_ENDPOINTS: dict[str, str] = {
    "chat": "/client/v2/ai/chat",
    "upload": "/client/v2/upload",
    "publish": "/client/v2/publish",
}


class LiteStartupProvider:
    """Unified provider for LiteStartup API services.

    Holds a single ``api_base`` + ``api_key`` pair and routes requests
    to the correct endpoint path.
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        endpoints: dict[str, str] | None = None,
    ) -> None:
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        # Merge user overrides on top of defaults
        self._endpoints = {**_DEFAULT_ENDPOINTS, **(endpoints or {})}

    # -- Public properties ---------------------------------------------------

    @property
    def api_base(self) -> str:
        return self._api_base

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def timeout(self) -> int:
        return self._timeout

    # -- Endpoint resolution -------------------------------------------------

    def endpoint(self, name: str) -> str:
        """Return the full URL for a named endpoint.

        Raises ``ValueError`` if *name* is not a known endpoint.
        """
        path = self._endpoints.get(name)
        if path is None:
            raise ValueError(
                f"Unknown endpoint: {name!r}. "
                f"Available: {', '.join(sorted(self._endpoints))}"
            )
        return f"{self._api_base}{path}"

    def auth_headers(self) -> dict[str, str]:
        """Return common authentication headers."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    # -- Upload --------------------------------------------------------------

    def upload(self, file_path: Path) -> dict[str, Any]:
        """Upload a file to LiteStartup.

        Returns ``{"success": True, "url": "..."}`` on success,
        or ``{"success": False, "error": "..."}`` on failure.
        """
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        url = self.endpoint("upload")
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

        logger.debug("Uploading %s to %s", file_path.name, url)

        try:
            with open(file_path, "rb") as f:
                resp = httpx.post(
                    url,
                    files={"file": (file_path.name, f, content_type)},
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=self._timeout,
                )
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException:
            return {"success": False, "error": f"Upload timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            return {"success": False, "error": f"HTTP {exc.response.status_code}"}
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        if data.get("success") and data.get("url"):
            return {"success": True, "url": data["url"]}
        return {"success": False, "error": data.get("message", "Unknown upload error")}

    # -- Publish -------------------------------------------------------------

    def publish(self, *, html_content: str, title: str) -> dict[str, Any]:
        """Publish HTML content to LiteStartup.

        Returns ``{"success": True, "url": "..."}`` on success,
        or ``{"success": False, "error": "..."}`` on failure.
        """
        url = self.endpoint("publish")
        payload = {"html": html_content, "title": title}

        logger.debug("Publishing '%s' to %s", title, url)

        try:
            resp = httpx.post(
                url,
                json=payload,
                headers=self.auth_headers(),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException:
            return {"success": False, "error": f"Publish timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            return {"success": False, "error": f"HTTP {exc.response.status_code}"}
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        if data.get("success") and data.get("url"):
            return {"success": True, "url": data["url"]}
        return {"success": False, "error": data.get("message", "Unknown publish error")}


# -- Factory -----------------------------------------------------------------


def _extract_api_base(api_url: str) -> str:
    """Extract the API base URL from a full endpoint URL.

    Example: ``https://api.litestartup.com/client/v2/ai/chat``
    -> ``https://api.litestartup.com``
    """
    parsed = urlparse(api_url)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else api_url


def create_litestartup_provider(cfg: dict[str, Any]) -> LiteStartupProvider:
    """Create a LiteStartupProvider from a config dict.

    Supports both new format (``api_base``) and legacy format (``api_url``).
    """
    api_key = cfg.get("api_key", "")
    timeout = cfg.get("timeout", _DEFAULT_TIMEOUT)
    endpoints = cfg.get("endpoints")

    # New format: explicit api_base
    api_base = cfg.get("api_base", "")
    if not api_base:
        # Legacy format: extract base from full api_url
        api_url = cfg.get("api_url", "")
        api_base = _extract_api_base(api_url) if api_url else ""

    return LiteStartupProvider(
        api_base=api_base,
        api_key=api_key,
        timeout=timeout,
        endpoints=endpoints,
    )
