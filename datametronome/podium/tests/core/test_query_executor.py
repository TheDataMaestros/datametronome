import pytest
from unittest.mock import AsyncMock, MagicMock
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.query_adapter import QueryAdapter


@pytest.fixture
def mock_connector():
    conn = AsyncMock()
    conn.query_with_params = AsyncMock(return_value=[{"id": "1", "name": "test"}])
    conn.execute = AsyncMock(return_value=1)
    conn.begin_transaction = AsyncMock()
    conn.commit_transaction = AsyncMock()
    conn.rollback_transaction = AsyncMock()
    return conn


@pytest.fixture
def sqlite_executor(mock_connector):
    adapter = QueryAdapter("sqlite")
    return QueryExecutor(mock_connector, adapter)


@pytest.fixture
def pg_executor(mock_connector):
    adapter = QueryAdapter("postgresql")
    return QueryExecutor(mock_connector, adapter)


class TestQuery:
    @pytest.mark.asyncio
    async def test_query_returns_rows(self, sqlite_executor, mock_connector):
        result = await sqlite_executor.query("SELECT * FROM staves WHERE id = ?", ["abc"])
        assert result == [{"id": "1", "name": "test"}]
        mock_connector.query_with_params.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_adapts_placeholders_for_pg(self, pg_executor, mock_connector):
        await pg_executor.query("SELECT * FROM staves WHERE id = ?", ["abc"])
        call_args = mock_connector.query_with_params.call_args
        assert "$1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_query_no_params(self, sqlite_executor, mock_connector):
        await sqlite_executor.query("SELECT * FROM staves")
        call_args = mock_connector.query_with_params.call_args
        assert call_args[0][1] == []


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_rows_affected(self, sqlite_executor, mock_connector):
        result = await sqlite_executor.execute("INSERT INTO staves VALUES (?)", ["abc"])
        assert result == 1

    @pytest.mark.asyncio
    async def test_execute_adapts_placeholders_for_pg(self, pg_executor, mock_connector):
        await pg_executor.execute("DELETE FROM staves WHERE id = ?", ["abc"])
        call_args = mock_connector.execute.call_args
        assert "$1" in call_args[0][0]


class TestExecuteDDL:
    @pytest.mark.asyncio
    async def test_ddl_adapts_types_for_sqlite(self, sqlite_executor, mock_connector):
        await sqlite_executor.execute_ddl("CREATE TABLE t (data JSONB, val DOUBLE PRECISION)")
        call_args = mock_connector.execute.call_args
        sql = call_args[0][0]
        assert "TEXT" in sql
        assert "REAL" in sql
        assert "JSONB" not in sql


class TestCRUDHelpers:
    @pytest.mark.asyncio
    async def test_select_basic(self, sqlite_executor, mock_connector):
        await sqlite_executor.select("staves")
        call_args = mock_connector.query_with_params.call_args
        assert 'SELECT * FROM "staves"' in call_args[0][0]

    @pytest.mark.asyncio
    async def test_select_with_where(self, sqlite_executor, mock_connector):
        await sqlite_executor.select("staves", where={"id": "abc"})
        call_args = mock_connector.query_with_params.call_args
        assert "WHERE" in call_args[0][0]
        assert "abc" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_select_with_order_limit_offset(self, sqlite_executor, mock_connector):
        await sqlite_executor.select("staves", order_by="created_at DESC", limit=10, offset=5)
        call_args = mock_connector.query_with_params.call_args
        sql = call_args[0][0]
        assert "ORDER BY created_at DESC" in sql
        assert "LIMIT" in sql
        assert "OFFSET" in sql

    @pytest.mark.asyncio
    async def test_insert(self, sqlite_executor, mock_connector):
        result = await sqlite_executor.insert("staves", {"id": "1", "name": "test"})
        assert result == 1
        call_args = mock_connector.execute.call_args
        sql = call_args[0][0]
        assert 'INSERT INTO "staves"' in sql

    @pytest.mark.asyncio
    async def test_update(self, sqlite_executor, mock_connector):
        await sqlite_executor.update("staves", {"name": "new"}, where={"id": "1"})
        call_args = mock_connector.execute.call_args
        sql = call_args[0][0]
        assert 'UPDATE "staves" SET' in sql
        assert "WHERE" in sql

    @pytest.mark.asyncio
    async def test_delete(self, sqlite_executor, mock_connector):
        await sqlite_executor.delete("staves", where={"id": "1"})
        call_args = mock_connector.execute.call_args
        sql = call_args[0][0]
        assert 'DELETE FROM "staves"' in sql
        assert "WHERE" in sql

    @pytest.mark.asyncio
    async def test_delete_without_where_raises(self, sqlite_executor):
        with pytest.raises(ValueError, match="requires a where clause"):
            await sqlite_executor.delete("staves")


class TestTransaction:
    @pytest.mark.asyncio
    async def test_transaction_commits_on_success(self, sqlite_executor, mock_connector):
        async with sqlite_executor.transaction():
            await sqlite_executor.execute("INSERT INTO t VALUES (?)", ["x"])
        mock_connector.begin_transaction.assert_called_once()
        mock_connector.commit_transaction.assert_called_once()
        mock_connector.rollback_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_transaction_rollbacks_on_error(self, sqlite_executor, mock_connector):
        with pytest.raises(ValueError):
            async with sqlite_executor.transaction():
                raise ValueError("boom")
        mock_connector.begin_transaction.assert_called_once()
        mock_connector.rollback_transaction.assert_called_once()
        mock_connector.commit_transaction.assert_not_called()
