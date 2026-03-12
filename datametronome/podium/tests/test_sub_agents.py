"""Tests: sub-agents can be built and respond with TestModel."""
import pytest
from pydantic_ai.models.test import TestModel


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
