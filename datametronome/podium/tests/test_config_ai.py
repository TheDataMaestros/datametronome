"""Tests for new AI provider config fields."""


def test_ai_provider_defaults():
    from datametronome_podium.core.config import settings

    assert settings.ai_provider in ("anthropic", "openai", "gemini", "ollama")
    assert settings.ai_model
    assert settings.ai_router_model is None or isinstance(settings.ai_router_model, str)


def test_ai_api_key_defaults_to_empty():
    from datametronome_podium.core.config import settings

    assert isinstance(settings.ai_api_key, str)


def test_ai_base_url_defaults_to_none():
    from datametronome_podium.core.config import settings

    assert settings.ai_base_url is None or isinstance(settings.ai_base_url, str)
