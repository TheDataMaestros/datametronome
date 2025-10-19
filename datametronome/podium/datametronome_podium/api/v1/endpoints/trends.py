"""Trends endpoints for DataMetronome Podium using DataPulse connectors."""

from typing import Any, List, Dict, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status, Query

from datametronome_podium.core.database import get_db

router = APIRouter()


@router.get("/stave/{stave_id}")
async def get_stave_trends(
    stave_id: str,
    days: int = Query(7, description="Number of days to look back"),
    granularity: str = Query("hour", description="Data granularity: hour, day, week")
) -> Dict[str, Any]:
    """Get trends data for a specific stave.
    
    Args:
        stave_id: The stave ID to analyze.
        days: Number of days to look back.
        granularity: Data granularity for grouping.
        
    Returns:
        Trends data including row counts, check results, and distribution changes.
    """
    try:
        db = await get_db()
        
        # Validate stave exists
        stave_result = await db.query({
            "sql": "SELECT * FROM staves WHERE id = ? AND is_active = 1",
            "params": [stave_id]
        })
        
        if not stave_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stave {stave_id} not found or inactive"
            )
        
        stave = stave_result[0]
        
        # Calculate date threshold
        threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Determine time grouping based on granularity
        time_grouping = {
            "hour": "%Y-%m-%d %H:00:00",
            "day": "%Y-%m-%d 00:00:00",
            "week": "%Y-%m-%d 00:00:00"
        }.get(granularity, "%Y-%m-%d %H:00:00")
        
        # Get check results over time for this stave
        checks_query = f"""
            SELECT 
                strftime('{time_grouping}', timestamp) as time_bucket,
                check_type,
                status,
                COUNT(*) as check_count,
                AVG(execution_time) as avg_execution_time,
                SUM(anomalies_count) as total_anomalies
            FROM checks 
            WHERE stave_id = ? AND timestamp >= ?
            GROUP BY time_bucket, check_type, status
            ORDER BY time_bucket DESC
        """
        
        checks_result = await db.query({
            "sql": checks_query,
            "params": [stave_id, threshold_date]
        })
        
        # Get row count trends (from volume_check type checks)
        row_count_query = f"""
            SELECT 
                strftime('{time_grouping}', timestamp) as time_bucket,
                details,
                status,
                timestamp
            FROM checks 
            WHERE stave_id = ? 
                AND check_type = 'row_count' 
                AND timestamp >= ?
            ORDER BY timestamp DESC
        """
        
        row_count_result = await db.query({
            "sql": row_count_query,
            "params": [stave_id, threshold_date]
        })
        
        # Process row count data to extract actual counts
        row_count_trends = []
        for row in row_count_result:
            try:
                # Parse details JSON to extract row count
                import json
                details = json.loads(row["details"]) if row["details"] else {}
                observed_value = details.get("row_count", 0)
                
                row_count_trends.append({
                    "timestamp": row["time_bucket"],
                    "row_count": observed_value,
                    "status": row["status"],
                    "raw_timestamp": row["timestamp"]
                })
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Calculate distribution changes
        distribution_changes = await _calculate_distribution_changes(db, stave_id, days)
        
        # Get recent anomalies for this stave
        anomalies_query = """
            SELECT 
                a.*,
                c.timestamp as check_timestamp,
                c.check_type
            FROM anomalies a
            JOIN checks c ON a.check_id = c.id
            WHERE c.stave_id = ? AND a.detected_at >= ?
            ORDER BY a.detected_at DESC
            LIMIT 10
        """
        
        anomalies_result = await db.query({
            "sql": anomalies_query,
            "params": [stave_id, threshold_date]
        })
        
        # Calculate trend summary
        trend_summary = await _calculate_trend_summary(checks_result, row_count_trends)
        
        return {
            "stave": {
                "id": stave["id"],
                "name": stave["name"],
                "data_source_type": stave["data_source_type"]
            },
            "period": {
                "days": days,
                "granularity": granularity,
                "start_date": threshold_date,
                "end_date": datetime.now().isoformat()
            },
            "row_count_trends": row_count_trends,
            "check_results": checks_result,
            "distribution_changes": distribution_changes,
            "recent_anomalies": anomalies_result,
            "trend_summary": trend_summary
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trends data: {str(e)}"
        )


@router.get("/overview")
async def get_trends_overview(
    days: int = Query(7, description="Number of days to look back")
) -> Dict[str, Any]:
    """Get trends overview across all active staves.
    
    Args:
        days: Number of days to look back.
        
    Returns:
        Overview trends data for all staves.
    """
    try:
        db = await get_db()
        
        # Calculate date threshold
        threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get all active staves
        staves_result = await db.query({
            "sql": "SELECT * FROM staves WHERE is_active = 1 ORDER BY name",
            "params": []
        })
        
        # Get summary data for each stave
        stave_summaries = []
        for stave in staves_result:
            # Get recent check counts
            check_counts = await db.query({
                "sql": """
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM checks 
                    WHERE stave_id = ? AND timestamp >= ?
                    GROUP BY status
                """,
                "params": [stave["id"], threshold_date]
            })
            
            # Get latest row count
            latest_row_count = await db.query({
                "sql": """
                    SELECT details, timestamp
                    FROM checks 
                    WHERE stave_id = ? 
                        AND check_type = 'row_count' 
                        AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """,
                "params": [stave["id"], threshold_date]
            })
            
            latest_count = 0
            if latest_row_count:
                try:
                    import json
                    details = json.loads(latest_row_count[0]["details"]) if latest_row_count[0]["details"] else {}
                    latest_count = details.get("observed_value", 0)
                except (json.JSONDecodeError, KeyError):
                    pass
            
            stave_summaries.append({
                "stave": {
                    "id": stave["id"],
                    "name": stave["name"],
                    "data_source_type": stave["data_source_type"]
                },
                "check_counts": {item["status"]: item["count"] for item in check_counts},
                "latest_row_count": latest_count,
                "last_check": latest_row_count[0]["timestamp"] if latest_row_count else None
            })
        
        return {
            "period": {
                "days": days,
                "start_date": threshold_date,
                "end_date": datetime.now().isoformat()
            },
            "stave_summaries": stave_summaries,
            "total_staves": len(staves_result)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trends overview: {str(e)}"
        )


async def _calculate_distribution_changes(db, stave_id: str, days: int) -> Dict[str, Any]:
    """Calculate distribution changes for a stave."""
    try:
        threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get check results for the period
        checks_result = await db.query({
            "sql": """
                SELECT 
                    check_type,
                    status,
                    COUNT(*) as count,
                    AVG(execution_time) as avg_execution_time
                FROM checks 
                WHERE stave_id = ? AND timestamp >= ?
                GROUP BY check_type, status
            """,
            "params": [stave_id, threshold_date]
        })
        
        # Calculate distribution metrics
        total_checks = sum(item["count"] for item in checks_result)
        status_distribution = {}
        check_type_distribution = {}
        
        for item in checks_result:
            status = item["status"]
            check_type = item["check_type"]
            
            if status not in status_distribution:
                status_distribution[status] = 0
            status_distribution[status] += item["count"]
            
            if check_type not in check_type_distribution:
                check_type_distribution[check_type] = {"total": 0, "passed": 0, "failed": 0}
            check_type_distribution[check_type]["total"] += item["count"]
            check_type_distribution[check_type][status] = item["count"]
        
        # Calculate percentages
        status_percentages = {
            status: (count / total_checks * 100) if total_checks > 0 else 0
            for status, count in status_distribution.items()
        }
        
        return {
            "status_distribution": status_distribution,
            "status_percentages": status_percentages,
            "check_type_distribution": check_type_distribution,
            "total_checks": total_checks
        }
        
    except Exception as e:
        return {"error": f"Failed to calculate distribution changes: {str(e)}"}


async def _calculate_trend_summary(checks_result: List[Dict], row_count_trends: List[Dict]) -> Dict[str, Any]:
    """Calculate trend summary from check results and row count trends."""
    try:
        # Calculate check success rate trend
        if checks_result:
            total_checks = sum(item["check_count"] for item in checks_result)
            passed_checks = sum(
                item["check_count"] for item in checks_result 
                if item["status"] == "pass"
            )
            success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 100.0
        else:
            success_rate = 100.0
        
        # Calculate row count trend
        row_count_trend = "stable"
        if len(row_count_trends) >= 2:
            recent_counts = [item["row_count"] for item in row_count_trends[:3]]
            older_counts = [item["row_count"] for item in row_count_trends[-3:]]
            
            if recent_counts and older_counts:
                recent_avg = sum(recent_counts) / len(recent_counts)
                older_avg = sum(older_counts) / len(older_counts)
                
                if recent_avg > older_avg * 1.1:
                    row_count_trend = "increasing"
                elif recent_avg < older_avg * 0.9:
                    row_count_trend = "decreasing"
        
        return {
            "success_rate": round(success_rate, 1),
            "row_count_trend": row_count_trend,
            "total_data_points": len(row_count_trends),
            "overall_status": "healthy" if success_rate >= 80 else "degraded"
        }
        
    except Exception as e:
        return {
            "success_rate": 0.0,
            "row_count_trend": "unknown",
            "total_data_points": 0,
            "overall_status": "error",
            "error": str(e)
        }
