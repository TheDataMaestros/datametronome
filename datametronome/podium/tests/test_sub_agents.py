"""Tests: sub-agents can be built and respond with TestModel.

Uses a mock database to prevent real DB connections and asyncpg concurrency issues.
"""
import pytest
from unittest.mock import AsyncMock, patch
from pydantic_ai.models.test import TestModel


@pytest.fixture(autouse=True)
def mock_db():
    """Mock get_db so agent tools don't hit a real database."""
    mock_connector = AsyncMock()
    mock_connector.query.return_value = []
    mock_connector.query_with_params.return_value = []
    mock_connector.execute.return_value = 0

    with patch(
        "datametronome_podium.services.agent_tools.get_db",
        new_callable=AsyncMock,
        return_value=mock_connector,
    ):
        yield mock_connector


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
