"""Tests for InsightAgent LLM output models."""
import pytest

from datametronome_podium.services.agents.insight_models import (
    LLMInsightReport,
    LLMDimension,
    LLMAnomaly,
    LLMSuggestion,
    LLMCheckSpec,
    LLMDomainClassification,
)


def test_llm_insight_report_validation():
    report = LLMInsightReport(
        health_score=78,
        report_type="daily",
        dimensions=[
            LLMDimension(
                name="freshness",
                label="Data Freshness",
                score=92,
                trend="improving",
                details="All tables fresh",
            ),
        ],
        anomalies=[
            LLMAnomaly(
                severity="high",
                category="quality",
                table="payments",
                description="Failure rate doubled",
                evidence="4.8% vs 2.3% baseline",
            ),
        ],
        suggestions=[
            LLMSuggestion(
                priority="high",
                category="operations",
                action="Check payment gateway",
                reasoning="Revenue loss",
                based_on="7-day trend",
            ),
        ],
        summary="Your data is mostly healthy.",
        key_findings=["Payment failures elevated"],
        checks_to_create=[],
    )
    assert report.health_score == 78
    assert len(report.dimensions) == 1
    assert report.dimensions[0].trend == "improving"


def test_llm_check_spec_valid_type():
    spec = LLMCheckSpec(
        table="orders",
        check_type="freshness",
        schedule="0 * * * *",
        config={"max_age_hours": 2},
        rationale="Monitor order flow",
    )
    assert spec.check_type == "freshness"


def test_llm_check_spec_invalid_type():
    with pytest.raises(ValueError):
        LLMCheckSpec(
            table="orders",
            check_type="python",
            schedule="0 * * * *",
            config={},
            rationale="Bad",
        )


def test_llm_domain_classification():
    dc = LLMDomainClassification(
        domain_type="e-commerce",
        confidence=0.85,
        business_context="Online retail store",
        entity_roles={"fact": ["orders"], "dimension": ["products"]},
        matched_archetype="e-commerce",
    )
    assert dc.confidence == 0.85
