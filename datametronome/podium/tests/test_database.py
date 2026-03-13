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
async def test_execute_query_sqlite():
    """execute_query should pass params as list for SQLite."""
    mock_conn = AsyncMock()
    mock_conn.query = AsyncMock(return_value=[{"id": 1}])

    with patch("datametronome_podium.core.database.get_db", return_value=mock_conn), \
         patch("datametronome_podium.core.database.dialect", "sqlite"), \
         patch("datametronome_podium.core.database._adapter", None):
        result = await execute_query("SELECT * FROM t WHERE id = ?", [1])
        assert result == [{"id": 1}]


@pytest.mark.asyncio
async def test_execute_write_postgresql():
    """execute_write should splat params for PostgreSQL."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    with patch("datametronome_podium.core.database.get_db", return_value=mock_conn), \
         patch("datametronome_podium.core.database.dialect", "postgresql"), \
         patch("datametronome_podium.core.database._adapter", None):
        result = await execute_write("INSERT INTO t (id) VALUES (?)", [1])
        assert result is True
        mock_conn.execute.assert_called_once()
        args = mock_conn.execute.call_args[0]
        assert args[0] == "INSERT INTO t (id) VALUES ($1)"
        assert args[1] == 1  # splatted, not [1]


@pytest.mark.asyncio
async def test_insert_data_postgresql():
    """insert_data for PostgreSQL should build raw INSERT, not use write()."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    with patch("datametronome_podium.core.database.get_db", return_value=mock_conn), \
         patch("datametronome_podium.core.database.dialect", "postgresql"), \
         patch("datametronome_podium.core.database._adapter", None):
        result = await insert_data("users", {"id": "1", "name": "test"})
        assert result is True
        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO users" in sql
        assert "$1" in sql
