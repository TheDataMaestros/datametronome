"""
Scheduler management endpoints for DataMetronome Podium.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status

from datametronome_podium.core.scheduler import get_scheduler_status, is_scheduler_running
from datametronome_podium.services.clef_scheduler import (
    get_scheduled_clefs,
    unschedule_clef,
    reschedule_clef,
    execute_scheduled_clef
)

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
            "scheduled_clefs_count": status_info.get("job_count", 0)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
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
                "scheduler_timezone": "UTC"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled clefs: {str(e)}"
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
                "clef_id": clef_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to unschedule clef {clef_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unschedule clef: {str(e)}"
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
                "clef_id": clef_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to reschedule clef {clef_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule clef: {str(e)}"
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
                "execution_result": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to execute clef {clef_id}: {result.get('error', 'Unknown error')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute clef: {str(e)}"
        )


@router.get("/jobs")
async def get_scheduler_jobs() -> Dict[str, Any]:
    """Get detailed information about all scheduler jobs."""
    try:
        from datametronome_podium.core.scheduler import scheduler
        
        if not scheduler:
            return {
                "scheduler_enabled": False,
                "jobs": []
            }
        
        jobs = scheduler.get_jobs()
        job_details = []
        
        for job in jobs:
            job_info = {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "func": job.func.__name__ if job.func else None,
                "args": job.args,
                "kwargs": job.kwargs
            }
            job_details.append(job_info)
        
        return {
            "scheduler_enabled": True,
            "total_jobs": len(jobs),
            "jobs": job_details
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler jobs: {str(e)}"
        )
