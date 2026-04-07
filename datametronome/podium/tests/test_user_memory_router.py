"""Tests for user memory API router."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from datametronome_podium.core.auth import get_current_user
from datametronome_podium.features.user_memory.router import router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_USER = "user-abc"
FAKE_CURRENT_USER = {"id": FAKE_USER, "username": "testuser"}


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/user/memory")
    app.dependency_overrides[get_current_user] = lambda: FAKE_CURRENT_USER
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


_REPO_PATH = "datametronome_podium.features.user_memory.router._repo"
_DISPATCH_PATH = "datametronome_podium.features.user_memory.router._dispatch_rebuild"

FAKE_PROFILE = {
    "id": "prof-001",
    "user_id": FAKE_USER,
    "domain_summary": "e-commerce analytics",
    "expertise_summary": "SQL, dbt",
    "investigation_summary": "null rates in orders table",
    "memory_count": 3,
    "last_rebuilt_at": "2026-04-01T10:00:00Z",
    "created_at": "2026-03-01T00:00:00Z",
}

FAKE_MEMORY = {
    "id": "mem-aabbcc112233",
    "user_id": FAKE_USER,
    "category": "expertise",
    "content": "Proficient in dbt",
    "source_conversation_id": None,
    "confidence": 0.95,
    "active": True,
    "superseded_by": None,
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-04-01T10:00:00Z",
}


# ---------------------------------------------------------------------------
# GET /profile
# ---------------------------------------------------------------------------


def test_get_profile_returns_200(client):
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.get_profile = AsyncMock(return_value=FAKE_PROFILE)
        resp = client.get("/user/memory/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == FAKE_USER
    assert data["domain_summary"] == "e-commerce analytics"
    assert data["memory_count"] == 3


def test_get_profile_returns_404_when_missing(client):
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.get_profile = AsyncMock(return_value=None)
        resp = client.get("/user/memory/profile")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


def test_list_memories_returns_200(client):
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.search_memories = AsyncMock(return_value=[FAKE_MEMORY])
        resp = client.get("/user/memory/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == FAKE_MEMORY["id"]


def test_list_memories_passes_query_params(client):
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.search_memories = AsyncMock(return_value=[])
        resp = client.get("/user/memory/?category=expertise&q=dbt&active=true")
    assert resp.status_code == 200
    mock_repo.return_value.search_memories.assert_called_once_with(
        FAKE_USER, q="dbt", category="expertise", active_only=True
    )


def test_list_memories_active_false_passes_inactive(client):
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.search_memories = AsyncMock(return_value=[])
        resp = client.get("/user/memory/?active=false")
    assert resp.status_code == 200
    mock_repo.return_value.search_memories.assert_called_once_with(
        FAKE_USER, q=None, category=None, active_only=False
    )


# ---------------------------------------------------------------------------
# GET /{memory_id}
# ---------------------------------------------------------------------------


def test_get_single_memory_returns_200(client):
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.get_memory = AsyncMock(return_value=FAKE_MEMORY)
        resp = client.get(f"/user/memory/{FAKE_MEMORY['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == FAKE_MEMORY["id"]


def test_get_single_memory_404_when_wrong_user(client):
    wrong_user_memory = {**FAKE_MEMORY, "user_id": "other-user"}
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.get_memory = AsyncMock(return_value=wrong_user_memory)
        resp = client.get(f"/user/memory/{FAKE_MEMORY['id']}")
    assert resp.status_code == 404


def test_get_single_memory_404_when_missing(client):
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.get_memory = AsyncMock(return_value=None)
        resp = client.get("/user/memory/mem-doesnotexist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------


def test_create_memory_returns_201(client):
    with patch(_REPO_PATH) as mock_repo, patch(_DISPATCH_PATH) as mock_dispatch:
        mock_repo.return_value.create_memory = AsyncMock()
        mock_repo.return_value.get_memory = AsyncMock(return_value=FAKE_MEMORY)
        payload = {"category": "expertise", "content": "Proficient in dbt", "confidence": 0.95}
        resp = client.post("/user/memory/", json=payload)
    assert resp.status_code == 201
    assert resp.json()["content"] == "Proficient in dbt"
    mock_dispatch.assert_called_once_with(FAKE_USER)


# ---------------------------------------------------------------------------
# PATCH /{memory_id}
# ---------------------------------------------------------------------------


def test_patch_memory_returns_updated(client):
    updated = {**FAKE_MEMORY, "content": "Expert in dbt and SQL"}
    with patch(_REPO_PATH) as mock_repo, patch(_DISPATCH_PATH):
        mock_repo.return_value.get_memory = AsyncMock(side_effect=[FAKE_MEMORY, updated])
        mock_repo.return_value.update_memory = AsyncMock()
        resp = client.patch(
            f"/user/memory/{FAKE_MEMORY['id']}",
            json={"content": "Expert in dbt and SQL"},
        )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Expert in dbt and SQL"


def test_patch_memory_converts_active_bool_to_int(client):
    inactive = {**FAKE_MEMORY, "active": False}
    with patch(_REPO_PATH) as mock_repo, patch(_DISPATCH_PATH):
        mock_repo.return_value.get_memory = AsyncMock(side_effect=[FAKE_MEMORY, inactive])
        mock_repo.return_value.update_memory = AsyncMock()
        client.patch(f"/user/memory/{FAKE_MEMORY['id']}", json={"active": False})
    mock_repo.return_value.update_memory.assert_called_once_with(
        FAKE_MEMORY["id"], {"active": 0}
    )


def test_patch_memory_404_when_wrong_user(client):
    wrong = {**FAKE_MEMORY, "user_id": "other"}
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.get_memory = AsyncMock(return_value=wrong)
        resp = client.patch(f"/user/memory/{FAKE_MEMORY['id']}", json={"content": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /{memory_id}
# ---------------------------------------------------------------------------


def test_delete_memory_returns_204(client):
    with patch(_REPO_PATH) as mock_repo, patch(_DISPATCH_PATH):
        mock_repo.return_value.get_memory = AsyncMock(return_value=FAKE_MEMORY)
        mock_repo.return_value.delete_memory = AsyncMock()
        resp = client.delete(f"/user/memory/{FAKE_MEMORY['id']}")
    assert resp.status_code == 204


def test_delete_memory_404_when_wrong_user(client):
    wrong = {**FAKE_MEMORY, "user_id": "other"}
    with patch(_REPO_PATH) as mock_repo:
        mock_repo.return_value.get_memory = AsyncMock(return_value=wrong)
        resp = client.delete(f"/user/memory/{FAKE_MEMORY['id']}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /rebuild
# ---------------------------------------------------------------------------


def test_rebuild_returns_202(client):
    with patch(_DISPATCH_PATH) as mock_dispatch:
        resp = client.post("/user/memory/rebuild")
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"
    assert resp.json()["user_id"] == FAKE_USER
    mock_dispatch.assert_called_once_with(FAKE_USER)
