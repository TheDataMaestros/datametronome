"""Tests for clef_actions run-now using dispatcher."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


def _make_app():
    """Create a minimal FastAPI app with clef_actions router."""
    from fastapi import FastAPI
    from datametronome_podium.api.v1.endpoints.clef_actions import router
    app = FastAPI()
    app.include_router(router, prefix="/clef-actions")
    return app


def test_run_now_returns_202_with_job_id():
    from datametronome_podium.core.check_dispatcher import JobStatus

    app = _make_app()
    client = TestClient(app)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch = AsyncMock(return_value="job-uuid-123")
    mock_dispatcher.get_status = AsyncMock(return_value=JobStatus.PENDING)

    with patch("datametronome_podium.api.v1.endpoints.clef_actions.get_dispatcher", return_value=mock_dispatcher):
        response = client.post("/clef-actions/clef-1/run-now")

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == "job-uuid-123"
    assert data["clef_id"] == "clef-1"
    assert data["status"] == "pending"
    mock_dispatcher.dispatch.assert_awaited_once_with("clef-1")
    mock_dispatcher.get_status.assert_awaited_once_with("job-uuid-123")


def test_run_now_dispatch_failure_returns_500():
    app = _make_app()
    client = TestClient(app)

    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch = AsyncMock(side_effect=Exception("Broker down"))

    with patch("datametronome_podium.api.v1.endpoints.clef_actions.get_dispatcher", return_value=mock_dispatcher):
        response = client.post("/clef-actions/clef-1/run-now")

    assert response.status_code == 500


def test_get_job_status_endpoint():
    app = _make_app()
    client = TestClient(app)

    from datametronome_podium.core.check_dispatcher import JobStatus
    mock_dispatcher = AsyncMock()
    mock_dispatcher.get_status = AsyncMock(return_value=JobStatus.COMPLETED)
    mock_dispatcher.get_result = AsyncMock(return_value={
        "clef_id": "clef-1", "status": "pass", "message": "OK"
    })

    with patch("datametronome_podium.api.v1.endpoints.clef_actions.get_dispatcher", return_value=mock_dispatcher):
        response = client.get("/clef-actions/jobs/job-uuid-123/status")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-uuid-123"
    assert data["status"] == "completed"
    assert data["result"]["status"] == "pass"
