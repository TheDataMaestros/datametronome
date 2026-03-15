import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.scheduler.repo import SchedulerRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    executor.execute = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    executor.delete = AsyncMock(return_value=1)
    return executor


class TestSchedulerRepo:
    @pytest.mark.asyncio
    async def test_get_job(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "job_c1", "clef_id": "c1", "schedule": "0 * * * *",
             "enabled": True, "last_run_time": None, "next_run_time": None,
             "execution_count": 0, "failure_count": 0,
             "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"}
        ]
        repo = SchedulerRepo(mock_executor)
        result = await repo.get_job("job_c1")
        assert result is not None
        assert result.clef_id == "c1"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, mock_executor):
        repo = SchedulerRepo(mock_executor)
        result = await repo.get_job("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_job(self, mock_executor):
        repo = SchedulerRepo(mock_executor)
        job = await repo.create_job("c1", "0 * * * *")
        assert job.id == "job_c1"
        assert job.schedule == "0 * * * *"
        mock_executor.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_enabled_jobs(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "job_c1", "clef_id": "c1", "schedule": "0 * * * *",
             "enabled": True, "last_run_time": None, "next_run_time": None,
             "execution_count": 5, "failure_count": 0,
             "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"}
        ]
        repo = SchedulerRepo(mock_executor)
        result = await repo.list_jobs(enabled_only=True)
        assert len(result) == 1
        mock_executor.select.assert_called_once_with("scheduler_jobs", where={"enabled": True})

    @pytest.mark.asyncio
    async def test_delete_job(self, mock_executor):
        repo = SchedulerRepo(mock_executor)
        result = await repo.delete_job("job_c1")
        assert result == 1

    @pytest.mark.asyncio
    async def test_record_execution(self, mock_executor):
        repo = SchedulerRepo(mock_executor)
        exec_id = await repo.record_execution(
            job_id="job_c1", clef_id="c1", status="success",
            execution_time=1.5
        )
        assert exec_id is not None
        mock_executor.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_execution_history(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "ex1", "job_id": "job_c1", "clef_id": "c1",
             "status": "success", "execution_time": 1.5,
             "error_message": None,
             "started_at": "2025-01-01T00:00:00Z", "completed_at": "2025-01-01T00:00:01Z"}
        ]
        repo = SchedulerRepo(mock_executor)
        result = await repo.get_execution_history("job_c1", limit=10)
        assert len(result) == 1
        assert result[0].status == "success"
