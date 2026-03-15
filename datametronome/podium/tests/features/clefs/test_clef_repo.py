import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.clefs.repo import ClefRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    executor.delete = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    return executor


class TestClefRepo:
    @pytest.mark.asyncio
    async def test_list_clefs(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "c1", "stave_id": "s1", "name": "Row Count", "description": None,
             "check_type": "row_count", "config": '{"table": "users"}',
             "warn": None, "fail": None, "retry_config": None,
             "schedule": "0 * * * *", "is_active": True,
             "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"}
        ]
        repo = ClefRepo(mock_executor)
        result = await repo.list(limit=10, offset=0)
        assert len(result) == 1
        assert result[0].name == "Row Count"

    @pytest.mark.asyncio
    async def test_get_clef(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "c1", "stave_id": "s1", "name": "Row Count", "description": None,
             "check_type": "row_count", "config": '{"table": "users"}',
             "warn": None, "fail": None, "retry_config": None,
             "schedule": None, "is_active": True,
             "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"}
        ]
        repo = ClefRepo(mock_executor)
        result = await repo.get("c1")
        assert result is not None
        assert result.check_type == "row_count"

    @pytest.mark.asyncio
    async def test_get_clef_not_found(self, mock_executor):
        repo = ClefRepo(mock_executor)
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_clef(self, mock_executor):
        from datametronome_podium.features.clefs.model import Clef
        repo = ClefRepo(mock_executor)
        clef = Clef(
            id="c1", stave_id="s1", name="Row Count",
            check_type="row_count", config='{"table": "users"}',
            is_active=True, created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z"
        )
        result = await repo.create(clef)
        assert result == 1

    @pytest.mark.asyncio
    async def test_update_clef(self, mock_executor):
        repo = ClefRepo(mock_executor)
        result = await repo.update("c1", {"name": "Updated"})
        assert result == 1

    @pytest.mark.asyncio
    async def test_delete_clef(self, mock_executor):
        repo = ClefRepo(mock_executor)
        result = await repo.delete("c1")
        assert result == 1

    @pytest.mark.asyncio
    async def test_list_by_stave(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "c1", "stave_id": "s1", "name": "Row Count", "description": None,
             "check_type": "row_count", "config": '{}',
             "warn": None, "fail": None, "retry_config": None,
             "schedule": None, "is_active": True,
             "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"}
        ]
        repo = ClefRepo(mock_executor)
        result = await repo.list_by_stave("s1")
        assert len(result) == 1
        mock_executor.select.assert_called_once_with("clefs", where={"stave_id": "s1"})
