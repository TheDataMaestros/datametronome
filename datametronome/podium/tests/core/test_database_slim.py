import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestGetExecutor:
    @pytest.mark.asyncio
    async def test_get_executor_returns_query_executor(self):
        from datametronome_podium.core.database import get_executor, init_db

        with patch("datametronome_podium.core.database._create_connector") as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = (mock_conn, "sqlite")

            with patch("datametronome_podium.core.seeding.create_default_admin", new_callable=AsyncMock):
                await init_db()

            from datametronome_podium.core.query import QueryExecutor
            executor = get_executor()
            assert isinstance(executor, QueryExecutor)


class TestGetExecutorNotInitialized:
    def test_get_executor_raises_before_init(self):
        from datametronome_podium.core import database
        # Save and clear state
        old_executor = database._executor
        database._executor = None
        try:
            with pytest.raises(RuntimeError, match="Database not initialized"):
                database.get_executor()
        finally:
            database._executor = old_executor


class TestBackwardCompat:
    @pytest.mark.asyncio
    async def test_execute_query_delegates_to_executor(self):
        from datametronome_podium.core.database import execute_query

        mock_executor = AsyncMock()
        mock_executor.query = AsyncMock(return_value=[{"id": "1"}])

        with patch("datametronome_podium.core.database.get_executor", return_value=mock_executor):
            result = await execute_query("SELECT * FROM t WHERE id = ?", ["1"])
            assert result == [{"id": "1"}]
            mock_executor.query.assert_called_once_with("SELECT * FROM t WHERE id = ?", ["1"])

    @pytest.mark.asyncio
    async def test_execute_write_delegates_to_executor(self):
        from datametronome_podium.core.database import execute_write

        mock_executor = AsyncMock()
        mock_executor.execute = AsyncMock(return_value=1)

        with patch("datametronome_podium.core.database.get_executor", return_value=mock_executor):
            result = await execute_write("INSERT INTO t VALUES (?)", ["x"])
            assert result is True

    @pytest.mark.asyncio
    async def test_insert_data_delegates_to_executor(self):
        from datametronome_podium.core.database import insert_data

        mock_executor = AsyncMock()
        mock_executor.insert = AsyncMock(return_value=1)

        with patch("datametronome_podium.core.database.get_executor", return_value=mock_executor):
            result = await insert_data("t", {"id": "1"})
            assert result is True
