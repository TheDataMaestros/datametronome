"""Tests for RouterAgent and RoutingDecision schema."""
import pytest
from pydantic import ValidationError


def test_routing_decision_valid():
    from datametronome_podium.services.agents.router import RoutingDecision

    rd = RoutingDecision(
        intent="investigation",
        mode="chain",
        agents=["investigation", "config"],
        reasoning="User asked why checks failed and how to fix them.",
    )
    assert rd.intent == "investigation"
    assert rd.mode == "chain"
    assert rd.agents == ["investigation", "config"]


def test_routing_decision_invalid_intent():
    from datametronome_podium.services.agents.router import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(intent="unknown_intent", mode="single", agents=["report"], reasoning="")  # type: ignore[invalid-argument-type]


def test_routing_decision_invalid_mode():
    from datametronome_podium.services.agents.router import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(intent="quick", mode="broadcast", agents=["report"], reasoning="")  # type: ignore[invalid-argument-type]


def test_routing_decision_invalid_agent():
    from datametronome_podium.services.agents.router import RoutingDecision

    with pytest.raises(ValidationError):
        RoutingDecision(intent="quick", mode="single", agents=["hacker"], reasoning="")  # type: ignore[invalid-argument-type]


@pytest.mark.asyncio
async def test_router_agent_structured_output_with_test_model():
    """RouterAgent must return a RoutingDecision when run with TestModel."""
    from pydantic_ai.models.test import TestModel
    from datametronome_podium.services.agents.router import build_router_agent, RoutingDecision

    agent = build_router_agent(TestModel())
    result = await agent.run("What is the status of my data sources?")
    assert isinstance(result.output, RoutingDecision)


def test_routing_decision_accepts_insight_intent():
    from datametronome_podium.services.agents.router import RoutingDecision
    decision = RoutingDecision(
        intent="insight", mode="single", agents=["insight"],
        reasoning="User wants data exploration",
    )
    assert decision.intent == "insight"
    assert decision.agents == ["insight"]


def test_routing_decision_insight_chain():
    from datametronome_podium.services.agents.router import RoutingDecision
    decision = RoutingDecision(
        intent="insight", mode="chain", agents=["insight", "config"],
        reasoning="Explore then configure",
    )
    assert decision.mode == "chain"
