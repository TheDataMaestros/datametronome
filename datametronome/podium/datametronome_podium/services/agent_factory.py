"""
Builds Pydantic AI Model objects from environment configuration.

Supported providers: anthropic | openai | gemini | ollama

Pydantic AI v1.x uses a Model + Provider pattern:
    Model(model_name, provider=Provider(api_key=..., base_url=...))
"""
import logging

from pydantic_ai.models import Model

logger = logging.getLogger(__name__)


def build_model(
    provider: str,
    model_name: str,
    api_key: str | None,
    base_url: str | None = None,
) -> Model:
    """Build a Pydantic AI Model for the given provider.

    Args:
        provider: One of "anthropic", "openai", "gemini", "ollama"
        model_name: Provider-specific model identifier
        api_key: API key (not required for Ollama)
        base_url: Custom base URL (required for Ollama; optional for others)

    Returns:
        A Pydantic AI Model instance
    """
    provider = provider.lower().strip()

    if provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(
            model_name,
            provider=AnthropicProvider(api_key=api_key or ""),
        )

    if provider == "openai":
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider

        kwargs: dict = {"api_key": api_key or ""}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAIModel(model_name, provider=OpenAIProvider(**kwargs))

    if provider == "gemini":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        return GoogleModel(
            model_name,
            provider=GoogleProvider(api_key=api_key or ""),
        )

    if provider == "ollama":
        # Ollama exposes an OpenAI-compatible API
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider

        ollama_base = base_url or "http://localhost:11434/v1"
        return OpenAIModel(
            model_name,
            provider=OpenAIProvider(base_url=ollama_base, api_key="ollama"),
        )

    raise ValueError(
        f"Unsupported AI provider: '{provider}'. "
        "Choose one of: anthropic, openai, gemini, ollama"
    )


def build_model_from_settings() -> Model:
    """Build the main agent model from application settings."""
    from datametronome_podium.core.config import settings

    base_url = settings.ai_base_url
    if settings.ai_provider == "ollama" and not base_url:
        # Derive from ollama_api_base (legacy compat)
        base_url = settings.ollama_api_base.rstrip("/") + "/v1"

    logger.info(
        "Building main model: provider=%s model=%s",
        settings.ai_provider,
        settings.ai_model,
    )
    return build_model(
        provider=settings.ai_provider,
        model_name=settings.ai_model,
        api_key=settings.ai_api_key or None,
        base_url=base_url,
    )


def build_router_model_from_settings() -> Model:
    """Build the router model from settings.

    Uses ai_router_model if set (cheaper model for routing), otherwise ai_model.
    """
    from datametronome_podium.core.config import settings

    router_model_name = settings.ai_router_model or settings.ai_model
    base_url = settings.ai_base_url
    if settings.ai_provider == "ollama" and not base_url:
        base_url = settings.ollama_api_base.rstrip("/") + "/v1"

    logger.info(
        "Building router model: provider=%s model=%s",
        settings.ai_provider,
        router_model_name,
    )
    return build_model(
        provider=settings.ai_provider,
        model_name=router_model_name,
        api_key=settings.ai_api_key or None,
        base_url=base_url,
    )
