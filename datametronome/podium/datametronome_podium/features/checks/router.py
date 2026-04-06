"""Checks API router."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from datametronome_podium.api.v1.endpoints.auth import get_current_user
from datametronome_podium.core.database import get_executor
from datametronome_podium.features.checks.model import Check
from datametronome_podium.features.checks.repo import CheckRepo
from datametronome_podium.features.checks.schema import CheckCreate, CheckUpdate, CheckResponse

router = APIRouter()


def _repo() -> CheckRepo:
    return CheckRepo(get_executor())


def _isoformat(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    s = dt.isoformat()
    return s.replace("+00:00", "Z")


@router.get("/", response_model=list[CheckResponse])
async def get_checks(
    skip: int = 0,
    limit: int = 100,
    status: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    check_type: str | None = None,
    stave_id: str | None = None,
    clef_id: str | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    _user: dict = Depends(get_current_user),
):
    executor = get_executor()
    # Build dynamic query with filters
    sql = "SELECT * FROM checks"
    params: list[Any] = []
    conditions: list[str] = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if check_type:
        conditions.append("check_type = ?")
        params.append(check_type)
    if stave_id:
        conditions.append("stave_id = ?")
        params.append(stave_id)
    if clef_id:
        conditions.append("clef_id = ?")
        params.append(clef_id)
    if started_after:
        conditions.append("timestamp >= ?")
        params.append(_isoformat(started_after))
    if started_before:
        conditions.append("timestamp <= ?")
        params.append(_isoformat(started_before))

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, skip])

    rows = await executor.query(sql, params)
    results = []
    for row in rows:
        data = dict(row)
        if isinstance(data.get("details"), str):
            try:
                data["details"] = json.loads(data["details"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(data)
    return results


@router.get("/{check_id}", response_model=CheckResponse)
async def get_check(check_id: str, _user: dict = Depends(get_current_user)):
    repo = _repo()
    check = await repo.get(check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    data = check.model_dump()
    if isinstance(data.get("details"), str):
        try:
            data["details"] = json.loads(data["details"])
        except (json.JSONDecodeError, TypeError):
            pass
    return data


@router.post("/", response_model=CheckResponse, status_code=201)
async def create_check(check_in: CheckCreate, _user: dict = Depends(get_current_user)):
    repo = _repo()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    check = Check(
        id=check_in.id,
        stave_id=check_in.stave_id,
        clef_id=check_in.clef_id,
        check_type=check_in.check_type,
        status=check_in.status,
        message=check_in.message,
        details=json.dumps(check_in.details) if check_in.details else None,
        timestamp=_isoformat(check_in.timestamp) or now,
        execution_time=check_in.execution_time,
        anomalies_count=check_in.anomalies_count,
        severity=check_in.severity,
    )
    await repo.create(check)
    data = check.model_dump()
    if check_in.details:
        data["details"] = check_in.details
    return data


@router.put("/{check_id}", response_model=CheckResponse)
async def update_check(check_id: str, check_in: CheckUpdate, _user: dict = Depends(get_current_user)):
    repo = _repo()
    existing = await repo.get(check_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Check not found")
    update_data = check_in.model_dump(exclude_unset=True)
    if "details" in update_data and isinstance(update_data["details"], dict):
        update_data["details"] = json.dumps(update_data["details"])
    await repo.update(check_id, update_data)
    updated = await repo.get(check_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Check not found")
    data = updated.model_dump()
    if isinstance(data.get("details"), str):
        try:
            data["details"] = json.loads(data["details"])
        except (json.JSONDecodeError, TypeError):
            pass
    return data


@router.delete("/{check_id}", status_code=204)
async def delete_check(check_id: str, _user: dict = Depends(get_current_user)):
    repo = _repo()
    existing = await repo.get(check_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Check not found")
    await repo.delete(check_id)
    return Response(status_code=204)
