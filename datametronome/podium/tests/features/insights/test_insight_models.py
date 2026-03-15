"""Tests for intelligence store domain models."""

from datametronome_podium.features.insights.model import DataProfile


def test_data_profile_defaults():
    p = DataProfile(
        id="dp-1",
        stave_id="stave-1",
        tenant_id="default",
        domain_type="e-commerce",
        domain_confidence=0.85,
        created_at="2026-03-15T00:00:00Z",
        updated_at="2026-03-15T00:00:00Z",
    )
    assert p.profile_version == 1
    assert p.previous_classification is None
    assert p.domain_context == {}
    assert p.schema_map == {}
    assert p.entity_roles == {}
    assert p.learned_patterns == {}


def test_data_profile_full():
    p = DataProfile(
        id="dp-1",
        stave_id="stave-1",
        tenant_id="default",
        domain_type="saas",
        domain_confidence=0.72,
        domain_context={"description": "SaaS platform"},
        schema_map={"users": {"columns": ["id", "email"]}},
        entity_roles={"fact": ["subscriptions"], "dimension": ["users"]},
        learned_patterns={"weekly_billing_cycle": {"confidence": 0.9}},
        profile_version=3,
        previous_classification={"domain_type": "generic", "confidence": 0.4, "changed_at": "2026-03-10"},
        created_at="2026-03-15T00:00:00Z",
        updated_at="2026-03-15T00:00:00Z",
    )
    assert p.domain_type == "saas"
    assert p.profile_version == 3
    assert p.previous_classification["domain_type"] == "generic"


# --- Task 2: remaining models ---

from datametronome_podium.features.insights.model import (
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
    TableMetrics,
)


def test_table_metrics_defaults():
    m = TableMetrics(row_count=1000, null_rates={"email": 0.05})
    assert m.status == "ok"
    assert m.skip_reason is None
    assert m.freshness is None
    assert m.distributions == {}


def test_table_metrics_skipped():
    m = TableMetrics(row_count=0, null_rates={}, status="skipped", skip_reason="timeout")
    assert m.status == "skipped"


def test_baseline_snapshot():
    s = BaselineSnapshot(
        id="snap-1",
        stave_id="stave-1",
        tenant_id="default",
        snapshot_type="daily",
        table_metrics={"orders": {"row_count": 5000, "null_rates": {}}},
        column_stats={},
        captured_at="2026-03-15T06:00:00Z",
    )
    assert s.snapshot_type == "daily"


def test_insight_report_minimal():
    r = InsightReport(
        id="rpt-1",
        stave_id="stave-1",
        tenant_id="default",
        report_type="initial",
        health_score=78,
        summary="Data source looks healthy.",
        created_at="2026-03-15T06:00:00Z",
    )
    assert r.dimensions == []
    assert r.anomalies == []
    assert r.suggestions == []
    assert r.key_findings == []
    assert r.snapshot_id is None


def test_insight_suggestion():
    s = InsightSuggestion(
        id="sug-1",
        stave_id="stave-1",
        tenant_id="default",
        report_id="rpt-1",
        priority="high",
        category="operations",
        action="Investigate payment gateway",
        reasoning="Failure rate doubled",
        based_on="7-day trend",
        created_at="2026-03-15T06:00:00Z",
    )
    assert s.status == "pending"
    assert s.resolved_at is None


def test_insight_created_check():
    c = InsightCreatedCheck(
        id="icc-1",
        report_id="rpt-1",
        clef_id="clef-1",
        rationale="Orders table needs freshness monitoring",
        created_at="2026-03-15T06:00:00Z",
    )
    assert c.report_id == "rpt-1"
