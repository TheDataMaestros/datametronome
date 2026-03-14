import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.staves.repo import StaveRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    executor.delete = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    return executor


class TestStaveRepo:
    @pytest.mark.asyncio
    async def test_list_staves(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "1", "name": "pg", "description": None,
             "data_source_type": "postgres", "connection_config": "{}",
             "is_active": True, "created_at": "2025-01-01", "updated_at": "2025-01-01"}
        ]
        repo = StaveRepo(mock_executor)
        result = await repo.list(limit=10, offset=0)
        assert len(result) == 1
        assert result[0].name == "pg"

    @pytest.mark.asyncio
    async def test_get_stave(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "1", "name": "pg", "description": None,
             "data_source_type": "postgres", "connection_config": "{}",
             "is_active": True, "created_at": "2025-01-01", "updated_at": "2025-01-01"}
        ]
        repo = StaveRepo(mock_executor)
        result = await repo.get("1")
        assert result is not None
        assert result.id == "1"

    @pytest.mark.asyncio
    async def test_get_stave_not_found(self, mock_executor):
        repo = StaveRepo(mock_executor)
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_stave(self, mock_executor):
        from datametronome_podium.features.staves.model import Stave
        repo = StaveRepo(mock_executor)
        stave = Stave(
            id="1", name="pg", data_source_type="postgres",
            connection_config="{}", is_active=True,
            created_at="2025-01-01", updated_at="2025-01-01"
        )
        result = await repo.create(stave)
        assert result == 1

    @pytest.mark.asyncio
    async def test_delete_stave(self, mock_executor):
        repo = StaveRepo(mock_executor)
        result = await repo.delete("1")
        assert result == 1

    @pytest.mark.asyncio
    async def test_find_clef_ids_for_stave(self, mock_executor):
        mock_executor.query.return_value = [{"id": "c1"}, {"id": "c2"}]
        repo = StaveRepo(mock_executor)
        result = await repo.find_clef_ids("stave-1")
        assert result == ["c1", "c2"]
