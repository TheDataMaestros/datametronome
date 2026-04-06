"""Tests for Phase 3 BI agent tools."""
import json
import pytest
from unittest.mock import AsyncMock

from datametronome_podium.services.agents.business_intelligence import Phase3Deps, build_phase3_agent


@pytest.fixture
def phase3_deps():
    connector = AsyncMock()
    connector.query = AsyncMock(return_value=[{"value": 42000.0}])
    return Phase3Deps(
        connector=connector,
        schema_prefix='"public".',
        kpi_queries={"monthly_revenue": "SELECT 42000 as value"},
        performer_queries={
            "product": {
                "rank_query": "SELECT 'Widget' as name, 1000 as value, '$' as unit",
                "drill_query": "SELECT '2026-03-01' as period, 1000 as revenue",
            }
        },
        skipped=[],
    )


def test_phase3_deps_fields(phase3_deps):
    assert "monthly_revenue" in phase3_deps.kpi_queries
    assert "product" in phase3_deps.performer_queries
    assert phase3_deps.skipped == []


def test_build_phase3_agent_returns_agent():
    from pydantic_ai.models.test import TestModel
    agent = build_phase3_agent(TestModel())
    assert agent is not None
