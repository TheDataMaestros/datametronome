"""Metrics endpoints for DataMetronome Podium using DataPulse connectors."""

import json as _json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from datametronome_podium.core.database import get_executor
from datametronome_podium.core.query import QueryExecutor
from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def get_system_health() -> dict:
    """Get system health metrics using DataPulse connector.

    Returns:
        System health metrics.
    """
    try:
        executor = get_executor()

        # Get counts from database
        checks_result = await executor.query("SELECT COUNT(*) as total FROM checks", [])
        total_checks = checks_result[0]["total"] if checks_result else 0

        passed_checks = await executor.query(
            "SELECT COUNT(*) as passed FROM checks WHERE status = 'passed'", []
        )
        passed_count = passed_checks[0]["passed"] if passed_checks else 0

        failed_checks = await executor.query(
            "SELECT COUNT(*) as failed FROM checks WHERE status = 'failed'", []
        )
        failed_count = failed_checks[0]["failed"] if failed_checks else 0

        anomalies_result = await executor.query("SELECT COUNT(*) as total FROM anomalies", [])
        total_anomalies = anomalies_result[0]["total"] if anomalies_result else 0

        critical_anomalies = await executor.query(
            "SELECT COUNT(*) as critical FROM anomalies WHERE severity = 'critical'", []
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
        logger.error("Failed to fetch system health: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch system health",
        )


@router.get("/performance")
async def get_performance_metrics() -> dict:
    """Get performance metrics using DataPulse connector.

    Returns:
        Performance metrics.
    """
    try:
        executor = get_executor()

        # Get average execution time
        avg_execution = await executor.query(
            "SELECT AVG(execution_time) as avg_time FROM checks WHERE execution_time IS NOT NULL", []
        )
        avg_time = (
            avg_execution[0]["avg_time"]
            if avg_execution and avg_execution[0]["avg_time"]
            else 0
        )

        # Get recent check performance
        recent_checks = await executor.query(
            "SELECT status, execution_time FROM checks ORDER BY timestamp DESC LIMIT 10", []
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
        logger.error("Failed to fetch performance metrics: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch performance metrics",
        )


@router.get("/anomalies")
async def get_anomaly_metrics() -> dict:
    """Get anomaly metrics using DataPulse connector.

    Returns:
        Anomaly metrics.
    """
    try:
        executor = get_executor()

        # Get anomaly counts by severity
        severity_counts = await executor.query(
            "SELECT severity, COUNT(*) as count FROM anomalies GROUP BY severity", []
        )

        # Get anomaly counts by type
        type_counts = await executor.query(
            "SELECT anomaly_type, COUNT(*) as count FROM anomalies GROUP BY anomaly_type", []
        )

        # Get resolution status counts
        resolution_counts = await executor.query(
            "SELECT resolution_status, COUNT(*) as count FROM anomalies GROUP BY resolution_status", []
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
        logger.error("Failed to fetch anomaly metrics: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch anomaly metrics",
        )


@router.get("/dashboard")
async def get_dashboard_metrics() -> dict:
    """Get comprehensive dashboard metrics for the home page.

    Returns:
        Dashboard metrics including success rate, sources, checks, anomalies, and distribution.
    """
    try:
        executor = get_executor()

        # Calculate time thresholds
        now = datetime.now(timezone.utc)
        last_24h = (now - timedelta(hours=24)).isoformat()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        # Get total and active staves
        total_staves_result = await executor.query("SELECT COUNT(*) as count FROM staves", [])
        total_staves = total_staves_result[0]["count"] if total_staves_result else 0

        active_staves_result = await executor.query(
            "SELECT COUNT(*) as count FROM staves WHERE is_active = TRUE", []
        )
        active_staves = active_staves_result[0]["count"] if active_staves_result else 0

        # Get total and active clefs (quality checks)
        total_clefs_result = await executor.query("SELECT COUNT(*) as count FROM clefs", [])
        total_clefs = total_clefs_result[0]["count"] if total_clefs_result else 0

        active_clefs_result = await executor.query(
            "SELECT COUNT(*) as count FROM clefs WHERE is_active = TRUE", []
        )
        active_clefs = active_clefs_result[0]["count"] if active_clefs_result else 0

        # Get scheduled clefs count (clefs with schedule)
        scheduled_clefs_result = await executor.query(
            "SELECT COUNT(*) as count FROM clefs WHERE schedule IS NOT NULL AND schedule != ''", []
        )
        scheduled_clefs = (
            scheduled_clefs_result[0]["count"] if scheduled_clefs_result else 0
        )

        # Get all checks count
        all_checks_result = await executor.query("SELECT COUNT(*) as count FROM checks", [])
        all_checks_count = all_checks_result[0]["count"] if all_checks_result else 0

        # Get checks from last 24 hours
        checks_24h_result = await executor.query(
            "SELECT COUNT(*) as count FROM checks WHERE timestamp >= ?", [last_24h]
        )
        checks_24h = checks_24h_result[0]["count"] if checks_24h_result else 0

        # Calculate success rate (all time)
        passed_checks_result = await executor.query(
            "SELECT COUNT(*) as count FROM checks WHERE status = 'passed'", []
        )
        passed_checks = (
            passed_checks_result[0]["count"] if passed_checks_result else 0
        )
        success_rate = (
            (passed_checks / all_checks_count * 100) if all_checks_count > 0 else 100.0
        )

        # Calculate success rate for today
        today_passed_result = await executor.query(
            "SELECT COUNT(*) as count FROM checks WHERE status = 'passed' AND timestamp >= ?",
            [today_start],
        )
        today_passed = today_passed_result[0]["count"] if today_passed_result else 0

        today_total_result = await executor.query(
            "SELECT COUNT(*) as count FROM checks WHERE timestamp >= ?", [today_start]
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

        yesterday_passed_result = await executor.query(
            "SELECT COUNT(*) as count FROM checks WHERE status = 'passed' AND timestamp >= ? AND timestamp < ?",
            [yesterday_start, yesterday_end],
        )
        yesterday_passed = (
            yesterday_passed_result[0]["count"] if yesterday_passed_result else 0
        )

        yesterday_total_result = await executor.query(
            "SELECT COUNT(*) as count FROM checks WHERE timestamp >= ? AND timestamp < ?",
            [yesterday_start, yesterday_end],
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
        anomalies_24h_result = await executor.query(
            "SELECT COUNT(*) as count FROM anomalies WHERE detected_at >= ?", [last_24h]
        )
        anomalies_24h = (
            anomalies_24h_result[0]["count"] if anomalies_24h_result else 0
        )

        # Get check status distribution (all time)
        status_distribution_result = await executor.query(
            "SELECT status, COUNT(*) as count FROM checks GROUP BY status", []
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
        intelligence = await _fetch_intelligence_metrics(executor)

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
        logger.error("Failed to fetch dashboard metrics: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard metrics",
        )


async def _fetch_intelligence_metrics(executor: QueryExecutor) -> dict[str, Any]:
    """Fetch intelligence-layer metrics (health, profiles, suggestions).

    Returns an empty dict if the intelligence tables do not exist yet.
    """
    intelligence: dict[str, Any] = {}
    try:
        # Average health score across all reports
        health_result = await executor.query(
            "SELECT AVG(health_score) as avg_health, COUNT(*) as report_count FROM insight_reports",
            [],
        )
        if health_result:
            raw_avg = health_result[0].get("avg_health")
            intelligence["avg_health_score"] = float(round(raw_avg, 1)) if raw_avg is not None else 0
            intelligence["total_reports"] = health_result[0].get("report_count") or 0
        else:
            intelligence["avg_health_score"] = 0
            intelligence["total_reports"] = 0

        # Timestamp of the most recent report
        latest_report_result = await executor.query(
            "SELECT created_at, snapshot_id FROM insight_reports ORDER BY created_at DESC LIMIT 1",
            [],
        )
        intelligence["last_analyzed_at"] = (
            latest_report_result[0].get("created_at") if latest_report_result else None
        )

        # Latest snapshot table metrics for business KPIs
        if latest_report_result and latest_report_result[0].get("snapshot_id"):
            snap_result = await executor.query(
                "SELECT table_metrics FROM baseline_snapshots WHERE id = ?",
                [latest_report_result[0]["snapshot_id"]],
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
        profiles_result = await executor.query("SELECT COUNT(*) as count FROM data_profiles", [])
        intelligence["profiled_sources"] = (
            profiles_result[0]["count"] if profiles_result else 0
        )

        # Health score for each stave — only staves with at least one report
        stave_scores_result = await executor.query(
            "SELECT ir.stave_id, MAX(ir.health_score) AS health_score "
            "FROM insight_reports ir "
            "JOIN staves st ON ir.stave_id = st.id "
            "WHERE st.is_active = TRUE "
            "GROUP BY ir.stave_id",
            [],
        )
        intelligence["stave_health_scores"] = {
            row["stave_id"]: int(row["health_score"])
            for row in (stave_scores_result or [])
            if row.get("stave_id") and row.get("health_score") is not None
        }

        # Pending suggestions — count + top items
        suggestions_result = await executor.query(
            "SELECT COUNT(*) as count FROM insight_suggestions WHERE status = 'pending'", []
        )
        intelligence["pending_suggestions"] = (
            suggestions_result[0]["count"] if suggestions_result else 0
        )

        top_suggestions_result = await executor.query(
            "SELECT s.priority, s.category, s.action, s.reasoning, "
            "s.stave_id, st.name AS stave_name "
            "FROM insight_suggestions s "
            "LEFT JOIN staves st ON s.stave_id = st.id "
            "WHERE s.status = 'pending' "
            "ORDER BY CASE s.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END "
            "LIMIT 3",
            [],
        )
        intelligence["top_suggestions"] = [
            {
                "priority": row.get("priority", "medium"),
                "category": row.get("category", "general"),
                "action": row.get("action", ""),
                "reasoning": row.get("reasoning", ""),
                "stave_id": row.get("stave_id", ""),
                "stave_name": row.get("stave_name") or row.get("stave_id", ""),
            }
            for row in (top_suggestions_result or [])
        ]

        # Anomalies from most recent reports — count + top critical items
        # Include created_at + snapshot's captured_at so UI can show "detected at / last snapshot"
        anomaly_reports = await executor.query(
            "SELECT r.anomalies, r.stave_id, st.name AS stave_name, "
            "r.created_at AS report_at, s.captured_at AS snapshot_at "
            "FROM insight_reports r "
            "LEFT JOIN baseline_snapshots s ON r.snapshot_id = s.id "
            "LEFT JOIN staves st ON r.stave_id = st.id "
            "ORDER BY r.created_at DESC LIMIT 5",
            [],
        )
        total_anomalies = 0
        critical_anomalies = 0
        top_anomalies: list[dict[str, Any]] = []
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
                                    "detected_at": row.get("report_at"),
                                    "snapshot_at": row.get("snapshot_at"),
                                    "stave_id": row.get("stave_id", ""),
                                    "stave_name": row.get("stave_name") or row.get("stave_id", ""),
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
