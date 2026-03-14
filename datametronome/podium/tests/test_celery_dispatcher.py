"""Tests for CeleryDispatcher."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_celery_dispatcher_dispatch():
    from datametronome_podium.core.celery_dispatcher import CeleryDispatcher

    mock_result = MagicMock()
    mock_result.id = "celery-task-uuid-123"

    with patch("datametronome_podium.core.celery_dispatcher.execute_check") as mock_task:
        mock_task.apply_async.return_value = mock_result
        dispatcher = CeleryDispatcher()
        job_id = await dispatcher.dispatch("clef-1")

    assert job_id == "celery-task-uuid-123"
    mock_task.apply_async.assert_called_once_with(
        args=["clef-1"],
        queue="checks.high",
    )


@pytest.mark.asyncio
async def test_celery_dispatcher_dispatch_with_queue():
    from datametronome_podium.core.celery_dispatcher import CeleryDispatcher

    mock_result = MagicMock()
    mock_result.id = "celery-task-uuid-456"

    with patch("datametronome_podium.core.celery_dispatcher.execute_check") as mock_task:
        mock_task.apply_async.return_value = mock_result
        dispatcher = CeleryDispatcher(default_queue="checks.default")
        job_id = await dispatcher.dispatch("clef-2")

    mock_task.apply_async.assert_called_once_with(
        args=["clef-2"],
        queue="checks.default",
    )


@pytest.mark.asyncio
async def test_celery_dispatcher_get_status_pending():
    from datametronome_podium.core.celery_dispatcher import CeleryDispatcher
    from datametronome_podium.core.check_dispatcher import JobStatus

    mock_async_result = MagicMock()
    mock_async_result.state = "PENDING"

    with patch("datametronome_podium.core.celery_dispatcher.AsyncResult", return_value=mock_async_result):
        dispatcher = CeleryDispatcher()
        status = await dispatcher.get_status("job-123")

    assert status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_celery_dispatcher_get_status_success():
    from datametronome_podium.core.celery_dispatcher import CeleryDispatcher
    from datametronome_podium.core.check_dispatcher import JobStatus

    mock_async_result = MagicMock()
    mock_async_result.state = "SUCCESS"

    with patch("datametronome_podium.core.celery_dispatcher.AsyncResult", return_value=mock_async_result):
        dispatcher = CeleryDispatcher()
        status = await dispatcher.get_status("job-123")

    assert status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_celery_dispatcher_get_result():
    from datametronome_podium.core.celery_dispatcher import CeleryDispatcher

    mock_async_result = MagicMock()
    mock_async_result.ready.return_value = True
    mock_async_result.result = {"status": "pass", "clef_id": "clef-1"}

    with patch("datametronome_podium.core.celery_dispatcher.AsyncResult", return_value=mock_async_result):
        dispatcher = CeleryDispatcher()
        result = await dispatcher.get_result("job-123")

    assert result == {"status": "pass", "clef_id": "clef-1"}


@pytest.mark.asyncio
async def test_celery_dispatcher_get_result_not_ready():
    from datametronome_podium.core.celery_dispatcher import CeleryDispatcher

    mock_async_result = MagicMock()
    mock_async_result.ready.return_value = False

    with patch("datametronome_podium.core.celery_dispatcher.AsyncResult", return_value=mock_async_result):
        dispatcher = CeleryDispatcher()
        result = await dispatcher.get_result("job-123")

    assert result is None


@pytest.mark.asyncio
async def test_celery_dispatcher_satisfies_protocol():
    from datametronome_podium.core.celery_dispatcher import CeleryDispatcher
    from datametronome_podium.core.check_dispatcher import CheckDispatcher
    dispatcher = CeleryDispatcher()
    assert isinstance(dispatcher, CheckDispatcher)
