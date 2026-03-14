"""Tests for worker DB session factory."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_create_worker_db_returns_connector_and_executor():
    from datametronome_podium.core.worker_db import create_worker_db

    mock_connector = AsyncMock()
    mock_connector.connect = AsyncMock()

    with patch("datametronome_podium.core.worker_db._create_connector", return_value=(mock_connector, "postgresql")):
        connector, executor = await create_worker_db("postgresql://test:test@localhost/db")

    assert connector is mock_connector
    assert executor is not None
    mock_connector.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_worker_db():
    from datametronome_podium.core.worker_db import create_worker_db, close_worker_db

    mock_connector = AsyncMock()
    mock_connector.connect = AsyncMock()
    mock_connector.close = AsyncMock()

    with patch("datametronome_podium.core.worker_db._create_connector", return_value=(mock_connector, "postgresql")):
        connector, executor = await create_worker_db("postgresql://test:test@localhost/db")
        await close_worker_db(connector)

    mock_connector.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_db_context_manager():
    from datametronome_podium.core.worker_db import worker_db_session

    mock_connector = AsyncMock()
    mock_connector.connect = AsyncMock()
    mock_connector.close = AsyncMock()

    with patch("datametronome_podium.core.worker_db._create_connector", return_value=(mock_connector, "postgresql")):
        async with worker_db_session("postgresql://test:test@localhost/db") as (connector, executor):
            assert connector is mock_connector
            assert executor is not None

    # close is called on exit
    mock_connector.close.assert_awaited_once()
