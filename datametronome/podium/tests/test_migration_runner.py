"""Tests for the migration runner."""
import pytest
from unittest.mock import AsyncMock, patch

from datametronome_podium.core.migrations.runner import run_migrations


@pytest.mark.asyncio
async def test_runner_creates_schema_migrations_table():
    """Runner should create schema_migrations table on first run."""
    mock_db = AsyncMock()
    mock_db.query = AsyncMock(return_value=[])
    mock_db.execute = AsyncMock()

    with patch(
        "datametronome_podium.core.migrations.runner._get_sql_files",
        return_value=[],
    ):
        await run_migrations(mock_db, "sqlite")

    create_calls = [
        c for c in mock_db.execute.call_args_list
        if "schema_migrations" in str(c)
    ]
    assert len(create_calls) >= 1


@pytest.mark.asyncio
async def test_runner_applies_new_migration():
    """Runner should apply SQL files not yet in schema_migrations."""
    mock_db = AsyncMock()
    mock_db.query = AsyncMock(return_value=[])
    mock_db.execute = AsyncMock()

    fake_sql = "CREATE TABLE IF NOT EXISTS test_table (id TEXT PRIMARY KEY);"

    with patch(
        "datametronome_podium.core.migrations.runner._get_sql_files",
        return_value=[("001_initial.sql", fake_sql)],
    ):
        await run_migrations(mock_db, "sqlite")

    execute_calls = [str(c) for c in mock_db.execute.call_args_list]
    assert any("test_table" in c for c in execute_calls)


@pytest.mark.asyncio
async def test_runner_skips_already_applied():
    """Runner should skip migrations already in schema_migrations."""
    mock_db = AsyncMock()
    mock_db.query = AsyncMock(return_value=[{"filename": "001_initial.sql"}])
    mock_db.execute = AsyncMock()

    fake_sql = "CREATE TABLE IF NOT EXISTS test_table (id TEXT PRIMARY KEY);"

    with patch(
        "datametronome_podium.core.migrations.runner._get_sql_files",
        return_value=[("001_initial.sql", fake_sql)],
    ):
        await run_migrations(mock_db, "sqlite")

    execute_calls = [str(c) for c in mock_db.execute.call_args_list]
    assert not any("test_table" in c for c in execute_calls)
