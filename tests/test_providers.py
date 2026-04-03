"""Tests for AI providers — LiteAgentProvider and OpenAICompatProvider."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from chatmd.providers.liteagent import (
    LiteAgentProvider,
)
from chatmd.providers.liteagent import (
    create_provider_from_config as create_litestartup,
)
from chatmd.providers.openai_compat import (
    OpenAICompatProvider,
)
from chatmd.providers.openai_compat import (
    create_provider_from_config as create_openai,
)

# ========== LiteAgentProvider ==========


class TestLiteAgentProviderInit:
    def test_defaults(self):
        p = LiteAgentProvider("https://api.example.com/chat", "sk-test")
        assert p._api_url == "https://api.example.com/chat"
        assert p._api_key == "sk-test"
        assert p._default_tag == "fast"
        assert p._default_temperature == 0.7
        assert p._max_tokens == 4000
        assert p._language == "en"
        assert p._timeout == 60
        assert p._tags == {}

    def test_custom_params(self):
        p = LiteAgentProvider(
            "https://api.example.com/chat",
            "sk-test",
            default_tag="smart",
            tags={"ask": "fast", "translate": "creative"},
            default_temperature=0.5,
            max_tokens=8000,
            language="en",
            timeout=120,
        )
        assert p._default_tag == "smart"
        assert p._tags == {"ask": "fast", "translate": "creative"}
        assert p._default_temperature == 0.5
        assert p._max_tokens == 8000
        assert p._language == "en"
        assert p._timeout == 120


class TestLiteAgentResolveTag:
    def test_default_tag_when_no_skill(self):
        p = LiteAgentProvider("u", "k", default_tag="smart")
        assert p._resolve_tag("") == "smart"

    def test_default_tag_when_skill_not_in_map(self):
        p = LiteAgentProvider("u", "k", default_tag="fast", tags={"ask": "smart"})
        assert p._resolve_tag("translate") == "fast"

    def test_skill_specific_tag(self):
        p = LiteAgentProvider("u", "k", default_tag="fast", tags={"ask": "smart"})
        assert p._resolve_tag("ask") == "smart"


class TestLiteAgentExtractPrompt:
    def test_single_user_message(self):
        msgs = [{"role": "user", "content": "Hello"}]
        assert LiteAgentProvider._extract_prompt(msgs) == "Hello"

    def test_multi_turn_extracts_last_user(self):
        msgs = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "How are you?"},
        ]
        assert LiteAgentProvider._extract_prompt(msgs) == "How are you?"

    def test_empty_messages(self):
        assert LiteAgentProvider._extract_prompt([]) == ""

    def test_no_user_message_fallback(self):
        msgs = [{"role": "system", "content": "You are helpful"}]
        assert LiteAgentProvider._extract_prompt(msgs) == "You are helpful"


class TestLiteAgentBuildConversation:
    def test_single_message_no_conversation(self):
        msgs = [{"role": "user", "content": "Hi"}]
        assert LiteAgentProvider._build_conversation(msgs) == []

    def test_multi_turn_excludes_last(self):
        msgs = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Bye"},
        ]
        conv = LiteAgentProvider._build_conversation(msgs)
        assert len(conv) == 2
        assert conv[0]["content"] == "Hi"
        assert conv[1]["content"] == "Hello"


class TestLiteAgentExtractText:
    def test_litestartup_format(self):
        data = {"code": 200, "data": {"content": "AI response"}}
        assert LiteAgentProvider._extract_text(data) == "AI response"

    def test_litestartup_string_data(self):
        data = {"code": 200, "data": "plain text"}
        assert LiteAgentProvider._extract_text(data) == "plain text"

    def test_openai_format_fallback(self):
        data = {"choices": [{"message": {"content": "from openai"}}]}
        assert LiteAgentProvider._extract_text(data) == "from openai"

    def test_common_key_fallback(self):
        data = {"content": "direct content"}
        assert LiteAgentProvider._extract_text(data) == "direct content"


class TestLiteAgentChat:
    @patch("chatmd.providers.liteagent.httpx.post")
    def test_successful_chat(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 200, "data": {"content": "Hello!"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteAgentProvider("https://api.example.com/chat", "sk-test")
        result = p.chat([{"role": "user", "content": "Hi"}], skill_name="ask")

        assert result == "Hello!"
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["prompt"] == "Hi"
        assert payload["mode"] == "direct"
        assert payload["tag"] == "fast"
        assert payload["language"] == "en"
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 4000
        assert "system_prompt" not in payload
        assert "conversation" not in payload

    @patch("chatmd.providers.liteagent.httpx.post")
    def test_chat_with_skill_tag(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"content": "ok"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteAgentProvider(
            "u", "k", default_tag="fast", tags={"ask": "smart"},
        )
        p.chat([{"role": "user", "content": "Q"}], skill_name="ask")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["tag"] == "smart"

    @patch("chatmd.providers.liteagent.httpx.post")
    def test_chat_with_system_prompt(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"content": "ok"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteAgentProvider("u", "k")
        p.chat(
            [{"role": "user", "content": "Hi"}],
            system_prompt="You are a translator",
        )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["system_prompt"] == "You are a translator"

    @patch("chatmd.providers.liteagent.httpx.post")
    def test_chat_with_conversation(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"content": "fine"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = LiteAgentProvider("u", "k")
        msgs = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "How are you?"},
        ]
        p.chat(msgs)

        payload = mock_post.call_args.kwargs["json"]
        assert payload["prompt"] == "How are you?"
        assert len(payload["conversation"]) == 2

    @patch("chatmd.providers.liteagent.httpx.post")
    def test_timeout_error(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timeout")
        p = LiteAgentProvider("u", "k", timeout=30)
        with pytest.raises(RuntimeError, match="timeout.*30s"):
            p.chat([{"role": "user", "content": "Hi"}])

    @patch("chatmd.providers.liteagent.httpx.post")
    def test_401_error(self, mock_post):
        resp = httpx.Response(401, request=httpx.Request("POST", "u"))
        mock_post.side_effect = httpx.HTTPStatusError("", request=resp.request, response=resp)
        p = LiteAgentProvider("u", "k")
        with pytest.raises(RuntimeError, match="API Key invalid"):
            p.chat([{"role": "user", "content": "Hi"}])

    @patch("chatmd.providers.liteagent.httpx.post")
    def test_429_error(self, mock_post):
        resp = httpx.Response(429, request=httpx.Request("POST", "u"))
        mock_post.side_effect = httpx.HTTPStatusError("", request=resp.request, response=resp)
        p = LiteAgentProvider("u", "k")
        with pytest.raises(RuntimeError, match="rate too high"):
            p.chat([{"role": "user", "content": "Hi"}])


class TestLiteAgentCreateFromConfig:
    def test_full_config(self):
        cfg = {
            "api_url": "https://api.example.com/chat",
            "api_key": "sk-test",
            "default_tag": "smart",
            "tags": {"ask": "fast"},
            "default_temperature": 0.5,
            "max_tokens": 8000,
            "language": "en",
            "timeout": 120,
        }
        p = create_litestartup(cfg)
        assert p._api_url == "https://api.example.com/chat"
        assert p._default_tag == "smart"
        assert p._tags == {"ask": "fast"}
        assert p._language == "en"

    def test_minimal_config(self):
        cfg = {"api_url": "https://api.example.com", "api_key": "sk-x"}
        p = create_litestartup(cfg)
        assert p._default_tag == "fast"
        assert p._default_temperature == 0.7
        assert p._max_tokens == 4000
        assert p._language == "en"


# ========== OpenAICompatProvider ==========


class TestOpenAICompatProviderInit:
    def test_defaults(self):
        p = OpenAICompatProvider("https://api.openai.com/v1/chat/completions", "sk-test")
        assert p._model == "gpt-4o-mini"
        assert p._default_temperature == 0.7
        assert p._max_tokens == 4000
        assert p._timeout == 60

    def test_custom_params(self):
        p = OpenAICompatProvider(
            "https://ollama.local/v1/chat/completions",
            "ollama",
            model="llama3",
            default_temperature=0.3,
            max_tokens=2000,
            timeout=30,
        )
        assert p._model == "llama3"
        assert p._default_temperature == 0.3


class TestOpenAICompatExtractText:
    def test_standard_openai_format(self):
        data = {"choices": [{"message": {"content": "Hello!"}}]}
        assert OpenAICompatProvider._extract_text(data) == "Hello!"

    def test_common_key_fallback(self):
        data = {"content": "direct"}
        assert OpenAICompatProvider._extract_text(data) == "direct"

    def test_data_field_fallback(self):
        data = {"data": {"content": "from data"}}
        assert OpenAICompatProvider._extract_text(data) == "from data"


class TestOpenAICompatChat:
    @patch("chatmd.providers.openai_compat.httpx.post")
    def test_successful_chat(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "World!"}}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = OpenAICompatProvider("https://api.openai.com/v1/chat/completions", "sk-test")
        result = p.chat([{"role": "user", "content": "Hello"}])

        assert result == "World!"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "gpt-4o-mini"
        assert payload["messages"] == [{"role": "user", "content": "Hello"}]
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 4000

    @patch("chatmd.providers.openai_compat.httpx.post")
    def test_system_prompt_prepended(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = OpenAICompatProvider("u", "k")
        p.chat(
            [{"role": "user", "content": "Hi"}],
            system_prompt="Be helpful",
        )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["messages"][0] == {"role": "system", "content": "Be helpful"}
        assert payload["messages"][1] == {"role": "user", "content": "Hi"}

    @patch("chatmd.providers.openai_compat.httpx.post")
    def test_system_prompt_not_duplicated(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = OpenAICompatProvider("u", "k")
        p.chat(
            [
                {"role": "system", "content": "Existing system"},
                {"role": "user", "content": "Hi"},
            ],
            system_prompt="New system",
        )

        payload = mock_post.call_args.kwargs["json"]
        # Should NOT prepend because first message is already system
        assert payload["messages"][0] == {"role": "system", "content": "Existing system"}
        assert len(payload["messages"]) == 2

    @patch("chatmd.providers.openai_compat.httpx.post")
    def test_timeout_error(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timeout")
        p = OpenAICompatProvider("u", "k", timeout=30)
        with pytest.raises(RuntimeError, match="timeout.*30s"):
            p.chat([{"role": "user", "content": "Hi"}])

    @patch("chatmd.providers.openai_compat.httpx.post")
    def test_model_override(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        p = OpenAICompatProvider("u", "k", model="gpt-4o")
        p.chat([{"role": "user", "content": "Hi"}], model="gpt-3.5-turbo")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "gpt-3.5-turbo"


class TestOpenAICompatCreateFromConfig:
    def test_full_config(self):
        cfg = {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_key": "sk-test",
            "model": "gpt-4o",
            "default_temperature": 0.5,
            "max_tokens": 8000,
            "timeout": 120,
        }
        p = create_openai(cfg)
        assert p._model == "gpt-4o"
        assert p._default_temperature == 0.5

    def test_minimal_config(self):
        cfg = {"api_key": "sk-x"}
        p = create_openai(cfg)
        assert p._api_url == "https://api.openai.com/v1/chat/completions"
        assert p._model == "gpt-4o-mini"
