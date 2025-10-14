"""
Clef Scheduler Service for DataMetronome Podium.

This service handles scheduling clefs for automatic execution based on their cron expressions.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from datametronome_podium.core.database import get_db
from datametronome_podium.core.scheduler import add_scheduled_job, remove_scheduled_job, get_scheduler_status
from datametronome_podium.services.clef_executor import ClefExecutor
from datametronome_podium.services.stave_service import deserialize_clef, deserialize_stave
from datametronome_podium.api.schemas.clef import ClefResponse

logger = logging.getLogger(__name__)


async def execute_scheduled_clef(clef_id: str) -> Dict[str, Any]:
    """
    Execute a clef on schedule and store the result.
    
    Args:
        clef_id: The ID of the clef to execute
        
    Returns:
        Dict with execution result information
    """
    logger.info(f"🔄 Executing scheduled clef: {clef_id}")
    
    try:
        # Get database connection
        db = await get_db()
        
        # Get the clef
        clef_result = await db.query({
            "sql": "SELECT * FROM clefs WHERE id = ?",
            "params": [clef_id]
        })
        
        if not clef_result:
            logger.error(f"❌ Clef not found: {clef_id}")
            return {"success": False, "error": "Clef not found"}
        
        # Deserialize the clef
        clef = deserialize_clef(clef_result[0])
        
        # Get the associated stave
        stave_result = await db.query({
            "sql": "SELECT * FROM staves WHERE id = ?",
            "params": [clef.stave_id]
        })
        
        if not stave_result:
            logger.error(f"❌ Stave not found for clef {clef_id}: {clef.stave_id}")
            return {"success": False, "error": "Associated stave not found"}
        
        # Deserialize the stave
        stave = deserialize_stave(stave_result[0])
        
        # Execute the clef
        executor = ClefExecutor()
        result = await executor.execute_clef(clef, stave)
        
        # Store the result
        await _store_clef_result(clef_id, result, clef, db)
        
        logger.info(f"✅ Scheduled execution completed for clef {clef_id}: {result.severity}")
        return {
            "success": True,
            "clef_id": clef_id,
            "severity": result.severity,
            "message": result.message,
            "executed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to execute scheduled clef {clef_id}: {e}")
        return {
            "success": False,
            "clef_id": clef_id,
            "error": str(e),
            "executed_at": datetime.utcnow().isoformat()
        }


async def _store_clef_result(clef_id: str, result, clef, db) -> None:
    """Store clef execution result in the database."""
    try:
        # Serialize metadata to JSON
        import json
        metadata_json = json.dumps(result.metadata) if result.metadata else "{}"
        
        # Store the result
        import uuid
        check_id = str(uuid.uuid4())
        success = await db.write([{
            "table": "checks",
            "id": check_id,
            "stave_id": clef.stave_id,
            "clef_id": clef_id,
            "check_type": clef.check_type,
            "status": result.status,  # Store the actual status: "pass", "warn", or "fail"
            "message": result.message,
            "details": metadata_json,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "execution_time": result.execution_time,  # Store execution time in seconds
            "anomalies_count": result.anomalies_count if hasattr(result, 'anomalies_count') else 0,
            "severity": result.severity.value  # Store the severity value: "harmony", "dissonance", "cacophony"
        }], "checks")
        
        if success:
            logger.debug(f"Stored result for clef {clef_id}")
        else:
            logger.warning(f"Failed to store result for clef {clef_id}")
            
    except Exception as e:
        logger.error(f"Failed to store result for clef {clef_id}: {e}")


async def load_and_schedule_all_clefs() -> Dict[str, int]:
    """
    Load all clefs from database and schedule those with cron expressions.
    
    Returns:
        Dict with scheduling statistics
    """
    logger.info("🔄 Loading and scheduling all clefs...")
    
    try:
        # Get database connection
        db = await get_db()
        
        # Get all clefs with schedules
        clefs_with_schedules = await db.query({
            "sql": "SELECT * FROM clefs WHERE schedule IS NOT NULL AND schedule != ''",
            "params": []
        })
        
        logger.info(f"Found {len(clefs_with_schedules)} clefs with schedules")
        
        scheduled_count = 0
        failed_count = 0
        
        for clef_data in clefs_with_schedules:
            clef = deserialize_clef(clef_data)
            
            try:
                # Parse cron expression (handle shorthand formats)
                cron_expression = _parse_cron_expression(clef.schedule)
                
                # Schedule the job
                job = add_scheduled_job(
                    clef_id=clef.id,
                    schedule=cron_expression,
                    func=execute_scheduled_clef
                )
                
                if job:
                    scheduled_count += 1
                    logger.info(f"✅ Scheduled clef: {clef.name} ({clef.schedule})")
                else:
                    failed_count += 1
                    logger.warning(f"❌ Failed to schedule clef: {clef.name}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error scheduling clef {clef.name}: {e}")
        
        result = {
            "total_clefs": len(clefs_with_schedules),
            "scheduled": scheduled_count,
            "failed": failed_count
        }
        
        logger.info(f"📊 Scheduling complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to load and schedule clefs: {e}")
        return {"total_clefs": 0, "scheduled": 0, "failed": 0}


def _parse_cron_expression(schedule: str) -> str:
    """
    Parse cron expression, converting shorthand formats to standard cron.
    
    Args:
        schedule: Cron expression or shorthand
        
    Returns:
        Standard 5-field cron expression
    """
    if not schedule:
        raise ValueError("Schedule cannot be empty")
    
    # Handle shorthand formats
    shorthand_map = {
        '@yearly': '0 0 1 1 *',      # Every year on January 1st at 00:00
        '@annually': '0 0 1 1 *',    # Same as yearly
        '@monthly': '0 0 1 * *',     # Every month on the 1st at 00:00
        '@weekly': '0 0 * * 0',      # Every Sunday at 00:00
        '@daily': '0 0 * * *',       # Every day at 00:00
        '@midnight': '0 0 * * *',    # Same as daily
        '@hourly': '0 * * * *',      # Every hour at minute 0
        '@minutely': '* * * * *'     # Every minute
    }
    
    schedule_lower = schedule.lower().strip()
    
    if schedule_lower in shorthand_map:
        return shorthand_map[schedule_lower]
    
    # If it's already a standard cron expression, return as-is
    parts = schedule.split()
    if len(parts) == 5:
        return schedule
    
    # Try to handle 6-field cron (with seconds)
    if len(parts) == 6:
        # Remove seconds field to make it 5-field
        return ' '.join(parts[1:])
    
    raise ValueError(f"Invalid cron expression: {schedule}")


async def get_scheduled_clefs() -> List[Dict[str, Any]]:
    """
    Get information about all currently scheduled clefs.
    
    Returns:
        List of scheduled clef information
    """
    try:
        from datametronome_podium.core.scheduler import scheduler
        
        if not scheduler:
            return []
        
        jobs = scheduler.get_jobs()
        scheduled_clefs = []
        
        for job in jobs:
            if job.id.startswith('clef_'):
                clef_id = job.id.replace('clef_', '')
                
                # Get clef details from database
                db = await get_db()
                clef_result = await db.query({
                    "sql": "SELECT * FROM clefs WHERE id = ?",
                    "params": [clef_id]
                })
                
                if clef_result:
                    clef = deserialize_clef(clef_result[0])
                    
                    # Ensure next_run timestamp is in UTC format
                    next_run = None
                    if job.next_run_time:
                        from datametronome_podium.core.timestamp_utils import to_utc_isoformat
                        next_run = to_utc_isoformat(job.next_run_time)
                    
                    scheduled_clefs.append({
                        "clef_id": clef_id,
                        "clef_name": clef.name,
                        "schedule": clef.schedule,
                        "next_run": next_run,
                        "job_id": job.id
                    })
        
        return scheduled_clefs
        
    except Exception as e:
        logger.error(f"Failed to get scheduled clefs: {e}")
        return []


async def unschedule_clef(clef_id: str) -> bool:
    """
    Remove a clef from the scheduler.
    
    Args:
        clef_id: The ID of the clef to unschedule
        
    Returns:
        True if successfully unscheduled, False otherwise
    """
    try:
        remove_scheduled_job(clef_id)
        logger.info(f"✅ Unscheduled clef: {clef_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to unschedule clef {clef_id}: {e}")
        return False


async def reschedule_clef(clef_id: str) -> bool:
    """
    Reschedule a clef (remove and add again).
    
    Args:
        clef_id: The ID of the clef to reschedule
        
    Returns:
        True if successfully rescheduled, False otherwise
    """
    try:
        # First unschedule
        await unschedule_clef(clef_id)
        
        # Get clef details
        db = await get_db()
        clef_result = await db.query({
            "sql": "SELECT * FROM clefs WHERE id = ?",
            "params": [clef_id]
        })
        
        if not clef_result or not clef_result[0].get('schedule'):
            logger.warning(f"No schedule found for clef {clef_id}")
            return False
        
        clef = deserialize_clef(clef_result[0])
        cron_expression = _parse_cron_expression(clef.schedule)
        
        # Schedule again
        job = add_scheduled_job(
            clef_id=clef.id,
            schedule=cron_expression,
            func=execute_scheduled_clef
        )
        
        if job:
            logger.info(f"✅ Rescheduled clef: {clef.name}")
            return True
        else:
            logger.error(f"❌ Failed to reschedule clef: {clef.name}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to reschedule clef {clef_id}: {e}")
        return False
