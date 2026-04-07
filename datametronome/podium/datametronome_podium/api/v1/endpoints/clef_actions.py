"""
Clef action endpoints - Run now and view results functionality.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from datametronome_podium.core.check_dispatcher import JobStatus
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.dispatcher_factory import get_dispatcher

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{clef_id}/run-now", status_code=status.HTTP_202_ACCEPTED)
async def run_clef_now(clef_id: str) -> dict:
    """Dispatch a clef for immediate execution. Returns 202 with job_id."""
    try:
        dispatcher = get_dispatcher()
        job_id = await dispatcher.dispatch(clef_id)
        job_status = await dispatcher.get_status(job_id)
        logger.info("Dispatched clef %s, job_id=%s", clef_id, job_id)
        return {
            "job_id": job_id,
            "clef_id": clef_id,
            "status": job_status.value,
        }
    except Exception as e:
        logger.error("Failed to dispatch clef %s: %s", clef_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dispatch check",
        )


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str) -> dict:
    """Get the status and result of a dispatched check job."""
    try:
        dispatcher = get_dispatcher()
        job_status = await dispatcher.get_status(job_id)
        result = await dispatcher.get_result(job_id) if job_status == JobStatus.COMPLETED else None

        return {
            "job_id": job_id,
            "status": job_status.value,
            "result": result,
        }
    except Exception as e:
        logger.error("Failed to get job status %s: %s", job_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status",
        )


@router.get("/{clef_id}/results")
async def get_clef_results(
    clef_id: str, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)
) -> dict:
    """
    Get execution results for a clef.

    This endpoint returns the historical execution results for a specific clef,
    including status, execution time, and metadata.

    Args:
        clef_id: ID of the clef
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip

    Returns:
        List of check execution results with pagination info
    """
    try:
        executor = get_executor()

        # Get total count
        count_result = await executor.query(
            "SELECT COUNT(*) as total FROM checks WHERE clef_id = ?",
            [clef_id],
        )
        total = count_result[0]["total"] if count_result else 0

        # Get results
        results = await executor.query(
            """
                SELECT * FROM checks
                WHERE clef_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """,
            [clef_id, limit, offset],
        )

        # Format results with consistent UTC timestamps
        import json

        from datametronome_podium.core.timestamp_utils import (
            add_timezone_info_to_response,
            to_utc_isoformat,
        )

        formatted_results = []
        for result in results:
            # Parse metadata from JSON string if it exists
            metadata = None
            if result["details"]:
                try:
                    metadata = (
                        json.loads(result["details"])
                        if isinstance(result["details"], str)
                        else result["details"]
                    )
                except (json.JSONDecodeError, TypeError):
                    metadata = result["details"]  # Keep as-is if parsing fails

            # Ensure timestamp is in UTC format
            timestamp = result["timestamp"]
            if timestamp and not timestamp.endswith("Z"):
                # Convert to UTC format if not already
                timestamp = to_utc_isoformat(timestamp)

            formatted_results.append(
                {
                    "id": result["id"],
                    "status": result["status"],
                    "message": result["message"],
                    "timestamp": timestamp,
                    "execution_time": result["execution_time"],
                    "anomalies_count": result["anomalies_count"],
                    "severity": result["severity"],
                    "metadata": metadata,
                }
            )

        response_data = {
            "clef_id": clef_id,
            "results": formatted_results,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            },
            "_timezone_info": {
                "backend_timezone": "UTC",
                "timestamp_format": "ISO 8601 with Z suffix (e.g., 2025-10-08T22:30:00Z)",
                "note": "All timestamps are stored and processed in UTC. UI converts to local timezone for display.",
            },
        }

        return response_data

    except Exception as e:
        logger.error("Failed to get results for clef %s: %s", clef_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get clef results",
        )


@router.get("/results/latest")
async def get_latest_results(limit: int = Query(20, ge=1, le=100)) -> dict:
    """
    Get the latest execution results across all clefs.

    This endpoint returns the most recent check execution results,
    useful for monitoring the overall health of data quality checks.

    Args:
        limit: Maximum number of results to return (1-100)

    Returns:
        List of latest check execution results with clef and stave info
    """
    try:
        executor = get_executor()

        # Get latest results with clef and stave info
        results = await executor.query(
            """
                SELECT
                    c.*,
                    cl.name as clef_name,
                    cl.check_type,
                    s.name as stave_name,
                    s.data_source_type
                FROM checks c
                JOIN clefs cl ON c.clef_id = cl.id
                JOIN staves s ON c.stave_id = s.id
                ORDER BY c.timestamp DESC
                LIMIT ?
            """,
            [limit],
        )

        # Format results
        import json

        formatted_results = []
        for result in results:
            metadata = None
            if result.get("details"):
                try:
                    metadata = (
                        json.loads(result["details"])
                        if isinstance(result["details"], str)
                        else result["details"]
                    )
                except (json.JSONDecodeError, TypeError):
                    metadata = result["details"]

            formatted_results.append(
                {
                    "id": result["id"],
                    "clef_id": result["clef_id"],
                    "clef_name": result["clef_name"],
                    "check_type": result["check_type"],
                    "stave_id": result["stave_id"],
                    "stave_name": result["stave_name"],
                    "data_source_type": result["data_source_type"],
                    "status": result["status"],
                    "message": result["message"],
                    "timestamp": result["timestamp"],
                    "execution_time": result["execution_time"],
                    "anomalies_count": result["anomalies_count"],
                    "severity": result["severity"],
                    "metadata": metadata,
                }
            )

        return {"results": formatted_results, "count": len(formatted_results)}

    except Exception as e:
        logger.error("Failed to get latest results: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get latest results",
        )
