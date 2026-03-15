"""Metrics endpoints for DataMetronome Podium using DataPulse connectors."""

import json as _json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from datametronome_podium.core.database import get_db
from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

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
                "sql": "SELECT COUNT(*) as count FROM staves WHERE is_active = TRUE",
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
                "sql": "SELECT COUNT(*) as count FROM clefs WHERE is_active = TRUE",
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

        # --- Intelligence metrics ---
        intelligence = await _fetch_intelligence_metrics(db)

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
            "intelligence": intelligence,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard metrics: {str(e)}",
        )


async def _fetch_intelligence_metrics(db: Any) -> Dict[str, Any]:
    """Fetch intelligence-layer metrics (health, profiles, suggestions).

    Returns an empty dict if the intelligence tables do not exist yet.
    """
    intelligence: Dict[str, Any] = {}
    try:
        # Average health score across all reports
        health_result = await db.query(
            {
                "sql": (
                    "SELECT AVG(health_score) as avg_health, COUNT(*) as report_count "
                    "FROM insight_reports"
                ),
                "params": [],
            }
        )
        if health_result:
            raw_avg = health_result[0].get("avg_health")
            intelligence["avg_health_score"] = float(round(raw_avg, 1)) if raw_avg is not None else 0
            intelligence["total_reports"] = health_result[0].get("report_count") or 0
        else:
            intelligence["avg_health_score"] = 0
            intelligence["total_reports"] = 0

        # Timestamp of the most recent report
        latest_report_result = await db.query(
            {
                "sql": "SELECT created_at, snapshot_id FROM insight_reports ORDER BY created_at DESC LIMIT 1",
                "params": [],
            }
        )
        intelligence["last_analyzed_at"] = (
            latest_report_result[0].get("created_at") if latest_report_result else None
        )

        # Latest snapshot table metrics for business KPIs
        if latest_report_result and latest_report_result[0].get("snapshot_id"):
            snap_result = await db.query(
                {
                    "sql": "SELECT table_metrics FROM baseline_snapshots WHERE id = ?",
                    "params": [latest_report_result[0]["snapshot_id"]],
                }
            )
            if snap_result:
                raw_metrics = snap_result[0].get("table_metrics", "{}")
                try:
                    table_metrics = (
                        _json.loads(raw_metrics)
                        if isinstance(raw_metrics, str)
                        else raw_metrics
                    )
                    intelligence["table_metrics"] = {
                        tbl: data.get("row_count", 0)
                        for tbl, data in table_metrics.items()
                        if isinstance(data, dict)
                    }
                except (ValueError, TypeError):
                    intelligence["table_metrics"] = {}
            else:
                intelligence["table_metrics"] = {}
        else:
            intelligence["table_metrics"] = {}

        # Profiled data sources
        profiles_result = await db.query(
            {"sql": "SELECT COUNT(*) as count FROM data_profiles", "params": []}
        )
        intelligence["profiled_sources"] = (
            profiles_result[0]["count"] if profiles_result else 0
        )

        # Pending suggestions — count + top items
        suggestions_result = await db.query(
            {
                "sql": "SELECT COUNT(*) as count FROM insight_suggestions WHERE status = 'pending'",
                "params": [],
            }
        )
        intelligence["pending_suggestions"] = (
            suggestions_result[0]["count"] if suggestions_result else 0
        )

        top_suggestions_result = await db.query(
            {
                "sql": (
                    "SELECT priority, category, action, reasoning "
                    "FROM insight_suggestions WHERE status = 'pending' "
                    "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END "
                    "LIMIT 3"
                ),
                "params": [],
            }
        )
        intelligence["top_suggestions"] = [
            {
                "priority": row.get("priority", "medium"),
                "category": row.get("category", "general"),
                "action": row.get("action", ""),
                "reasoning": row.get("reasoning", ""),
            }
            for row in (top_suggestions_result or [])
        ]

        # Anomalies from most recent reports — count + top critical items
        anomaly_reports = await db.query(
            {
                "sql": "SELECT anomalies FROM insight_reports ORDER BY created_at DESC LIMIT 5",
                "params": [],
            }
        )
        total_anomalies = 0
        critical_anomalies = 0
        top_anomalies: List[Dict[str, Any]] = []
        for row in anomaly_reports or []:
            try:
                raw = row.get("anomalies", "[]")
                anomalies_list = (
                    _json.loads(raw) if isinstance(raw, str) else raw
                )
                if isinstance(anomalies_list, list):
                    total_anomalies += len(anomalies_list)
                    for a in anomalies_list:
                        if not isinstance(a, dict):
                            continue
                        severity = a.get("severity", "")
                        if severity in ("high", "critical"):
                            critical_anomalies += 1
                            if len(top_anomalies) < 3:
                                top_anomalies.append({
                                    "severity": severity,
                                    "category": a.get("category", ""),
                                    "description": a.get("description", a.get("title", "")),
                                    "table": a.get("table", ""),
                                    "evidence": a.get("evidence", ""),
                                })
            except (ValueError, TypeError):
                pass
        intelligence["insight_anomalies"] = total_anomalies
        intelligence["critical_anomalies"] = critical_anomalies
        intelligence["top_anomalies"] = top_anomalies

    except Exception as exc:
        logger.warning("Failed to fetch intelligence metrics: %s", exc)
        intelligence = {}

    return intelligence
