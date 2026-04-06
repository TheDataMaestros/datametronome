"""Pydantic models for InsightAgent structured LLM output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LLMDimension(BaseModel):
    """A scored dimension of data health (e.g. freshness, completeness)."""

    name: str
    label: str
    score: int  # 0-100
    trend: Literal["improving", "stable", "declining"]
    delta: float | None = None
    details: str


class LLMAnomaly(BaseModel):
    """An anomaly detected in the data, with evidence."""

    severity: Literal["low", "medium", "high", "critical"]
    category: str
    table: str
    description: str
    evidence: str
    compared_to: str | None = None


class LLMSuggestion(BaseModel):
    """An actionable suggestion with reasoning and data basis."""

    priority: Literal["low", "medium", "high"]
    category: str
    action: str
    reasoning: str
    based_on: str


class LLMCheckSpec(BaseModel):
    """A quality check the LLM recommends creating."""

    table: str
    check_type: Literal[
        "row_count",
        "freshness",
        "column_values",
        "forecast",
        "data_profile_drift",
        "lookup_validation",
    ]
    schedule: str
    config: dict
    rationale: str


class LLMInsightReport(BaseModel):
    """Full structured output from the InsightAgent analysis stage."""

    health_score: int  # 0-100
    report_type: Literal["initial", "daily", "on_demand"]
    dimensions: list[LLMDimension] = []
    anomalies: list[LLMAnomaly] = []
    suggestions: list[LLMSuggestion] = []
    summary: str
    key_findings: list[str] = []
    checks_to_create: list[LLMCheckSpec] = []


class LLMDomainClassification(BaseModel):
    """Structured output for domain classification."""

    domain_type: str
    confidence: float  # 0-1
    business_context: str
    entity_roles: dict  # {"fact": [...], "dimension": [...]}
    matched_archetype: str | None = None
