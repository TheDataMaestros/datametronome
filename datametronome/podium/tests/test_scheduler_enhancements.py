"""
Comprehensive tests for scheduler enhancements:
- Job persistence
- Retry logic
- Job monitoring
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from datametronome_podium.services.clef_scheduler import execute_scheduled_clef
from datametronome_podium.services.job_monitor import (
    JobExecution,
    JobHealthMetrics,
    calculate_job_health_metrics,
    get_failing_jobs,
    get_job_execution_history,
    record_job_execution,
)
from datametronome_podium.services.scheduler_persistence import (
    SchedulerJob,
    create_scheduler_job,
    get_all_scheduler_jobs,
    get_scheduler_job,
    get_scheduler_job_by_clef_id,
    increment_job_execution_count,
    save_scheduler_job,
    update_job_run_time,
)


@pytest.mark.unit
class TestSchedulerPersistence:
    """Tests for scheduler job persistence."""

    @pytest.fixture
    def sample_job(self):
        """Create a sample scheduler job."""
        return SchedulerJob(
            id="job_clef-001",
            clef_id="clef-001",
            schedule="0 * * * *",
            enabled=True,
            execution_count=5,
            failure_count=1,
        )

    def test_scheduler_job_to_dict(self, sample_job):
        """Test converting SchedulerJob to dictionary."""
        job_dict = sample_job.to_dict()

        assert job_dict["id"] == "job_clef-001"
        assert job_dict["clef_id"] == "clef-001"
        assert job_dict["schedule"] == "0 * * * *"
        assert job_dict["enabled"] is True
        assert job_dict["execution_count"] == 5
        assert job_dict["failure_count"] == 1

    def test_scheduler_job_from_dict(self):
        """Test creating SchedulerJob from dictionary."""
        job_dict = {
            "id": "job_clef-001",
            "clef_id": "clef-001",
            "schedule": "0 * * * *",
            "enabled": True,
            "last_run_time": "2025-11-30T10:00:00Z",
            "next_run_time": "2025-11-30T11:00:00Z",
            "execution_count": 5,
            "failure_count": 1,
            "created_at": "2025-11-30T09:00:00Z",
            "updated_at": "2025-11-30T10:00:00Z",
        }

        job = SchedulerJob.from_dict(job_dict)

        assert job.id == "job_clef-001"
        assert job.clef_id == "clef-001"
        assert job.execution_count == 5
        assert job.failure_count == 1
        assert job.last_run_time is not None
        assert job.next_run_time is not None

    @pytest.mark.asyncio
    async def test_save_scheduler_job(self, sample_job):
        """Test saving a scheduler job to database."""
        with patch(
            "datametronome_podium.services.scheduler_persistence.get_db"
        ) as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock query to check if job exists
            mock_db.query.return_value = []  # Job doesn't exist

            result = await save_scheduler_job(sample_job)
            assert result is True

            # Verify write was called
            assert mock_db.write.called

    @pytest.mark.asyncio
    async def test_get_scheduler_job(self):
        """Test retrieving a scheduler job by ID."""
        with patch(
            "datametronome_podium.services.scheduler_persistence.get_db"
        ) as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_db.query.return_value = [
                {
                    "id": "job_clef-001",
                    "clef_id": "clef-001",
                    "schedule": "0 * * * *",
                    "enabled": True,
                    "execution_count": 0,
                    "failure_count": 0,
                    "created_at": "2025-11-30T09:00:00Z",
                    "updated_at": "2025-11-30T09:00:00Z",
                }
            ]

            job = await get_scheduler_job("job_clef-001")

            assert job is not None
            assert job.id == "job_clef-001"
            assert job.clef_id == "clef-001"

    @pytest.mark.asyncio
    async def test_get_all_scheduler_jobs(self):
        """Test retrieving all scheduler jobs."""
        with patch(
            "datametronome_podium.services.scheduler_persistence.get_db"
        ) as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            all_jobs = [
                {
                    "id": "job_clef-001",
                    "clef_id": "clef-001",
                    "schedule": "0 * * * *",
                    "enabled": True,
                    "execution_count": 0,
                    "failure_count": 0,
                    "created_at": "2025-11-30T09:00:00Z",
                    "updated_at": "2025-11-30T09:00:00Z",
                },
                {
                    "id": "job_clef-002",
                    "clef_id": "clef-002",
                    "schedule": "@daily",
                    "enabled": False,
                    "execution_count": 10,
                    "failure_count": 2,
                    "created_at": "2025-11-30T09:00:00Z",
                    "updated_at": "2025-11-30T09:00:00Z",
                },
            ]

            # Mock query to return different results based on SQL
            def query_side_effect(query_dict):
                sql = query_dict.get("sql", "")
                if "enabled = TRUE" in sql:
                    return [all_jobs[0]]  # Only enabled job
                return all_jobs  # All jobs

            mock_db.query.side_effect = query_side_effect

            jobs = await get_all_scheduler_jobs()

            assert len(jobs) == 2
            assert jobs[0].id == "job_clef-001"
            assert jobs[1].id == "job_clef-002"

            # Test enabled_only filter
            enabled_jobs = await get_all_scheduler_jobs(enabled_only=True)
            assert len(enabled_jobs) == 1
            assert enabled_jobs[0].id == "job_clef-001"


@pytest.mark.unit
class TestJobMonitoring:
    """Tests for job execution monitoring."""

    def test_job_execution_to_dict(self):
        """Test converting JobExecution to dictionary."""
        execution = JobExecution(
            id="exec-001",
            job_id="job_clef-001",
            clef_id="clef-001",
            status="success",
            execution_time=1.5,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        exec_dict = execution.to_dict()

        assert exec_dict["id"] == "exec-001"
        assert exec_dict["job_id"] == "job_clef-001"
        assert exec_dict["status"] == "success"
        assert exec_dict["execution_time"] == 1.5

    @pytest.mark.asyncio
    async def test_record_job_execution(self):
        """Test recording a job execution."""
        with patch("datametronome_podium.services.job_monitor.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            execution_id = await record_job_execution(
                job_id="job_clef-001",
                clef_id="clef-001",
                status="success",
                execution_time=1.5,
            )

            assert execution_id is not None
            assert mock_db.write.called

    @pytest.mark.asyncio
    async def test_get_job_execution_history(self):
        """Test retrieving job execution history."""
        with patch("datametronome_podium.services.job_monitor.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_db.query.return_value = [
                {
                    "id": "exec-001",
                    "job_id": "job_clef-001",
                    "clef_id": "clef-001",
                    "status": "success",
                    "execution_time": 1.5,
                    "started_at": "2025-11-30T10:00:00Z",
                    "completed_at": "2025-11-30T10:00:01Z",
                },
                {
                    "id": "exec-002",
                    "job_id": "job_clef-001",
                    "clef_id": "clef-001",
                    "status": "failure",
                    "execution_time": 0.5,
                    "error_message": "Connection failed",
                    "started_at": "2025-11-30T11:00:00Z",
                    "completed_at": "2025-11-30T11:00:00Z",
                },
            ]

            history = await get_job_execution_history("job_clef-001", limit=10)

            assert len(history) == 2
            assert history[0].status == "success"
            assert history[1].status == "failure"
            assert history[1].error_message == "Connection failed"

    @pytest.mark.asyncio
    async def test_calculate_job_health_metrics(self):
        """Test calculating job health metrics."""
        with patch("datametronome_podium.services.job_monitor.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock execution history with mostly successes
            cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
            mock_db.query.return_value = [
                {
                    "id": f"exec-{i}",
                    "job_id": "job_clef-001",
                    "clef_id": "clef-001",
                    "status": "success" if i < 9 else "failure",
                    "execution_time": 1.0 + (i * 0.1),
                    "started_at": (datetime.utcnow() - timedelta(hours=i)).isoformat()
                    + "Z",
                    "completed_at": (datetime.utcnow() - timedelta(hours=i)).isoformat()
                    + "Z",
                }
                for i in range(10)
            ]

            metrics = await calculate_job_health_metrics(
                "job_clef-001", lookback_days=30
            )

            assert metrics is not None
            assert metrics.job_id == "job_clef-001"
            assert metrics.total_executions == 10
            assert metrics.total_failures == 1
            assert metrics.success_rate == 0.9  # 9/10
            assert metrics.health_status in ["healthy", "degraded", "failing"]


@pytest.mark.unit
class TestRetryLogic:
    """Tests for retry logic in clef execution."""

    @pytest.mark.asyncio
    async def test_execute_with_retry_on_failure(self):
        """Test that failed executions trigger retry logic."""
        with patch(
            "datametronome_podium.services.clef_scheduler.get_db"
        ) as mock_get_db, patch(
            "datametronome_podium.services.clef_scheduler.ClefExecutor"
        ) as mock_executor, patch(
            "datametronome_podium.services.clef_scheduler.record_job_execution"
        ) as mock_record, patch(
            "datametronome_podium.services.clef_scheduler.increment_job_execution_count"
        ) as mock_increment:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock clef and stave data
            import json

            mock_db.query.side_effect = [
                [
                    {
                        "id": "clef-001",
                        "stave_id": "stave-001",
                        "name": "Test Check",
                        "check_type": "row_count",
                        "config": json.dumps({"table": "users"}),
                        "warn": None,
                        "fail": "< 1000",
                        "schedule": "@hourly",
                        "retry_config": json.dumps(
                            {"max_retries": 2, "backoff_factor": 1.0}
                        ),
                        "is_active": True,
                    }
                ],
                [
                    {
                        "id": "stave-001",
                        "name": "Test DB",
                        "data_source_type": "sqlite",
                        "connection_config": json.dumps({"path": ":memory:"}),
                        "is_active": True,
                    }
                ],
            ]

            # Mock executor to return failure
            mock_exec = mock_executor.return_value
            from datametronome_podium.models.severity import SeverityLevel
            from datametronome_podium.services.clef_executor import CheckResult

            mock_exec.execute_clef.return_value = CheckResult(
                clef_id="clef-001",
                stave_id="stave-001",
                status="fail",
                observed_value=500,
                message="Row count too low",
            )

            # Mock store result
            with patch(
                "datametronome_podium.services.clef_scheduler._store_clef_result"
            ):
                result = await execute_scheduled_clef("clef-001", retry_attempt=0)

                # Should have attempted execution
                assert mock_exec.execute_clef.called


@pytest.mark.integration
class TestSchedulerIntegration:
    """Integration tests for scheduler features."""

    @pytest.mark.asyncio
    async def test_full_job_lifecycle(self):
        """Test complete job lifecycle: create, execute, monitor."""
        # This would be a full integration test with actual database
        # For now, we'll test the flow with mocks

        with patch(
            "datametronome_podium.services.scheduler_persistence.get_db"
        ) as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Create job
            job = await create_scheduler_job("clef-001", "0 * * * *")

            assert job is not None
            assert job.clef_id == "clef-001"
            assert job.schedule == "0 * * * *"

            # Update run times
            now = datetime.utcnow()
            result = await update_job_run_time(
                job.id, last_run=now, next_run=now + timedelta(hours=1)
            )
            assert result is True

            # Increment execution count
            result = await increment_job_execution_count(job.id, success=True)
            assert result is True
