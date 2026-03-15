"""Scheduler domain models."""
from pydantic import BaseModel


class SchedulerJob(BaseModel):
    id: str
    clef_id: str
    schedule: str
    enabled: bool = True
    last_run_time: str | None = None
    next_run_time: str | None = None
    execution_count: int = 0
    failure_count: int = 0
    created_at: str
    updated_at: str


class JobExecution(BaseModel):
    id: str
    job_id: str
    clef_id: str
    status: str  # success, failure, retry
    execution_time: float | None = None
    error_message: str | None = None
    started_at: str
    completed_at: str | None = None
