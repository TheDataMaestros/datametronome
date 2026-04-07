"""Clefs API router."""
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from datametronome_podium.core.auth import get_current_user, require_admin, require_editor
from datametronome_podium.core.check_dispatcher import JobStatus
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.dispatcher_factory import get_dispatcher
from datametronome_podium.core.timestamp_utils import now_utc_iso, to_utc_isoformat
from datametronome_podium.features.clefs.model import ClefRow as Clef
from datametronome_podium.features.clefs.repo import ClefRepo
from datametronome_podium.features.clefs.schema import ClefCreate, ClefUpdate, ClefResponse

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

CHECK_TYPE_METADATA = {
    "row_count": {"tier": 1, "display_name": "Row Count", "description": "Validates expected row counts"},
    "freshness": {"tier": 1, "display_name": "Freshness", "description": "Checks data recency"},
    "column_values": {"tier": 2, "display_name": "Column Values", "description": "Validates column value constraints"},
    "forecast": {"tier": 3, "display_name": "Forecast", "description": "ML-based anomaly detection"},
    "data_profile_drift": {"tier": 3, "display_name": "Data Profile Drift", "description": "Detects schema/distribution drift"},
    "lookup_validation": {"tier": 2, "display_name": "Lookup Validation", "description": "Cross-table reference checks"},
}


def _repo() -> ClefRepo:
    return ClefRepo(get_executor())


# ── Fixed-prefix routes (must come before parameterised /{clef_id}) ──────────

@router.get("/", response_model=list[ClefResponse])
async def get_clefs(skip: int = 0, limit: int = 100, _user: dict = Depends(get_current_user)):
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
async def get_check_types(_user: dict = Depends(get_current_user)):
    by_tier: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    check_types = []
    for name, meta in CHECK_TYPE_METADATA.items():
        entry = {"name": name, **meta}
        check_types.append(entry)
        by_tier[int(meta["tier"])].append(entry)
    return {"check_types": check_types, "by_tier": by_tier}


@router.get("/results/latest")
async def get_latest_results(
    limit: int = Query(20, ge=1, le=100), _user: dict = Depends(get_current_user)
) -> dict:
    """Get the most recent check execution results across all clefs."""
    try:
        executor = get_executor()

        results = await executor.query(
            """
                SELECT
                    c.*,
                    cl.name as clef_name,
                    cl.check_type,
                    s.name as stave_name,
                    s.data_source_type
                FROM checks c
                JOIN clefs cl ON c.clef_id = cl.id
                JOIN staves s ON c.stave_id = s.id
                ORDER BY c.timestamp DESC
                LIMIT ?
            """,
            [limit],
        )

        formatted_results = []
        for result in results:
            metadata = None
            if result.get("details"):
                try:
                    metadata = (
                        json.loads(result["details"])
                        if isinstance(result["details"], str)
                        else result["details"]
                    )
                except (json.JSONDecodeError, TypeError):
                    metadata = result["details"]

            formatted_results.append(
                {
                    "id": result["id"],
                    "clef_id": result["clef_id"],
                    "clef_name": result["clef_name"],
                    "check_type": result["check_type"],
                    "stave_id": result["stave_id"],
                    "stave_name": result["stave_name"],
                    "data_source_type": result["data_source_type"],
                    "status": result["status"],
                    "message": result["message"],
                    "timestamp": result["timestamp"],
                    "execution_time": result["execution_time"],
                    "anomalies_count": result["anomalies_count"],
                    "severity": result["severity"],
                    "metadata": metadata,
                }
            )

        return {"results": formatted_results, "count": len(formatted_results)}

    except Exception as e:
        logger.error("Failed to get latest results: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get latest results",
        )


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str, _user: dict = Depends(get_current_user)) -> dict:
    """Get the status and result of a dispatched check job."""
    try:
        dispatcher = get_dispatcher()
        job_status = await dispatcher.get_status(job_id)
        result = await dispatcher.get_result(job_id) if job_status == JobStatus.COMPLETED else None

        return {
            "job_id": job_id,
            "status": job_status.value,
            "result": result,
        }
    except Exception as e:
        logger.error("Failed to get job status %s: %s", job_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status",
        )


# ── Parameterised routes (/{clef_id} and sub-paths) ──────────────────────────

@router.get("/{clef_id}", response_model=ClefResponse)
async def get_clef(clef_id: str, _user: dict = Depends(get_current_user)):
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
async def create_clef(clef_in: ClefCreate, _user: dict = Depends(require_editor)):
    repo = _repo()
    now = now_utc_iso()
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
async def update_clef(clef_id: str, clef_in: ClefUpdate, _user: dict = Depends(require_editor)):
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
async def delete_clef(clef_id: str, _user: dict = Depends(require_admin)):
    repo = _repo()
    existing = await repo.get(clef_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Clef not found")
    await repo.delete(clef_id)
    return Response(status_code=204)


@router.post("/{clef_id}/run-now", status_code=status.HTTP_202_ACCEPTED)
async def run_clef_now(clef_id: str, _user: dict = Depends(require_editor)) -> dict:
    """Dispatch a clef for immediate execution. Returns 202 with job_id."""
    try:
        dispatcher = get_dispatcher()
        job_id = await dispatcher.dispatch(clef_id)
        job_status = await dispatcher.get_status(job_id)
        logger.info("Dispatched clef %s, job_id=%s", clef_id, job_id)
        return {
            "job_id": job_id,
            "clef_id": clef_id,
            "status": job_status.value,
        }
    except Exception as e:
        logger.error("Failed to dispatch clef %s: %s", clef_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dispatch check",
        )


@router.get("/{clef_id}/results")
async def get_clef_results(
    clef_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Get historical execution results for a specific clef with pagination."""
    try:
        executor = get_executor()

        count_result = await executor.query(
            "SELECT COUNT(*) as total FROM checks WHERE clef_id = ?",
            [clef_id],
        )
        total = count_result[0]["total"] if count_result else 0

        results = await executor.query(
            """
                SELECT * FROM checks
                WHERE clef_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """,
            [clef_id, limit, offset],
        )

        formatted_results = []
        for result in results:
            metadata = None
            if result["details"]:
                try:
                    metadata = (
                        json.loads(result["details"])
                        if isinstance(result["details"], str)
                        else result["details"]
                    )
                except (json.JSONDecodeError, TypeError):
                    metadata = result["details"]

            # Normalise to UTC ISO format with Z suffix
            timestamp = result["timestamp"]
            if timestamp and not timestamp.endswith("Z"):
                timestamp = to_utc_isoformat(timestamp)

            formatted_results.append(
                {
                    "id": result["id"],
                    "status": result["status"],
                    "message": result["message"],
                    "timestamp": timestamp,
                    "execution_time": result["execution_time"],
                    "anomalies_count": result["anomalies_count"],
                    "severity": result["severity"],
                    "metadata": metadata,
                }
            )

        return {
            "clef_id": clef_id,
            "results": formatted_results,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            },
            "_timezone_info": {
                "backend_timezone": "UTC",
                "timestamp_format": "ISO 8601 with Z suffix (e.g., 2025-10-08T22:30:00Z)",
                "note": "All timestamps are stored and processed in UTC. UI converts to local timezone for display.",
            },
        }

    except Exception as e:
        logger.error("Failed to get results for clef %s: %s", clef_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get clef results",
        )
