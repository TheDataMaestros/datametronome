"""Staves API router."""
import json
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from datametronome_podium.core.auth import get_current_user, require_admin, require_editor
from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.group_access import (
    assert_group_membership,
    assert_stave_group_access,
    is_super_admin,
    user_group_ids,
)
from datametronome_podium.core.encryption import (
    MASKED_VALUE,
    encrypt_sensitive_fields,
    mask_sensitive_fields,
)
from datametronome_podium.core.redis import get_redis_client
from datametronome_podium.core.timestamp_utils import now_utc_iso
from datametronome_podium.features.staves.model import StaveRow as Stave
from datametronome_podium.features.staves.repo import StaveRepo
from datametronome_podium.features.staves.schema import (
    VALID_DATA_SOURCE_TYPES,
    StaveCreate,
    StaveUpdate,
    StaveResponse,
)
import datametronome_podium.features.staves.service as stave_svc

router = APIRouter()



def _dispatch_auto_scan(stave_id: str) -> None:
    """Dispatch auto-scan task and register daily schedule.

    Uses Celery's built-in countdown retry rather than a background thread +
    time.sleep, which could block a worker thread and leak resources when the
    broker is temporarily unavailable.
    """
    import logging
    log = logging.getLogger(__name__)

    try:
        from datametronome_podium.tasks.intelligence_tasks import run_auto_scan
        run_auto_scan.apply_async(args=[stave_id], countdown=0)
        log.info("Auto-scan dispatched for stave %s", stave_id)
    except Exception as e:
        # If the broker is unavailable at stave creation time, schedule a
        # delayed retry via Celery rather than sleeping in a thread.
        log.warning("Auto-scan dispatch failed for %s: %s. Will retry via Celery.", stave_id, e)
        try:
            from datametronome_podium.tasks.intelligence_tasks import run_auto_scan
            run_auto_scan.apply_async(args=[stave_id], countdown=5)
        except Exception as e2:
            log.error("Auto-scan dispatch failed permanently for %s: %s", stave_id, e2)

    try:
        from datametronome_podium.services.intelligence_scheduler import register_daily_intelligence
        register_daily_intelligence(stave_id)
    except Exception:
        pass


def _prepare_stave_response(data: dict[str, Any]) -> dict[str, Any]:
    """Parse connection_config JSON and mask sensitive fields for API responses."""
    if isinstance(data.get("connection_config"), str):
        try:
            data["connection_config"] = json.loads(data["connection_config"])
        except (json.JSONDecodeError, TypeError):
            pass
    if isinstance(data.get("connection_config"), dict):
        data["connection_config"] = mask_sensitive_fields(
            data["connection_config"], data.get("data_source_type")
        )
    return data


def _repo() -> StaveRepo:
    return StaveRepo(get_executor())


async def _resolve_create_group(user: dict, requested: str | None) -> str:
    """Decide which group a new stave belongs to.

    An explicit group is honoured if the caller may write to it. Otherwise it
    is inferred, but only when there is exactly one candidate: guessing between
    several groups would silently put a data source somewhere unintended.
    """
    if requested:
        await assert_group_membership(requested, user)
        return requested

    groups = await user_group_ids(user)
    if len(groups) == 1:
        return groups[0]

    if is_super_admin(user):
        raise HTTPException(
            status_code=400,
            detail="group_id is required: admins are not scoped to one group",
        )
    if not groups:
        raise HTTPException(
            status_code=403,
            detail="You do not belong to any group. Ask an admin to add you to one.",
        )
    raise HTTPException(
        status_code=400,
        detail="group_id is required: you belong to more than one group",
    )


def _get_circuit_breaker() -> StaveCircuitBreaker | None:
    """Get circuit breaker if Redis is available. Returns None otherwise."""
    try:
        client = get_redis_client()
        return StaveCircuitBreaker(redis_client=client, executor=get_executor())
    except Exception:
        return None


@router.get("/", response_model=list[StaveResponse])
async def get_staves(skip: int = 0, limit: int = 100, _user: dict = Depends(get_current_user)):
    repo = _repo()
    staves = await repo.list(limit=limit, offset=skip)
    results = []
    for s in staves:
        data = _prepare_stave_response(s.model_dump())
        results.append(data)
    return results


@router.get("/types")
async def get_stave_types(_user: dict = Depends(get_current_user)):
    """The types a stave can be created with.

    Served from the schema's list rather than a copy. This endpoint used to
    keep its own, which drifted: it still advertised only postgres, sqlite,
    bigquery and dbt after redshift and s3 shipped, so a client building a
    picker from it could not offer them.
    """
    return VALID_DATA_SOURCE_TYPES


@router.get("/{stave_id}", response_model=StaveResponse)
async def get_stave(stave_id: str, _user: dict = Depends(get_current_user)):
    repo = _repo()
    stave = await repo.get(stave_id)
    if not stave:
        raise HTTPException(status_code=404, detail="Stave not found")
    return _prepare_stave_response(stave.model_dump())


@router.get("/{stave_id}/delete-info")
async def get_stave_delete_info(stave_id: str, _user: dict = Depends(get_current_user)):
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
async def create_stave(
    stave_in: StaveCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_editor),
):
    repo = _repo()
    group_id = await _resolve_create_group(user, stave_in.group_id)
    now = now_utc_iso()
    encrypted_config = encrypt_sensitive_fields(
        stave_in.connection_config, stave_in.data_source_type
    )
    stave = Stave(
        id=str(uuid.uuid4()),
        name=stave_in.name,
        description=stave_in.description,
        data_source_type=stave_in.data_source_type,
        connection_config=json.dumps(encrypted_config),
        is_active=stave_in.is_active,
        group_id=group_id,
        created_at=now,
        updated_at=now,
    )
    await repo.create(stave)
    data = stave.model_dump()
    data["connection_config"] = mask_sensitive_fields(
        stave_in.connection_config, stave_in.data_source_type
    )
    # Dispatch intelligence scan in background to avoid blocking the response
    # with sync Redis I/O from register_daily_intelligence().
    background_tasks.add_task(_dispatch_auto_scan, stave.id)
    return data


@router.put("/{stave_id}", response_model=StaveResponse)
async def update_stave(stave_id: str, stave_in: StaveUpdate, user: dict = Depends(require_editor)):
    await assert_stave_group_access(stave_id, user)
    repo = _repo()
    existing = await repo.get(stave_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Stave not found")
    update_data = stave_in.model_dump(exclude_unset=True)
    if "connection_config" in update_data and isinstance(update_data["connection_config"], dict):
        # Preserve existing encrypted values when user sends MASKED_VALUE
        existing_config_raw = existing.connection_config
        if isinstance(existing_config_raw, str):
            try:
                existing_config_raw = json.loads(existing_config_raw)
            except (json.JSONDecodeError, TypeError):
                existing_config_raw = {}
        if isinstance(existing_config_raw, dict):
            from datametronome_podium.core.encryption import _sensitive_keys
            ds_type = update_data.get("data_source_type") or existing.data_source_type
            for key in _sensitive_keys(ds_type):
                if update_data["connection_config"].get(key) == MASKED_VALUE:
                    # Keep the existing (encrypted) value from DB
                    if key in existing_config_raw:
                        update_data["connection_config"][key] = existing_config_raw[key]
                    else:
                        del update_data["connection_config"][key]
        update_data["connection_config"] = json.dumps(
            encrypt_sensitive_fields(
                update_data["connection_config"],
                update_data.get("data_source_type") or existing.data_source_type,
            )
        )
    now = now_utc_iso()
    update_data["updated_at"] = now
    await repo.update(stave_id, update_data)
    updated = await repo.get(stave_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Stave not found")
    return _prepare_stave_response(updated.model_dump())


@router.post("/{stave_id}/unpause")
async def unpause_stave(stave_id: str, background_tasks: BackgroundTasks, user: dict = Depends(require_editor)):
    await assert_stave_group_access(stave_id, user)
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
        def safe_register():
            try:
                register_daily_intelligence(stave_id)
            except Exception:
                pass
        background_tasks.add_task(safe_register)
    except Exception:
        pass

    return {"message": "Stave unpaused", "stave_id": stave_id}


@router.delete("/{stave_id}")
async def delete_stave(stave_id: str, force: bool = False, user: dict = Depends(require_admin)):
    await assert_stave_group_access(stave_id, user)
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


# ---------------------------------------------------------------------------
# Stave action endpoints (migrated from api/v1/endpoints/stave_actions.py)
# ---------------------------------------------------------------------------

class PreviewDataRequest(BaseModel):
    """Request body for the preview-data endpoint."""
    table_name: str
    count: int = Field(default=100, ge=1, le=500_000)


@router.post("/{stave_id}/test-connection")
async def test_stave_connection(
    stave_id: str, user: dict = Depends(require_editor)
) -> dict[str, Any]:
    """Test connectivity to a stave's data source.

    Group-guarded: this opens a connection to another team's database using
    their stored credentials, which is an action against their infrastructure
    rather than a read of ours.
    """
    await assert_stave_group_access(stave_id, user)
    try:
        return await stave_svc.test_connection(stave_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "Connection test failed for stave %s: %s", stave_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection test failed",
        )


@router.post("/{stave_id}/preview-data")
async def preview_stave_data(
    stave_id: str, request: PreviewDataRequest, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    """Preview rows from a stave table (capped at 500 rows).

    Group-scoped rather than role-gated. This returns real rows from the
    owning team's database, so membership is the right gate, and a viewer in
    that group should see their own group's data.
    """
    await assert_stave_group_access(stave_id, user)
    try:
        return await stave_svc.preview_data(stave_id, request.table_name, request.count)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "Data preview failed for stave %s, table %s: %s",
            stave_id, request.table_name, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data preview failed",
        )


@router.get("/{stave_id}/tables")
async def list_stave_tables(
    stave_id: str,
    include_structure: bool = Query(True, description="Include table structure/schema"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """List tables available in a stave's data source.

    Group-scoped for the same reason as preview-data: it reads the source
    database's schema, not our metadata about it.
    """
    await assert_stave_group_access(stave_id, user)
    try:
        return await stave_svc.list_tables(stave_id, include_structure=include_structure)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "Failed to list tables for stave %s: %s", stave_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tables",
        )
