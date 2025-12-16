"""
Clef action endpoints - Run now and view results functionality.

This module provides endpoints for executing clefs immediately and viewing
their execution results.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from datametronome_podium.core.database import get_db, insert_data
from datametronome_podium.services.clef_executor import ClefExecutor
from datametronome_podium.services.connection_tester import ConnectionTester
from datametronome_podium.services.stave_service import (
    deserialize_clef,
    deserialize_stave,
)
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{clef_id}/run-now")
async def run_clef_now(clef_id: str) -> Dict[str, Any]:
    """
    Execute a clef immediately.

    This endpoint runs a data quality check immediately, bypassing the schedule.
    It returns the execution result with status, observed value, and metadata.

    Args:
        clef_id: ID of the clef to execute

    Returns:
        Check execution result with status, message, and metadata

    Example Response:
        {
            "success": true,
            "clef_id": "clef-email-check-001",
            "stave_id": "stave-prod-db-001",
            "status": "pass",
            "observed_value": 0.02,
            "message": "Email null rate within acceptable limits",
            "execution_time": 0.456,
            "metadata": {
                "table": "users",
                "column": "email",
                "total_rows": 10000,
                "null_rows": 200
            }
        }
    """
    try:
        # Get the clef and its stave from database
        db = await get_db()

        # Get clef
        clefs = await db.query(
            {"sql": "SELECT * FROM clefs WHERE id = ?", "params": [clef_id]}
        )

        if not clefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clef not found"
            )

        clef = deserialize_clef(clefs[0])

        # Get stave
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [clef.stave_id]}
        )

        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated stave not found",
            )

        stave = deserialize_stave(staves[0])

        # Execute the clef
        executor = ClefExecutor()
        result = await executor.execute_clef(clef, stave)

        # Store the result in database
        import json

        # Persist metadata in checks.details, and always include observed_value so the UI can chart it.
        metadata_for_storage = dict(result.metadata or {})
        metadata_for_storage["observed_value"] = result.observed_value

        check_data = {
            "id": f"check-{clef_id}-{datetime.utcnow().isoformat()}",
            "stave_id": stave.id,
            "clef_id": clef.id,
            "check_type": clef.check_type,
            "status": result.status,
            "message": result.message,
            "details": json.dumps(metadata_for_storage)
            if metadata_for_storage
            else None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "execution_time": result.execution_time,
            "anomalies_count": result.anomalies_count,
            "severity": result.severity.value,  # Store the severity value: "harmony", "dissonance", "cacophony"
        }

        await insert_data("checks", check_data)

        # Log the execution
        logger.info(f"Clef {clef_id} executed: {result.status}")

        return {
            "success": True,
            "clef_id": clef.id,
            "stave_id": stave.id,
            "status": result.status,
            "observed_value": result.observed_value,
            "message": result.message,
            "execution_time": result.execution_time,
            "metadata": result.metadata,
            "check_id": check_data["id"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clef execution failed for {clef_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clef execution failed: {str(e)}",
        )


@router.get("/{clef_id}/results")
async def get_clef_results(
    clef_id: str, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
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
        db = await get_db()

        # Get total count
        count_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as total FROM checks WHERE clef_id = ?",
                "params": [clef_id],
            }
        )
        total = count_result[0]["total"] if count_result else 0

        # Get results
        results = await db.query(
            {
                "sql": """
                SELECT * FROM checks
                WHERE clef_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """,
                "params": [clef_id, limit, offset],
            }
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
        logger.error(f"Failed to get results for clef {clef_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clef results: {str(e)}",
        )


@router.get("/results/latest")
async def get_latest_results(limit: int = Query(20, ge=1, le=100)) -> Dict[str, Any]:
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
        db = await get_db()

        # Get latest results with clef and stave info
        results = await db.query(
            {
                "sql": """
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
                "params": [limit],
            }
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
        logger.error(f"Failed to get latest results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest results: {str(e)}",
        )
