"""Tests for clef run-now and job-status endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from datametronome_podium.core.auth import get_current_user, require_editor

FAKE_USER = {"id": "u1", "username": "test", "role": "editor"}


def _make_app():
    """Create a minimal FastAPI app with clefs router, auth overridden."""
    from fastapi import FastAPI
    from datametronome_podium.features.clefs.router import router

    app = FastAPI()
    app.include_router(router, prefix="/clefs")
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[require_editor] = lambda: FAKE_USER
    return app


def test_run_now_returns_202_with_job_id():
    from datametronome_podium.core.check_dispatcher import JobStatus

    app = _make_app()
    client = TestClient(app)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch = AsyncMock(return_value="job-uuid-123")
    mock_dispatcher.get_status = AsyncMock(return_value=JobStatus.PENDING)

    with patch("datametronome_podium.features.clefs.router.get_dispatcher", return_value=mock_dispatcher):
        response = client.post("/clefs/clef-1/run-now")

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == "job-uuid-123"
    assert data["clef_id"] == "clef-1"
    assert data["status"] == "pending"


def test_run_now_dispatch_failure_returns_500():
    app = _make_app()
    client = TestClient(app)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch = AsyncMock(side_effect=Exception("Broker down"))

    with patch("datametronome_podium.features.clefs.router.get_dispatcher", return_value=mock_dispatcher):
        response = client.post("/clefs/clef-1/run-now")

    assert response.status_code == 500


def test_get_job_status_endpoint():
    from datametronome_podium.core.check_dispatcher import JobStatus

    app = _make_app()
    client = TestClient(app)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.get_status = AsyncMock(return_value=JobStatus.COMPLETED)
    mock_dispatcher.get_result = AsyncMock(return_value={
        "clef_id": "clef-1", "status": "pass", "message": "OK"
    })

    with patch("datametronome_podium.features.clefs.router.get_dispatcher", return_value=mock_dispatcher):
        response = client.get("/clefs/jobs/job-uuid-123/status")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-uuid-123"
    assert data["status"] == "completed"
    assert data["result"]["status"] == "pass"
