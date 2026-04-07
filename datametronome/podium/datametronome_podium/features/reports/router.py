"""Report endpoints for DataMetronome Podium using DataPulse connectors."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from datametronome_podium.core.database import get_executor
from fastapi import APIRouter, HTTPException, status

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_summary_report(days: int = 7) -> dict[str, Any]:
    """Get summary report using DataPulse connector.

    Args:
        days: Number of days to look back for recent activity. Defaults to 7.

    Returns:
        Summary report data.
    """
    try:
        executor = get_executor()

        # Get basic counts — use ? placeholder with bool param; QueryAdapter
        # handles bool→int conversion for SQLite and leaves it as-is for Postgres.
        staves_count = await executor.query(
            "SELECT COUNT(*) as count FROM staves WHERE is_active = ?",
            [True],
        )
        total_staves = staves_count[0]["count"] if staves_count else 0

        clefs_count = await executor.query(
            "SELECT COUNT(*) as count FROM clefs WHERE is_active = ?",
            [True],
        )
        total_clefs = clefs_count[0]["count"] if clefs_count else 0

        checks_count = await executor.query(
            "SELECT COUNT(*) as count FROM checks",
            [],
        )
        total_checks = checks_count[0]["count"] if checks_count else 0

        # Get recent activity within the specified time period
        threshold_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        recent_checks = await executor.query(
            "SELECT * FROM checks WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 5",
            [threshold_date],
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "summary": {
                "total_staves": total_staves,
                "total_clefs": total_clefs,
                "total_checks": total_checks,
            },
            "recent_activity": recent_checks,
        }

    except Exception as e:
        logger.error("Failed to generate summary report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary report",
        )


@router.get("/quality")
async def get_quality_report(days: int = 7) -> dict[str, Any]:
    """Get data quality report using DataPulse connector.

    Args:
        days: Number of days to look back.

    Returns:
        Quality report data.
    """
    try:
        executor = get_executor()

        # Calculate date threshold
        threshold_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Get checks in the time period
        period_checks = await executor.query(
            "SELECT * FROM checks WHERE timestamp >= ? ORDER BY timestamp DESC",
            [threshold_date],
        )

        # Calculate quality metrics
        total_checks = len(period_checks)
        passed_checks = sum(1 for check in period_checks if check["status"] == "passed")
        failed_checks = total_checks - passed_checks

        quality_score = (
            (passed_checks / total_checks * 100) if total_checks > 0 else 100.0
        )

        # Get anomaly summary
        anomalies = await executor.query(
            "SELECT * FROM anomalies WHERE detected_at >= ? ORDER BY detected_at DESC",
            [threshold_date],
        )

        return {
            "period_days": days,
            "quality_score": round(quality_score, 1),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "total_anomalies": len(anomalies),
            "anomalies_by_severity": {
                "low": sum(1 for a in anomalies if a["severity"] == "low"),
                "medium": sum(1 for a in anomalies if a["severity"] == "medium"),
                "high": sum(1 for a in anomalies if a["severity"] == "high"),
                "critical": sum(1 for a in anomalies if a["severity"] == "critical"),
            },
        }

    except Exception as e:
        logger.error("Failed to generate quality report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate quality report",
        )


@router.get("/performance")
async def get_performance_report(days: int = 7) -> dict[str, Any]:
    """Get performance report using DataPulse connector.

    Args:
        days: Number of days to look back.

    Returns:
        Performance report data.
    """
    try:
        executor = get_executor()

        # Calculate date threshold
        threshold_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Get performance metrics
        performance_data = await executor.query(
            """
            SELECT
                AVG(execution_time) as avg_execution_time,
                MIN(execution_time) as min_execution_time,
                MAX(execution_time) as max_execution_time,
                COUNT(*) as total_checks
            FROM checks
            WHERE timestamp >= ? AND execution_time IS NOT NULL
            """,
            [threshold_date],
        )

        if not performance_data:
            return {
                "period_days": days,
                "message": "No performance data available for the specified period",
            }

        data = performance_data[0]

        return {
            "period_days": days,
            "execution_times_ms": {
                "average": round(data["avg_execution_time"] * 1000, 2)
                if data["avg_execution_time"]
                else 0,
                "minimum": round(data["min_execution_time"] * 1000, 2)
                if data["min_execution_time"]
                else 0,
                "maximum": round(data["max_execution_time"] * 1000, 2)
                if data["max_execution_time"]
                else 0,
            },
            "total_checks": data["total_checks"],
            "performance_trend": "stable",
        }

    except Exception as e:
        logger.error("Failed to generate performance report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate performance report",
        )
