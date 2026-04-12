"""Tests for intelligence data in dashboard metrics."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datametronome_podium.features.metrics.router import get_dashboard_metrics


def _make_mock_executor(query_fn):
    """Create a mock QueryExecutor with the given query function."""
    mock = MagicMock()
    mock.query = query_fn
    return mock


@pytest.mark.asyncio
async def test_dashboard_includes_intelligence_key():
    """Dashboard metrics should include an 'intelligence' section."""
    async def _mock_query(sql, params=None):
        if "GROUP BY" in sql:
            return []
        return [{"count": 0, "total": 0, "passed": 0, "failed": 0, "critical": 0, "avg_health": None, "report_count": 0}]

    executor = _make_mock_executor(_mock_query)

    with patch("datametronome_podium.features.metrics.router.get_executor", return_value=executor):
        result = await get_dashboard_metrics()

    assert "intelligence" in result


@pytest.mark.asyncio
async def test_dashboard_intelligence_with_data():
    """Intelligence section should reflect actual database values."""
    async def mock_query(sql, params=None):
        # Intelligence queries
        if "insight_reports" in sql:
            return [{"avg_health": 82.5, "report_count": 10}]
        if "data_profiles" in sql:
            return [{"count": 3}]
        if "insight_suggestions" in sql:
            return [{"count": 7}]

        # Default for existing dashboard queries
        return [{"count": 0, "total": 0, "passed": 0, "failed": 0, "critical": 0, "status": "passed"}]

    executor = _make_mock_executor(mock_query)

    with patch("datametronome_podium.features.metrics.router.get_executor", return_value=executor):
        result = await get_dashboard_metrics()

    intel = result.get("intelligence", {})
    assert intel.get("avg_health_score") == 82.5
    assert intel.get("profiled_sources") == 3
    assert intel.get("pending_suggestions") == 7


@pytest.mark.asyncio
async def test_dashboard_intelligence_graceful_on_missing_tables():
    """If intelligence tables do not exist, dashboard should still work."""
    async def mock_query(sql, params=None):
        # Intelligence tables don't exist
        if any(t in sql for t in ("insight_reports", "data_profiles", "insight_suggestions")):
            raise Exception("no such table: insight_reports")

        # Existing dashboard queries work fine
        return [{"count": 0, "total": 0, "passed": 0, "failed": 0, "critical": 0, "status": "passed"}]

    executor = _make_mock_executor(mock_query)

    with patch("datametronome_podium.features.metrics.router.get_executor", return_value=executor):
        result = await get_dashboard_metrics()

    # Should still return successfully with empty intelligence
    assert "intelligence" in result
    assert result["intelligence"] == {}
