"""Tests for user memory integration in the orchestrator."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_memory_intent_returns_recall():
    """When router classifies as 'memory', orchestrator returns recall directly."""
    from datametronome_podium.services.orchestrator import run_chat
    from datametronome_podium.services.agents.router import RoutingDecision

    decision = RoutingDecision(
        intent="memory", mode="single", agents=["report"],
        reasoning="User asks about their profile",
    )
    mock_router_result = MagicMock()
    mock_router_result.output = decision

    with patch("datametronome_podium.services.orchestrator._get_router_agent") as mock_router:
        mock_router.return_value.run = AsyncMock(return_value=mock_router_result)
        with patch("datametronome_podium.services.orchestrator._load_user_profile", return_value=None):
            with patch("datametronome_podium.services.orchestrator._handle_memory_recall", return_value="Here's what I know about you..."):
                result = await run_chat("What do you know about me?", [], user_id="user-1")

    assert result["intent"] == "memory"
    assert "what I know" in result["message"]


@pytest.mark.asyncio
async def test_fallback_route_detects_memory():
    """Keyword fallback should detect memory-related phrases."""
    from datametronome_podium.services.orchestrator import _fallback_route

    decision = _fallback_route("what do you know about me")
    assert decision.intent == "memory"

    decision2 = _fallback_route("show my profile")
    assert decision2.intent == "memory"
