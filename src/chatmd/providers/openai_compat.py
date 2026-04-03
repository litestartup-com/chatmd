"""OpenAI-compatible AI Provider — standard messages format.

Works with any OpenAI-compatible API (OpenAI, Azure OpenAI, Ollama,
LM Studio, vLLM, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from chatmd.providers.base import AIProvider

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_MAX_TOKENS = 4000


class OpenAICompatProvider(AIProvider):
    """AI Provider using the standard OpenAI chat completions format.

    Payload: ``{"model": "...", "messages": [...], "temperature": ..., "max_tokens": ...}``
    """

    name = "openai"

    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        model: str = _DEFAULT_MODEL,
        default_temperature: float = _DEFAULT_TEMPERATURE,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._model = model
        self._default_temperature = default_temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    def chat(self, messages: list[dict], **kwargs: Any) -> str:
        """Send a chat request using OpenAI-compatible format.

        Keyword args:
            model: str — override default model.
            system_prompt: str — prepended as a system message.
            temperature: float — override default temperature.
            max_tokens: int — override default max_tokens.
        """
        model = kwargs.get("model", self._model)
        temperature = kwargs.get("temperature", self._default_temperature)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)
        system_prompt = kwargs.get("system_prompt", "")

        # Prepend system message if provided and not already present
        final_messages = list(messages)
        if system_prompt and (
            not final_messages or final_messages[0].get("role") != "system"
        ):
            final_messages.insert(0, {"role": "system", "content": system_prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": final_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(
            "OpenAI-compat request: model=%s, messages=%d",
            model,
            len(final_messages),
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

    @staticmethod
    def _extract_text(data: dict) -> str:
        """Extract the assistant message text from OpenAI-format response."""
        # Standard OpenAI format: {choices: [{message: {content: "..."}}]}
        choices = data.get("choices")
        if choices and isinstance(choices, list):
            msg = choices[0].get("message", {})
            return msg.get("content", "")

        # Fallback: look for common keys
        for key in ("content", "text", "result", "answer", "response"):
            if key in data:
                return str(data[key])

        # Generic data field
        if "data" in data:
            d = data["data"]
            if isinstance(d, str):
                return d
            if isinstance(d, dict):
                return d.get("content", d.get("text", str(d)))

        logger.warning("Cannot extract text from AI response: %s", list(data.keys()))
        return str(data)


def create_provider_from_config(provider_cfg: dict) -> OpenAICompatProvider:
    """Create an OpenAICompatProvider from a config dict."""
    return OpenAICompatProvider(
        api_url=provider_cfg.get("api_url", "https://api.openai.com/v1/chat/completions"),
        api_key=provider_cfg.get("api_key", ""),
        model=provider_cfg.get("model", _DEFAULT_MODEL),
        default_temperature=provider_cfg.get("default_temperature", _DEFAULT_TEMPERATURE),
        max_tokens=provider_cfg.get("max_tokens", _DEFAULT_MAX_TOKENS),
        timeout=provider_cfg.get("timeout", _DEFAULT_TIMEOUT),
    )
