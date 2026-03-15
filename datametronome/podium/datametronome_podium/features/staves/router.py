"""Staves API router."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker
from datametronome_podium.core.database import get_executor
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.features.staves.repo import StaveRepo
from datametronome_podium.features.staves.schema import StaveCreate, StaveUpdate, StaveResponse

router = APIRouter()

VALID_DATA_SOURCE_TYPES = [
    "postgres", "mysql", "mongodb", "sqlite", "redis", "snowflake", "bigquery"
]

_redis_client = None


def _get_or_create_redis_client():
    """Return a cached Redis client, creating one on first call."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        from datametronome_podium.core.config import settings
        _redis_client = aioredis.from_url(settings.redis_url)
    return _redis_client


def _dispatch_auto_scan(stave_id: str) -> None:
    """Fire-and-forget: dispatch auto-scan + register daily schedule.

    Retries once after 2 seconds if the first attempt fails (e.g., Celery not ready).
    """
    import logging
    import threading

    log = logging.getLogger(__name__)

    def _dispatch():
        try:
            from datametronome_podium.tasks.intelligence_tasks import run_auto_scan
            run_auto_scan.delay(stave_id)
            log.info("Auto-scan dispatched for stave %s", stave_id)
        except Exception as e:
            log.warning("Auto-scan dispatch failed for %s: %s. Retrying in 2s...", stave_id, e)
            import time
            time.sleep(2)
            try:
                from datametronome_podium.tasks.intelligence_tasks import run_auto_scan
                run_auto_scan.delay(stave_id)
                log.info("Auto-scan dispatched for stave %s (retry)", stave_id)
            except Exception as e2:
                log.error("Auto-scan dispatch failed permanently for %s: %s", stave_id, e2)

    def _register_schedule():
        try:
            from datametronome_podium.services.intelligence_scheduler import register_daily_intelligence
            register_daily_intelligence(stave_id)
        except Exception:
            pass

    # Run in background threads to not block the API response
    threading.Thread(target=_dispatch, daemon=True).start()
    threading.Thread(target=_register_schedule, daemon=True).start()


def _repo() -> StaveRepo:
    return StaveRepo(get_executor())


def _get_circuit_breaker() -> StaveCircuitBreaker | None:
    """Get circuit breaker if Redis is available. Returns None otherwise."""
    try:
        client = _get_or_create_redis_client()
        return StaveCircuitBreaker(redis_client=client, executor=get_executor())
    except Exception:
        return None


@router.get("/", response_model=list[StaveResponse])
async def get_staves(skip: int = 0, limit: int = 100):
    repo = _repo()
    staves = await repo.list(limit=limit, offset=skip)
    results = []
    for s in staves:
        data = s.model_dump()
        if isinstance(data.get("connection_config"), str):
            try:
                data["connection_config"] = json.loads(data["connection_config"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(data)
    return results


@router.get("/types")
async def get_stave_types():
    return VALID_DATA_SOURCE_TYPES


@router.get("/{stave_id}", response_model=StaveResponse)
async def get_stave(stave_id: str):
    repo = _repo()
    stave = await repo.get(stave_id)
    if not stave:
        raise HTTPException(status_code=404, detail="Stave not found")
    data = stave.model_dump()
    if isinstance(data.get("connection_config"), str):
        try:
            data["connection_config"] = json.loads(data["connection_config"])
        except (json.JSONDecodeError, TypeError):
            pass
    return data


@router.get("/{stave_id}/delete-info")
async def get_stave_delete_info(stave_id: str):
    repo = _repo()
    stave = await repo.get(stave_id)
    if not stave:
        raise HTTPException(status_code=404, detail="Stave not found")
    clef_ids = await repo.find_clef_ids(stave_id)
    return {
        "stave": stave.model_dump(),
        "impact": {"clefs_affected": len(clef_ids), "clef_ids": clef_ids},
        "warning": f"Deleting this stave will also remove {len(clef_ids)} associated clef(s) and their check results."
    }


@router.post("/", response_model=StaveResponse, status_code=201)
async def create_stave(stave_in: StaveCreate):
    repo = _repo()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    stave = Stave(
        id=str(uuid.uuid4()),
        name=stave_in.name,
        description=stave_in.description,
        data_source_type=stave_in.data_source_type,
        connection_config=json.dumps(stave_in.connection_config),
        is_active=stave_in.is_active,
        created_at=now,
        updated_at=now,
    )
    await repo.create(stave)
    data = stave.model_dump()
    data["connection_config"] = stave_in.connection_config
    # Trigger background intelligence scan
    _dispatch_auto_scan(stave.id)
    return data


@router.put("/{stave_id}", response_model=StaveResponse)
async def update_stave(stave_id: str, stave_in: StaveUpdate):
    repo = _repo()
    existing = await repo.get(stave_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Stave not found")
    update_data = stave_in.model_dump(exclude_unset=True)
    if "connection_config" in update_data and isinstance(update_data["connection_config"], dict):
        update_data["connection_config"] = json.dumps(update_data["connection_config"])
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    update_data["updated_at"] = now
    await repo.update(stave_id, update_data)
    updated = await repo.get(stave_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Stave not found")
    data = updated.model_dump()
    if isinstance(data.get("connection_config"), str):
        try:
            data["connection_config"] = json.loads(data["connection_config"])
        except (json.JSONDecodeError, TypeError):
            pass
    return data


@router.post("/{stave_id}/unpause")
async def unpause_stave(stave_id: str):
    repo = _repo()
    stave = await repo.get(stave_id)
    if not stave:
        raise HTTPException(status_code=404, detail="Stave not found")

    cb = _get_circuit_breaker()
    if cb:
        await cb.reset(stave_id)
    else:
        await repo.update(stave_id, {"paused": False})

    # Re-register intelligence schedule
    try:
        from datametronome_podium.services.intelligence_scheduler import register_daily_intelligence
        register_daily_intelligence(stave_id)
    except Exception:
        pass

    return {"message": "Stave unpaused", "stave_id": stave_id}


@router.delete("/{stave_id}")
async def delete_stave(stave_id: str, force: bool = False):
    repo = _repo()
    existing = await repo.get(stave_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Stave not found")

    # Remove intelligence schedule before deleting
    try:
        from datametronome_podium.services.intelligence_scheduler import remove_daily_intelligence
        remove_daily_intelligence(stave_id)
    except Exception:
        pass

    deleted = await repo.delete(stave_id)
    return {"message": "Stave deleted successfully", "deleted": {"stave_id": stave_id}}
