"""
Celery task for executing data quality checks.

The execute_check task wraps ClefExecutor. It:
1. Creates its own DB session (workers can't use the API's global session)
2. Fetches clef + stave from Postgres
3. Executes the check via ClefExecutor
4. Stores the result in the checks table
5. Bridges async/sync: uses asyncio.run() since Celery tasks are synchronous
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.core.celery_app import celery_app, QUEUE_DEFAULT
from datametronome_podium.core.config import settings
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.worker_db import worker_db_session
from datametronome_podium.services.clef_executor import ClefExecutor
from datametronome_podium.services.stave_service import deserialize_clef, deserialize_stave

logger = logging.getLogger(__name__)

_redis_client = None


def _get_or_create_redis_client():
    """Return a cached Redis client, creating one on first call."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(settings.redis_url)
    return _redis_client


def _get_circuit_breaker(executor):
    """Create a circuit breaker if Redis is available."""
    try:
        from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker
        client = _get_or_create_redis_client()
        return StaveCircuitBreaker(redis_client=client, threshold=5, executor=executor)
    except Exception:
        return None


async def _execute_check_async(
    clef_id: str,
    connector: Any,
    executor: QueryExecutor,
) -> dict[str, Any]:
    """Async inner function that does the actual work.

    Separated from the Celery task so it can be tested without Celery.
    """
    # Fetch clef
    clef_rows = await executor.query(
        "SELECT * FROM clefs WHERE id = ?", [clef_id]
    )
    if not clef_rows:
        raise ValueError(f"Clef not found: {clef_id}")
    clef = deserialize_clef(clef_rows[0])

    # Fetch stave
    stave_rows = await executor.query(
        "SELECT * FROM staves WHERE id = ?", [clef.stave_id]
    )
    if not stave_rows:
        raise ValueError(f"Stave not found: {clef.stave_id}")
    stave = deserialize_stave(stave_rows[0])

    # Check circuit breaker (Redis may be unavailable — fail open)
    cb = _get_circuit_breaker(executor)
    try:
        if cb and await cb.is_tripped(stave.id):
            raise ValueError(f"Stave {stave.id} is paused due to consecutive failures")
    except ValueError:
        raise
    except Exception:
        cb = None

    # Execute the check
    clef_executor = ClefExecutor()
    result = await clef_executor.execute_clef(clef, stave)

    # Record result in circuit breaker
    if cb:
        try:
            is_success = result.status in ("pass", "warn")
            if is_success:
                await cb.record_success(stave.id)
            else:
                await cb.record_failure(stave.id)
        except Exception:
            pass

    # Store result
    metadata_for_storage = dict(result.metadata or {})
    metadata_for_storage["observed_value"] = result.observed_value
    check_id = f"check-{clef_id}-{datetime.now(timezone.utc).isoformat()}"

    await executor.insert("checks", {
        "id": check_id,
        "stave_id": stave.id,
        "clef_id": clef.id,
        "check_type": clef.check_type,
        "status": result.status,
        "message": result.message,
        "details": json.dumps(metadata_for_storage),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "execution_time": result.execution_time,
        "anomalies_count": result.anomalies_count,
        "severity": result.severity.value,
    })

    logger.info("Check completed: clef=%s status=%s severity=%s",
                clef_id, result.status, result.severity.value)

    return {
        "clef_id": clef.id,
        "stave_id": stave.id,
        "status": result.status,
        "message": result.message,
        "observed_value": result.observed_value,
        "execution_time": result.execution_time,
        "check_id": check_id,
        "severity": result.severity.value,
    }


@celery_app.task(
    name="datametronome.execute_check",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def execute_check(self, clef_id: str) -> dict[str, Any]:
    """Celery task that executes a data quality check.

    Uses asyncio.run() to bridge Celery's sync world with our async ClefExecutor.
    Each task gets its own DB session, created and closed within the task scope.
    """
    try:
        return asyncio.run(_run_check(clef_id))
    except ValueError:
        # Permanent failures (clef not found, stave paused) — don't retry
        raise
    except Exception as exc:
        # Transient failures (DB timeout, connection error) — retry
        logger.error("execute_check failed for clef %s: %s", clef_id, exc)
        raise self.retry(exc=exc)


async def _run_check(clef_id: str) -> dict[str, Any]:
    """Create a worker DB session and run the check."""
    async with worker_db_session(settings.database_url) as (connector, executor):
        return await _execute_check_async(clef_id, connector, executor)
