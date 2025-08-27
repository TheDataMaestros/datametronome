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
    """Initialize the scheduler."""
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
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise


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
        "timezone": scheduler.timezone
    }
