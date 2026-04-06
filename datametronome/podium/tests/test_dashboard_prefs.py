"""Tests for dashboard_prefs on /auth/me endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_me_includes_dashboard_prefs():
    """GET /auth/me must include dashboard_prefs with pinned_staves list."""
    mock_user = {
        "username": "admin",
        "email": "admin@datametronome.dev",
        "is_active": True,
        "is_superuser": True,
        "dashboard_prefs": json.dumps({"pinned_staves": ["stave-1", "stave-2"]}),
    }

    from datametronome_podium.api.v1.endpoints.auth import get_current_user_info

    result = await get_current_user_info(current_user=mock_user)

    assert "dashboard_prefs" in result
    prefs = result["dashboard_prefs"]
    assert isinstance(prefs, dict)
    assert prefs["pinned_staves"] == ["stave-1", "stave-2"]


@pytest.mark.asyncio
async def test_get_me_dashboard_prefs_defaults_to_empty():
    """GET /auth/me returns empty pinned_staves when dashboard_prefs is absent."""
    mock_user = {
        "username": "admin",
        "email": "admin@datametronome.dev",
        "is_active": True,
        "is_superuser": True,
        # no dashboard_prefs key — simulates legacy row
    }

    from datametronome_podium.api.v1.endpoints.auth import get_current_user_info

    result = await get_current_user_info(current_user=mock_user)

    assert result["dashboard_prefs"] == {"pinned_staves": []}


@pytest.mark.asyncio
async def test_patch_me_saves_pinned_staves():
    """PATCH /auth/me saves pinned_staves (up to 3) and returns updated prefs."""
    from datametronome_podium.api.v1.endpoints.auth import patch_current_user

    mock_user = {
        "username": "admin",
        "email": "admin@datametronome.dev",
        "is_active": True,
        "is_superuser": True,
        "dashboard_prefs": "{}",
    }

    mock_executor = MagicMock()
    mock_executor.execute = AsyncMock(return_value=1)
    with patch(
        "datametronome_podium.api.v1.endpoints.auth.get_executor",
        return_value=mock_executor,
    ):
        result = await patch_current_user(
            body={"dashboard_prefs": {"pinned_staves": ["s1", "s2"]}},
            current_user=mock_user,
        )

    assert result["dashboard_prefs"]["pinned_staves"] == ["s1", "s2"]


@pytest.mark.asyncio
async def test_patch_me_accepts_exactly_3_pinned():
    """PATCH /auth/me accepts exactly 3 pinned_staves (boundary)."""
    from datametronome_podium.api.v1.endpoints.auth import patch_current_user

    mock_user = {
        "username": "admin",
        "email": "admin@datametronome.dev",
        "is_active": True,
        "is_superuser": True,
        "dashboard_prefs": "{}",
    }

    mock_executor = MagicMock()
    mock_executor.execute = AsyncMock(return_value=1)
    with patch(
        "datametronome_podium.api.v1.endpoints.auth.get_executor",
        return_value=mock_executor,
    ):
        result = await patch_current_user(
            body={"dashboard_prefs": {"pinned_staves": ["s1", "s2", "s3"]}},
            current_user=mock_user,
        )

    assert len(result["dashboard_prefs"]["pinned_staves"]) == 3


@pytest.mark.asyncio
async def test_patch_me_rejects_more_than_3_pinned():
    """PATCH /auth/me returns 400 when more than 3 staves are pinned."""
    from fastapi import HTTPException
    from datametronome_podium.api.v1.endpoints.auth import patch_current_user

    mock_user = {"username": "admin", "email": "x", "is_active": True, "is_superuser": False, "dashboard_prefs": "{}"}

    with pytest.raises(HTTPException) as exc_info:
        await patch_current_user(
            body={"dashboard_prefs": {"pinned_staves": ["s1", "s2", "s3", "s4"]}},
            current_user=mock_user,
        )

    assert exc_info.value.status_code == 400
