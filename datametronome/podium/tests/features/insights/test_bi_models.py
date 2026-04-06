"""Tests for BI LLM structured output models (bi_models.py)."""

from datametronome_podium.services.agents.bi_models import (
    LLMKPIResult,
    LLMPerformerInsight,
    LLMTrendInsight,
    LLMBusinessReport,
    SchemaInterpretation,
    GeneratedQueryPlan,
)


def test_llm_kpi_result():
    kpi = LLMKPIResult(
        name="aov", label="AOV", value=124.5, unit="$", trend_direction="up"
    )
    assert kpi.value == 124.5
    assert kpi.vs_benchmark is None


def test_llm_performer_insight():
    p = LLMPerformerInsight(
        entity_type="product",
        entity_name="Widget",
        metric="revenue",
        value=45000,
        unit="$",
        vs_average=34.2,
        drill_down_explanation="Spike in Region Y",
    )
    assert p.vs_average == 34.2


def test_llm_trend_insight():
    t = LLMTrendInsight(
        metric="revenue",
        direction="up",
        magnitude=12.3,
        timeframe="last 7 days",
        explanation="Revenue grew 12% driven by Product X",
    )
    assert t.direction == "up"
    assert t.magnitude == 12.3


def test_llm_business_report_defaults():
    r = LLMBusinessReport(
        business_health_score=80, executive_summary="Business is healthy."
    )
    assert r.kpis == []
    assert r.opportunities == []
    assert r.top_performers == []
    assert r.bottom_performers == []
    assert r.trends == []
    assert r.risks == []


def test_schema_interpretation_defaults():
    si = SchemaInterpretation(
        table_roles={"orders": "fact_table"},
        column_roles={"orders.created_at": "transaction_time"},
        key_observations=["orders is the primary fact table"],
    )
    assert si.table_roles["orders"] == "fact_table"
    assert si.key_observations[0].startswith("orders")


def test_generated_query_plan_defaults():
    plan = GeneratedQueryPlan(
        kpi_queries={"monthly_revenue": "SELECT 1 as value"},
        performer_queries={},
        skipped=[],
    )
    assert "monthly_revenue" in plan.kpi_queries
    assert plan.skipped == []


def test_llm_business_report_has_skipped_kpis():
    report = LLMBusinessReport(
        business_health_score=72,
        executive_summary="Revenue is strong.",
        skipped_kpis=[{"name": "cart_abandonment_rate", "reason": "could not generate valid SQL"}],
    )
    assert len(report.skipped_kpis) == 1
    assert report.skipped_kpis[0]["name"] == "cart_abandonment_rate"
