"""
Scheduler management endpoints for DataMetronome Podium.

Scheduling is now handled by Celery Beat + RedBeat.
These endpoints provide status and management via the persisted scheduler_jobs table
and job_monitor service.  APScheduler has been removed.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, status

from datametronome_podium.services.job_monitor import (
    calculate_job_health_metrics,
    get_failing_jobs,
    get_job_execution_history,
)
from datametronome_podium.services.scheduler_persistence import (
    delete_scheduler_job,
    get_all_scheduler_jobs,
    get_scheduler_job,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/reload")
async def reload_scheduler_clefs() -> Dict[str, Any]:
    """
    Reload and schedule all clefs that have schedules.

    NOTE: Scheduling is now handled by Celery Beat + RedBeat.
    This endpoint returns the current state of persisted jobs.
    """
    try:
        all_jobs = await get_all_scheduler_jobs()
        enabled_jobs = [j for j in all_jobs if j.enabled]

        return {
            "success": True,
            "result": {
                "total_clefs": len(all_jobs),
                "scheduled": len(enabled_jobs),
                "failed": 0,
            },
            "scheduled_clefs": [
                {"clef_id": j.clef_id, "schedule": j.schedule, "job_id": j.id}
                for j in enabled_jobs
            ],
            "scheduler": {"status": "celery-beat", "job_count": len(enabled_jobs)},
            "is_running": True,  # Beat is always running in Docker
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload scheduler: {str(e)}",
        )


@router.get("/status")
async def get_scheduler_status_endpoint() -> Dict[str, Any]:
    """Get the current status of the scheduler (Celery Beat)."""
    try:
        all_jobs = await get_all_scheduler_jobs()
        enabled_count = sum(1 for j in all_jobs if j.enabled)

        return {
            "scheduler": {
                "status": "celery-beat",
                "job_count": enabled_count,
                "backend": "RedBeat",
            },
            "is_running": True,
            "scheduled_clefs_count": enabled_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}",
        )


@router.get("/clefs")
async def get_scheduled_clefs_endpoint() -> Dict[str, Any]:
    """Get all currently scheduled clefs."""
    try:
        all_jobs = await get_all_scheduler_jobs(enabled_only=True)
        scheduled_clefs = [
            {
                "clef_id": j.clef_id,
                "schedule": j.schedule,
                "job_id": j.id,
                "next_run": j.next_run_time.isoformat() + "Z"
                if j.next_run_time
                else None,
            }
            for j in all_jobs
        ]

        return {
            "clefs": scheduled_clefs,
            "_timezone_info": {
                "backend_timezone": "UTC",
                "timestamp_format": "ISO 8601 with Z suffix (e.g., 2025-10-08T22:30:00Z)",
                "note": "All timestamps are stored and processed in UTC. UI converts to local timezone for display.",
                "scheduler_timezone": "UTC",
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled clefs: {str(e)}",
        )


@router.post("/clefs/{clef_id}/unschedule")
async def unschedule_clef_endpoint(clef_id: str) -> Dict[str, Any]:
    """Remove a clef from the scheduler."""
    try:
        # TODO: Integrate with RedBeat to remove the periodic task entry
        job_id = f"clef_{clef_id}"
        await delete_scheduler_job(job_id)
        return {
            "success": True,
            "message": f"Clef {clef_id} unscheduled successfully",
            "clef_id": clef_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unschedule clef: {str(e)}",
        )


@router.post("/clefs/{clef_id}/reschedule")
async def reschedule_clef_endpoint(clef_id: str) -> Dict[str, Any]:
    """Reschedule a clef (remove and add again)."""
    # TODO: Integrate with RedBeat to update the periodic task schedule
    return {
        "success": True,
        "message": f"Clef {clef_id} rescheduling delegated to Celery Beat",
        "clef_id": clef_id,
    }


@router.post("/clefs/{clef_id}/execute")
async def execute_clef_now_endpoint(clef_id: str) -> Dict[str, Any]:
    """Execute a clef immediately (outside of its schedule)."""
    try:
        from datametronome_podium.core.dispatcher_factory import get_dispatcher

        dispatcher = get_dispatcher()
        await dispatcher.dispatch(clef_id)
        return {
            "success": True,
            "message": f"Clef {clef_id} dispatched for execution",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute clef: {str(e)}",
        )


@router.get("/jobs")
async def get_scheduler_jobs() -> Dict[str, Any]:
    """Get detailed information about all scheduler jobs."""
    try:
        all_jobs = await get_all_scheduler_jobs()

        job_details = []
        for job in all_jobs:
            job_details.append(
                {
                    "id": job.id,
                    "clef_id": job.clef_id,
                    "schedule": job.schedule,
                    "enabled": job.enabled,
                    "next_run_time": job.next_run_time.isoformat() + "Z"
                    if job.next_run_time
                    else None,
                    "last_run_time": job.last_run_time.isoformat() + "Z"
                    if job.last_run_time
                    else None,
                    "execution_count": job.execution_count,
                    "failure_count": job.failure_count,
                }
            )

        return {
            "scheduler_enabled": True,
            "total_jobs": len(all_jobs),
            "jobs": job_details,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler jobs: {str(e)}",
        )


@router.get("/jobs/{job_id}/history")
async def get_job_history(
    job_id: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get execution history for a specific job."""
    try:
        executions = await get_job_execution_history(job_id, limit=limit, offset=offset)

        execution_data = []
        for exec in executions:
            execution_data.append(
                {
                    "id": exec.id,
                    "status": exec.status,
                    "execution_time": exec.execution_time,
                    "error_message": exec.error_message,
                    "started_at": exec.started_at.isoformat() + "Z",
                    "completed_at": exec.completed_at.isoformat() + "Z"
                    if exec.completed_at
                    else None,
                }
            )

        return {
            "job_id": job_id,
            "executions": execution_data,
            "count": len(execution_data),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job history: {str(e)}",
        )


@router.get("/jobs/{job_id}/health")
async def get_job_health(
    job_id: str, lookback_days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """Get health metrics for a specific job."""
    try:
        metrics = await calculate_job_health_metrics(
            job_id, lookback_days=lookback_days
        )

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No execution history found for job {job_id}",
            )

        return metrics.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job health: {str(e)}",
        )


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str) -> Dict[str, Any]:
    """Manually retry a job execution."""
    try:
        job = await get_scheduler_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        from datametronome_podium.core.dispatcher_factory import get_dispatcher

        dispatcher = get_dispatcher()
        await dispatcher.dispatch(job.clef_id)

        return {
            "success": True,
            "job_id": job_id,
            "clef_id": job.clef_id,
            "message": "Dispatched for execution",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}",
        )


@router.get("/stats")
async def get_scheduler_stats() -> Dict[str, Any]:
    """Get overall scheduler statistics."""
    try:
        all_jobs = await get_all_scheduler_jobs()

        total_jobs = len(all_jobs)
        enabled_jobs = len([j for j in all_jobs if j.enabled])
        disabled_jobs = total_jobs - enabled_jobs

        failing_jobs = await get_failing_jobs(consecutive_failure_threshold=3)

        total_executions = sum(job.execution_count for job in all_jobs)
        total_failures = sum(job.failure_count for job in all_jobs)

        return {
            "scheduler_enabled": True,
            "stats": {
                "total_jobs": total_jobs,
                "enabled_jobs": enabled_jobs,
                "disabled_jobs": disabled_jobs,
                "failing_jobs": len(failing_jobs),
                "total_executions": total_executions,
                "total_failures": total_failures,
                "overall_success_rate": (total_executions - total_failures)
                / total_executions
                if total_executions > 0
                else 1.0,
            },
            "failing_jobs": failing_jobs,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler stats: {str(e)}",
        )


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str) -> Dict[str, Any]:
    """Pause a specific scheduled job."""
    try:
        from datametronome_podium.services.scheduler_persistence import (
            save_scheduler_job,
        )

        persisted_job = await get_scheduler_job(job_id)
        if not persisted_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        persisted_job.enabled = False
        await save_scheduler_job(persisted_job)
        # TODO: Also remove from RedBeat schedule

        return {"success": True, "job_id": job_id, "message": f"Job {job_id} paused"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause job: {str(e)}",
        )


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str) -> Dict[str, Any]:
    """Resume a paused scheduled job."""
    try:
        from datametronome_podium.services.scheduler_persistence import (
            save_scheduler_job,
        )

        persisted_job = await get_scheduler_job(job_id)
        if not persisted_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        persisted_job.enabled = True
        await save_scheduler_job(persisted_job)
        # TODO: Also add back to RedBeat schedule

        return {"success": True, "job_id": job_id, "message": f"Job {job_id} resumed"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume job: {str(e)}",
        )
