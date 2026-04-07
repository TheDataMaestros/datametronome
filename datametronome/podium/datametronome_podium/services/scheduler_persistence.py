"""
Scheduler Persistence Service.

This service handles persisting scheduler job state to the database,
allowing jobs to survive service restarts.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.core.database import get_executor

logger = logging.getLogger(__name__)


class SchedulerJob:
    """Represents a persisted scheduler job."""

    def __init__(
        self,
        id: str,
        clef_id: str,
        schedule: str,
        enabled: bool = True,
        last_run_time: datetime | None = None,
        next_run_time: datetime | None = None,
        execution_count: int = 0,
        failure_count: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.clef_id = clef_id
        self.schedule = schedule
        self.enabled = enabled
        self.last_run_time = last_run_time
        self.next_run_time = next_run_time
        self.execution_count = execution_count
        self.failure_count = failure_count
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "clef_id": self.clef_id,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "last_run_time": self.last_run_time.isoformat() + "Z"
            if self.last_run_time
            else None,
            "next_run_time": self.next_run_time.isoformat() + "Z"
            if self.next_run_time
            else None,
            "execution_count": self.execution_count,
            "failure_count": self.failure_count,
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SchedulerJob":
        """Create from dictionary loaded from database."""

        def parse_datetime(dt_str: str | None) -> datetime | None:
            if not dt_str:
                return None
            try:
                # Handle both with and without Z suffix
                if dt_str.endswith("Z"):
                    dt_str = dt_str[:-1] + "+00:00"
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except (ValueError, TypeError, OSError):
                return None

        return cls(
            id=data["id"],
            clef_id=data["clef_id"],
            schedule=data["schedule"],
            enabled=bool(data.get("enabled", True)),
            last_run_time=parse_datetime(data.get("last_run_time")),
            next_run_time=parse_datetime(data.get("next_run_time")),
            execution_count=int(data.get("execution_count", 0)),
            failure_count=int(data.get("failure_count", 0)),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


async def save_scheduler_job(job: SchedulerJob) -> bool:
    """
    Save or update a scheduler job in the database.

    Args:
        job: SchedulerJob to save

    Returns:
        True if successful, False otherwise
    """
    try:
        executor = get_executor()
        job_data = job.to_dict()

        # Upsert: insert the job, updating all columns on conflict with the primary key.
        # This replaces the old db.write(..., config={"type": "replace"}) semantics.
        columns = list(job_data.keys())
        col_names = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in columns if c != "id")
        sql = (
            f"INSERT INTO scheduler_jobs ({col_names}) VALUES ({placeholders})"
            f" ON CONFLICT (id) DO UPDATE SET {updates}"
        )
        await executor.execute(sql, list(job_data.values()))

        logger.debug("Saved scheduler job: %s", job.id)
        return True

    except Exception as e:
        logger.error("Failed to save scheduler job %s: %s", job.id, e)
        return False


async def get_scheduler_job(job_id: str) -> SchedulerJob | None:
    """
    Get a scheduler job by ID.

    Args:
        job_id: Job ID

    Returns:
        SchedulerJob or None if not found
    """
    try:
        executor = get_executor()
        results = await executor.query(
            "SELECT * FROM scheduler_jobs WHERE id = ?", [job_id]
        )

        if results:
            return SchedulerJob.from_dict(results[0])
        return None

    except Exception as e:
        logger.error("Failed to get scheduler job %s: %s", job_id, e)
        return None


async def get_scheduler_job_by_clef_id(clef_id: str) -> SchedulerJob | None:
    """
    Get a scheduler job by clef ID.

    Args:
        clef_id: Clef ID

    Returns:
        SchedulerJob or None if not found
    """
    try:
        executor = get_executor()
        results = await executor.query(
            "SELECT * FROM scheduler_jobs WHERE clef_id = ?", [clef_id]
        )

        if results:
            return SchedulerJob.from_dict(results[0])
        return None

    except Exception as e:
        logger.error("Failed to get scheduler job for clef %s: %s", clef_id, e)
        return None


async def get_all_scheduler_jobs(enabled_only: bool = False) -> list[SchedulerJob]:
    """
    Get all scheduler jobs.

    Args:
        enabled_only: If True, only return enabled jobs

    Returns:
        List of SchedulerJob objects
    """
    try:
        executor = get_executor()

        if enabled_only:
            results = await executor.query(
                "SELECT * FROM scheduler_jobs WHERE enabled = TRUE", []
            )
        else:
            results = await executor.query("SELECT * FROM scheduler_jobs", [])

        return [SchedulerJob.from_dict(row) for row in results]

    except Exception as e:
        logger.error("Failed to get scheduler jobs: %s", e)
        return []


async def delete_scheduler_job(job_id: str) -> bool:
    """
    Delete a scheduler job from the database.

    Args:
        job_id: Job ID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        executor = get_executor()
        await executor.execute("DELETE FROM scheduler_jobs WHERE id = ?", [job_id])

        logger.debug("Deleted scheduler job: %s", job_id)
        return True

    except Exception as e:
        logger.error("Failed to delete scheduler job %s: %s", job_id, e)
        return False


async def update_job_run_time(
    job_id: str,
    last_run: datetime | None = None,
    next_run: datetime | None = None,
) -> bool:
    """
    Update job run times.

    Args:
        job_id: Job ID
        last_run: Last run time
        next_run: Next run time

    Returns:
        True if successful
    """
    try:
        executor = get_executor()
        updates = []
        params: list[Any] = []

        if last_run is not None:
            updates.append("last_run_time = ?")
            params.append(last_run.isoformat() + "Z")

        if next_run is not None:
            updates.append("next_run_time = ?")
            params.append(next_run.isoformat() + "Z")

        if not updates:
            return True

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat() + "Z")
        params.append(job_id)

        sql = f"UPDATE scheduler_jobs SET {', '.join(updates)} WHERE id = ?"
        await executor.execute(sql, params)

        return True

    except Exception as e:
        logger.error("Failed to update job run times for %s: %s", job_id, e)
        return False


async def increment_job_execution_count(job_id: str, success: bool = True) -> bool:
    """
    Increment job execution or failure count.

    Args:
        job_id: Job ID
        success: Whether execution was successful

    Returns:
        True if successful
    """
    try:
        executor = get_executor()

        if success:
            sql = "UPDATE scheduler_jobs SET execution_count = execution_count + 1, updated_at = ? WHERE id = ?"
        else:
            sql = "UPDATE scheduler_jobs SET failure_count = failure_count + 1, updated_at = ? WHERE id = ?"

        await executor.execute(sql, [datetime.now(timezone.utc).isoformat() + "Z", job_id])

        return True

    except Exception as e:
        logger.error("Failed to increment execution count for %s: %s", job_id, e)
        return False


async def create_scheduler_job(clef_id: str, schedule: str) -> SchedulerJob | None:
    """
    Create a new scheduler job.

    Args:
        clef_id: Clef ID
        schedule: Cron schedule expression

    Returns:
        Created SchedulerJob or None if failed
    """
    job_id = f"job_{clef_id}"
    job = SchedulerJob(id=job_id, clef_id=clef_id, schedule=schedule, enabled=True)

    if await save_scheduler_job(job):
        return job
    return None
