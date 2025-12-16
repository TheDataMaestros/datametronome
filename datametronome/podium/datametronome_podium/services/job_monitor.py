"""
Job Execution Monitoring Service.

This service tracks job execution history and calculates health metrics.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from datametronome_podium.core.database import get_db

logger = logging.getLogger(__name__)


class JobExecution:
    """Represents a single job execution record."""

    def __init__(
        self,
        id: str,
        job_id: str,
        clef_id: str,
        status: str,  # 'success', 'failure', 'retry'
        execution_time: Optional[float] = None,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.job_id = job_id
        self.clef_id = clef_id
        self.status = status
        self.execution_time = execution_time
        self.error_message = error_message
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "clef_id": self.clef_id,
            "status": self.status,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() + "Z",
            "completed_at": self.completed_at.isoformat() + "Z"
            if self.completed_at
            else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobExecution":
        """Create from dictionary loaded from database."""

        def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            try:
                if dt_str.endswith("Z"):
                    dt_str = dt_str[:-1] + "+00:00"
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except:
                return None

        return cls(
            id=data["id"],
            job_id=data["job_id"],
            clef_id=data["clef_id"],
            status=data["status"],
            execution_time=data.get("execution_time"),
            error_message=data.get("error_message"),
            started_at=parse_datetime(data.get("started_at")),
            completed_at=parse_datetime(data.get("completed_at")),
        )


class JobHealthMetrics:
    """Job health metrics calculated from execution history."""

    def __init__(
        self,
        job_id: str,
        clef_id: str,
        success_rate: float,
        avg_execution_time: float,
        total_executions: int,
        total_failures: int,
        consecutive_failures: int,
        health_status: str,  # 'healthy', 'degraded', 'failing'
        last_success: Optional[datetime] = None,
        last_failure: Optional[datetime] = None,
    ):
        self.job_id = job_id
        self.clef_id = clef_id
        self.success_rate = success_rate
        self.avg_execution_time = avg_execution_time
        self.total_executions = total_executions
        self.total_failures = total_failures
        self.consecutive_failures = consecutive_failures
        self.health_status = health_status
        self.last_success = last_success
        self.last_failure = last_failure

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "clef_id": self.clef_id,
            "success_rate": self.success_rate,
            "avg_execution_time": self.avg_execution_time,
            "total_executions": self.total_executions,
            "total_failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
            "health_status": self.health_status,
            "last_success": self.last_success.isoformat() + "Z"
            if self.last_success
            else None,
            "last_failure": self.last_failure.isoformat() + "Z"
            if self.last_failure
            else None,
        }


async def record_job_execution(
    job_id: str,
    clef_id: str,
    status: str,
    execution_time: Optional[float] = None,
    error_message: Optional[str] = None,
) -> Optional[str]:
    """
    Record a job execution in the database.

    Args:
        job_id: Job ID
        clef_id: Clef ID
        status: Execution status ('success', 'failure', 'retry')
        execution_time: Execution time in seconds
        error_message: Error message if failed

    Returns:
        Execution record ID or None if failed
    """
    try:
        execution_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        completed_at = datetime.utcnow()

        execution = JobExecution(
            id=execution_id,
            job_id=job_id,
            clef_id=clef_id,
            status=status,
            execution_time=execution_time,
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )

        db = await get_db()
        await db.write([execution.to_dict()], "job_executions")

        logger.debug(f"Recorded job execution: {execution_id} for job {job_id}")
        return execution_id

    except Exception as e:
        logger.error(f"Failed to record job execution: {e}")
        return None


async def get_job_execution_history(
    job_id: str, limit: int = 100, offset: int = 0
) -> List[JobExecution]:
    """
    Get execution history for a job.

    Args:
        job_id: Job ID
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        List of JobExecution objects
    """
    try:
        db = await get_db()
        results = await db.query(
            {
                "sql": """
                SELECT * FROM job_executions
                WHERE job_id = ?
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
            """,
                "params": [job_id, limit, offset],
            }
        )

        return [JobExecution.from_dict(row) for row in results]

    except Exception as e:
        logger.error(f"Failed to get job execution history for {job_id}: {e}")
        return []


async def calculate_job_health_metrics(
    job_id: str, lookback_days: int = 30
) -> Optional[JobHealthMetrics]:
    """
    Calculate health metrics for a job based on execution history.

    Args:
        job_id: Job ID
        lookback_days: Number of days to look back for metrics

    Returns:
        JobHealthMetrics or None if no executions found
    """
    try:
        db = await get_db()

        # Get executions from the last N days
        cutoff_date = (
            datetime.utcnow() - timedelta(days=lookback_days)
        ).isoformat() + "Z"

        results = await db.query(
            {
                "sql": """
                SELECT * FROM job_executions
                WHERE job_id = ? AND started_at >= ?
                ORDER BY started_at DESC
            """,
                "params": [job_id, cutoff_date],
            }
        )

        if not results:
            return None

        executions = [JobExecution.from_dict(row) for row in results]

        # Calculate metrics
        total_executions = len(executions)
        successful = sum(1 for e in executions if e.status == "success")
        failed = sum(1 for e in executions if e.status == "failure")
        success_rate = successful / total_executions if total_executions > 0 else 0.0

        # Average execution time (only for successful executions)
        successful_times = [
            e.execution_time
            for e in executions
            if e.status == "success" and e.execution_time
        ]
        avg_execution_time = (
            sum(successful_times) / len(successful_times) if successful_times else 0.0
        )

        # Consecutive failures
        consecutive_failures = 0
        for execution in executions:
            if execution.status == "failure":
                consecutive_failures += 1
            else:
                break

        # Determine health status
        if success_rate >= 0.95 and consecutive_failures == 0:
            health_status = "healthy"
        elif success_rate >= 0.80 and consecutive_failures < 3:
            health_status = "degraded"
        else:
            health_status = "failing"

        # Get last success and failure
        last_success = next(
            (e.started_at for e in executions if e.status == "success"), None
        )
        last_failure = next(
            (e.started_at for e in executions if e.status == "failure"), None
        )

        # Get clef_id from first execution
        clef_id = executions[0].clef_id if executions else ""

        return JobHealthMetrics(
            job_id=job_id,
            clef_id=clef_id,
            success_rate=success_rate,
            avg_execution_time=avg_execution_time,
            total_executions=total_executions,
            total_failures=failed,
            consecutive_failures=consecutive_failures,
            health_status=health_status,
            last_success=last_success,
            last_failure=last_failure,
        )

    except Exception as e:
        logger.error(f"Failed to calculate health metrics for {job_id}: {e}")
        return None


async def get_failing_jobs(
    consecutive_failure_threshold: int = 3,
) -> List[Dict[str, Any]]:
    """
    Get list of jobs that are currently failing.

    Args:
        consecutive_failure_threshold: Number of consecutive failures to consider as failing

    Returns:
        List of job information dictionaries
    """
    try:
        db = await get_db()

        # Get all jobs
        jobs = await db.query(
            {"sql": "SELECT * FROM scheduler_jobs WHERE enabled = TRUE", "params": []}
        )

        failing_jobs = []

        for job_data in jobs:
            job_id = job_data["id"]
            metrics = await calculate_job_health_metrics(job_id)

            if (
                metrics
                and metrics.consecutive_failures >= consecutive_failure_threshold
            ):
                failing_jobs.append(
                    {
                        "job_id": job_id,
                        "clef_id": metrics.clef_id,
                        "consecutive_failures": metrics.consecutive_failures,
                        "success_rate": metrics.success_rate,
                        "health_status": metrics.health_status,
                        "last_failure": metrics.last_failure.isoformat() + "Z"
                        if metrics.last_failure
                        else None,
                    }
                )

        return failing_jobs

    except Exception as e:
        logger.error(f"Failed to get failing jobs: {e}")
        return []


