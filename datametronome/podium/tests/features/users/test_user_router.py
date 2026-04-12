"""Tests for the admin user management router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from datametronome_podium.features.users.model import UserRow
from datametronome_podium.features.users.schema import AdminUserCreate, PasswordReset, UserUpdate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_executor(query_rows=None):
    """Return a mock QueryExecutor with configurable results."""
    mock = MagicMock()
    mock.query = AsyncMock(return_value=query_rows or [])
    mock.insert = AsyncMock()
    mock.select = AsyncMock(return_value=query_rows or [])
    mock.update = AsyncMock(return_value=1)
    mock.delete = AsyncMock(return_value=1)
    return mock


def _admin_user(username="admin", user_id="admin"):
    """Return a mock admin current_user dict."""
    return {"id": user_id, "username": username, "role": "admin", "email": "admin@test.com", "is_active": True}


def _sample_row(**overrides):
    """Return a sample user row dict."""
    row = {
        "id": "testuser",
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "$2b$12$fakehash",
        "is_active": True,
        "role": "viewer",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    row.update(overrides)
    return row


def _patch_executor(mock):
    return patch("datametronome_podium.features.users.router.get_executor", return_value=mock)


# ── List Users ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users():
    """GET / returns list of users without hashed_password."""
    rows = [
        {"id": "u1", "username": "alice", "email": "a@b.com", "is_active": True, "role": "admin", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
        {"id": "u2", "username": "bob", "email": "b@b.com", "is_active": True, "role": "viewer", "created_at": "2026-01-02T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"},
    ]
    mock = _mock_executor(rows)
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import list_users
        result = await list_users(limit=100, offset=0, _user=_admin_user())
        assert len(result) == 2
        # Ensure hashed_password is not in results
        for r in result:
            assert "hashed_password" not in r


# ── Get User ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_found():
    """GET /{id} returns user details."""
    mock = _mock_executor([_sample_row()])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import get_user
        result = await get_user("testuser", _user=_admin_user())
        assert result["username"] == "testuser"
        assert "hashed_password" not in result


@pytest.mark.asyncio
async def test_get_user_not_found():
    """GET /{id} returns 404 when user doesn't exist."""
    mock = _mock_executor([])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import get_user
        with pytest.raises(HTTPException) as exc_info:
            await get_user("nonexistent", _user=_admin_user())
        assert exc_info.value.status_code == 404


# ── Create User ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_success():
    """POST / creates a new user with hashed password."""
    mock = _mock_executor([])
    # exists() calls select with columns=["id"] → empty = not exists
    # find_by_email() calls select with where={"email": ...} → empty = not found
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import create_user
        body = AdminUserCreate(username="newuser", email="new@test.com", password="password123", role="editor")
        result = await create_user(body, _user=_admin_user())
        assert result["username"] == "newuser"
        assert result["role"] == "editor"
        assert "hashed_password" not in result
        mock.insert.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_username():
    """POST / returns 409 on duplicate username."""
    # exists() returns True when select returns rows
    mock = _mock_executor([{"id": "existing"}])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import create_user
        body = AdminUserCreate(username="existing", email="new@test.com", password="password123")
        with pytest.raises(HTTPException) as exc_info:
            await create_user(body, _user=_admin_user())
        assert exc_info.value.status_code == 409
        assert "Username" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    """POST / returns 409 on duplicate email."""
    mock = _mock_executor()
    # First select (exists check for username) → empty
    # Second select (find_by_email) → found
    mock.select = AsyncMock(side_effect=[[], [_sample_row(email="dup@test.com")]])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import create_user
        body = AdminUserCreate(username="newuser", email="dup@test.com", password="password123")
        with pytest.raises(HTTPException) as exc_info:
            await create_user(body, _user=_admin_user())
        assert exc_info.value.status_code == 409
        assert "Email" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_user_assigns_role():
    """POST / respects the role field."""
    mock = _mock_executor([])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import create_user
        body = AdminUserCreate(username="adminuser", email="admin2@test.com", password="password123", role="admin")
        result = await create_user(body, _user=_admin_user())
        assert result["role"] == "admin"


# ── Update User ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_user_success():
    """PATCH /{id} updates user fields."""
    row = _sample_row()
    updated_row = {**row, "role": "editor"}
    mock = _mock_executor()
    # First find_by_id → found, second find_by_id (re-fetch) → updated
    mock.select = AsyncMock(side_effect=[[row], [updated_row]])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import update_user
        body = UserUpdate(role="editor")
        result = await update_user("testuser", body, current_user=_admin_user())
        assert result["role"] == "editor"
        mock.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_not_found():
    """PATCH /{id} returns 404 when user doesn't exist."""
    mock = _mock_executor([])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import update_user
        body = UserUpdate(role="editor")
        with pytest.raises(HTTPException) as exc_info:
            await update_user("nonexistent", body, current_user=_admin_user())
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_user_empty_body():
    """PATCH /{id} returns 400 when no fields are provided."""
    mock = _mock_executor([_sample_row()])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import update_user
        body = UserUpdate()  # all None, nothing set
        with pytest.raises(HTTPException) as exc_info:
            await update_user("testuser", body, current_user=_admin_user())
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_self_demote_blocked():
    """PATCH /{id} blocks admins from changing their own role."""
    admin = _admin_user(username="admin", user_id="admin")
    row = _sample_row(id="admin", username="admin", role="admin")
    mock = _mock_executor([row])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import update_user
        body = UserUpdate(role="viewer")
        with pytest.raises(HTTPException) as exc_info:
            await update_user("admin", body, current_user=admin)
        assert exc_info.value.status_code == 400
        assert "own role" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_self_deactivate_blocked():
    """PATCH /{id} blocks admins from deactivating themselves."""
    admin = _admin_user(username="admin", user_id="admin")
    row = _sample_row(id="admin", username="admin", role="admin")
    mock = _mock_executor([row])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import update_user
        body = UserUpdate(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await update_user("admin", body, current_user=admin)
        assert exc_info.value.status_code == 400
        assert "own account" in exc_info.value.detail


# ── Reset Password ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_password_success():
    """POST /{id}/reset-password updates the hashed password."""
    mock = _mock_executor([_sample_row()])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import reset_password
        body = PasswordReset(new_password="newpassword123")
        result = await reset_password("testuser", body, _user=_admin_user())
        assert result["message"] == "Password reset successfully"
        mock.update.assert_called_once()
        # Check that hashed_password was set (not plaintext)
        update_call = mock.update.call_args
        data = update_call[0][1] if len(update_call[0]) > 1 else update_call[1].get("data", {})
        assert "hashed_password" in data
        assert data["hashed_password"] != "newpassword123"


@pytest.mark.asyncio
async def test_reset_password_not_found():
    """POST /{id}/reset-password returns 404 when user doesn't exist."""
    mock = _mock_executor([])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import reset_password
        body = PasswordReset(new_password="newpassword123")
        with pytest.raises(HTTPException) as exc_info:
            await reset_password("nonexistent", body, _user=_admin_user())
        assert exc_info.value.status_code == 404


# ── Delete User ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_user_soft():
    """DELETE /{id} soft-deletes (deactivates) by default."""
    mock = _mock_executor([_sample_row()])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import delete_user
        result = await delete_user("testuser", hard=False, current_user=_admin_user())
        assert "deactivated" in result["message"]
        mock.update.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_hard():
    """DELETE /{id}?hard=true permanently deletes the user."""
    mock = _mock_executor([_sample_row()])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import delete_user
        result = await delete_user("testuser", hard=True, current_user=_admin_user())
        assert "permanently deleted" in result["message"]
        mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_self_blocked():
    """DELETE /{id} blocks admins from deleting themselves."""
    admin = _admin_user(username="admin", user_id="admin")
    row = _sample_row(id="admin", username="admin")
    mock = _mock_executor([row])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import delete_user
        with pytest.raises(HTTPException) as exc_info:
            await delete_user("admin", hard=False, current_user=admin)
        assert exc_info.value.status_code == 400
        assert "own account" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_user_not_found():
    """DELETE /{id} returns 404 when user doesn't exist."""
    mock = _mock_executor([])
    with _patch_executor(mock):
        from datametronome_podium.features.users.router import delete_user
        with pytest.raises(HTTPException) as exc_info:
            await delete_user("nonexistent", hard=False, current_user=_admin_user())
        assert exc_info.value.status_code == 404
