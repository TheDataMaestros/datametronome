"""Metrics endpoints for DataMetronome Podium using DataPulse connectors."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from datametronome_podium.core.database import get_db
from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """Get system health metrics using DataPulse connector.

    Returns:
        System health metrics.
    """
    try:
        db = await get_db()

        # Get counts from database
        checks_result = await db.query(
            {"sql": "SELECT COUNT(*) as total FROM checks", "params": []}
        )
        total_checks = checks_result[0]["total"] if checks_result else 0

        passed_checks = await db.query(
            {
                "sql": "SELECT COUNT(*) as passed FROM checks WHERE status = 'passed'",
                "params": [],
            }
        )
        passed_count = passed_checks[0]["passed"] if passed_checks else 0

        failed_checks = await db.query(
            {
                "sql": "SELECT COUNT(*) as failed FROM checks WHERE status = 'failed'",
                "params": [],
            }
        )
        failed_count = failed_checks[0]["failed"] if failed_checks else 0

        anomalies_result = await db.query(
            {"sql": "SELECT COUNT(*) as total FROM anomalies", "params": []}
        )
        total_anomalies = anomalies_result[0]["total"] if anomalies_result else 0

        critical_anomalies = await db.query(
            {
                "sql": "SELECT COUNT(*) as critical FROM anomalies WHERE severity = 'critical'",
                "params": [],
            }
        )
        critical_count = critical_anomalies[0]["critical"] if critical_anomalies else 0

        # Calculate overall score
        overall_score = (
            (passed_count / total_checks * 100) if total_checks > 0 else 100.0
        )

        return {
            "overall_score": round(overall_score, 1),
            "total_checks": total_checks,
            "passed_checks": passed_count,
            "failed_checks": failed_count,
            "total_anomalies": total_anomalies,
            "critical_anomalies": critical_count,
            "status": "healthy" if overall_score >= 80 else "degraded",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch system health: {str(e)}",
        )


@router.get("/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics using DataPulse connector.

    Returns:
        Performance metrics.
    """
    try:
        db = await get_db()

        # Get average execution time
        avg_execution = await db.query(
            {
                "sql": "SELECT AVG(execution_time) as avg_time FROM checks WHERE execution_time IS NOT NULL",
                "params": [],
            }
        )
        avg_time = (
            avg_execution[0]["avg_time"]
            if avg_execution and avg_execution[0]["avg_time"]
            else 0
        )

        # Get recent check performance
        recent_checks = await db.query(
            {
                "sql": "SELECT status, execution_time FROM checks ORDER BY timestamp DESC LIMIT 10",
                "params": [],
            }
        )

        # Calculate success rate for recent checks
        recent_success = sum(
            1 for check in recent_checks if check["status"] == "passed"
        )
        recent_total = len(recent_checks)
        recent_success_rate = (
            (recent_success / recent_total * 100) if recent_total > 0 else 100.0
        )

        return {
            "average_execution_time_ms": round(avg_time * 1000, 2) if avg_time else 0,
            "recent_success_rate": round(recent_success_rate, 1),
            "recent_checks_count": recent_total,
            "performance_trend": "stable",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch performance metrics: {str(e)}",
        )


@router.get("/anomalies")
async def get_anomaly_metrics() -> Dict[str, Any]:
    """Get anomaly metrics using DataPulse connector.

    Returns:
        Anomaly metrics.
    """
    try:
        db = await get_db()

        # Get anomaly counts by severity
        severity_counts = await db.query(
            {
                "sql": "SELECT severity, COUNT(*) as count FROM anomalies GROUP BY severity",
                "params": [],
            }
        )

        # Get anomaly counts by type
        type_counts = await db.query(
            {
                "sql": "SELECT anomaly_type, COUNT(*) as count FROM anomalies GROUP BY anomaly_type",
                "params": [],
            }
        )

        # Get resolution status counts
        resolution_counts = await db.query(
            {
                "sql": "SELECT resolution_status, COUNT(*) as count FROM anomalies GROUP BY resolution_status",
                "params": [],
            }
        )

        return {
            "by_severity": {
                item["severity"]: item["count"] for item in severity_counts
            },
            "by_type": {item["anomaly_type"]: item["count"] for item in type_counts},
            "by_resolution": {
                item["resolution_status"]: item["count"] for item in resolution_counts
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch anomaly metrics: {str(e)}",
        )


@router.get("/dashboard")
async def get_dashboard_metrics() -> Dict[str, Any]:
    """Get comprehensive dashboard metrics for the home page.

    Returns:
        Dashboard metrics including success rate, sources, checks, anomalies, and distribution.
    """
    try:
        db = await get_db()

        # Calculate time thresholds
        now = datetime.now(timezone.utc)
        last_24h = (now - timedelta(hours=24)).isoformat()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        # Get total and active staves
        total_staves_result = await db.query(
            {"sql": "SELECT COUNT(*) as count FROM staves", "params": []}
        )
        total_staves = total_staves_result[0]["count"] if total_staves_result else 0

        active_staves_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM staves WHERE is_active = 1",
                "params": [],
            }
        )
        active_staves = active_staves_result[0]["count"] if active_staves_result else 0

        # Get total and active clefs (quality checks)
        total_clefs_result = await db.query(
            {"sql": "SELECT COUNT(*) as count FROM clefs", "params": []}
        )
        total_clefs = total_clefs_result[0]["count"] if total_clefs_result else 0

        active_clefs_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM clefs WHERE is_active = 1",
                "params": [],
            }
        )
        active_clefs = active_clefs_result[0]["count"] if active_clefs_result else 0

        # Get scheduled clefs count (clefs with schedule)
        scheduled_clefs_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM clefs WHERE schedule IS NOT NULL AND schedule != ''",
                "params": [],
            }
        )
        scheduled_clefs = (
            scheduled_clefs_result[0]["count"] if scheduled_clefs_result else 0
        )

        # Get all checks count
        all_checks_result = await db.query(
            {"sql": "SELECT COUNT(*) as count FROM checks", "params": []}
        )
        all_checks_count = all_checks_result[0]["count"] if all_checks_result else 0

        # Get checks from last 24 hours
        checks_24h_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM checks WHERE timestamp >= ?",
                "params": [last_24h],
            }
        )
        checks_24h = checks_24h_result[0]["count"] if checks_24h_result else 0

        # Calculate success rate (all time)
        passed_checks_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM checks WHERE status = 'passed'",
                "params": [],
            }
        )
        passed_checks = (
            passed_checks_result[0]["count"] if passed_checks_result else 0
        )
        success_rate = (
            (passed_checks / all_checks_count * 100) if all_checks_count > 0 else 100.0
        )

        # Calculate success rate for today
        today_passed_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM checks WHERE status = 'passed' AND timestamp >= ?",
                "params": [today_start],
            }
        )
        today_passed = today_passed_result[0]["count"] if today_passed_result else 0

        today_total_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM checks WHERE timestamp >= ?",
                "params": [today_start],
            }
        )
        today_total = today_total_result[0]["count"] if today_total_result else 0
        today_success_rate = (
            (today_passed / today_total * 100) if today_total > 0 else 100.0
        )

        # Calculate success rate for yesterday
        yesterday_start = (now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        yesterday_passed_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM checks WHERE status = 'passed' AND timestamp >= ? AND timestamp < ?",
                "params": [yesterday_start, yesterday_end],
            }
        )
        yesterday_passed = (
            yesterday_passed_result[0]["count"] if yesterday_passed_result else 0
        )

        yesterday_total_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM checks WHERE timestamp >= ? AND timestamp < ?",
                "params": [yesterday_start, yesterday_end],
            }
        )
        yesterday_total = (
            yesterday_total_result[0]["count"] if yesterday_total_result else 0
        )
        yesterday_success_rate = (
            (yesterday_passed / yesterday_total * 100) if yesterday_total > 0 else 100.0
        )

        # Calculate success rate change
        success_rate_change = today_success_rate - yesterday_success_rate

        # Get anomalies from last 24 hours
        anomalies_24h_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM anomalies WHERE detected_at >= ?",
                "params": [last_24h],
            }
        )
        anomalies_24h = (
            anomalies_24h_result[0]["count"] if anomalies_24h_result else 0
        )

        # Get check status distribution (all time)
        status_distribution_result = await db.query(
            {
                "sql": "SELECT status, COUNT(*) as count FROM checks GROUP BY status",
                "params": [],
            }
        )
        status_distribution = {
            item["status"]: item["count"] for item in status_distribution_result
        }

        # Calculate percentages for distribution
        total_for_distribution = sum(status_distribution.values())
        distribution_percentages = {}
        if total_for_distribution > 0:
            distribution_percentages = {
                "passed": round(
                    (status_distribution.get("passed", 0) / total_for_distribution) * 100,
                    1,
                ),
                "failed": round(
                    (status_distribution.get("failed", 0) / total_for_distribution) * 100,
                    1,
                ),
                "warning": round(
                    (status_distribution.get("warning", 0) / total_for_distribution) * 100,
                    1,
                ),
            }

        return {
            "success_rate": round(success_rate, 1),
            "success_rate_change": round(success_rate_change, 1),
            "active_sources": active_staves,
            "total_sources": total_staves,
            "active_checks": active_clefs,
            "scheduled_checks": scheduled_clefs,
            "anomalies": anomalies_24h,
            "distribution": distribution_percentages,
            "total_checks": all_checks_count,
            "checks_24h": checks_24h,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard metrics: {str(e)}",
        )
