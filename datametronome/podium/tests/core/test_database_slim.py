import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestGetExecutor:
    @pytest.mark.asyncio
    async def test_get_executor_returns_query_executor(self):
        from datametronome_podium.core.database import get_executor, init_db

        with patch("datametronome_podium.core.database._create_connector") as mock_create:
            mock_conn = AsyncMock()
            mock_create.return_value = (mock_conn, "sqlite")

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


class TestDeprecatedFunctionsRemoved:
    """Verify that deprecated backward-compat functions were removed from database.py."""

    def test_execute_query_removed(self):
        import datametronome_podium.core.database as db_module
        assert not hasattr(db_module, "execute_query"), "execute_query should be removed"

    def test_execute_write_removed(self):
        import datametronome_podium.core.database as db_module
        assert not hasattr(db_module, "execute_write"), "execute_write should be removed"

    def test_insert_data_removed(self):
        import datametronome_podium.core.database as db_module
        assert not hasattr(db_module, "insert_data"), "insert_data should be removed"
