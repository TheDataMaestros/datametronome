"""Tests for BI domain models (BusinessReport, KPIResult, etc.)."""

import pytest
from datametronome_podium.features.insights.model import (
    KPIResult,
    PerformerInsight,
    TrendInsight,
    BusinessReport,
    InsightSuggestion,
)


def test_kpi_result_fields():
    kpi = KPIResult(
        name="average_order_value",
        label="Average Order Value",
        value=124.5,
        unit="$",
        vs_benchmark="above typical range ($20-$200)",
        trend_direction="up",
    )
    assert kpi.value == 124.5
    assert kpi.trend_direction == "up"


def test_performer_insight_fields():
    p = PerformerInsight(
        entity_type="product",
        entity_name="Widget Pro",
        metric="revenue",
        value=45000.0,
        unit="$",
        vs_average=34.2,
        drill_down_explanation="Up 34% because spike in Region Y on Tuesday",
    )
    assert p.vs_average == 34.2


def test_trend_insight_fields():
    t = TrendInsight(
        metric="revenue",
        direction="up",
        magnitude=12.3,
        timeframe="last 7 days",
        explanation="Revenue grew 12% driven by Product X",
    )
    assert t.direction == "up"


def test_business_report_fields():
    br = BusinessReport(
        id="br-test",
        stave_id="s1",
        snapshot_id="snap-1",
        tenant_id="default",
        business_health_score=78,
        executive_summary="Business is growing at 12% MoM.",
        kpis=[],
        top_performers=[],
        bottom_performers=[],
        trends=[],
        opportunities=["Expand into Region Y"],
        risks=["Payment failure rate rising"],
        generated_at="2026-03-15T06:00:00Z",
    )
    assert br.business_health_score == 78


def test_suggestion_check_spec_optional():
    sug = InsightSuggestion(
        id="sug-1",
        stave_id="s1",
        tenant_id="default",
        report_id="r1",
        priority="high",
        category="quality",
        action="Add freshness check",
        reasoning="Orders table not updated today",
        based_on="row count",
        created_at="2026-03-15T06:00:00Z",
    )
    assert sug.check_spec is None


def test_suggestion_with_check_spec():
    from datametronome_podium.services.agents.insight_models import LLMCheckSpec

    spec = LLMCheckSpec(
        table="orders",
        check_type="freshness",
        schedule="0 * * * *",
        config={"max_age_hours": 2},
        rationale="Orders must be fresh",
    )
    sug = InsightSuggestion(
        id="sug-2",
        stave_id="s1",
        tenant_id="default",
        report_id="r1",
        priority="high",
        category="freshness",
        action="Monitor orders freshness",
        reasoning="ETL may be broken",
        based_on="no row change in 24h",
        check_spec=spec.model_dump(),
        created_at="2026-03-15T06:00:00Z",
    )
    assert sug.check_spec is not None
