"""Tests for BI endpoints and updated accept_suggestion."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from datametronome_podium.features.insights.router import router
from datametronome_podium.features.insights.model import (
    InsightSuggestion,
    BusinessReport,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/insights")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_get_business_report_404(client):
    """GET /business returns 404 when no report exists."""
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_latest_business_report = AsyncMock(
            return_value=None
        )
        resp = client.get("/insights/nonexistent/business")
    assert resp.status_code == 404


def test_get_business_report_found(client):
    """GET /business returns the latest business report."""
    report = BusinessReport(
        id="br-1", stave_id="s1", snapshot_id="snap-1", tenant_id="default",
        business_health_score=85, executive_summary="All good",
        generated_at="2026-03-15T06:00:00Z",
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_latest_business_report = AsyncMock(
            return_value=report
        )
        resp = client.get("/insights/s1/business")
    assert resp.status_code == 200
    data = resp.json()
    assert data["business_health_score"] == 85
    assert data["executive_summary"] == "All good"


def test_get_business_report_history(client):
    """GET /business/history returns list of reports."""
    report = BusinessReport(
        id="br-1", stave_id="s1", snapshot_id="snap-1", tenant_id="default",
        business_health_score=85, executive_summary="All good",
        generated_at="2026-03-15T06:00:00Z",
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.list_business_reports = AsyncMock(
            return_value=[report]
        )
        resp = client.get("/insights/s1/business/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_accept_suggestion_no_check_spec(client):
    """Accept with no check_spec — no clef created."""
    sug = InsightSuggestion(
        id="sug-1", stave_id="s1", tenant_id="default", report_id="r1",
        priority="medium", category="quality", action="Fix nulls",
        reasoning="high null rate", based_on="profile",
        created_at="2026-03-15T06:00:00Z", check_spec=None,
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo:
        mock_repo.return_value.get_suggestion = AsyncMock(return_value=sug)
        mock_repo.return_value.update_suggestion_status = AsyncMock(
            return_value=1
        )
        resp = client.post("/insights/s1/suggestions/sug-1/accept")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["check_created"] is False


def test_accept_suggestion_with_check_spec(client):
    """Accept with check_spec — auto-creates clef."""
    sug = InsightSuggestion(
        id="sug-2", stave_id="s1", tenant_id="default", report_id="r1",
        priority="high", category="quality", action="Monitor nulls",
        reasoning="high null rate", based_on="profile",
        created_at="2026-03-15T06:00:00Z",
        check_spec={"name": "null_check", "sql": "SELECT count(*) FROM t"},
    )
    mock_svc = AsyncMock()
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo, patch(
        "datametronome_podium.features.insights.router.get_executor"
    ), patch(
        "datametronome_podium.features.insights.router.InsightPipelineService",
        return_value=mock_svc,
    ):
        mock_repo.return_value.get_suggestion = AsyncMock(return_value=sug)
        mock_repo.return_value.update_suggestion_status = AsyncMock(
            return_value=1
        )
        resp = client.post("/insights/s1/suggestions/sug-2/accept")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["check_created"] is True
    mock_svc._create_check_from_spec.assert_called_once()
