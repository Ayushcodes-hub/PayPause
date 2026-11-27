import logging

from groq import APIError, AsyncGroq

from app.core.config import settings


logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Base exception for AI provider failures."""


class AIProviderNotConfigured(AIProviderError):
    """Raised when required provider configuration is missing."""


class AIProviderUnavailable(AIProviderError):
    """Raised when the external AI provider cannot complete a request."""


class GroqAIProvider:
    """Reusable asynchronous Groq chat-completion provider."""

    def __init__(self, client=None):
        if settings.AI_PROVIDER != "groq":
            raise AIProviderNotConfigured(
                "The configured AI provider is not supported."
            )

        if not settings.AI_API_KEY or not settings.AI_MODEL:
            raise AIProviderNotConfigured(
                "Groq API key and model must be configured."
            )

        if settings.AI_REQUEST_TIMEOUT_SECONDS <= 0:
            raise AIProviderNotConfigured(
                "AI request timeout must be greater than zero."
            )

        self.model = settings.AI_MODEL
        self.client = client or AsyncGroq(
            api_key=settings.AI_API_KEY,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=1,
        )

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using Groq chat completions."""

        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError("System prompt cannot be empty.")

        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError("User prompt cannot be empty.")

        if not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2.")

        if not 1 <= max_tokens <= 8192:
            raise ValueError("max_tokens must be between 1 and 8192.")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stream=False,
            )

            if not response.choices:
                raise AIProviderUnavailable(
                    "The AI provider returned no response choices."
                )

            content = response.choices[0].message.content

            if not isinstance(content, str) or not content.strip():
                raise AIProviderUnavailable(
                    "The AI provider returned an empty response."
                )

            return content.strip()

        except APIError as exc:
            status_code = getattr(exc, "status_code", None)
            logger.warning(
                "Groq API request failed. HTTP status: %s",
                status_code,
            )
            raise AIProviderUnavailable(
                "The AI provider request failed. Please try again later."
            ) from exc


def get_ai_provider() -> GroqAIProvider:
    """Create a configured Groq provider instance."""
    return GroqAIProvider()
