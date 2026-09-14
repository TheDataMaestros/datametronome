"""Group management — admin-only CRUD for groups and their membership.

Groups decide who may modify a stave. Reads are unaffected: any authenticated
user can still view every stave, clef and check result.
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from datametronome_podium.core.auth import get_current_user, require_admin
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.group_access import user_group_ids
from datametronome_podium.core.timestamp_utils import now_utc_iso
from datametronome_podium.features.groups.model import GroupRow
from datametronome_podium.features.groups.repo import GroupRepo
from datametronome_podium.features.groups.schema import (
    GroupCreate,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
)
from datametronome_podium.features.users.repo import UserRepo, is_duplicate_user_insert

router = APIRouter()
logger = logging.getLogger(__name__)


def _repo() -> GroupRepo:
    return GroupRepo(get_executor())


@router.get("/", response_model=list[GroupResponse])
async def list_groups(
    limit: int = 100,
    offset: int = 0,
    _user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List groups. Readable by any authenticated user."""
    return [g.model_dump() for g in await _repo().list_all(limit=limit, offset=offset)]


@router.get("/mine", response_model=list[GroupResponse])
async def list_my_groups(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Groups the caller belongs to.

    Returns whole records rather than ids so a client can show which group it
    is acting in without a second call to resolve names.
    """
    ids = set(await user_group_ids(user))
    if not ids:
        return []
    return [g.model_dump() for g in await _repo().list_all(limit=500) if g.id in ids]


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    group = await _repo().get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.model_dump()


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    repo = _repo()
    if await repo.find_by_name(body.name):
        raise HTTPException(status_code=409, detail="Group name already exists")

    now = now_utc_iso()
    group = GroupRow(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        created_at=now,
        updated_at=now,
    )
    try:
        await repo.create(group)
    except Exception as e:
        # The name check above races with a concurrent create.
        if is_duplicate_user_insert(e):
            raise HTTPException(status_code=409, detail="Group name already exists") from e
        raise
    return group.model_dump()


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    body: GroupUpdate,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    repo = _repo()
    group = await repo.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "name" in updates and updates["name"] != group.name:
        if await repo.find_by_name(updates["name"]):
            raise HTTPException(status_code=409, detail="Group name already exists")

    updates["updated_at"] = now_utc_iso()
    await repo.update(group_id, updates)

    updated = await repo.get(group_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Group not found after update")
    return updated.model_dump()


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    """Delete a group. Refused while staves still belong to it.

    Deleting a group that owns staves would leave them with no owner, which
    assert_stave_group_access treats as unwritable by anyone but an admin.
    """
    repo = _repo()
    group = await repo.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    owned = await repo.stave_count(group_id)
    if owned:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Group still owns {owned} data source(s). "
                "Reassign them before deleting the group."
            ),
        )

    await repo.delete(group_id)
    return {"message": f"Group '{group.name}' deleted"}


@router.get("/{group_id}/members", response_model=list[GroupMemberResponse])
async def list_members(
    group_id: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = _repo()
    if not await repo.get(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    return await repo.members(group_id)


@router.post("/{group_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    group_id: str,
    body: GroupMemberAdd,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    repo = _repo()
    if not await repo.get(group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    if not await UserRepo(get_executor()).find_by_id(body.user_id):
        raise HTTPException(status_code=404, detail="User not found")

    if await repo.is_member(group_id, body.user_id):
        return {"message": "User is already a member"}

    try:
        await repo.add_member(group_id, body.user_id, now_utc_iso())
    except Exception as e:
        # Composite primary key settles the race with a concurrent add.
        if is_duplicate_user_insert(e):
            return {"message": "User is already a member"}
        raise
    return {"message": "Member added"}


@router.delete("/{group_id}/members/{user_id}")
async def remove_member(
    group_id: str,
    user_id: str,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    repo = _repo()
    if not await repo.is_member(group_id, user_id):
        raise HTTPException(status_code=404, detail="User is not a member of this group")
    await repo.remove_member(group_id, user_id)
    return {"message": "Member removed"}
