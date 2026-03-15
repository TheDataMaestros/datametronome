import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.analytics.repo import AnalyticsRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.select = AsyncMock(return_value=[])
    return executor


class TestAnalyticsRepo:
    @pytest.mark.asyncio
    async def test_get_check_summary(self, mock_executor):
        mock_executor.query.return_value = [
            {"total": 100, "passed": 90, "failed": 8, "warning": 2}
        ]
        repo = AnalyticsRepo(mock_executor)
        result = await repo.get_check_summary()
        assert result["total"] == 100
        assert result["passed"] == 90

    @pytest.mark.asyncio
    async def test_get_check_summary_empty(self, mock_executor):
        repo = AnalyticsRepo(mock_executor)
        result = await repo.get_check_summary()
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_active_sources_count(self, mock_executor):
        mock_executor.query.return_value = [{"count": 5}]
        repo = AnalyticsRepo(mock_executor)
        result = await repo.get_active_sources_count()
        assert result == 5

    @pytest.mark.asyncio
    async def test_get_anomaly_count(self, mock_executor):
        mock_executor.query.return_value = [{"count": 3}]
        repo = AnalyticsRepo(mock_executor)
        result = await repo.get_anomaly_count(hours=24)
        assert result == 3

    @pytest.mark.asyncio
    async def test_get_recent_checks(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "ch1", "check_type": "row_count", "status": "pass",
             "timestamp": "2025-01-01T00:00:00Z", "stave_name": "pg",
             "clef_name": "Row Count"}
        ]
        repo = AnalyticsRepo(mock_executor)
        result = await repo.get_recent_checks(limit=10)
        assert len(result) == 1
        assert result[0]["stave_name"] == "pg"
