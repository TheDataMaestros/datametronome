"""Tests for agent_factory — builds Pydantic AI Model from provider/model/key."""
import pytest


def test_build_model_ollama():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.openai import OpenAIModel

    model = build_model("ollama", "qwen2.5", api_key=None, base_url="http://localhost:11434/v1")
    assert isinstance(model, OpenAIModel)


def test_build_model_anthropic():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.anthropic import AnthropicModel

    model = build_model("anthropic", "claude-haiku-4-5", api_key="sk-ant-test")
    assert isinstance(model, AnthropicModel)


def test_build_model_openai():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.openai import OpenAIModel

    model = build_model("openai", "gpt-4o-mini", api_key="sk-test")
    assert isinstance(model, OpenAIModel)


def test_build_model_gemini():
    from datametronome_podium.services.agent_factory import build_model
    from pydantic_ai.models.google import GoogleModel

    model = build_model("gemini", "gemini-1.5-flash", api_key="test-key")
    assert isinstance(model, GoogleModel)


def test_build_model_unknown_raises():
    from datametronome_podium.services.agent_factory import build_model

    with pytest.raises(ValueError, match="Unsupported AI provider"):
        build_model("foobar", "model", api_key=None)


def test_build_model_from_settings():
    from datametronome_podium.services.agent_factory import build_model_from_settings

    # Should not raise — uses defaults (ollama/qwen2.5)
    model = build_model_from_settings()
    assert model is not None


def test_build_router_model_falls_back_to_ai_model():
    """When ai_router_model is not set, router uses the same model as main agents."""
    from datametronome_podium.services.agent_factory import build_router_model_from_settings
    from datametronome_podium.services.agent_factory import build_model_from_settings

    main = build_model_from_settings()
    router = build_router_model_from_settings()
    # Both should be the same type when no router model is configured
    assert type(main) == type(router)
