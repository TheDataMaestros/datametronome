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


class TestLoginEndpoint:
    """Login exercised through the real app.

    Both cases below shipped green through the unit suite and only showed up
    when the app was actually booted and driven.
    """

    @staticmethod
    def _client():
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from datametronome_podium.core.rate_limit import limiter
        from datametronome_podium.features.auth.router import router

        app = FastAPI()
        app.state.limiter = limiter
        app.include_router(router, prefix="/auth")
        return TestClient(app)

    @staticmethod
    def _rows(is_active):
        from datametronome_podium.core.security import get_password_hash

        return [
            {
                "username": "alice",
                "hashed_password": get_password_hash("correct-horse"),
                "is_active": is_active,
            }
        ]

    def test_login_succeeds_for_active_user(self):
        """The limiter decorator needs `response` in the signature.

        Without it slowapi raises while injecting rate-limit headers and every
        login returns 500.
        """
        executor = AsyncMock()
        executor.query = AsyncMock(return_value=self._rows(True))

        with patch(
            "datametronome_podium.features.auth.router.get_executor",
            return_value=executor,
        ):
            response = self._client().post(
                "/auth/login", json={"username": "alice", "password": "correct-horse"}
            )

        assert response.status_code == 200
        assert response.json()["access_token"]

    def test_disabled_user_cannot_obtain_a_token(self):
        """A disabled account must not get a token, even a useless one.

        get_current_user rejects it on every later request, but a 200 here
        still confirms the password was right.
        """
        executor = AsyncMock()
        executor.query = AsyncMock(return_value=self._rows(False))

        with patch(
            "datametronome_podium.features.auth.router.get_executor",
            return_value=executor,
        ):
            response = self._client().post(
                "/auth/login", json={"username": "alice", "password": "correct-horse"}
            )

        assert response.status_code == 401
        assert "access_token" not in response.json()


class TestChangeOwnPassword:
    """A signed-in user changing their own password."""

    @staticmethod
    def _client(user):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from datametronome_podium.core.auth import get_current_user
        from datametronome_podium.core.rate_limit import limiter
        from datametronome_podium.features.auth.router import router

        app = FastAPI()
        app.state.limiter = limiter
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    @staticmethod
    def _executor(stored_password):
        from datametronome_podium.core.security import get_password_hash

        executor = AsyncMock()
        executor.query = AsyncMock(
            return_value=[{"hashed_password": get_password_hash(stored_password)}]
        )
        executor.execute = AsyncMock()
        return executor

    def _post(self, body, stored_password="correct-horse", user=None):
        executor = self._executor(stored_password)
        client = self._client(user or {"username": "alice", "role": "viewer"})
        with patch(
            "datametronome_podium.features.auth.router.get_executor",
            return_value=executor,
        ):
            return client.post("/auth/me/password", json=body), executor

    def test_correct_current_password_updates_the_hash(self):
        response, executor = self._post(
            {"current_password": "correct-horse", "new_password": "battery-staple"}
        )

        assert response.status_code == 200
        executor.execute.assert_awaited_once()

    def test_wrong_current_password_is_refused(self):
        """A stolen token alone must not be enough to take over the account."""
        response, executor = self._post(
            {"current_password": "guessing", "new_password": "battery-staple"}
        )

        assert response.status_code == 401
        executor.execute.assert_not_awaited()

    def test_reusing_the_current_password_is_refused(self):
        response, executor = self._post(
            {"current_password": "correct-horse", "new_password": "correct-horse"}
        )

        assert response.status_code == 400
        executor.execute.assert_not_awaited()

    def test_short_new_password_is_refused_before_any_write(self):
        response, executor = self._post(
            {"current_password": "correct-horse", "new_password": "short"}
        )

        assert response.status_code == 422
        executor.execute.assert_not_awaited()
