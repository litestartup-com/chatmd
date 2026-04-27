"""LiteStartup unified provider — single API key, multiple endpoints.

Centralizes authentication and endpoint routing for all LiteStartup services:
- AI chat:       POST /client/v2/ai/chat
- Plans confirm: POST /client/v2/ai/plans/confirm  (T-MVP03-M2 · destructive Phase-2)
- Upload:        POST /client/v2/storage/upload
- Publish:       POST /client/v2/publish
- Email:         POST /client/v2/emails
- Bot bind:      POST /api/bot/bind/initiate, GET /api/bot/bind/status
- Bot notify:    POST /api/bot/notify

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
    "plans_confirm": "/client/v2/ai/plans/confirm",
    "upload": "/client/v2/storage/upload",
    "publish": "/client/v2/publish",
    "email": "/client/v2/emails",
    "bind_initiate": "/api/bot/bind/initiate",
    "bind_status": "/api/bot/bind/status",
    "bot_notify": "/api/bot/notify",
    "bot_sync_complete": "/api/bot/sync-complete",
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

    # -- AI Plans (destructive two-phase confirm) ---------------------------

    def confirm_plan(self, confirm_token: str) -> dict[str, Any]:
        """Execute Phase-2 of the destructive tool confirm flow (T-MVP03-M2).

        Calls ``POST /client/v2/ai/plans/confirm`` with ``{confirm_token}``
        body. The server atomically consumes the token (single-use) and
        replays the previously prepared plan from MySQL ``os_tool_plans``
        without re-entering LiteAgent. See LAD ``RULE.md`` §R2.2 / §R4 / §R8.

        Args:
            confirm_token: The ``cft_<32 hex>`` token issued during Phase-1
                by ``POST /client/v2/ai/chat`` with a ``/la <destructive>``
                prompt.

        Returns:
            Success: ``{"success": True, "tool": str, "rendered": str,
                       "data": dict}``
            Failure: ``{"success": False, "error": str, "code": int}``
                where ``code`` follows LS mapping — 400 bad format,
                403 cross-team, 404 unknown, 409 already consumed,
                410 expired, 500 internal.
        """
        url = self.endpoint("plans_confirm")
        payload = {"confirm_token": confirm_token}
        logger.debug("Confirming plan token=%s", _mask_token(confirm_token))

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
            return {"success": False, "error": f"Confirm timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            return self._parse_error_response(exc, "Confirm")
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        # LS envelope: {code: 200, message, data: {rendered, tool, data, ...}}
        status_code = data.get("code", resp.status_code)
        inner = data.get("data", {}) or {}

        if status_code == 200 and isinstance(inner, dict):
            return {
                "success": True,
                "tool": inner.get("tool", ""),
                "rendered": inner.get("rendered", ""),
                "data": inner.get("data", {}),
            }
        return {
            "success": False,
            "error": data.get("message", "Unknown confirm error"),
            "code": status_code,
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

        # LiteStartup Storage API returns {code, message, data: {publicUrl, ...}}
        status_code = data.get("code", resp.status_code)
        inner = data.get("data", {}) or {}
        public_url = inner.get("publicUrl", "")

        if status_code in (200, 201) and public_url:
            return {"success": True, "url": public_url}
        return {"success": False, "error": data.get("message", "Unknown upload error")}

    # -- Email ----------------------------------------------------------------

    def send_email(
        self,
        *,
        subject: str,
        html: str,
        from_addr: str | None = None,
        from_name: str | None = None,
        to_addr: str | None = None,
        to_name: str | None = None,
    ) -> dict[str, Any]:
        """Send an email via LiteStartup Email API.

        Uses the general ``/client/v2/emails`` endpoint.

        Returns ``{"success": True, "message_id": "..."}`` on success,
        or ``{"success": False, "error": "..."}`` on failure.
        """
        url = self.endpoint("email")
        payload: dict[str, str] = {
            "subject": subject,
            "html": html,
        }
        if from_addr:
            payload["from"] = from_addr
        if from_name:
            payload["from_name"] = from_name
        if to_addr:
            payload["to"] = to_addr
        if to_name:
            payload["to_name"] = to_name

        logger.debug("Sending email: %s", subject)

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
            return {"success": False, "error": f"Email timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            body = ""
            try:
                body = exc.response.json().get("message", "")
            except Exception:
                pass
            msg = f"HTTP {exc.response.status_code}"
            if body:
                msg += f": {body}"
            return {"success": False, "error": msg}
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        status_code = data.get("code", resp.status_code)
        if status_code == 200:
            message_id = (data.get("data") or {}).get("messageId", "")
            return {"success": True, "message_id": message_id}
        return {
            "success": False,
            "error": data.get("message", "Unknown email error"),
        }

    # -- Bot Bind ------------------------------------------------------------

    def bind_initiate(
        self,
        *,
        repo_url: str,
        git_token: str,
        platform: str = "telegram",
        timezone: str = "",
    ) -> dict[str, Any]:
        """Initiate a Bot binding and obtain a 6-digit bind code.

        Calls ``POST /api/bot/bind/initiate``.

        Returns ``{"success": True, "bind_code": "...", ...}`` on success,
        or ``{"success": False, "error": "...", "code": ...}`` on failure.
        """
        url = self.endpoint("bind_initiate")
        payload: dict[str, str] = {
            "repo_url": repo_url,
            "git_token": git_token,
            "platform": platform,
        }
        if timezone:
            payload["timezone"] = timezone

        logger.debug("Initiating bot bind for platform=%s", platform)

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
            return {"success": False, "error": f"Bind timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            return self._parse_error_response(exc, "Bind")
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        if data.get("code") == 0:
            inner = data.get("data", {}) or {}
            return {
                "success": True,
                "bind_code": inner.get("bind_code", ""),
                "expires_in": inner.get("expires_in", 300),
                "bot_username": inner.get("bot_username", ""),
                "bot_deep_link": inner.get("bot_deep_link", ""),
            }
        return {
            "success": False,
            "error": data.get("message", "Unknown bind error"),
            "code": data.get("code"),
        }

    def bind_status(self) -> dict[str, Any]:
        """Query current Bot binding status.

        Calls ``GET /api/bot/bind/status``.

        Returns ``{"success": True, "status": "...", ...}`` on success,
        or ``{"success": False, "error": "..."}`` on failure.
        """
        url = self.endpoint("bind_status")

        try:
            resp = httpx.get(
                url,
                headers=self.auth_headers(),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException:
            return {"success": False, "error": f"Status timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            return self._parse_error_response(exc, "Status")
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        if data.get("code") == 0:
            inner = data.get("data", {}) or {}
            return {
                "success": True,
                "status": inner.get("status", "none"),
                "platform": inner.get("platform"),
                "repo_url_masked": inner.get("repo_url_masked"),
                "bound_at": inner.get("bound_at"),
                "last_sync_at": inner.get("last_sync_at"),
                "pending_messages": inner.get("pending_messages", 0),
            }
        return {
            "success": False,
            "error": data.get("message", "Unknown status error"),
        }

    # -- Bot Notify ----------------------------------------------------------

    def bot_notify(
        self,
        *,
        message: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Push a notification to user's bound Bot platforms.

        Calls ``POST /api/bot/notify``.

        Returns ``{"success": True, "delivered_to": [...]}`` on success,
        or ``{"success": False, "error": "..."}`` on failure.
        """
        url = self.endpoint("bot_notify")
        payload = {"message": message, "priority": priority}

        logger.debug("Sending bot notification: %s", message[:80])

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
            return {"success": False, "error": f"Notify timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            return self._parse_error_response(exc, "Notify")
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        if data.get("success"):
            return {
                "success": True,
                "delivered_to": data.get("delivered_to", []),
            }
        return {
            "success": False,
            "error": data.get("message", "Unknown notify error"),
        }

    # -- Bot Sync Complete ---------------------------------------------------

    def bot_sync_complete(self) -> dict[str, Any]:
        """Notify LiteStartup that a sync cycle completed.

        Calls ``POST /api/bot/sync-complete``.  The server resets
        ``pending_messages`` to 0 for the authenticated user's binding.

        Returns ``{"success": True}`` on success,
        or ``{"success": False, "error": "..."}`` on failure.
        """
        url = self.endpoint("bot_sync_complete")

        try:
            resp = httpx.post(
                url,
                json={},
                headers=self.auth_headers(),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException:
            return {"success": False, "error": f"Sync-complete timeout ({self._timeout}s)"}
        except httpx.HTTPStatusError as exc:
            return self._parse_error_response(exc, "SyncComplete")
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Network error: {exc}"}

        return {"success": data.get("success", False)}

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _parse_error_response(
        exc: httpx.HTTPStatusError,
        label: str,
    ) -> dict[str, Any]:
        """Extract error details from an HTTP error response."""
        body_msg = ""
        code = None
        try:
            body = exc.response.json()
            body_msg = body.get("message", "")
            code = body.get("code")
        except Exception:
            pass
        msg = f"HTTP {exc.response.status_code}"
        if body_msg:
            msg += f": {body_msg}"
        result: dict[str, Any] = {"success": False, "error": msg}
        if code is not None:
            result["code"] = code
        return result

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


def _mask_token(token: str, *, prefix_len: int = 8) -> str:
    """Return a log-safe preview of a confirm_token.

    Shows the first ``prefix_len`` characters (which include the ``cft_``
    family prefix) plus an ellipsis, keeping full tokens out of debug logs
    and audit trails. For tokens shorter than the prefix length, returns
    the whole string unchanged to avoid misleading masks.
    """
    if not token or len(token) <= prefix_len:
        return token or ""
    return f"{token[:prefix_len]}…"


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
