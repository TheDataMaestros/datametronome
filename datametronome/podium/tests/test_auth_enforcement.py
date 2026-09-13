"""Tests for authentication enforcement in get_current_user."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from datametronome_podium.core.auth import create_access_token, get_current_user

ACTIVE_ROW = {
    "id": "alice",
    "username": "alice",
    "email": "alice@example.com",
    "role": "viewer",
    "is_active": True,
    "dashboard_prefs": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def _creds(username: str = "alice", **kwargs) -> HTTPAuthorizationCredentials:
    token = create_access_token(data={"sub": username}, **kwargs)
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _executor_returning(rows):
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=rows)
    return executor


@pytest.mark.asyncio
async def test_active_user_is_allowed():
    with patch(
        "datametronome_podium.core.auth.get_executor",
        return_value=_executor_returning([ACTIVE_ROW]),
    ):
        user = await get_current_user(_creds())

    assert user["username"] == "alice"


@pytest.mark.asyncio
@pytest.mark.parametrize("disabled_value", [False, 0])
async def test_disabled_user_is_rejected(disabled_value):
    """Deactivating a user must actually revoke access.

    Postgres stores a bool and SQLite stores 0/1, so both shapes must reject.
    """
    row = {**ACTIVE_ROW, "is_active": disabled_value}

    with patch(
        "datametronome_podium.core.auth.get_executor",
        return_value=_executor_returning([row]),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds())

    assert exc.value.status_code == 401
    assert "disabled" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_null_is_active_fails_closed():
    """A NULL must not be treated as active."""
    row = {**ACTIVE_ROW, "is_active": None}

    with patch(
        "datametronome_podium.core.auth.get_executor",
        return_value=_executor_returning([row]),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds())

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_unknown_user_is_rejected():
    with patch(
        "datametronome_podium.core.auth.get_executor",
        return_value=_executor_returning([]),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_creds("ghost"))

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_is_rejected():
    creds = _creds(expires_delta=timedelta(minutes=-5))

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)

    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_register_endpoint_is_gone():
    """Self-service registration was public and is deliberately removed."""
    from datametronome_podium.features.auth.router import router

    paths = {route.path for route in router.routes}  # ty: ignore[unresolved-attribute]
    assert "/register" not in paths
    assert "/login" in paths
