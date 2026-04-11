"""
Authentication endpoints for DataMetronome Podium.

Route handlers only (login, register, /me, PATCH /me).
Core auth utilities (get_current_user, create_access_token, security) live in
datametronome_podium.core.auth so all feature routers can import from one place.
"""

import json
import logging
import sqlite3
from typing import Any

from pydantic import BaseModel

from datametronome_podium.api.schemas.auth import (
    SetupInit,
    SetupStatus,
    Token,
    UserCreate,
    UserLogin,
)
from datametronome_podium.core.auth import (
    create_access_token,
    get_current_user,
    security,
)
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.security import get_password_hash, verify_password
from datametronome_podium.core.timestamp_utils import now_utc_iso
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
logger = logging.getLogger(__name__)


class DashboardPrefs(BaseModel):
    pinned_staves: list[str] = []


class PatchUserRequest(BaseModel):
    dashboard_prefs: DashboardPrefs


def _pg_unique_violation(exc: BaseException | None) -> bool:
    """Postgres unique violation (asyncpg or SQLSTATE 23505)."""
    if exc is None:
        return False
    try:
        import asyncpg

        if isinstance(exc, asyncpg.exceptions.UniqueViolationError):
            return True
    except ImportError:
        pass
    if getattr(exc, "sqlstate", None) == "23505":
        return True
    return False


def _is_duplicate_user_insert(exc: BaseException) -> bool:
    """True if the insert failed only because of a uniqueness constraint."""
    if _pg_unique_violation(exc):
        return True
    bc = exc.__cause__
    if isinstance(bc, BaseException) and _pg_unique_violation(bc):
        return True
    if isinstance(exc, sqlite3.IntegrityError):
        return "unique" in str(exc).lower()
    if isinstance(bc, sqlite3.IntegrityError):
        return "unique" in str(bc).lower()
    lowered = str(exc).lower()
    return "unique" in lowered or "duplicate" in lowered


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin) -> dict[str, str]:
    """Authenticate user and return access token.

    Args:
        user_credentials: User login credentials.

    Returns:
        Access token.

    Raises:
        HTTPException: If authentication fails.
    """
    users = await get_executor().query(
        "SELECT username, hashed_password FROM users WHERE username = ?",
        [user_credentials.username],
    )
    user = users[0] if users else None

    if not user or not verify_password(user_credentials.password, str(user["hashed_password"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # expires_delta omitted — create_access_token defaults to settings.access_token_expire_minutes
    access_token = create_access_token(data={"sub": user["username"]})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate) -> dict[str, str]:
    """Register a new user.

    Args:
        user_data: User registration data.

    Returns:
        Access token for the new user.

    Raises:
        HTTPException: If registration fails.
    """
    existing_users = await get_executor().query(
        "SELECT 1 FROM users WHERE username = ?", [user_data.username]
    )
    if existing_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    now = now_utc_iso()

    new_user_data = {
        "id": user_data.username,  # Use username as ID for simplicity
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await get_executor().insert("users", new_user_data)
    except Exception as e:
        if _is_duplicate_user_insert(e):
            logger.warning(
                "Duplicate user registration (constraint): username=%s",
                user_data.username,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            ) from e
        logger.exception("User insert failed for username=%s", user_data.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        ) from e

    # Generate access token — expires_delta defaults to settings.access_token_expire_minutes
    access_token = create_access_token(data={"sub": user_data.username})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=dict[str, Any])
async def get_current_user_info(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Get current user information.

    Args:
        current_user: Current authenticated user.

    Returns:
        Current user information.
    """
    # Parse dashboard_prefs — stored as JSON text in DB, default to empty prefs
    raw_prefs = current_user.get("dashboard_prefs") or "{}"
    try:
        prefs = json.loads(raw_prefs) if isinstance(raw_prefs, str) else raw_prefs
    except (ValueError, TypeError):
        prefs = {}
    if "pinned_staves" not in prefs:
        prefs["pinned_staves"] = []

    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "is_active": current_user["is_active"],
        "role": current_user.get("role", "viewer"),
        "dashboard_prefs": prefs,
    }


@router.patch("/me", response_model=dict[str, Any])
async def patch_current_user(
    body: PatchUserRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Update current user preferences.

    Accepts: { "dashboard_prefs": { "pinned_staves": ["id1", "id2", "id3"] } }
    Replaces dashboard_prefs fully (not a merge).
    """
    pinned = body.dashboard_prefs.pinned_staves

    if len(pinned) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pinned_staves cannot exceed 3 entries",
        )

    prefs_to_save = {"pinned_staves": [str(s) for s in pinned]}
    prefs_json = json.dumps(prefs_to_save)

    await get_executor().execute(
        "UPDATE users SET dashboard_prefs = ? WHERE username = ?",
        [prefs_json, current_user["username"]],
    )

    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "is_active": current_user["is_active"],
        "role": current_user.get("role", "viewer"),
        "dashboard_prefs": prefs_to_save,
    }


@router.get("/setup/status", response_model=SetupStatus)
async def setup_status() -> dict[str, bool]:
    """Check if first-run setup is needed (users table is empty)."""
    rows = await get_executor().query("SELECT COUNT(*) AS cnt FROM users", [])
    count = rows[0]["cnt"] if rows else 0
    return {"needs_setup": count == 0}


@router.post("/setup/init", response_model=Token)
async def setup_init(body: SetupInit) -> dict[str, str]:
    """Create the initial admin account. Only works when no users exist."""
    rows = await get_executor().query("SELECT COUNT(*) AS cnt FROM users", [])
    count = rows[0]["cnt"] if rows else 0
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already completed — users exist",
        )

    hashed_password = get_password_hash(body.password)
    now = now_utc_iso()

    await get_executor().insert("users", {
        "id": body.username,
        "username": body.username,
        "email": body.email,
        "hashed_password": hashed_password,
        "is_active": True,
        "role": "admin",
        "created_at": now,
        "updated_at": now,
    })

    access_token = create_access_token(data={"sub": body.username})
    return {"access_token": access_token, "token_type": "bearer"}
