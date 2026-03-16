"""Tests for StaveQueryPlan model + schema_interpretation on DataProfile."""
import json

import pytest
from unittest.mock import AsyncMock

from datametronome_podium.features.insights.model import StaveQueryPlan, DataProfile
from datametronome_podium.features.insights.repo import InsightsRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.select = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    executor.execute = AsyncMock(return_value=1)
    return executor


@pytest.fixture
def repo(mock_executor):
    return InsightsRepo(mock_executor)


def test_stave_query_plan_model_defaults():
    plan = StaveQueryPlan(
        id="plan-1",
        stave_id="stave-1",
        schema_fingerprint="abc123",
        generated_at="2026-03-16T00:00:00Z",
    )
    assert plan.kpi_queries == {}
    assert plan.performer_queries == {}
    assert plan.invalidated_at is None
    assert plan.tenant_id == "default"
    assert isinstance(plan.generated_at, str)


def test_data_profile_has_schema_interpretation_field():
    profile = DataProfile(
        id="dp-1", stave_id="s-1", tenant_id="default",
        domain_type="e-commerce", domain_confidence=0.9,
        created_at="2026-03-16T00:00:00Z", updated_at="2026-03-16T00:00:00Z",
    )
    assert profile.schema_interpretation == {}


@pytest.mark.asyncio
async def test_get_profile_deserializes_schema_interpretation(repo, mock_executor):
    """schema_interpretation must be deserialized from JSON string -> dict by get_profile."""
    mock_executor.select.return_value = [{
        "id": "dp-1", "stave_id": "stave-1", "tenant_id": "default",
        "domain_type": "e-commerce", "domain_confidence": 0.9,
        "domain_context": "{}", "schema_map": "{}", "entity_roles": "{}",
        "learned_patterns": "{}", "profile_version": 1,
        "previous_classification": None,
        "schema_interpretation": json.dumps({"orders": "fact_table"}),
        "created_at": "2026-03-16T00:00:00Z", "updated_at": "2026-03-16T00:00:00Z",
    }]
    result = await repo.get_profile("stave-1")
    assert result is not None
    assert result.schema_interpretation == {"orders": "fact_table"}
