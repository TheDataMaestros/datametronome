"""Tests for database connector factory and normalization."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from datametronome_podium.core.database import (
    _parse_pg_url,
    _parse_sqlite_path,
    execute_query,
    execute_write,
    insert_data,
)


class TestParseURL:
    def test_parse_pg_url(self):
        result = _parse_pg_url("postgresql://user:pass@host:5432/mydb")
        assert result["host"] == "host"
        assert result["port"] == 5432
        assert result["database"] == "mydb"
        assert result["user"] == "user"
        assert result["password"] == "pass"

    def test_parse_pg_url_defaults(self):
        result = _parse_pg_url("postgresql:///mydb")
        assert result["host"] == "localhost"
        assert result["port"] == 5432

    def test_parse_sqlite_path(self):
        path = _parse_sqlite_path("sqlite:///./data/test.db")
        assert path.endswith("data/test.db")


@pytest.mark.asyncio
async def test_execute_query_delegates_to_executor():
    """execute_query should delegate to QueryExecutor.query()."""
    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(return_value=[{"id": 1}])

    with patch("datametronome_podium.core.database.get_executor", return_value=mock_executor):
        result = await execute_query("SELECT * FROM t WHERE id = ?", [1])
        assert result == [{"id": 1}]
        mock_executor.query.assert_called_once_with("SELECT * FROM t WHERE id = ?", [1])


@pytest.mark.asyncio
async def test_execute_write_delegates_to_executor():
    """execute_write should delegate to QueryExecutor.execute()."""
    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(return_value=1)

    with patch("datametronome_podium.core.database.get_executor", return_value=mock_executor):
        result = await execute_write("INSERT INTO t (id) VALUES (?)", [1])
        assert result is True
        mock_executor.execute.assert_called_once_with("INSERT INTO t (id) VALUES (?)", [1])


@pytest.mark.asyncio
async def test_insert_data_delegates_to_executor():
    """insert_data should delegate to QueryExecutor.insert()."""
    mock_executor = AsyncMock()
    mock_executor.insert = AsyncMock(return_value=1)

    with patch("datametronome_podium.core.database.get_executor", return_value=mock_executor):
        result = await insert_data("users", {"id": "1", "name": "test"})
        assert result is True
        mock_executor.insert.assert_called_once_with("users", {"id": "1", "name": "test"})
