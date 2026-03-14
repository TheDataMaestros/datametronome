"""Tests for CheckDispatcher protocol and JobStatus enum."""
import pytest
from enum import Enum


def test_job_status_values():
    from datametronome_podium.core.check_dispatcher import JobStatus
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"


def test_check_dispatcher_is_protocol():
    from datametronome_podium.core.check_dispatcher import CheckDispatcher
    from typing import runtime_checkable, Protocol
    assert hasattr(CheckDispatcher, "__protocol_attrs__") or issubclass(CheckDispatcher, Protocol)


def test_check_dispatcher_has_dispatch():
    from datametronome_podium.core.check_dispatcher import CheckDispatcher
    import inspect
    sig = inspect.signature(CheckDispatcher.dispatch)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "clef_id" in params


def test_check_dispatcher_has_get_status():
    from datametronome_podium.core.check_dispatcher import CheckDispatcher
    import inspect
    sig = inspect.signature(CheckDispatcher.get_status)
    params = list(sig.parameters.keys())
    assert "job_id" in params


def test_check_dispatcher_has_get_result():
    from datametronome_podium.core.check_dispatcher import CheckDispatcher
    import inspect
    sig = inspect.signature(CheckDispatcher.get_result)
    params = list(sig.parameters.keys())
    assert "job_id" in params


@pytest.mark.asyncio
async def test_inline_dispatcher_dispatch_returns_job_id():
    from datametronome_podium.core.check_dispatcher import InlineDispatcher, JobStatus
    from unittest.mock import AsyncMock, patch, MagicMock
    from datametronome_podium.services.clef_executor import CheckResult

    mock_result = CheckResult(
        clef_id="clef-1",
        stave_id="stave-1",
        status="pass",
        message="OK",
        observed_value=42,
        execution_time=0.5,
    )

    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(side_effect=[
        [{"id": "clef-1", "stave_id": "stave-1", "name": "test", "check_type": "row_count",
          "config": '{"table": "users"}', "schedule": None, "retry_config": None,
          "is_active": True, "created_at": "2026-01-01T00:00:00Z",
          "updated_at": "2026-01-01T00:00:00Z", "warn": None, "fail": None,
          "description": None}],
        [{"id": "stave-1", "name": "prod-db", "data_source_type": "postgres",
          "connection_config": '{"host": "localhost", "port": 5432}',
          "is_active": True, "created_at": "2026-01-01T00:00:00Z",
          "updated_at": "2026-01-01T00:00:00Z", "description": None}],
    ])
    mock_executor.insert = AsyncMock()

    with patch("datametronome_podium.core.check_dispatcher.get_executor", return_value=mock_executor):
        with patch("datametronome_podium.core.check_dispatcher.ClefExecutor") as MockExecutor:
            MockExecutor.return_value.execute_clef = AsyncMock(return_value=mock_result)
            dispatcher = InlineDispatcher()
            job_id = await dispatcher.dispatch("clef-1")

    assert isinstance(job_id, str)
    assert len(job_id) > 0


@pytest.mark.asyncio
async def test_inline_dispatcher_get_status_completed():
    from datametronome_podium.core.check_dispatcher import InlineDispatcher, JobStatus
    from unittest.mock import AsyncMock, patch
    from datametronome_podium.services.clef_executor import CheckResult

    mock_result = CheckResult(
        clef_id="clef-1", stave_id="stave-1", status="pass",
        message="OK", observed_value=42, execution_time=0.5,
    )

    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(side_effect=[
        [{"id": "clef-1", "stave_id": "stave-1", "name": "test", "check_type": "row_count",
          "config": '{"table": "users"}', "schedule": None, "retry_config": None,
          "is_active": True, "created_at": "2026-01-01T00:00:00Z",
          "updated_at": "2026-01-01T00:00:00Z", "warn": None, "fail": None,
          "description": None}],
        [{"id": "stave-1", "name": "prod-db", "data_source_type": "postgres",
          "connection_config": '{"host": "localhost", "port": 5432}',
          "is_active": True, "created_at": "2026-01-01T00:00:00Z",
          "updated_at": "2026-01-01T00:00:00Z", "description": None}],
    ])
    mock_executor.insert = AsyncMock()

    with patch("datametronome_podium.core.check_dispatcher.get_executor", return_value=mock_executor):
        with patch("datametronome_podium.core.check_dispatcher.ClefExecutor") as MockExecutor:
            MockExecutor.return_value.execute_clef = AsyncMock(return_value=mock_result)
            dispatcher = InlineDispatcher()
            job_id = await dispatcher.dispatch("clef-1")
            status = await dispatcher.get_status(job_id)

    assert status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_inline_dispatcher_get_result():
    from datametronome_podium.core.check_dispatcher import InlineDispatcher
    from unittest.mock import AsyncMock, patch
    from datametronome_podium.services.clef_executor import CheckResult

    mock_result = CheckResult(
        clef_id="clef-1", stave_id="stave-1", status="pass",
        message="OK", observed_value=42, execution_time=0.5,
    )

    mock_executor = AsyncMock()
    mock_executor.query = AsyncMock(side_effect=[
        [{"id": "clef-1", "stave_id": "stave-1", "name": "test", "check_type": "row_count",
          "config": '{"table": "users"}', "schedule": None, "retry_config": None,
          "is_active": True, "created_at": "2026-01-01T00:00:00Z",
          "updated_at": "2026-01-01T00:00:00Z", "warn": None, "fail": None,
          "description": None}],
        [{"id": "stave-1", "name": "prod-db", "data_source_type": "postgres",
          "connection_config": '{"host": "localhost", "port": 5432}',
          "is_active": True, "created_at": "2026-01-01T00:00:00Z",
          "updated_at": "2026-01-01T00:00:00Z", "description": None}],
    ])
    mock_executor.insert = AsyncMock()

    with patch("datametronome_podium.core.check_dispatcher.get_executor", return_value=mock_executor):
        with patch("datametronome_podium.core.check_dispatcher.ClefExecutor") as MockExecutor:
            MockExecutor.return_value.execute_clef = AsyncMock(return_value=mock_result)
            dispatcher = InlineDispatcher()
            job_id = await dispatcher.dispatch("clef-1")
            result = await dispatcher.get_result(job_id)

    assert result is not None
    assert result["status"] == "pass"
    assert result["clef_id"] == "clef-1"


@pytest.mark.asyncio
async def test_inline_dispatcher_unknown_job():
    from datametronome_podium.core.check_dispatcher import InlineDispatcher, JobStatus
    dispatcher = InlineDispatcher()
    status = await dispatcher.get_status("nonexistent-id")
    assert status == JobStatus.FAILED
    result = await dispatcher.get_result("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_inline_dispatcher_satisfies_protocol():
    from datametronome_podium.core.check_dispatcher import InlineDispatcher, CheckDispatcher
    dispatcher = InlineDispatcher()
    assert isinstance(dispatcher, CheckDispatcher)
