"""
Scheduler management endpoints for DataMetronome Podium.
"""

from typing import Any, Dict, List

from datametronome_podium.core.scheduler import (
    get_scheduler_status,
    is_scheduler_running,
)
from datametronome_podium.services.clef_scheduler import (
    execute_scheduled_clef,
    get_scheduled_clefs,
    reschedule_clef,
    unschedule_clef,
)
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
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter()


@router.get("/status")
async def get_scheduler_status_endpoint() -> Dict[str, Any]:
    """Get the current status of the scheduler."""
    try:
        status_info = get_scheduler_status()
        is_running = await is_scheduler_running()

        return {
            "scheduler": status_info,
            "is_running": is_running,
            "scheduled_clefs_count": status_info.get("job_count", 0),
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
        scheduled_clefs = await get_scheduled_clefs()

        # Add timezone information to the response
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
        success = await unschedule_clef(clef_id)

        if success:
            return {
                "success": True,
                "message": f"Clef {clef_id} unscheduled successfully",
                "clef_id": clef_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to unschedule clef {clef_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unschedule clef: {str(e)}",
        )


@router.post("/clefs/{clef_id}/reschedule")
async def reschedule_clef_endpoint(clef_id: str) -> Dict[str, Any]:
    """Reschedule a clef (remove and add again)."""
    try:
        success = await reschedule_clef(clef_id)

        if success:
            return {
                "success": True,
                "message": f"Clef {clef_id} rescheduled successfully",
                "clef_id": clef_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to reschedule clef {clef_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule clef: {str(e)}",
        )


@router.post("/clefs/{clef_id}/execute")
async def execute_clef_now_endpoint(clef_id: str) -> Dict[str, Any]:
    """Execute a clef immediately (outside of its schedule)."""
    try:
        result = await execute_scheduled_clef(clef_id)

        if result.get("success"):
            return {
                "success": True,
                "message": f"Clef {clef_id} executed successfully",
                "execution_result": result,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to execute clef {clef_id}: {result.get('error', 'Unknown error')}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute clef: {str(e)}",
        )


@router.get("/jobs")
async def get_scheduler_jobs() -> Dict[str, Any]:
    """Get detailed information about all scheduler jobs."""
    try:
        from datametronome_podium.core.scheduler import scheduler

        if not scheduler:
            return {"scheduler_enabled": False, "jobs": []}

        jobs = scheduler.get_jobs()
        job_details = []

        for job in jobs:
            job_info = {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat()
                if job.next_run_time
                else None,
                "trigger": str(job.trigger),
                "func": job.func.__name__ if job.func else None,
                "args": job.args,
                "kwargs": job.kwargs,
            }
            job_details.append(job_info)

        return {"scheduler_enabled": True, "total_jobs": len(jobs), "jobs": job_details}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler jobs: {str(e)}",
        )


@router.get("/jobs/{job_id}/history")
async def get_job_history(
    job_id: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Get execution history for a specific job.

    Args:
        job_id: Job ID
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        Execution history with pagination
    """
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
    """
    Get health metrics for a specific job.

    Args:
        job_id: Job ID
        lookback_days: Number of days to look back for metrics

    Returns:
        Job health metrics
    """
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
    """
    Manually retry a job execution.

    Args:
        job_id: Job ID to retry

    Returns:
        Execution result
    """
    try:
        # Get job to find clef_id
        job = await get_scheduler_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        # Execute the clef
        result = await execute_scheduled_clef(job.clef_id)

        return {
            "success": result.get("success", False),
            "job_id": job_id,
            "clef_id": job.clef_id,
            "result": result,
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
    """
    Get overall scheduler statistics.

    Returns:
        Scheduler statistics including job counts, health metrics, etc.
    """
    try:
        from datametronome_podium.core.scheduler import scheduler

        if not scheduler:
            return {"scheduler_enabled": False, "stats": {}}

        jobs = scheduler.get_jobs()
        all_jobs = await get_all_scheduler_jobs()

        # Calculate stats
        total_jobs = len(jobs)
        enabled_jobs = len([j for j in all_jobs if j.enabled])
        disabled_jobs = total_jobs - enabled_jobs

        # Get failing jobs
        failing_jobs = await get_failing_jobs(consecutive_failure_threshold=3)

        # Calculate total executions and failures
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
    """
    Pause a specific scheduled job.

    Args:
        job_id: Job ID to pause

    Returns:
        Success status
    """
    try:
        from datametronome_podium.core.scheduler import scheduler

        if not scheduler:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not enabled",
            )

        # Get job from scheduler
        try:
            job = scheduler.get_job(job_id)
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job {job_id} not found",
                )
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        # Pause job
        job.pause()

        # Update persistence
        persisted_job = await get_scheduler_job(job_id)
        if persisted_job:
            persisted_job.enabled = False
            from datametronome_podium.services.scheduler_persistence import (
                save_scheduler_job,
            )

            await save_scheduler_job(persisted_job)

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
    """
    Resume a paused scheduled job.

    Args:
        job_id: Job ID to resume

    Returns:
        Success status
    """
    try:
        from datametronome_podium.core.scheduler import scheduler

        if not scheduler:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler is not enabled",
            )

        # Get job from scheduler
        try:
            job = scheduler.get_job(job_id)
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job {job_id} not found",
                )
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        # Resume job
        job.resume()

        # Update persistence
        persisted_job = await get_scheduler_job(job_id)
        if persisted_job:
            persisted_job.enabled = True
            from datametronome_podium.services.scheduler_persistence import (
                save_scheduler_job,
            )

            await save_scheduler_job(persisted_job)

        return {"success": True, "job_id": job_id, "message": f"Job {job_id} resumed"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume job: {str(e)}",
        )
