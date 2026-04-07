"""
Core authentication utilities for DataMetronome Podium.

Provides JWT token creation, request-level user resolution, and role-based
dependency helpers. All endpoints should import from here rather than from
api/v1/endpoints/auth.py.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_executor
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

security = HTTPBearer()


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Claims to encode (must include "sub" for subject).
        expires_delta: Optional TTL override; defaults to settings value.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """FastAPI dependency — validate JWT and return the requesting user.

    Fetches explicit columns only; hashed_password is never loaded into memory
    on ordinary authenticated requests.

    Args:
        credentials: Bearer token extracted by HTTPBearer.

    Returns:
        Row dict for the authenticated user.

    Raises:
        HTTPException: 401 on any authentication failure.
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Explicit columns — hashed_password excluded to avoid loading credentials into memory.
    users = await get_executor().query(
        """
        SELECT id, username, email, role, is_active,
               dashboard_prefs, created_at, updated_at
        FROM users WHERE username = ?
        """,
        [username],
    )
    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return dict(users[0])


def require_role(*allowed_roles: str):
    """Return a FastAPI dependency that gates access by user role.

    Usage:
        router.get("/admin-only", dependencies=[Depends(require_admin)])

    Args:
        allowed_roles: One or more role strings that are permitted.

    Returns:
        An async FastAPI dependency function.
    """
    async def _check(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check


# Convenience role guards — import these directly as Depends() arguments.
require_editor = require_role("admin", "editor")
require_admin = require_role("admin")
