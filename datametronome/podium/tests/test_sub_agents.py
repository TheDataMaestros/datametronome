"""Tests: sub-agents can be built and respond with TestModel.

Uses a mock QueryExecutor so agent_tools never calls the real DB.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai.models.test import TestModel

# TestModel agent runs can exceed the default 10s CLI timeout (tool orchestration).
pytestmark = pytest.mark.timeout(30)


@pytest.fixture(autouse=True)
def mock_executor_for_agent_tools():
    """Patch get_executor everywhere agent_tools resolves it.

    Module-level `from core.database import get_executor` keeps a stale reference
    unless we patch `agent_tools.get_executor`. Functions that import get_executor
    inside the body need `core.database.get_executor` patched.
    """
    mock_executor = MagicMock()
    mock_executor.query = AsyncMock(return_value=[])
    mock_executor.insert = AsyncMock()
    mock_executor.execute = AsyncMock(return_value=0)

    with (
        patch(
            "datametronome_podium.core.database.get_executor",
            return_value=mock_executor,
        ),
        patch(
            "datametronome_podium.services.agent_tools.get_executor",
            return_value=mock_executor,
        ),
    ):
        yield mock_executor


@pytest.mark.asyncio
async def test_config_agent_runs():
    from datametronome_podium.services.agents.config import build_config_agent

    agent = build_config_agent(TestModel())
    result = await agent.run("How do I create a new data source?")
    assert isinstance(result.output, str)
    assert len(result.output) > 0


@pytest.mark.asyncio
async def test_investigation_agent_runs():
    from datametronome_podium.services.agents.investigation import (
        build_investigation_agent,
    )

    agent = build_investigation_agent(TestModel())
    result = await agent.run("Why did the row count check fail yesterday?")
    assert isinstance(result.output, str)


@pytest.mark.asyncio
async def test_report_agent_runs():
    from datametronome_podium.services.agents.report import build_report_agent

    agent = build_report_agent(TestModel())
    result = await agent.run("Give me a summary of the system status.")
    assert isinstance(result.output, str)
