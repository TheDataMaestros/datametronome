"""User memory API router."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from datametronome_podium.api.deps import get_current_user
from datametronome_podium.core.database import get_executor
from datametronome_podium.features.user_memory.repo import UserMemoryRepo
from datametronome_podium.features.user_memory.schemas import (
    UserMemoryCreate,
    UserMemoryProfileResponse,
    UserMemoryResponse,
    UserMemoryUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _repo() -> UserMemoryRepo:
    """Build UserMemoryRepo with the current database executor."""
    return UserMemoryRepo(get_executor())


def _get_user_id(current_user: dict) -> str:
    """Extract user_id from the authenticated user dict."""
    user_id = current_user.get("id")
    if not user_id:
        # Refuse to proceed — falling back to a placeholder would violate FK constraints.
        raise HTTPException(status_code=401, detail="User ID not found in authentication token")
    return user_id


def _dispatch_rebuild(user_id: str) -> None:
    """Fire-and-forget: dispatch Celery task to rebuild the user's memory profile.

    Wrapped in try/except because Celery may not be running in all environments
    (dev, tests). The profile rebuild is async and non-critical — the data is
    already persisted before this is called.
    """
    try:
        from datametronome_podium.tasks.user_memory_tasks import rebuild_user_profile
        rebuild_user_profile.delay(user_id)
    except Exception:
        logger.warning("Failed to dispatch profile rebuild for user %s", user_id)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _gen_memory_id() -> str:
    return f"mem-{uuid.uuid4().hex[:12]}"


# --- Profile ---


@router.get("/profile", response_model=UserMemoryProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get the precomputed memory profile for the current user."""
    user_id = _get_user_id(current_user)
    profile = await _repo().get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="No memory profile found for this user")
    return profile


# --- Memory list / search ---


@router.get("/", response_model=list[UserMemoryResponse])
async def list_memories(
    category: str | None = None,
    active: bool | None = None,
    q: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """List or search memories for the current user.

    When `active` is omitted the search defaults to active-only (consistent
    with the repo's default). Pass `active=false` to include inactive memories.
    """
    user_id = _get_user_id(current_user)
    # active=None → default active_only=True; active=False → include all
    active_only = active if active is not None else True
    rows = await _repo().search_memories(
        user_id, q=q, category=category, active_only=active_only
    )
    return rows


# --- Single memory ---


@router.get("/{memory_id}", response_model=UserMemoryResponse)
async def get_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single memory. Fails with 404 if it doesn't exist or belongs to another user."""
    user_id = _get_user_id(current_user)
    memory = await _repo().get_memory(memory_id)
    if not memory or memory.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


# --- Create ---


@router.post("/", response_model=UserMemoryResponse, status_code=201)
async def create_memory(body: UserMemoryCreate, current_user: dict = Depends(get_current_user)):
    """Manually create a memory for the current user."""
    user_id = _get_user_id(current_user)
    now = _now_utc()
    memory_id = _gen_memory_id()

    repo = _repo()
    await repo.create_memory(
        id=memory_id,
        user_id=user_id,
        category=body.category,
        content=body.content,
        source_conversation_id=None,
        confidence=body.confidence,
        created_at=now,
        updated_at=now,
    )
    memory = await repo.get_memory(memory_id)

    _dispatch_rebuild(user_id)
    return memory


# --- Update ---


@router.patch("/{memory_id}", response_model=UserMemoryResponse)
async def update_memory(memory_id: str, body: UserMemoryUpdate, current_user: dict = Depends(get_current_user)):
    """Partially update a memory. Only `content` and `active` are patchable."""
    user_id = _get_user_id(current_user)
    repo = _repo()

    existing = await repo.get_memory(memory_id)
    if not existing or existing.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")

    patch: dict = {}
    if body.content is not None:
        patch["content"] = body.content
    # active is stored as int 0/1 in SQLite; convert bool to int here
    if body.active is not None:
        patch["active"] = 1 if body.active else 0

    if patch:
        await repo.update_memory(memory_id, patch)

    updated = await repo.get_memory(memory_id)
    _dispatch_rebuild(user_id)
    return updated


# --- Delete ---


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    """Hard-delete a memory. Returns 404 if it doesn't exist or belongs to another user."""
    user_id = _get_user_id(current_user)
    repo = _repo()

    existing = await repo.get_memory(memory_id)
    if not existing or existing.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")

    await repo.delete_memory(memory_id)
    _dispatch_rebuild(user_id)
    return Response(status_code=204)


# --- Force rebuild ---


@router.post("/rebuild", status_code=202)
async def rebuild_profile(current_user: dict = Depends(get_current_user)):
    """Force an async profile rebuild for the current user. Returns 202 Accepted."""
    user_id = _get_user_id(current_user)
    _dispatch_rebuild(user_id)
    return {"status": "queued", "user_id": user_id}
