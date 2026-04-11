"""
Builds Pydantic AI Model objects from configuration.

Resolution order for AI settings: DB (app_settings table) → env vars.
This lets each installation manage its AI provider/model/key via the UI
without requiring a redeploy.

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
        from pydantic_ai.models.openai import OpenAIModel  # ty:ignore[deprecated]
        from pydantic_ai.providers.openai import OpenAIProvider

        kwargs: dict = {"api_key": api_key or ""}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAIModel(model_name, provider=OpenAIProvider(**kwargs))  # ty:ignore[deprecated]

    if provider == "gemini":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        return GoogleModel(
            model_name,
            provider=GoogleProvider(api_key=api_key or ""),
        )

    if provider == "ollama":
        # Ollama exposes an OpenAI-compatible API
        from pydantic_ai.models.openai import OpenAIModel  # ty:ignore[deprecated]
        from pydantic_ai.providers.openai import OpenAIProvider

        ollama_base = base_url or "http://localhost:11434/v1"
        return OpenAIModel(  # ty:ignore[deprecated]
            model_name,
            provider=OpenAIProvider(base_url=ollama_base, api_key="ollama"),
        )

    raise ValueError(
        f"Unsupported AI provider: '{provider}'. "
        "Choose one of: anthropic, openai, gemini, ollama"
    )


def _get_ai_config() -> dict[str, str | None]:
    """Resolve AI configuration: DB app_settings first, env vars as fallback.

    Returns a dict with keys: provider, model, api_key, router_model,
    heavy_model, base_url.
    """
    from datametronome_podium.core.config import settings

    # Start with env-var defaults
    cfg: dict[str, str | None] = {
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "api_key": settings.ai_api_key or None,
        "router_model": settings.ai_router_model,
        "heavy_model": settings.ai_heavy_model,
        "base_url": settings.ai_base_url,
    }

    # Try to overlay DB settings (best-effort — table may not exist yet)
    try:
        import asyncio
        from datametronome_podium.core.database import get_executor
        from datametronome_podium.features.settings.repo import AppSettingsRepo

        repo = AppSettingsRepo(get_executor())
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context — can't block.  Use a sync query.
            return cfg

        mapping = {
            "ai_provider": "provider",
            "ai_model": "model",
            "ai_api_key": "api_key",
            "ai_router_model": "router_model",
            "ai_heavy_model": "heavy_model",
            "ai_base_url": "base_url",
        }
        for db_key, cfg_key in mapping.items():
            val = loop.run_until_complete(repo.get_decrypted(db_key))
            if val:
                cfg[cfg_key] = val
    except Exception:
        # DB not ready, table missing, etc. — fall back silently to env vars.
        pass

    return cfg


def build_model_from_settings() -> Model:
    """Build the main agent model from application settings."""
    cfg = _get_ai_config()
    provider = cfg["provider"] or "ollama"
    model_name = cfg["model"] or "qwen2.5"
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]

    if provider == "ollama" and not base_url:
        from datametronome_podium.core.config import settings
        base_url = settings.ollama_api_base.rstrip("/") + "/v1"

    logger.info("Building main model: provider=%s model=%s", provider, model_name)
    return build_model(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
    )


def build_router_model_from_settings() -> Model:
    """Build the router model from settings.

    Uses ai_router_model if set (cheaper model for routing), otherwise ai_model.
    """
    cfg = _get_ai_config()
    provider = cfg["provider"] or "ollama"
    model_name = cfg["router_model"] or cfg["model"] or "qwen2.5"
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]

    if provider == "ollama" and not base_url:
        from datametronome_podium.core.config import settings
        base_url = settings.ollama_api_base.rstrip("/") + "/v1"

    logger.info("Building router model: provider=%s model=%s", provider, model_name)
    return build_model(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
    )


def build_heavy_model_from_settings() -> Model:
    """Build a more capable model for complex analysis tasks.

    Uses ai_heavy_model if set (e.g. gemini-2.5-pro for deep analysis),
    otherwise falls back to ai_model.
    """
    cfg = _get_ai_config()
    provider = cfg["provider"] or "ollama"
    model_name = cfg["heavy_model"] or cfg["model"] or "qwen2.5"
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]

    if provider == "ollama" and not base_url:
        from datametronome_podium.core.config import settings
        base_url = settings.ollama_api_base.rstrip("/") + "/v1"

    logger.info("Building heavy model: provider=%s model=%s", provider, model_name)
    return build_model(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
    )
