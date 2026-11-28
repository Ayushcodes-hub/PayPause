from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from groq import APIError

from app.services.ai import groq_provider
from app.services.ai.groq_provider import (
    AIProviderNotConfigured,
    AIProviderUnavailable,
    GroqAIProvider,
)


def configure_groq(monkeypatch):
    monkeypatch.setattr(groq_provider.settings, "AI_PROVIDER", "groq")
    monkeypatch.setattr(groq_provider.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(groq_provider.settings, "AI_MODEL", "test-model")
    monkeypatch.setattr(
        groq_provider.settings,
        "AI_REQUEST_TIMEOUT_SECONDS",
        30.0,
    )


@pytest.mark.asyncio
async def test_groq_provider_generates_text(monkeypatch):
    configure_groq(monkeypatch)

    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Payment explanation")
                )
            ]
        )
    )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )
    )

    provider = GroqAIProvider(client=client)

    result = await provider.generate_text(
        system_prompt="You are a financial assistant.",
        user_prompt="Explain a failed payment.",
    )

    assert result == "Payment explanation"
    create.assert_awaited_once()

    request = create.await_args.kwargs
    assert request["model"] == "test-model"
    assert request["temperature"] == 0.2
    assert request["stream"] is False


@pytest.mark.asyncio
async def test_groq_provider_rejects_missing_configuration(monkeypatch):
    configure_groq(monkeypatch)
    monkeypatch.setattr(groq_provider.settings, "AI_API_KEY", None)

    with pytest.raises(AIProviderNotConfigured):
        GroqAIProvider()


@pytest.mark.asyncio
async def test_groq_provider_rejects_empty_prompts(monkeypatch):
    configure_groq(monkeypatch)

    provider = GroqAIProvider(client=object())

    with pytest.raises(ValueError):
        await provider.generate_text(
            system_prompt=" ",
            user_prompt="Explain payment status.",
        )


@pytest.mark.asyncio
async def test_groq_provider_sanitizes_api_errors(monkeypatch):
    configure_groq(monkeypatch)

    from httpx import Request

    create = AsyncMock(
        side_effect=APIError(
            "private provider error",
            request=Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
            body=None,
        )
    )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )
    )

    provider = GroqAIProvider(client=client)

    with pytest.raises(AIProviderUnavailable) as error:
        await provider.generate_text(
            system_prompt="Assistant",
            user_prompt="Explain payment status.",
        )

    assert "private provider error" not in str(error.value)
