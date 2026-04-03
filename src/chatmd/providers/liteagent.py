"""LiteAgent AI Provider — LiteStartup Client API format.

Payload format (matching X-AI prototype and LiteStartup /client/v2/ai/chat):
    prompt, mode, tag, language, system_prompt, conversation, temperature, max_tokens
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from chatmd.providers.base import AIProvider

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60
_DEFAULT_TAG = "fast"
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_MAX_TOKENS = 4000
_DEFAULT_LANGUAGE = "en"


class LiteAgentProvider(AIProvider):
    """AI Provider for the LiteStartup Client API (/client/v2/ai/chat).

    Uses prompt + tag + mode format, NOT OpenAI messages format.
    """

    name = "litestartup"

    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        default_tag: str = _DEFAULT_TAG,
        tags: dict[str, str] | None = None,
        default_temperature: float = _DEFAULT_TEMPERATURE,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        language: str = _DEFAULT_LANGUAGE,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._default_tag = default_tag
        self._tags = tags or {}
        self._default_temperature = default_temperature
        self._max_tokens = max_tokens
        self._language = language
        self._timeout = timeout

    def chat(self, messages: list[dict], **kwargs: Any) -> str:
        """Send a chat request to the LiteStartup Client API.

        Keyword args:
            skill_name: str — used to look up per-skill tag override.
            system_prompt: str — system prompt (optional).
            tag: str — explicit tag override.
            temperature: float — override default temperature.
            max_tokens: int — override default max_tokens.
        """
        skill_name = kwargs.get("skill_name", "")
        tag = kwargs.get("tag", self._resolve_tag(skill_name))
        temperature = kwargs.get("temperature", self._default_temperature)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)
        system_prompt = kwargs.get("system_prompt", "")

        # Extract prompt from messages (last user message)
        prompt = self._extract_prompt(messages)
        # Build conversation from earlier messages (if multi-turn)
        conversation = self._build_conversation(messages)

        payload: dict[str, Any] = {
            "prompt": prompt,
            "mode": "direct",
            "tag": tag,
            "language": self._language,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if conversation:
            payload["conversation"] = conversation

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(
            "LiteStartup request: tag=%s, prompt_len=%d",
            tag,
            len(prompt),
        )

        try:
            resp = httpx.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"AI API request timeout ({self._timeout}s)") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                raise RuntimeError("API Key invalid, please check configuration") from exc
            if status == 429:
                raise RuntimeError("Request rate too high, please retry later") from exc
            raise RuntimeError(f"AI API error (HTTP {status})") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error: {exc}") from exc

        return self._extract_text(data)

    def _resolve_tag(self, skill_name: str) -> str:
        """Resolve the model tag for a given skill name."""
        if skill_name and skill_name in self._tags:
            return self._tags[skill_name]
        return self._default_tag

    @staticmethod
    def _extract_prompt(messages: list[dict]) -> str:
        """Extract the prompt text from the last user message."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        # Fallback: use last message content regardless of role
        if messages:
            return messages[-1].get("content", "")
        return ""

    @staticmethod
    def _build_conversation(messages: list[dict]) -> list[dict]:
        """Build conversation history from messages (excluding last user message)."""
        if len(messages) <= 1:
            return []
        return [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]

    @staticmethod
    def _extract_text(data: dict) -> str:
        """Extract the assistant message text from the API response."""
        # LiteStartup format: {code: 200, data: {content: "..."}}
        if "data" in data:
            d = data["data"]
            if isinstance(d, str):
                return d
            if isinstance(d, dict):
                return d.get("content", d.get("text", str(d)))

        # OpenAI-compatible format (fallback)
        choices = data.get("choices")
        if choices and isinstance(choices, list):
            msg = choices[0].get("message", {})
            return msg.get("content", "")

        # Fallback: look for common keys
        for key in ("content", "text", "result", "answer", "response"):
            if key in data:
                return str(data[key])

        logger.warning("Cannot extract text from AI response: %s", list(data.keys()))
        return str(data)


def create_provider_from_config(provider_cfg: dict) -> LiteAgentProvider:
    """Create a LiteAgentProvider from a config dict."""
    return LiteAgentProvider(
        api_url=provider_cfg.get("api_url", ""),
        api_key=provider_cfg.get("api_key", ""),
        default_tag=provider_cfg.get("default_tag", _DEFAULT_TAG),
        tags=provider_cfg.get("tags", {}),
        default_temperature=provider_cfg.get("default_temperature", _DEFAULT_TEMPERATURE),
        max_tokens=provider_cfg.get("max_tokens", _DEFAULT_MAX_TOKENS),
        language=provider_cfg.get("language", _DEFAULT_LANGUAGE),
        timeout=provider_cfg.get("timeout", _DEFAULT_TIMEOUT),
    )
