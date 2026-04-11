"""User management router — admin-only CRUD for user accounts."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from datametronome_podium.core.auth import require_admin
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.security import get_password_hash
from datametronome_podium.core.timestamp_utils import now_utc_iso
from datametronome_podium.features.users.repo import UserRepo
from datametronome_podium.features.users.schema import (
    AdminUserCreate,
    PasswordReset,
    UserDetailResponse,
    UserUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _repo() -> UserRepo:
    return UserRepo(get_executor())


@router.get("/", response_model=list[UserDetailResponse])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    _user: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    """List all users (excludes hashed_password)."""
    return await _repo().list_all(limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Get a single user by ID."""
    user = await _repo().find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    row = user.model_dump()
    row.pop("hashed_password", None)
    return row


@router.post("/", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: AdminUserCreate,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Create a new user (admin only)."""
    repo = _repo()

    # Check duplicate username
    if await repo.exists(body.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    # Check duplicate email
    if await repo.find_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already in use")

    now = now_utc_iso()
    from datametronome_podium.features.users.model import UserRow

    new_user = UserRow(
        id=body.username,
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        is_active=True,
        role=body.role,
        created_at=now,
        updated_at=now,
    )
    await repo.create(new_user)

    result = new_user.model_dump()
    result.pop("hashed_password", None)
    return result


@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    current_user: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Update user role, email, or active status."""
    repo = _repo()
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Self-protection: cannot demote or deactivate yourself
    is_self = current_user.get("id") == user_id or current_user.get("username") == user.username
    if is_self:
        if "role" in updates and updates["role"] != current_user.get("role"):
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        if "is_active" in updates and not updates["is_active"]:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    # Check duplicate email if changing
    if "email" in updates and updates["email"] != user.email:
        existing = await repo.find_by_email(updates["email"])
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")

    updates["updated_at"] = now_utc_iso()
    await repo.update(user_id, updates)

    # Re-fetch to return updated state
    updated = await repo.find_by_id(user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found after update")
    result = updated.model_dump()
    result.pop("hashed_password", None)
    return result


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    body: PasswordReset,
    _user: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    """Reset a user's password (admin only)."""
    repo = _repo()
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await repo.update(user_id, {
        "hashed_password": get_password_hash(body.new_password),
        "updated_at": now_utc_iso(),
    })
    return {"message": "Password reset successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    hard: bool = False,
    current_user: dict[str, Any] = Depends(require_admin),
) -> dict[str, str]:
    """Delete a user. Soft-delete by default (sets is_active=false), hard-delete with ?hard=true."""
    repo = _repo()
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Self-protection
    is_self = current_user.get("id") == user_id or current_user.get("username") == user.username
    if is_self:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    if hard:
        await repo.delete(user_id)
        return {"message": f"User '{user.username}' permanently deleted"}
    else:
        await repo.update(user_id, {"is_active": False, "updated_at": now_utc_iso()})
        return {"message": f"User '{user.username}' deactivated"}
