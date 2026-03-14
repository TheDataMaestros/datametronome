"""Tests for the new orchestrator — dispatch logic, chain, parallel."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_mock_result(text: str):
    """Create a mock agent run result."""
    result = MagicMock()
    result.output = text  # pydantic-ai 1.67.0 uses .output
    return result


@pytest.mark.asyncio
async def test_convert_history_user_message():
    from datametronome_podium.services.orchestrator import convert_history_to_messages
    from pydantic_ai.messages import ModelRequest

    history = [{"role": "user", "content": "hello"}]
    messages = convert_history_to_messages(history)
    assert len(messages) == 1
    assert isinstance(messages[0], ModelRequest)


@pytest.mark.asyncio
async def test_convert_history_assistant_message():
    from datametronome_podium.services.orchestrator import convert_history_to_messages
    from pydantic_ai.messages import ModelResponse

    history = [{"role": "assistant", "content": "Hi there!"}]
    messages = convert_history_to_messages(history)
    assert len(messages) == 1
    assert isinstance(messages[0], ModelResponse)


@pytest.mark.asyncio
async def test_convert_history_skips_unknown_roles():
    from datametronome_podium.services.orchestrator import convert_history_to_messages

    history = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "hello"},
    ]
    messages = convert_history_to_messages(history)
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_run_chat_single_mode():
    """Single mode: router returns single agent, result is that agent's text."""
    from datametronome_podium.services.agents.router import RoutingDecision

    mock_routing = RoutingDecision(
        intent="report", mode="single", agents=["report"],
        reasoning="Simple report request."
    )

    with patch(
        "datametronome_podium.services.orchestrator._get_router_agent"
    ) as mock_router_factory, patch(
        "datametronome_podium.services.orchestrator._get_report_agent"
    ) as mock_report_factory:
        mock_router = AsyncMock()
        mock_router.run.return_value = MagicMock(output=mock_routing)
        mock_router_factory.return_value = mock_router

        mock_report = AsyncMock()
        mock_report.run.return_value = make_mock_result("System status: all green.")
        mock_report_factory.return_value = mock_report

        from datametronome_podium.services import orchestrator
        result = await orchestrator.run_chat("What is the status?", history=[])
        assert result["message"] == "System status: all green."
        assert result["intent"] == "report"
        assert result["mode"] == "single"


@pytest.mark.asyncio
async def test_run_chat_chain_mode():
    """Chain mode: investigation result is injected into config agent's prompt."""
    from datametronome_podium.services.agents.router import RoutingDecision

    mock_routing = RoutingDecision(
        intent="investigation", mode="chain",
        agents=["investigation", "config"],
        reasoning="User wants to diagnose and fix."
    )

    with patch(
        "datametronome_podium.services.orchestrator.settings"
    ) as mock_settings, patch(
        "datametronome_podium.services.orchestrator._get_router_agent"
    ) as mock_router_factory, patch(
        "datametronome_podium.services.orchestrator._get_investigation_agent"
    ) as mock_inv_factory, patch(
        "datametronome_podium.services.orchestrator._get_config_agent"
    ) as mock_cfg_factory:
        mock_settings.ai_provider = "anthropic"  # Force LLM routing path

        mock_router = AsyncMock()
        mock_router.run.return_value = MagicMock(output=mock_routing)
        mock_router_factory.return_value = mock_router

        mock_inv = AsyncMock()
        mock_inv.run.return_value = make_mock_result("Found 3 failed checks.")
        mock_inv_factory.return_value = mock_inv

        mock_cfg = AsyncMock()
        mock_cfg.run.return_value = make_mock_result("Recommendation: add freshness check.")
        mock_cfg_factory.return_value = mock_cfg

        from datametronome_podium.services import orchestrator
        result = await orchestrator.run_chat(
            "Why did checks fail and how to fix?", history=[]
        )
        assert result["message"] == "Recommendation: add freshness check."
        assert result["mode"] == "chain"
        # Second agent call should have included previous output in the prompt
        second_call_msg = mock_cfg.run.call_args[0][0]
        assert "Found 3 failed checks." in second_call_msg


@pytest.mark.asyncio
async def test_run_chat_parallel_mode():
    """Parallel mode: both agents run, results are combined."""
    from datametronome_podium.services.agents.router import RoutingDecision

    mock_routing = RoutingDecision(
        intent="report", mode="parallel",
        agents=["report", "config"],
        reasoning="User wants overview and suggestions."
    )

    with patch(
        "datametronome_podium.services.orchestrator.settings"
    ) as mock_settings, patch(
        "datametronome_podium.services.orchestrator._get_router_agent"
    ) as mock_router_factory, patch(
        "datametronome_podium.services.orchestrator._get_report_agent"
    ) as mock_report_factory, patch(
        "datametronome_podium.services.orchestrator._get_config_agent"
    ) as mock_cfg_factory:
        mock_settings.ai_provider = "anthropic"  # Force LLM routing path

        mock_router = AsyncMock()
        mock_router.run.return_value = MagicMock(output=mock_routing)
        mock_router_factory.return_value = mock_router

        mock_report = AsyncMock()
        mock_report.run.return_value = make_mock_result("System: 5 staves, 12 checks.")
        mock_report_factory.return_value = mock_report

        mock_cfg = AsyncMock()
        mock_cfg.run.return_value = make_mock_result("Suggestion: add 2 more checks.")
        mock_cfg_factory.return_value = mock_cfg

        from datametronome_podium.services import orchestrator
        result = await orchestrator.run_chat("Give overview and suggestions", history=[])
        assert "System: 5 staves" in result["message"]
        assert "Suggestion: add 2 more checks." in result["message"]
        assert result["mode"] == "parallel"


@pytest.mark.asyncio
async def test_run_chat_creates_checkpoint():
    """run_chat should create a checkpoint and log events when conversation_id provided."""
    from datametronome_podium.services.agents.router import RoutingDecision
    from datametronome_podium.services import orchestrator

    mock_routing = RoutingDecision(
        intent="quick", mode="single", agents=["report"],
        reasoning="test"
    )

    mock_create = AsyncMock(return_value="cp-123")
    mock_update = AsyncMock()
    mock_log = AsyncMock()
    mock_find = AsyncMock(return_value=None)

    with patch.object(orchestrator, "create_checkpoint", mock_create), \
         patch.object(orchestrator, "update_checkpoint", mock_update), \
         patch.object(orchestrator, "log_event", mock_log), \
         patch.object(orchestrator, "find_active_checkpoint", mock_find), \
         patch.object(orchestrator, "_get_router_agent") as mock_router_factory, \
         patch.object(orchestrator, "_get_report_agent") as mock_report_factory:

        mock_router = AsyncMock()
        mock_router.run.return_value = MagicMock(output=mock_routing)
        mock_router_factory.return_value = mock_router

        mock_report = AsyncMock()
        mock_report.run.return_value = make_mock_result("Test response")
        mock_report_factory.return_value = mock_report

        result = await orchestrator.run_chat(
            message="Hello",
            history=[],
            conversation_id="conv-1",
            user_id="user-1",
        )

    assert result["message"] == "Test response"
    mock_create.assert_called_once()
    # Should log at least decision_made, node_entered, node_completed
    assert mock_log.call_count >= 3
    # Should update checkpoint to completed
    completed_calls = [
        c for c in mock_update.call_args_list
        if c.kwargs.get("status") == "completed"
    ]
    assert len(completed_calls) == 1
