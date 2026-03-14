"""Tests for execute_check Celery task."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datametronome_podium.services.clef_executor import CheckResult


def _mock_check_result():
    return CheckResult(
        clef_id="clef-1",
        stave_id="stave-1",
        status="pass",
        message="Row count OK",
        observed_value=1000,
        execution_time=0.5,
    )


def _mock_clef_row():
    return {
        "id": "clef-1", "stave_id": "stave-1", "name": "row-count",
        "check_type": "row_count", "config": '{"table": "users"}',
        "schedule": "0 * * * *", "retry_config": None, "is_active": True,
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        "warn": None, "fail": None, "description": None,
    }


def _mock_stave_row():
    return {
        "id": "stave-1", "name": "prod-db", "data_source_type": "postgres",
        "connection_config": '{"host": "localhost", "port": 5432}',
        "is_active": True, "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z", "description": None,
    }


def test_execute_check_importable():
    from datametronome_podium.tasks.check_tasks import execute_check
    assert callable(execute_check)


@pytest.mark.asyncio
async def test_execute_check_async_inner():
    """Test the async inner function that the Celery task wraps."""
    from datametronome_podium.tasks.check_tasks import _execute_check_async

    mock_connector = AsyncMock()
    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(side_effect=[
        [_mock_clef_row()],
        [_mock_stave_row()],
    ])
    mock_executor.insert = AsyncMock()

    with patch("datametronome_podium.tasks.check_tasks.ClefExecutor") as MockExec:
        MockExec.return_value.execute_clef = AsyncMock(return_value=_mock_check_result())
        result = await _execute_check_async("clef-1", mock_connector, mock_executor)

    assert result["status"] == "pass"
    assert result["clef_id"] == "clef-1"
    mock_executor.insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_check_async_clef_not_found():
    """Test error when clef doesn't exist."""
    from datametronome_podium.tasks.check_tasks import _execute_check_async

    mock_connector = AsyncMock()
    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(return_value=[])

    with pytest.raises(ValueError, match="Clef not found"):
        await _execute_check_async("nonexistent", mock_connector, mock_executor)


@pytest.mark.asyncio
async def test_execute_check_async_stave_not_found():
    """Test error when stave doesn't exist."""
    from datametronome_podium.tasks.check_tasks import _execute_check_async

    mock_connector = AsyncMock()
    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(side_effect=[
        [_mock_clef_row()],
        [],  # stave not found
    ])

    with pytest.raises(ValueError, match="Stave not found"):
        await _execute_check_async("clef-1", mock_connector, mock_executor)


@pytest.mark.asyncio
async def test_execute_check_async_records_success_in_circuit_breaker():
    from datametronome_podium.tasks.check_tasks import _execute_check_async

    mock_connector = AsyncMock()
    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(side_effect=[
        [_mock_clef_row()],
        [_mock_stave_row()],
    ])
    mock_executor.insert = AsyncMock()

    mock_cb = AsyncMock()
    mock_cb.record_success = AsyncMock()
    mock_cb.is_tripped = AsyncMock(return_value=False)

    with patch("datametronome_podium.tasks.check_tasks.ClefExecutor") as MockExec:
        MockExec.return_value.execute_clef = AsyncMock(return_value=_mock_check_result())
        with patch("datametronome_podium.tasks.check_tasks._get_circuit_breaker", return_value=mock_cb):
            result = await _execute_check_async("clef-1", mock_connector, mock_executor)

    assert result["status"] == "pass"
    mock_cb.record_success.assert_awaited_once_with("stave-1")


@pytest.mark.asyncio
async def test_execute_check_async_skips_paused_stave():
    from datametronome_podium.tasks.check_tasks import _execute_check_async

    mock_connector = AsyncMock()
    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(side_effect=[
        [_mock_clef_row()],
        [_mock_stave_row()],
    ])

    mock_cb = AsyncMock()
    mock_cb.is_tripped = AsyncMock(return_value=True)

    with patch("datametronome_podium.tasks.check_tasks._get_circuit_breaker", return_value=mock_cb):
        with pytest.raises(ValueError, match="paused"):
            await _execute_check_async("clef-1", mock_connector, mock_executor)
