"""Tests for insights API schemas."""
from datametronome_podium.features.insights.schema import (
    DataProfileResponse,
    InsightReportResponse,
    DashboardResponse,
    SuggestionResponse,
    AnalyzeRequest,
    SnapshotResponse,
    AnalyzeStatusResponse,
)


def test_dashboard_response():
    d = DashboardResponse(
        stave_id="s1", health_score=78, health_trend="improving",
        dimensions=[], active_anomalies=[], pending_suggestions=[],
        ai_created_checks=[], last_analyzed_at="2026-03-15T06:00:00Z",
    )
    assert d.health_score == 78
    assert d.health_trend == "improving"


def test_dashboard_response_defaults():
    d = DashboardResponse(
        stave_id="s1", health_score=50, health_trend="stable",
    )
    assert d.dimensions == []
    assert d.active_anomalies == []
    assert d.pending_suggestions == []
    assert d.ai_created_checks == []
    assert d.last_analyzed_at is None


def test_analyze_request_defaults():
    r = AnalyzeRequest()
    assert r.force is False


def test_analyze_request_force():
    r = AnalyzeRequest(force=True)
    assert r.force is True


def test_data_profile_response():
    p = DataProfileResponse(
        id="dp-1", stave_id="s1", domain_type="e-commerce",
        domain_confidence=0.85, profile_version=1,
        created_at="2026-03-15T00:00:00Z", updated_at="2026-03-15T00:00:00Z",
    )
    assert p.domain_context == {}
    assert p.schema_map == {}


def test_insight_report_response():
    r = InsightReportResponse(
        id="rpt-1", stave_id="s1", report_type="daily",
        health_score=78, summary="Good.",
        created_at="2026-03-15T06:00:00Z",
    )
    assert r.dimensions == []
    assert r.snapshot_id is None


def test_suggestion_response():
    s = SuggestionResponse(
        id="sug-1", stave_id="s1", report_id="rpt-1",
        priority="high", category="ops", action="Fix it",
        reasoning="Broken", based_on="data", status="pending",
        created_at="2026-03-15T00:00:00Z",
    )
    assert s.resolved_at is None


def test_snapshot_response():
    s = SnapshotResponse(
        id="snap-1", stave_id="s1", snapshot_type="daily",
        captured_at="2026-03-15T06:00:00Z",
    )
    assert s.table_metrics == {}
    assert s.column_stats == {}


def test_analyze_status_response():
    a = AnalyzeStatusResponse(
        task_id="task-1", status="pending",
    )
    assert a.report_id is None
