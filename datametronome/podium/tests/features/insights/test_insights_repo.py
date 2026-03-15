"""Tests for InsightsRepo data access."""
import json
import pytest
from unittest.mock import AsyncMock

from datametronome_podium.features.insights.model import (
    DataProfile,
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
)
from datametronome_podium.features.insights.repo import InsightsRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.select = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    executor.delete = AsyncMock(return_value=1)
    return executor


@pytest.fixture
def repo(mock_executor):
    return InsightsRepo(mock_executor)


@pytest.mark.asyncio
async def test_create_profile(repo, mock_executor):
    profile = DataProfile(
        id="dp-1", stave_id="stave-test", tenant_id="default",
        domain_type="e-commerce", domain_confidence=0.85,
        created_at="2026-03-15T00:00:00Z", updated_at="2026-03-15T00:00:00Z",
    )
    await repo.create_profile(profile)
    mock_executor.insert.assert_called_once()
    call_args = mock_executor.insert.call_args
    assert call_args[0][0] == "data_profiles"


@pytest.mark.asyncio
async def test_get_profile(repo, mock_executor):
    mock_executor.select.return_value = [{
        "id": "dp-1", "stave_id": "stave-test", "tenant_id": "default",
        "domain_type": "e-commerce", "domain_confidence": 0.85,
        "domain_context": '{}', "schema_map": '{}', "entity_roles": '{}',
        "learned_patterns": '{}', "profile_version": 1,
        "previous_classification": None,
        "created_at": "2026-03-15T00:00:00Z", "updated_at": "2026-03-15T00:00:00Z",
    }]
    result = await repo.get_profile("stave-test")
    assert result is not None
    assert result.domain_type == "e-commerce"
    assert result.profile_version == 1


@pytest.mark.asyncio
async def test_get_profile_not_found(repo, mock_executor):
    mock_executor.select.return_value = []
    result = await repo.get_profile("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_update_profile(repo, mock_executor):
    await repo.update_profile("stave-test", {"domain_type": "saas", "domain_confidence": 0.8})
    mock_executor.update.assert_called_once()


@pytest.mark.asyncio
async def test_create_snapshot(repo, mock_executor):
    snap = BaselineSnapshot(
        id="snap-1", stave_id="stave-test", tenant_id="default",
        snapshot_type="daily",
        table_metrics={"orders": {"row_count": 5000, "null_rates": {}}},
        column_stats={}, captured_at="2026-03-15T06:00:00Z",
    )
    await repo.create_snapshot(snap)
    mock_executor.insert.assert_called_once()


@pytest.mark.asyncio
async def test_list_snapshots(repo, mock_executor):
    mock_executor.query.return_value = [{
        "id": "snap-1", "stave_id": "stave-test", "tenant_id": "default",
        "snapshot_type": "daily",
        "table_metrics": '{"orders": {"row_count": 5000}}',
        "column_stats": '{}', "captured_at": "2026-03-15T06:00:00Z",
    }]
    results = await repo.list_snapshots("stave-test", days=7)
    assert len(results) == 1
    assert results[0].id == "snap-1"


@pytest.mark.asyncio
async def test_create_report(repo, mock_executor):
    report = InsightReport(
        id="rpt-1", stave_id="stave-test", tenant_id="default",
        report_type="daily", health_score=78,
        summary="Looking good.", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_report(report)
    mock_executor.insert.assert_called_once()


@pytest.mark.asyncio
async def test_get_latest_report(repo, mock_executor):
    mock_executor.query.return_value = [{
        "id": "rpt-1", "stave_id": "stave-test", "tenant_id": "default",
        "snapshot_id": None, "report_type": "daily", "health_score": 78,
        "dimensions": '[]', "anomalies": '[]', "suggestions": '[]',
        "summary": "Looking good.", "key_findings": '[]',
        "created_at": "2026-03-15T06:00:00Z",
    }]
    result = await repo.get_latest_report("stave-test")
    assert result is not None
    assert result.health_score == 78


@pytest.mark.asyncio
async def test_create_suggestion(repo, mock_executor):
    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-test", tenant_id="default",
        report_id="rpt-1", priority="high", category="operations",
        action="Fix payment gateway", reasoning="Failure rate doubled",
        based_on="7-day trend", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_suggestion(sug)
    mock_executor.insert.assert_called_once()


@pytest.mark.asyncio
async def test_list_suggestions_with_status(repo, mock_executor):
    mock_executor.query.return_value = [{
        "id": "sug-1", "stave_id": "stave-test", "tenant_id": "default",
        "report_id": "rpt-1", "priority": "high", "category": "ops",
        "action": "Fix it", "reasoning": "Broken", "based_on": "data",
        "status": "pending", "resolved_at": None,
        "created_at": "2026-03-15T06:00:00Z",
    }]
    results = await repo.list_suggestions("stave-test", status="pending")
    assert len(results) == 1
    assert results[0].status == "pending"


@pytest.mark.asyncio
async def test_update_suggestion_status(repo, mock_executor):
    await repo.update_suggestion_status("sug-1", "accepted")
    mock_executor.update.assert_called_once()


@pytest.mark.asyncio
async def test_create_check_link(repo, mock_executor):
    link = InsightCreatedCheck(
        id="icc-1", report_id="rpt-1", clef_id="clef-1",
        rationale="Monitor freshness", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_check_link(link)
    mock_executor.insert.assert_called_once()
