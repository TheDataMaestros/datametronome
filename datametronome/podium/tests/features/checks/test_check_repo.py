import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.checks.repo import CheckRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    executor.delete = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    return executor


class TestCheckRepo:
    @pytest.mark.asyncio
    async def test_list_checks(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "ch1", "stave_id": "s1", "clef_id": "c1",
             "check_type": "row_count", "status": "pass",
             "message": "OK", "details": None,
             "timestamp": "2025-01-01T00:00:00Z",
             "execution_time": 0.5, "anomalies_count": 0,
             "severity": "medium"}
        ]
        repo = CheckRepo(mock_executor)
        result = await repo.list(limit=10, offset=0)
        assert len(result) == 1
        assert result[0].status == "pass"

    @pytest.mark.asyncio
    async def test_get_check(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "ch1", "stave_id": "s1", "clef_id": "c1",
             "check_type": "row_count", "status": "pass",
             "message": None, "details": None,
             "timestamp": "2025-01-01T00:00:00Z",
             "execution_time": None, "anomalies_count": 0,
             "severity": "medium"}
        ]
        repo = CheckRepo(mock_executor)
        result = await repo.get("ch1")
        assert result is not None
        assert result.id == "ch1"

    @pytest.mark.asyncio
    async def test_get_check_not_found(self, mock_executor):
        repo = CheckRepo(mock_executor)
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_check(self, mock_executor):
        from datametronome_podium.features.checks.model import Check
        repo = CheckRepo(mock_executor)
        check = Check(
            id="ch1", stave_id="s1", clef_id="c1",
            check_type="row_count", status="pass",
            timestamp="2025-01-01T00:00:00Z",
            anomalies_count=0, severity="medium"
        )
        result = await repo.create(check)
        assert result == 1

    @pytest.mark.asyncio
    async def test_list_by_clef(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "ch1", "stave_id": "s1", "clef_id": "c1",
             "check_type": "row_count", "status": "pass",
             "message": None, "details": None,
             "timestamp": "2025-01-01T00:00:00Z",
             "execution_time": None, "anomalies_count": 0,
             "severity": "medium"}
        ]
        repo = CheckRepo(mock_executor)
        result = await repo.list_by_clef("c1", limit=10, offset=0)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_by_stave(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "ch1", "stave_id": "s1", "clef_id": "c1",
             "check_type": "row_count", "status": "fail",
             "message": None, "details": None,
             "timestamp": "2025-01-01T00:00:00Z",
             "execution_time": None, "anomalies_count": 1,
             "severity": "high"}
        ]
        repo = CheckRepo(mock_executor)
        result = await repo.list_by_stave("s1", limit=10, offset=0)
        assert len(result) == 1
        assert result[0].severity == "high"

    @pytest.mark.asyncio
    async def test_delete_check(self, mock_executor):
        repo = CheckRepo(mock_executor)
        result = await repo.delete("ch1")
        assert result == 1
