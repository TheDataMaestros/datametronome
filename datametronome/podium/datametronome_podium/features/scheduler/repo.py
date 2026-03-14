"""Scheduler data access."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.scheduler.model import SchedulerJob, JobExecution


class SchedulerRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def get_job(self, job_id: str) -> SchedulerJob | None:
        rows = await self.db.select("scheduler_jobs", where={"id": job_id})
        return SchedulerJob(**rows[0]) if rows else None

    async def get_job_by_clef(self, clef_id: str) -> SchedulerJob | None:
        rows = await self.db.select("scheduler_jobs", where={"clef_id": clef_id})
        return SchedulerJob(**rows[0]) if rows else None

    async def create_job(self, clef_id: str, schedule: str) -> SchedulerJob:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        job = SchedulerJob(
            id=f"job_{clef_id}",
            clef_id=clef_id,
            schedule=schedule,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        await self.db.insert("scheduler_jobs", job.model_dump())
        return job

    async def list_jobs(self, enabled_only: bool = False) -> list[SchedulerJob]:
        if enabled_only:
            rows = await self.db.select("scheduler_jobs", where={"enabled": True})
        else:
            rows = await self.db.select("scheduler_jobs")
        return [SchedulerJob(**row) for row in rows]

    async def update_job(self, job_id: str, data: dict) -> int:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        data["updated_at"] = now
        return await self.db.update("scheduler_jobs", data, where={"id": job_id})

    async def delete_job(self, job_id: str) -> int:
        return await self.db.delete("scheduler_jobs", where={"id": job_id})

    async def record_execution(
        self, job_id: str, clef_id: str, status: str,
        execution_time: float | None = None, error_message: str | None = None
    ) -> str:
        exec_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        await self.db.insert("job_executions", {
            "id": exec_id,
            "job_id": job_id,
            "clef_id": clef_id,
            "status": status,
            "execution_time": execution_time,
            "error_message": error_message,
            "started_at": now,
            "completed_at": now if status != "retry" else None,
        })
        return exec_id

    async def get_execution_history(
        self, job_id: str, limit: int = 100, offset: int = 0
    ) -> list[JobExecution]:
        rows = await self.db.query(
            "SELECT * FROM job_executions WHERE job_id = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
            [job_id, limit, offset]
        )
        return [JobExecution(**row) for row in rows]
