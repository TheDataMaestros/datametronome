"""Tests for BI response DTOs in insights schema."""
from datametronome_podium.features.insights.schema import (
    BusinessReportResponse, KPIResultResponse, DashboardResponse, SuggestionResponse,
    PerformerInsightResponse, TrendInsightResponse,
)


def test_business_report_response():
    br = BusinessReportResponse(
        id="br-1", stave_id="s1", snapshot_id="snap-1",
        business_health_score=80, executive_summary="Business healthy.",
        generated_at="2026-03-15T06:00:00Z",
    )
    assert br.business_health_score == 80
    assert br.kpis == []
    assert br.top_performers == []
    assert br.bottom_performers == []
    assert br.trends == []
    assert br.opportunities == []
    assert br.risks == []


def test_kpi_result_response():
    kpi = KPIResultResponse(
        name="revenue", label="Revenue", value=1000.0,
        unit="USD", trend_direction="up",
    )
    assert kpi.value == 1000.0
    assert kpi.vs_benchmark is None


def test_performer_insight_response():
    p = PerformerInsightResponse(
        entity_type="product", entity_name="Widget A",
        metric="sales", value=500.0, unit="units",
        vs_average=1.5, drill_down_explanation="Above average",
    )
    assert p.vs_average == 1.5


def test_trend_insight_response():
    t = TrendInsightResponse(
        metric="orders", direction="up", magnitude=12.5,
        timeframe="7d", explanation="Orders increasing",
    )
    assert t.direction == "up"


def test_dashboard_response_has_business_report_field():
    d = DashboardResponse(stave_id="s1", health_score=75, health_trend="stable")
    assert d.business_report is None  # optional field


def test_suggestion_response_has_check_spec_field():
    s = SuggestionResponse(
        id="sug-1", stave_id="s1", report_id="r1",
        priority="high", category="freshness", action="Fix it",
        reasoning="stale", based_on="row count", status="pending",
        created_at="2026-03-15T06:00:00Z",
    )
    assert s.check_spec is None
