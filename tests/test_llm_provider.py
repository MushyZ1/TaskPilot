from types import SimpleNamespace
from unittest.mock import Mock
import pytest

import llm_provider
from llm_provider import OllamaProvider
from llm_provider import OpenAICompatibleProvider


def test_ollama_provider_generate(monkeypatch):

    mock_chat = Mock(
        return_value=SimpleNamespace(
            message=SimpleNamespace(
                content='{"action": "list_tasks"}'
            )
        )
    )

    monkeypatch.setattr(llm_provider, "chat", mock_chat)

    provider = OllamaProvider()

    result = provider.generate(
        messages=[{"role": "user", "content": "List my tasks"}],
        response_format={"type": "object"}
    )

    assert result == '{"action": "list_tasks"}'
    mock_chat.assert_called_once()


def test_ollama_provider_empty_response(monkeypatch):

    mock_chat = Mock(
        return_value=SimpleNamespace(
            message=SimpleNamespace(content=None)
        )
    )

    monkeypatch.setattr(llm_provider, "chat", mock_chat)

    provider = OllamaProvider()

    with pytest.raises(ValueError):
        provider.generate([], {})


def test_openai_provider_generate():
    provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)

    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"action": "list_tasks"}'
                )
            )
        ]
    )

    mock_create = Mock(return_value=mock_response)

    provider.client = Mock()
    provider.client.chat.completions.create = mock_create
    provider.model = "test-model"

    result = provider.generate(
        messages=[{"role": "user", "content": "Show my tasks"}],
        response_format={"type": "object"}
    )

    assert result == '{"action": "list_tasks"}'
    mock_create.assert_called_once()


def test_openai_provider_empty_response():
    provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)

    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None)
            )
        ]
    )

    provider.client = Mock()
    provider.client.chat.completions.create.return_value = mock_response
    provider.model = "test-model"

    with pytest.raises(ValueError, match="LLM returned an empty response"):
        provider.generate(
            messages=[{"role": "user", "content": "Show my tasks"}],
            response_format={"type": "object"}
        )


def test_get_provider_defaults_to_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    mock_provider = Mock()
    mock_ollama = Mock(return_value=mock_provider)

    monkeypatch.setattr(llm_provider, "OllamaProvider", mock_ollama)

    result = llm_provider.get_provider()

    assert result is mock_provider
    mock_ollama.assert_called_once()


def test_get_provider_selects_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    mock_provider = Mock()
    mock_openai = Mock(return_value=mock_provider)

    monkeypatch.setattr(
        llm_provider, "OpenAICompatibleProvider", mock_openai
    )

    result = llm_provider.get_provider()

    assert result is mock_provider
    mock_openai.assert_called_once()


def test_get_provider_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "invalid")

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        llm_provider.get_provider()
