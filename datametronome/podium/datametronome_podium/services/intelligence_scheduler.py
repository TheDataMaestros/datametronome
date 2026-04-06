"""Manage Celery Beat schedules for intelligence tasks."""
import logging

from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry  # type: ignore[unresolved-import]

from datametronome_podium.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def register_daily_intelligence(
    stave_id: str, hour: int = 6, minute: int = 0
) -> None:
    """Register a daily intelligence run for a stave in Celery Beat."""
    entry = RedBeatSchedulerEntry(
        name=f"intelligence-{stave_id}",
        task="datametronome.run_daily_intelligence",
        schedule=crontab(hour=hour, minute=minute),
        args=[stave_id],
        app=celery_app,
    )
    entry.save()
    logger.info("Registered daily intelligence schedule for stave %s", stave_id)


def remove_daily_intelligence(stave_id: str) -> None:
    """Remove the daily intelligence schedule for a stave."""
    try:
        entry = RedBeatSchedulerEntry.from_key(
            f"redbeat:intelligence-{stave_id}",
            app=celery_app,
        )
        entry.delete()
        logger.info(
            "Removed daily intelligence schedule for stave %s", stave_id
        )
    except (KeyError, Exception) as e:
        logger.debug("No schedule to remove for stave %s: %s", stave_id, e)


def register_prune_schedule() -> None:
    """Register the global weekly snapshot pruning task."""
    entry = RedBeatSchedulerEntry(
        name="prune-old-snapshots",
        task="datametronome.prune_old_snapshots",
        schedule=crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        app=celery_app,
    )
    entry.save()
    logger.info("Registered weekly snapshot pruning schedule")
