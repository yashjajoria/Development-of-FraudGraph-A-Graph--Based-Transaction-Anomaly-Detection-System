from app.core.config import settings
from app.services.llm.base import (  # noqa: F401
    Done, LLMError, LLMProvider, Message, ProviderUnavailableError, RateLimitError, TextDelta, ToolCall, ToolSpec,
)


def get_provider(name: str | None = None) -> LLMProvider:
    """Select the adapter by LLM_PROVIDER (imports lazy so unused SDKs aren't loaded)."""
    name = (name or settings.llm_provider).lower()
    t = settings.llm_timeout
    if name == "groq":
        from app.services.llm.groq_provider import GroqProvider
        return GroqProvider(settings.groq_api_key, settings.groq_model, t)
    if name == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model, t)
    if name == "ollama":
        from app.services.llm.ollama_provider import OllamaProvider
        return OllamaProvider(settings.ollama_url, settings.ollama_model, t)
    if name == "mock":
        from app.services.llm.mock_provider import MockProvider
        return MockProvider(["Mock answer."])
    raise ValueError(f"Unknown LLM_PROVIDER: {name}")
