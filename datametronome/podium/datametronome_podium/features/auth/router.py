"""
Authentication endpoints for DataMetronome Podium.

Route handlers only (login, /me, PATCH /me, first-run setup).
Core auth utilities (get_current_user, create_access_token, security) live in
datametronome_podium.core.auth so all feature routers can import from one place.
"""

import json
import logging
from typing import Any

from pydantic import BaseModel

from datametronome_podium.api.schemas.auth import (
    PasswordChange,
    SetupInit,
    SetupStatus,
    Token,
    UserLogin,
)
from datametronome_podium.core.auth import (
    create_access_token,
    get_current_user,
    security,
)
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.security import get_password_hash, verify_password
from datametronome_podium.core.rate_limit import limiter
from datametronome_podium.core.timestamp_utils import now_utc_iso
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

router = APIRouter()
logger = logging.getLogger(__name__)


class DashboardPrefs(BaseModel):
    pinned_staves: list[str] = []


class PatchUserRequest(BaseModel):
    dashboard_prefs: DashboardPrefs


@router.post("/login", response_model=Token)
@limiter.limit("10 per minute")
async def login(
    request: Request, response: Response, user_credentials: UserLogin
) -> dict[str, str]:
    """Authenticate user and return access token.

    Rate limited well below the global default. The global 100 per minute
    still allows password guessing at a useful rate.

    `request` and `response` are both unused here and both required by
    slowapi. It reads the caller from the request, and because the limiter
    runs with headers_enabled it writes the rate-limit headers into the
    response. Omitting `response` makes every call to this endpoint raise.

    Args:
        request: Incoming request, used by the rate limiter.
        response: Outgoing response, used by the rate limiter for headers.
        user_credentials: User login credentials.

    Returns:
        Access token.

    Raises:
        HTTPException: If authentication fails.
    """
    users = await get_executor().query(
        "SELECT username, hashed_password, is_active FROM users WHERE username = ?",
        [user_credentials.username],
    )
    user = users[0] if users else None

    if not user or not verify_password(user_credentials.password, str(user["hashed_password"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # get_current_user rejects a disabled account on every later request, but
    # without this check login still hands out a token and answers 200, which
    # confirms the password was right.
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # expires_delta omitted — create_access_token defaults to settings.access_token_expire_minutes
    access_token = create_access_token(data={"sub": user["username"]})

    return {"access_token": access_token, "token_type": "bearer"}


# Self-service registration was removed deliberately. It was public, assigned
# the default 'viewer' role, and gave anyone who could reach the API read
# access to every stave. Accounts are created by an admin via POST /users/,
# or by POST /auth/setup/init for the very first account.


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


@router.post("/me/password")
@limiter.limit("5 per minute")
async def change_own_password(
    request: Request,
    response: Response,
    body: PasswordChange,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Change the signed-in user's own password.

    Requires the current password, so holding a stolen token is not enough to
    take the account over. Admins can still reset a forgotten one through
    POST /users/{id}/reset-password.

    `request` and `response` are required by the rate limiter, not used here.
    """
    users = await get_executor().query(
        "SELECT hashed_password FROM users WHERE username = ?",
        [current_user["username"]],
    )
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not verify_password(body.current_password, str(users[0]["hashed_password"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current one",
        )

    await get_executor().execute(
        "UPDATE users SET hashed_password = ?, updated_at = ? WHERE username = ?",
        [get_password_hash(body.new_password), now_utc_iso(), current_user["username"]],
    )
    logger.info("Password changed for user %s", current_user["username"])
    return {"message": "Password updated"}


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
