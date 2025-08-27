"""Metrics endpoints for DataMetronome Podium using DataPulse connectors."""

from typing import Any, List, Dict

from fastapi import APIRouter, HTTPException, status

from datametronome_podium.core.database import get_db

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
        checks_result = await db.query({
            "sql": "SELECT COUNT(*) as total FROM checks",
            "params": []
        })
        total_checks = checks_result[0]["total"] if checks_result else 0
        
        passed_checks = await db.query({
            "sql": "SELECT COUNT(*) as passed FROM checks WHERE status = 'passed'",
            "params": []
        })
        passed_count = passed_checks[0]["passed"] if passed_checks else 0
        
        failed_checks = await db.query({
            "sql": "SELECT COUNT(*) as failed FROM checks WHERE status = 'failed'",
            "params": []
        })
        failed_count = failed_checks[0]["failed"] if failed_checks else 0
        
        anomalies_result = await db.query({
            "sql": "SELECT COUNT(*) as total FROM anomalies",
            "params": []
        })
        total_anomalies = anomalies_result[0]["total"] if anomalies_result else 0
        
        critical_anomalies = await db.query({
            "sql": "SELECT COUNT(*) as critical FROM anomalies WHERE severity = 'critical'",
            "params": []
        })
        critical_count = critical_anomalies[0]["critical"] if critical_anomalies else 0
        
        # Calculate overall score
        overall_score = (passed_count / total_checks * 100) if total_checks > 0 else 100.0
        
        return {
            "overall_score": round(overall_score, 1),
            "total_checks": total_checks,
            "passed_checks": passed_count,
            "failed_checks": failed_count,
            "total_anomalies": total_anomalies,
            "critical_anomalies": critical_count,
            "status": "healthy" if overall_score >= 80 else "degraded"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch system health: {str(e)}"
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
        avg_execution = await db.query({
            "sql": "SELECT AVG(execution_time) as avg_time FROM checks WHERE execution_time IS NOT NULL",
            "params": []
        })
        avg_time = avg_execution[0]["avg_time"] if avg_execution and avg_execution[0]["avg_time"] else 0
        
        # Get recent check performance
        recent_checks = await db.query({
            "sql": "SELECT status, execution_time FROM checks ORDER BY timestamp DESC LIMIT 10",
            "params": []
        })
        
        # Calculate success rate for recent checks
        recent_success = sum(1 for check in recent_checks if check["status"] == "passed")
        recent_total = len(recent_checks)
        recent_success_rate = (recent_success / recent_total * 100) if recent_total > 0 else 100.0
        
        return {
            "average_execution_time_ms": round(avg_time * 1000, 2) if avg_time else 0,
            "recent_success_rate": round(recent_success_rate, 1),
            "recent_checks_count": recent_total,
            "performance_trend": "stable"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch performance metrics: {str(e)}"
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
        severity_counts = await db.query({
            "sql": "SELECT severity, COUNT(*) as count FROM anomalies GROUP BY severity",
            "params": []
        })
        
        # Get anomaly counts by type
        type_counts = await db.query({
            "sql": "SELECT anomaly_type, COUNT(*) as count FROM anomalies GROUP BY anomaly_type",
            "params": []
        })
        
        # Get resolution status counts
        resolution_counts = await db.query({
            "sql": "SELECT resolution_status, COUNT(*) as count FROM anomalies GROUP BY resolution_status",
            "params": []
        })
        
        return {
            "by_severity": {item["severity"]: item["count"] for item in severity_counts},
            "by_type": {item["anomaly_type"]: item["count"] for item in type_counts},
            "by_resolution": {item["resolution_status"]: item["count"] for item in resolution_counts}
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch anomaly metrics: {str(e)}"
        )
