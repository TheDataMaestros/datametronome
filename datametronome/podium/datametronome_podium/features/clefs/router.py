"""Clefs API router."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from datametronome_podium.core.database import get_executor
from datametronome_podium.features.clefs.model import Clef
from datametronome_podium.features.clefs.repo import ClefRepo
from datametronome_podium.features.clefs.schema import ClefCreate, ClefUpdate, ClefResponse

router = APIRouter()

CHECK_TYPE_METADATA = {
    "row_count": {"tier": 1, "display_name": "Row Count", "description": "Validates expected row counts"},
    "freshness": {"tier": 1, "display_name": "Freshness", "description": "Checks data recency"},
    "column_values": {"tier": 2, "display_name": "Column Values", "description": "Validates column value constraints"},
    "forecast": {"tier": 3, "display_name": "Forecast", "description": "ML-based anomaly detection"},
    "data_profile_drift": {"tier": 3, "display_name": "Data Profile Drift", "description": "Detects schema/distribution drift"},
    "lookup_validation": {"tier": 2, "display_name": "Lookup Validation", "description": "Cross-table reference checks"},
    "python": {"tier": 4, "display_name": "Python", "description": "Custom Python check scripts"},
}


def _repo() -> ClefRepo:
    return ClefRepo(get_executor())


@router.get("/", response_model=list[ClefResponse])
async def get_clefs(skip: int = 0, limit: int = 100):
    repo = _repo()
    clefs = await repo.list(limit=limit, offset=skip)
    results = []
    for c in clefs:
        data = c.model_dump()
        if isinstance(data.get("config"), str):
            try:
                data["config"] = json.loads(data["config"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(data)
    return results


@router.get("/types")
async def get_check_types():
    by_tier: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    check_types = []
    for name, meta in CHECK_TYPE_METADATA.items():
        entry = {"name": name, **meta}
        check_types.append(entry)
        by_tier[int(meta["tier"])].append(entry)
    return {"check_types": check_types, "by_tier": by_tier}


@router.get("/{clef_id}", response_model=ClefResponse)
async def get_clef(clef_id: str):
    repo = _repo()
    clef = await repo.get(clef_id)
    if not clef:
        raise HTTPException(status_code=404, detail="Clef not found")
    data = clef.model_dump()
    if isinstance(data.get("config"), str):
        try:
            data["config"] = json.loads(data["config"])
        except (json.JSONDecodeError, TypeError):
            pass
    return data


@router.post("/", response_model=ClefResponse, status_code=201)
async def create_clef(clef_in: ClefCreate):
    repo = _repo()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    clef = Clef(
        id=str(uuid.uuid4()),
        stave_id=clef_in.stave_id,
        name=clef_in.name,
        description=clef_in.description,
        check_type=clef_in.check_type,
        config=json.dumps(clef_in.config),
        warn=clef_in.warn,
        fail=clef_in.fail,
        schedule=clef_in.schedule,
        is_active=clef_in.is_active,
        created_at=now,
        updated_at=now,
    )
    await repo.create(clef)
    data = clef.model_dump()
    data["config"] = clef_in.config
    return data


@router.put("/{clef_id}", response_model=ClefResponse)
async def update_clef(clef_id: str, clef_in: ClefUpdate):
    repo = _repo()
    existing = await repo.get(clef_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Clef not found")
    update_data = clef_in.model_dump(exclude_unset=True)
    if "config" in update_data and isinstance(update_data["config"], dict):
        update_data["config"] = json.dumps(update_data["config"])
    await repo.update(clef_id, update_data)
    updated = await repo.get(clef_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Clef not found")
    data = updated.model_dump()
    if isinstance(data.get("config"), str):
        try:
            data["config"] = json.loads(data["config"])
        except (json.JSONDecodeError, TypeError):
            pass
    return data


@router.delete("/{clef_id}", status_code=204)
async def delete_clef(clef_id: str):
    repo = _repo()
    existing = await repo.get(clef_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Clef not found")
    await repo.delete(clef_id)
    return Response(status_code=204)
