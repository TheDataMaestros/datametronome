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
    assert plan.skipped == []
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


@pytest.mark.asyncio
async def test_create_plan(repo, mock_executor):
    plan = StaveQueryPlan(
        id="plan-1",
        stave_id="stave-1",
        schema_fingerprint="fp1",
        kpi_queries={"monthly_revenue": "SELECT 1 as value"},
        generated_by_model="claude-sonnet-4-6",
        generated_at="2026-03-16T00:00:00Z",
    )
    await repo.create_plan(plan)
    mock_executor.insert.assert_called_once()
    call_args = mock_executor.insert.call_args
    assert call_args[0][0] == "stave_query_plans"
    row = call_args[0][1]
    assert "kpi_queries" in row
    # kpi_queries must be JSON-serialized (a string), not a raw dict
    assert isinstance(row["kpi_queries"], str)
    import json
    assert json.loads(row["kpi_queries"]) == {"monthly_revenue": "SELECT 1 as value"}


@pytest.mark.asyncio
async def test_create_plan_serializes_skipped(repo, mock_executor):
    plan = StaveQueryPlan(
        id="plan-2",
        stave_id="stave-1",
        schema_fingerprint="fp1",
        kpi_queries={"rev": "SELECT 1"},
        skipped=[{"name": "churn_rate", "reason": "no column found"}],
        generated_at="2026-03-16T00:00:00Z",
    )
    await repo.create_plan(plan)
    call_args = mock_executor.insert.call_args
    row = call_args[0][1]
    assert isinstance(row["skipped"], str)
    assert json.loads(row["skipped"]) == [{"name": "churn_rate", "reason": "no column found"}]


@pytest.mark.asyncio
async def test_get_valid_plan_deserializes_skipped(repo, mock_executor):
    mock_executor.query.return_value = [{
        "id": "plan-1",
        "stave_id": "stave-1",
        "tenant_id": "default",
        "schema_fingerprint": "fp1",
        "kpi_queries": json.dumps({}),
        "performer_queries": json.dumps({}),
        "skipped": json.dumps([{"name": "churn_rate", "reason": "missing"}]),
        "generated_by_model": "claude-sonnet-4-6",
        "generated_at": "2026-03-16T00:00:00Z",
        "invalidated_at": None,
    }]
    result = await repo.get_valid_plan("stave-1")
    assert result is not None
    assert result.skipped == [{"name": "churn_rate", "reason": "missing"}]


@pytest.mark.asyncio
async def test_get_valid_plan_returns_none_when_empty(repo, mock_executor):
    mock_executor.query.return_value = []
    result = await repo.get_valid_plan("stave-1")
    assert result is None
    mock_executor.query.assert_called_once()
    sql = mock_executor.query.call_args[0][0]
    assert "invalidated_at IS NULL" in sql


@pytest.mark.asyncio
async def test_get_valid_plan_deserializes_correctly(repo, mock_executor):
    mock_executor.query.return_value = [{
        "id": "plan-1",
        "stave_id": "stave-1",
        "tenant_id": "default",
        "schema_fingerprint": "fp1",
        "kpi_queries": json.dumps({"monthly_revenue": "SELECT 1 as value"}),
        "performer_queries": json.dumps({}),
        "generated_by_model": "claude-sonnet-4-6",
        "generated_at": "2026-03-16T00:00:00Z",
        "invalidated_at": None,
    }]
    result = await repo.get_valid_plan("stave-1")
    assert result is not None
    assert result.schema_fingerprint == "fp1"
    assert result.kpi_queries == {"monthly_revenue": "SELECT 1 as value"}


@pytest.mark.asyncio
async def test_invalidate_plan(repo, mock_executor):
    await repo.invalidate_plan("stave-1", "2026-03-16T01:00:00Z")
    mock_executor.execute.assert_called_once()
    sql = mock_executor.execute.call_args[0][0]
    assert "invalidated_at" in sql
    assert "stave_query_plans" in sql


@pytest.mark.asyncio
async def test_prune_old_plans(repo, mock_executor):
    await repo.prune_old_plans("2025-12-16T00:00:00Z")
    mock_executor.execute.assert_called_once()
    sql = mock_executor.execute.call_args[0][0]
    assert "stave_query_plans" in sql
    assert "invalidated_at" in sql
