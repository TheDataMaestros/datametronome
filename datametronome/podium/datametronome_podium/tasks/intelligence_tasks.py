"""Celery tasks for the data intelligence pipeline.

These tasks run on the intelligence.default queue, separate from check execution.
Each task acquires a per-stave Redis lock to prevent overlapping runs.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.core.celery_app import celery_app
from datametronome_podium.core.config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine in a fresh event loop (safe for Celery prefork workers).

    asyncio.set_event_loop(loop) is required so that any internal calls to
    asyncio.get_event_loop() (in httpx, asyncpg, redis) get the new loop,
    not the closed loop from a previous task on the same worker process.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

LOCK_PREFIX = "intelligence:lock"
LOCK_TTL = 1800  # 30 minutes


async def _acquire_lock(redis_client, stave_id: str) -> bool:
    """Acquire a per-stave distributed lock. Returns True if acquired."""
    key = f"{LOCK_PREFIX}:{stave_id}"
    return await redis_client.set(key, "1", nx=True, ex=LOCK_TTL)


async def _release_lock(redis_client, stave_id: str) -> None:
    """Release the per-stave lock."""
    key = f"{LOCK_PREFIX}:{stave_id}"
    await redis_client.delete(key)


def _get_redis_client():
    """Lazy Redis client for intelligence tasks."""
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.redis_url)


@celery_app.task(
    name="datametronome.run_auto_scan",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    acks_late=True,
)
def run_auto_scan(self, stave_id: str) -> dict[str, Any]:
    """Auto-scan triggered after stave creation. Stages 1->2->3->5."""
    try:
        return _run_async(_run_auto_scan_async(stave_id))
    except Exception as exc:
        logger.error("Auto-scan failed for stave %s: %s", stave_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="datametronome.run_daily_intelligence",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def run_daily_intelligence(self, stave_id: str) -> dict[str, Any]:
    """Scheduled daily intelligence. Full pipeline 1->2->3->4->5."""
    try:
        return _run_async(_run_daily_async(stave_id))
    except Exception as exc:
        logger.error("Daily intelligence failed for stave %s: %s", stave_id, exc)
        raise


@celery_app.task(
    name="datametronome.run_on_demand_analysis",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def run_on_demand_analysis(
    self, stave_id: str, conversation_id: str | None = None
) -> dict[str, Any]:
    """On-demand analysis triggered by user. Stages 3->4->5."""
    try:
        return _run_async(_run_on_demand_async(stave_id, conversation_id))
    except Exception as exc:
        logger.error(
            "On-demand analysis failed for stave %s: %s", stave_id, exc
        )
        raise


@celery_app.task(
    name="datametronome.prune_old_snapshots",
    acks_late=True,
)
def prune_old_snapshots() -> dict[str, Any]:
    """Weekly task: delete raw snapshots beyond 90 days."""
    try:
        return _run_async(_prune_snapshots_async())
    except Exception as exc:
        logger.error("Snapshot pruning failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


async def _prune_snapshots_async() -> dict[str, Any]:
    """Delete baseline snapshots older than 90 days (except weekly_aggregate)."""
    from datetime import timedelta

    from datametronome_podium.core.worker_db import worker_db_session

    cutoff = (
        (datetime.now(timezone.utc) - timedelta(days=90))
        .isoformat()
        .replace("+00:00", "Z")
    )

    async with worker_db_session(settings.database_url) as (_, executor):
        await executor.execute(
            "DELETE FROM baseline_snapshots WHERE captured_at < ? AND snapshot_type != ?",
            [cutoff, "weekly_aggregate"],
        )
        logger.info("Pruned old snapshots before %s", cutoff)
        return {"status": "completed", "cutoff": cutoff}


def _aggregate_weekly_snapshots(snapshots: list[dict]) -> list[dict]:
    """Group snapshots by stave_id + ISO week, compute average metrics.

    Returns list of weekly_aggregate snapshot dicts ready for insertion.
    """
    import json
    from collections import defaultdict
    from datetime import date

    groups: dict[str, list[dict]] = defaultdict(list)
    for snap in snapshots:
        captured = snap["captured_at"][:10]  # YYYY-MM-DD
        try:
            d = date.fromisoformat(captured)
            iso = d.isocalendar()
            week_key = f"{snap['stave_id']}:{iso[0]}-W{iso[1]:02d}"
        except (ValueError, IndexError):
            continue
        groups[week_key].append(snap)

    aggregates: list[dict] = []
    for key, group in groups.items():
        stave_id = group[0]["stave_id"]
        table_counts: dict[str, list[int]] = defaultdict(list)
        for snap in group:
            metrics = snap.get("table_metrics", "{}")
            if isinstance(metrics, str):
                metrics = json.loads(metrics)
            for table, data in metrics.items():
                if isinstance(data, dict):
                    table_counts[table].append(data.get("row_count", 0))

        avg_metrics = {
            table: {"row_count": sum(counts) // len(counts), "null_rates": {}}
            for table, counts in table_counts.items()
        }

        aggregates.append({
            "id": f"snap-agg-{key}",
            "stave_id": stave_id,
            "tenant_id": "default",
            "snapshot_type": "weekly_aggregate",
            "table_metrics": json.dumps(avg_metrics),
            "column_stats": "{}",
            "captured_at": group[0]["captured_at"],
        })

    return aggregates


async def _run_auto_scan_async(stave_id: str) -> dict[str, Any]:
    """Auto-scan implementation. Acquires lock, runs stages 1->2->3->5."""
    redis = _get_redis_client()
    if not await _acquire_lock(redis, stave_id):
        logger.info("Auto-scan skipped for stave %s -- lock held", stave_id)
        return {"status": "skipped", "reason": "lock_held"}
    try:
        from datametronome_podium.core.worker_db import worker_db_session
        from datametronome_podium.features.insights.service import (
            InsightPipelineService,
        )

        async with worker_db_session(settings.database_url) as (_, executor):
            service = InsightPipelineService(executor=executor)
            report = await service.run_auto_scan(stave_id)
            logger.info(
                "Auto-scan completed for stave %s: report=%s",
                stave_id,
                report.id,
            )
            return {
                "status": "completed",
                "stave_id": stave_id,
                "report_id": report.id,
            }
    except Exception as exc:
        logger.error("Auto-scan pipeline failed for stave %s: %s", stave_id, exc)
        return {"status": "failed", "error": str(exc)}
    finally:
        await _release_lock(redis, stave_id)
        await redis.aclose()


async def _run_daily_async(stave_id: str) -> dict[str, Any]:
    """Daily intelligence implementation. Acquires lock, runs full pipeline."""
    redis = _get_redis_client()
    if not await _acquire_lock(redis, stave_id):
        logger.info(
            "Daily intelligence skipped for stave %s -- lock held", stave_id
        )
        return {"status": "skipped", "reason": "lock_held"}
    try:
        from datametronome_podium.core.worker_db import worker_db_session
        from datametronome_podium.features.insights.service import (
            InsightPipelineService,
        )

        async with worker_db_session(settings.database_url) as (_, executor):
            service = InsightPipelineService(executor=executor)
            report = await service.run_daily(stave_id)
            logger.info(
                "Daily intelligence completed for stave %s: report=%s",
                stave_id,
                report.id,
            )
            return {
                "status": "completed",
                "stave_id": stave_id,
                "report_id": report.id,
            }
    except Exception as exc:
        logger.error(
            "Daily intelligence pipeline failed for stave %s: %s",
            stave_id,
            exc,
        )
        return {"status": "failed", "error": str(exc)}
    finally:
        await _release_lock(redis, stave_id)
        await redis.aclose()


async def _run_on_demand_async(
    stave_id: str, conversation_id: str | None
) -> dict[str, Any]:
    """On-demand analysis implementation. Acquires lock, runs stages 3->4->5."""
    redis = _get_redis_client()
    if not await _acquire_lock(redis, stave_id):
        return {
            "status": "in_progress",
            "message": "An analysis is already running for this data source.",
        }
    try:
        from datametronome_podium.core.worker_db import worker_db_session
        from datametronome_podium.features.insights.service import (
            InsightPipelineService,
        )

        async with worker_db_session(settings.database_url) as (_, executor):
            service = InsightPipelineService(executor=executor)
            report = await service.run_on_demand(stave_id)
            logger.info(
                "On-demand analysis completed for stave %s: report=%s",
                stave_id,
                report.id,
            )
            return {
                "status": "completed",
                "stave_id": stave_id,
                "report_id": report.id,
            }
    except Exception as exc:
        logger.error(
            "On-demand analysis pipeline failed for stave %s: %s",
            stave_id,
            exc,
        )
        return {"status": "failed", "error": str(exc)}
    finally:
        await _release_lock(redis, stave_id)
        await redis.aclose()
