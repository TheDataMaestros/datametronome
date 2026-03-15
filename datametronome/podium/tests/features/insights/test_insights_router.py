"""Tests for insights API router."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from datametronome_podium.features.insights.router import router
from datametronome_podium.features.insights.model import (
    DataProfile,
    InsightReport,
    InsightSuggestion,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/insights")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_get_profile_not_found(client):
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_profile = AsyncMock(return_value=None)
        resp = client.get("/insights/stave-1/profile")
        assert resp.status_code == 404


def test_get_profile_found(client):
    profile = DataProfile(
        id="dp-1", stave_id="stave-1", tenant_id="default",
        domain_type="e-commerce", domain_confidence=0.85,
        created_at="2026-03-15T00:00:00Z", updated_at="2026-03-15T00:00:00Z",
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_profile = AsyncMock(return_value=profile)
        resp = client.get("/insights/stave-1/profile")
        assert resp.status_code == 200
        assert resp.json()["domain_type"] == "e-commerce"


def test_get_latest_report(client):
    report = InsightReport(
        id="rpt-1", stave_id="stave-1", tenant_id="default",
        report_type="daily", health_score=78,
        summary="Looking good.", created_at="2026-03-15T06:00:00Z",
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_latest_report = AsyncMock(
            return_value=report
        )
        resp = client.get("/insights/stave-1/latest")
        assert resp.status_code == 200
        assert resp.json()["health_score"] == 78


def test_get_latest_report_not_found(client):
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_latest_report = AsyncMock(
            return_value=None
        )
        resp = client.get("/insights/stave-1/latest")
        assert resp.status_code == 404


def test_list_suggestions(client):
    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-1", tenant_id="default",
        report_id="rpt-1", priority="high", category="ops",
        action="Fix it", reasoning="Broken", based_on="data",
        created_at="2026-03-15T00:00:00Z",
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.list_suggestions = AsyncMock(
            return_value=[sug]
        )
        resp = client.get("/insights/stave-1/suggestions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


def test_accept_suggestion(client):
    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-1", tenant_id="default",
        report_id="rpt-1", priority="high", category="ops",
        action="Fix it", reasoning="Broken", based_on="data",
        created_at="2026-03-15T00:00:00Z",
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_suggestion = AsyncMock(return_value=sug)
        mock_repo.return_value.update_suggestion_status = AsyncMock(
            return_value=1
        )
        resp = client.post("/insights/stave-1/suggestions/sug-1/accept")
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"


def test_dismiss_suggestion(client):
    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-1", tenant_id="default",
        report_id="rpt-1", priority="high", category="ops",
        action="Fix it", reasoning="Broken", based_on="data",
        created_at="2026-03-15T00:00:00Z",
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_suggestion = AsyncMock(return_value=sug)
        mock_repo.return_value.update_suggestion_status = AsyncMock(
            return_value=1
        )
        resp = client.post("/insights/stave-1/suggestions/sug-1/dismiss")
        assert resp.status_code == 200
        assert resp.json()["status"] == "dismissed"


def test_accept_suggestion_not_found(client):
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_suggestion = AsyncMock(return_value=None)
        resp = client.post("/insights/stave-1/suggestions/sug-1/accept")
        assert resp.status_code == 404


def test_trigger_analysis_dispatches_task(client):
    """POST /analyze dispatches Celery task and returns task_id."""
    from unittest.mock import MagicMock
    mock_task = MagicMock()
    mock_task.id = "task-abc-123"
    with patch(
        "datametronome_podium.tasks.intelligence_tasks.run_on_demand_analysis"
    ) as mock_analysis:
        mock_analysis.delay.return_value = mock_task
        resp = client.post("/insights/stave-1/analyze")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc-123"
        assert data["status"] == "queued"
        mock_analysis.delay.assert_called_once_with("stave-1")


def test_trigger_analysis_handles_celery_failure(client):
    """POST /analyze returns 500 if Celery dispatch fails."""
    with patch(
        "datametronome_podium.tasks.intelligence_tasks.run_on_demand_analysis"
    ) as mock_analysis:
        mock_analysis.delay.side_effect = Exception("No broker")
        resp = client.post("/insights/stave-1/analyze")
        assert resp.status_code == 500


def test_get_analysis_status_running(client):
    """GET /analyze/{task_id} returns running for incomplete tasks."""
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.ready.return_value = False
    with patch(
        "datametronome_podium.core.celery_app.celery_app"
    ) as mock_celery:
        mock_celery.AsyncResult.return_value = mock_result
        resp = client.get("/insights/stave-1/analyze/task-abc-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["task_id"] == "task-abc-123"


def test_get_analysis_status_completed(client):
    """GET /analyze/{task_id} returns completed with report_id."""
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.ready.return_value = True
    mock_result.get.return_value = {"report_id": "rpt-42"}
    with patch(
        "datametronome_podium.core.celery_app.celery_app"
    ) as mock_celery:
        mock_celery.AsyncResult.return_value = mock_result
        resp = client.get("/insights/stave-1/analyze/task-abc-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["report_id"] == "rpt-42"
