"""Report endpoints for DataMetronome Podium using DataPulse connectors."""

from typing import Any, List, Dict
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status

from datametronome_podium.core.database import get_db

router = APIRouter()


@router.get("/summary")
async def get_summary_report() -> Dict[str, Any]:
    """Get summary report using DataPulse connector.
    
    Returns:
        Summary report data.
    """
    try:
        db = await get_db()
        
        # Get basic counts
        staves_count = await db.query({
            "sql": "SELECT COUNT(*) as count FROM staves WHERE is_active = 1",
            "params": []
        })
        total_staves = staves_count[0]["count"] if staves_count else 0
        
        clefs_count = await db.query({
            "sql": "SELECT COUNT(*) as count FROM clefs WHERE is_active = 1",
            "params": []
        })
        total_clefs = clefs_count[0]["count"] if clefs_count else 0
        
        checks_count = await db.query({
            "sql": "SELECT COUNT(*) as count FROM checks",
            "params": []
        })
        total_checks = checks_count[0]["count"] if checks_count else 0
        
        # Get recent activity
        recent_checks = await db.query({
            "sql": "SELECT * FROM checks ORDER BY timestamp DESC LIMIT 5",
            "params": []
        })
        
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_staves": total_staves,
                "total_clefs": total_clefs,
                "total_checks": total_checks
            },
            "recent_activity": recent_checks
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary report: {str(e)}"
        )


@router.get("/quality")
async def get_quality_report(days: int = 7) -> Dict[str, Any]:
    """Get data quality report using DataPulse connector.
    
    Args:
        days: Number of days to look back.
        
    Returns:
        Quality report data.
    """
    try:
        db = await get_db()
        
        # Calculate date threshold
        threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get checks in the time period
        period_checks = await db.query({
            "sql": "SELECT * FROM checks WHERE timestamp >= ? ORDER BY timestamp DESC",
            "params": [threshold_date]
        })
        
        # Calculate quality metrics
        total_checks = len(period_checks)
        passed_checks = sum(1 for check in period_checks if check["status"] == "passed")
        failed_checks = total_checks - passed_checks
        
        quality_score = (passed_checks / total_checks * 100) if total_checks > 0 else 100.0
        
        # Get anomaly summary
        anomalies = await db.query({
            "sql": "SELECT * FROM anomalies WHERE detected_at >= ? ORDER BY detected_at DESC",
            "params": [threshold_date]
        })
        
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
                "critical": sum(1 for a in anomalies if a["severity"] == "critical")
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quality report: {str(e)}"
        )


@router.get("/performance")
async def get_performance_report(days: int = 7) -> Dict[str, Any]:
    """Get performance report using DataPulse connector.
    
    Args:
        days: Number of days to look back.
        
    Returns:
        Performance report data.
    """
    try:
        db = await get_db()
        
        # Calculate date threshold
        threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get performance metrics
        performance_data = await db.query({
            "sql": """
                SELECT 
                    AVG(execution_time) as avg_execution_time,
                    MIN(execution_time) as min_execution_time,
                    MAX(execution_time) as max_execution_time,
                    COUNT(*) as total_checks
                FROM checks 
                WHERE timestamp >= ? AND execution_time IS NOT NULL
            """,
            "params": [threshold_date]
        })
        
        if not performance_data:
            return {
                "period_days": days,
                "message": "No performance data available for the specified period"
            }
        
        data = performance_data[0]
        
        return {
            "period_days": days,
            "execution_times_ms": {
                "average": round(data["avg_execution_time"] * 1000, 2) if data["avg_execution_time"] else 0,
                "minimum": round(data["min_execution_time"] * 1000, 2) if data["min_execution_time"] else 0,
                "maximum": round(data["max_execution_time"] * 1000, 2) if data["max_execution_time"] else 0
            },
            "total_checks": data["total_checks"],
            "performance_trend": "stable"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance report: {str(e)}"
        )
