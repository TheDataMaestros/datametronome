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

    return {"message": "Stave unpaused", "stave_id": stave_id}


@router.delete("/{stave_id}")
async def delete_stave(stave_id: str, force: bool = False):
    repo = _repo()
    existing = await repo.get(stave_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Stave not found")
    deleted = await repo.delete(stave_id)
    return {"message": "Stave deleted successfully", "deleted": {"stave_id": stave_id}}
