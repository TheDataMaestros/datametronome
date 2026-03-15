"""Tests for intelligence data in dashboard metrics."""
import pytest
from unittest.mock import AsyncMock, patch

from datametronome_podium.api.v1.endpoints.metrics import get_dashboard_metrics


@pytest.mark.asyncio
async def test_dashboard_includes_intelligence_key():
    """Dashboard metrics should include an 'intelligence' section."""
    mock_db = AsyncMock()
    # Return empty list for GROUP BY queries, sensible defaults for COUNT queries
    async def _mock_query(params):
        sql = params.get("sql", "")
        if "GROUP BY" in sql:
            return []
        return [{"count": 0, "total": 0, "passed": 0, "failed": 0, "critical": 0, "avg_health": None, "report_count": 0}]

    mock_db.query = AsyncMock(side_effect=_mock_query)

    with patch("datametronome_podium.api.v1.endpoints.metrics.get_db", return_value=mock_db):
        result = await get_dashboard_metrics()

    assert "intelligence" in result


@pytest.mark.asyncio
async def test_dashboard_intelligence_with_data():
    """Intelligence section should reflect actual database values."""
    call_count = 0

    async def mock_query(params):
        nonlocal call_count
        call_count += 1
        sql = params.get("sql", "")

        # Intelligence queries
        if "insight_reports" in sql:
            return [{"avg_health": 82.5, "report_count": 10}]
        if "data_profiles" in sql:
            return [{"count": 3}]
        if "insight_suggestions" in sql:
            return [{"count": 7}]

        # Default for existing dashboard queries
        return [{"count": 0, "total": 0, "passed": 0, "failed": 0, "critical": 0, "status": "passed"}]

    mock_db = AsyncMock()
    mock_db.query = AsyncMock(side_effect=mock_query)

    with patch("datametronome_podium.api.v1.endpoints.metrics.get_db", return_value=mock_db):
        result = await get_dashboard_metrics()

    intel = result.get("intelligence", {})
    assert intel.get("avg_health_score") == 82.5
    assert intel.get("profiled_sources") == 3
    assert intel.get("pending_suggestions") == 7


@pytest.mark.asyncio
async def test_dashboard_intelligence_graceful_on_missing_tables():
    """If intelligence tables do not exist, dashboard should still work."""
    call_count = 0

    async def mock_query(params):
        nonlocal call_count
        call_count += 1
        sql = params.get("sql", "")

        # Intelligence tables don't exist
        if any(t in sql for t in ("insight_reports", "data_profiles", "insight_suggestions")):
            raise Exception("no such table: insight_reports")

        # Existing dashboard queries work fine
        return [{"count": 0, "total": 0, "passed": 0, "failed": 0, "critical": 0, "status": "passed"}]

    mock_db = AsyncMock()
    mock_db.query = AsyncMock(side_effect=mock_query)

    with patch("datametronome_podium.api.v1.endpoints.metrics.get_db", return_value=mock_db):
        result = await get_dashboard_metrics()

    # Should still return successfully with empty intelligence
    assert "intelligence" in result
    assert result["intelligence"] == {}
