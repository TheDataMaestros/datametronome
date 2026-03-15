"""Smoke test: pydantic-ai must be importable."""


def test_pydantic_ai_importable():
    from pydantic_ai import Agent  # noqa: F401
    from pydantic_ai.models.test import TestModel  # noqa: F401
    assert True
