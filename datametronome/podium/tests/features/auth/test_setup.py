"""Tests for first-run setup wizard endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from datametronome_podium.api.schemas.auth import SetupInit


def _mock_executor(query_rows=None):
    """Return a mock QueryExecutor with configurable query results."""
    mock = MagicMock()
    mock.query = AsyncMock(return_value=query_rows or [])
    mock.insert = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_setup_status_returns_needs_setup_true():
    """Empty DB → needs_setup: true."""
    mock = _mock_executor(query_rows=[{"cnt": 0}])
    with patch(
        "datametronome_podium.features.auth.router.get_executor",
        return_value=mock,
    ):
        from datametronome_podium.features.auth.router import setup_status

        result = await setup_status()
        assert result == {"needs_setup": True}


@pytest.mark.asyncio
async def test_setup_status_returns_needs_setup_false():
    """DB has users → needs_setup: false."""
    mock = _mock_executor(query_rows=[{"cnt": 2}])
    with patch(
        "datametronome_podium.features.auth.router.get_executor",
        return_value=mock,
    ):
        from datametronome_podium.features.auth.router import setup_status

        result = await setup_status()
        assert result == {"needs_setup": False}


@pytest.mark.asyncio
async def test_setup_init_creates_admin():
    """Setup init creates a user with role=admin."""
    mock = _mock_executor(query_rows=[{"cnt": 0}])
    with patch(
        "datametronome_podium.features.auth.router.get_executor",
        return_value=mock,
    ):
        from datametronome_podium.features.auth.router import setup_init

        body = SetupInit(username="myadmin", email="admin@example.com", password="securepass123")
        await setup_init(body)

        mock.insert.assert_called_once()
        call_args = mock.insert.call_args
        assert call_args[0][0] == "users"
        inserted = call_args[0][1]
        assert inserted["username"] == "myadmin"
        assert inserted["email"] == "admin@example.com"
        assert inserted["role"] == "admin"
        assert inserted["is_active"] is True
        assert "hashed_password" in inserted
        # Password should be hashed, not plaintext
        assert inserted["hashed_password"] != "securepass123"


@pytest.mark.asyncio
async def test_setup_init_returns_token():
    """Setup init returns a valid access token."""
    mock = _mock_executor(query_rows=[{"cnt": 0}])
    with patch(
        "datametronome_podium.features.auth.router.get_executor",
        return_value=mock,
    ):
        from datametronome_podium.features.auth.router import setup_init

        body = SetupInit(username="myadmin", email="admin@example.com", password="securepass123")
        result = await setup_init(body)

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert len(result["access_token"]) > 0


@pytest.mark.asyncio
async def test_setup_init_rejects_when_users_exist():
    """Setup init returns 409 when users already exist."""
    mock = _mock_executor(query_rows=[{"cnt": 1}])
    with patch(
        "datametronome_podium.features.auth.router.get_executor",
        return_value=mock,
    ):
        from datametronome_podium.features.auth.router import setup_init

        body = SetupInit(username="myadmin", email="admin@example.com", password="securepass123")
        with pytest.raises(HTTPException) as exc_info:
            await setup_init(body)

        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_setup_init_validates_password_length():
    """SetupInit schema rejects passwords shorter than 8 chars."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        SetupInit(username="admin", email="a@b.com", password="short")

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("password",) for e in errors)
