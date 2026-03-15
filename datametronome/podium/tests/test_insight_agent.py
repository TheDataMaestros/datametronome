"""Tests for InsightAgent construction."""
from pydantic_ai.models.test import TestModel

from datametronome_podium.services.agents.insight import build_insight_agent


def test_build_insight_agent_returns_agent():
    agent = build_insight_agent(TestModel())
    assert agent is not None


def test_build_insight_agent_with_archetype_context():
    archetype = {
        "name": "e-commerce",
        "metrics": [{"name": "aov", "typical_range": [20, 200]}],
        "patterns": ["weekend_spike"],
    }
    agent = build_insight_agent(TestModel(), archetype_context=archetype)
    assert agent is not None


def test_build_insight_agent_with_profile_context():
    profile_context = {
        "domain_type": "e-commerce",
        "learned_patterns": {"weekend_spike": {"confidence": 0.9}},
    }
    agent = build_insight_agent(TestModel(), profile_context=profile_context)
    assert agent is not None
