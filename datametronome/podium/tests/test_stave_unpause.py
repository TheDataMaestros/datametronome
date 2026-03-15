"""Tests for stave unpause endpoint."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


def _make_app():
    from fastapi import FastAPI
    from datametronome_podium.features.staves.router import router
    app = FastAPI()
    app.include_router(router, prefix="/staves")
    return app


def test_unpause_stave_success():
    app = _make_app()
    client = TestClient(app)

    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=MagicMock(id="stave-1", paused=True))
    mock_repo.update = AsyncMock()

    mock_circuit_breaker = AsyncMock()
    mock_circuit_breaker.reset = AsyncMock()

    with patch("datametronome_podium.features.staves.router._repo", return_value=mock_repo):
        with patch("datametronome_podium.features.staves.router._get_circuit_breaker", return_value=mock_circuit_breaker):
            response = client.post("/staves/stave-1/unpause")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Stave unpaused"
    mock_circuit_breaker.reset.assert_awaited_once_with("stave-1")


def test_unpause_stave_not_found():
    app = _make_app()
    client = TestClient(app)

    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=None)

    mock_circuit_breaker = AsyncMock()

    with patch("datametronome_podium.features.staves.router._repo", return_value=mock_repo):
        with patch("datametronome_podium.features.staves.router._get_circuit_breaker", return_value=mock_circuit_breaker):
            response = client.post("/staves/nonexistent/unpause")

    assert response.status_code == 404
