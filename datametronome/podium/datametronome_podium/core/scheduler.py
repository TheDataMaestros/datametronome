"""
Scheduler management for DataMetronome Podium.
"""

import asyncio
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


async def init_scheduler():
    """Initialize the scheduler and load all scheduled clefs."""
    global scheduler
    
    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled")
        return
    
    try:
        scheduler = AsyncIOScheduler(
            timezone=settings.scheduler_timezone,
            job_defaults={
                'coalesce': False,
                'max_instances': 3
            }
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        # Load and schedule all clefs with cron expressions
        await _load_and_schedule_clefs()
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise


async def _load_and_schedule_clefs():
    """Load and schedule all clefs from the database."""
    try:
        from datametronome_podium.services.clef_scheduler import load_and_schedule_all_clefs
        
        logger.info("🔄 Loading and scheduling clefs...")
        result = await load_and_schedule_all_clefs()
        
        if result["scheduled"] > 0:
            logger.info(f"✅ Scheduled {result['scheduled']} clefs successfully")
        if result["failed"] > 0:
            logger.warning(f"⚠️  Failed to schedule {result['failed']} clefs")
            
    except Exception as e:
        logger.error(f"Failed to load and schedule clefs: {e}")
        # Don't raise here - we want the scheduler to start even if clef loading fails


async def shutdown_scheduler():
    """Shutdown the scheduler."""
    global scheduler
    
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler shutdown")


def add_scheduled_job(clef_id: str, schedule: str, func, *args, **kwargs):
    """Add a scheduled job to the scheduler."""
    if not scheduler:
        logger.warning("Scheduler not initialized")
        return None
    
    try:
        # Parse cron expression
        trigger = CronTrigger.from_crontab(schedule)
        
        job = scheduler.add_job(
            func,
            trigger=trigger,
            args=[clef_id] + list(args),
            kwargs=kwargs,
            id=f"clef_{clef_id}",
            replace_existing=True
        )
        
        logger.info(f"Added scheduled job for clef {clef_id}: {schedule}")
        return job
        
    except Exception as e:
        logger.error(f"Failed to add scheduled job for clef {clef_id}: {e}")
        return None


def remove_scheduled_job(clef_id: str):
    """Remove a scheduled job from the scheduler."""
    if not scheduler:
        return
    
    try:
        scheduler.remove_job(f"clef_{clef_id}")
        logger.info(f"Removed scheduled job for clef {clef_id}")
    except Exception as e:
        logger.error(f"Failed to remove scheduled job for clef {clef_id}: {e}")


def get_scheduler_status():
    """Get scheduler status."""
    if not scheduler:
        return {"status": "disabled"}
    
    return {
        "status": "running",
        "job_count": len(scheduler.get_jobs()),
        "timezone": str(scheduler.timezone)
    }


async def is_scheduler_running() -> bool:
    """
    Check if scheduler is running and healthy.
    
    Returns:
        bool: True if scheduler is running, False if disabled or failed.
    """
    try:
        if not scheduler:
            return False
        return scheduler.running
    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}")
        return False
