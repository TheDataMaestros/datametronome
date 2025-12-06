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
        # Get advanced scheduler settings
        max_instances = getattr(settings, 'scheduler_max_instances', 3)
        max_workers = getattr(settings, 'scheduler_max_workers', 10)
        
        scheduler = AsyncIOScheduler(
            timezone=settings.scheduler_timezone,
            job_defaults={
                'coalesce': False,
                'max_instances': max_instances,
                'misfire_grace_time': 60  # Grace period for missed executions
            },
            executors={
                'default': {
                    'type': 'threadpool',
                    'max_workers': max_workers
                }
            }
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        # Add the streaming data generator job
        try:
            from datametronome_podium.services.default_setup import generate_streaming_data_job
            scheduler.add_job(
                generate_streaming_data_job,
                trigger='interval',
                minutes=10,
                id='streaming_data_generator',
                replace_existing=True
            )
            logger.info("Added streaming data generator job to run every 10 minutes.")
        except Exception as e:
            logger.error(f"Failed to add streaming data generator job: {e}")

        # Load and schedule all clefs with cron expressions
        await _load_and_schedule_clefs()
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise


async def _load_and_schedule_clefs():
    """Load and schedule all clefs from the database."""
    try:
        from datametronome_podium.services.clef_scheduler import load_and_schedule_all_clefs
        from datametronome_podium.services.scheduler_persistence import (
            get_all_scheduler_jobs,
            SchedulerJob
        )
        
        logger.info("🔄 Loading and scheduling clefs...")
        
        # First, try to restore persisted jobs
        persisted_jobs = await get_all_scheduler_jobs(enabled_only=True)
        restored_count = 0
        
        for job in persisted_jobs:
            try:
                # Restore job to scheduler
                trigger = CronTrigger.from_crontab(job.schedule)
                from datametronome_podium.services.clef_scheduler import execute_scheduled_clef
                
                scheduler.add_job(
                    execute_scheduled_clef,
                    trigger=trigger,
                    args=[job.clef_id],
                    id=job.id,
                    replace_existing=True
                )
                restored_count += 1
                logger.debug(f"Restored persisted job: {job.id}")
            except Exception as e:
                logger.warning(f"Failed to restore job {job.id}: {e}")
        
        if restored_count > 0:
            logger.info(f"✅ Restored {restored_count} persisted jobs")
        
        # Then load and schedule any new clefs
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


def add_scheduled_job(clef_id: str, schedule: str, func, priority: str = "medium", *args, **kwargs):
    """
    Add a scheduled job to the scheduler and persist it.
    
    Args:
        clef_id: Clef ID
        schedule: Cron schedule expression
        func: Function to execute
        priority: Job priority ('high', 'medium', 'low') - affects execution order
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments
    """
    if not scheduler:
        logger.warning("Scheduler not initialized")
        return None
    
    try:
        # Parse cron expression
        trigger = CronTrigger.from_crontab(schedule)
        job_id = f"clef_{clef_id}"
        
        # Map priority to jobstore (for future priority queue implementation)
        # For now, all jobs go to default store
        jobstore = 'default'
        
        # Add job with priority metadata in kwargs
        job_kwargs = kwargs.copy()
        job_kwargs['priority'] = priority
        
        job = scheduler.add_job(
            func,
            trigger=trigger,
            args=[clef_id] + list(args),
            kwargs=job_kwargs,
            id=job_id,
            replace_existing=True,
            jobstore=jobstore
        )
        
        # Persist job to database
        async def persist_job():
            from datametronome_podium.services.scheduler_persistence import (
                get_scheduler_job_by_clef_id,
                save_scheduler_job,
                SchedulerJob
            )
            from datetime import datetime
            
            # Check if job already exists
            existing_job = await get_scheduler_job_by_clef_id(clef_id)
            if existing_job:
                # Update existing
                existing_job.schedule = schedule
                existing_job.next_run_time = job.next_run_time
                existing_job.updated_at = datetime.utcnow()
                await save_scheduler_job(existing_job)
            else:
                # Create new
                new_job = SchedulerJob(
                    id=job_id,
                    clef_id=clef_id,
                    schedule=schedule,
                    enabled=True,
                    next_run_time=job.next_run_time
                )
                await save_scheduler_job(new_job)
        
        # Run persistence in background
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(persist_job())
            else:
                loop.run_until_complete(persist_job())
        except:
            # If we can't persist, log but don't fail
            logger.warning(f"Could not persist job {job_id}, but job is scheduled")
        
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
