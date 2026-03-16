"""Intelligence Store domain models."""

from typing import Literal

from pydantic import BaseModel


class DataProfile(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    domain_type: str
    domain_confidence: float
    domain_context: dict = {}
    schema_map: dict = {}
    entity_roles: dict = {}
    learned_patterns: dict = {}
    schema_interpretation: dict = {}
    profile_version: int = 1
    previous_classification: dict | None = None
    created_at: str
    updated_at: str


class TableMetrics(BaseModel):
    row_count: int
    freshness: str | None = None
    null_rates: dict[str, float]
    distributions: dict[str, dict] = {}
    status: Literal["ok", "skipped"] = "ok"
    skip_reason: str | None = None


class BaselineSnapshot(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    snapshot_type: Literal["auto_scan", "daily", "on_demand", "weekly_aggregate"]
    table_metrics: dict
    column_stats: dict
    captured_at: str


class InsightReport(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    snapshot_id: str | None = None
    report_type: Literal["initial", "daily", "on_demand"]
    health_score: int
    dimensions: list[dict] = []
    anomalies: list[dict] = []
    suggestions: list[dict] = []
    summary: str
    key_findings: list[str] = []
    created_at: str


class InsightSuggestion(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    report_id: str
    priority: Literal["low", "medium", "high"]
    category: str
    action: str
    reasoning: str
    based_on: str
    status: Literal["pending", "accepted", "dismissed"] = "pending"
    resolved_at: str | None = None
    # Lifecycle fields (added migration 005)
    read_at: str | None = None
    read_by: str | None = None
    dismiss_reason: str | None = None
    assigned_to: str | None = None
    assigned_at: str | None = None
    created_at: str
    check_spec: dict | None = None  # populated by LLM when it recommends a monitoring check


class Notification(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    body: str
    reference_type: str = "suggestion"
    reference_id: str | None = None
    read_at: str | None = None
    created_at: str


class InsightCreatedCheck(BaseModel):
    id: str
    report_id: str
    clef_id: str
    rationale: str
    created_at: str


class KPIResult(BaseModel):
    name: str
    label: str
    value: float
    unit: str
    vs_benchmark: str | None = None
    trend_direction: Literal["up", "down", "stable"]


class PerformerInsight(BaseModel):
    entity_type: str
    entity_name: str
    metric: str
    value: float
    unit: str
    vs_average: float
    drill_down_explanation: str


class TrendInsight(BaseModel):
    metric: str
    direction: Literal["up", "down", "stable"]
    magnitude: float
    timeframe: str
    explanation: str


class BusinessReport(BaseModel):
    id: str
    stave_id: str
    snapshot_id: str
    tenant_id: str
    business_health_score: int
    executive_summary: str
    kpis: list[dict] = []
    top_performers: list[dict] = []
    bottom_performers: list[dict] = []
    trends: list[dict] = []
    opportunities: list[str] = []
    risks: list[str] = []
    generated_at: str


class StaveQueryPlan(BaseModel):
    """Agent-generated SQL query plan for a stave, cached for reuse."""

    id: str
    stave_id: str
    tenant_id: str = "default"
    schema_fingerprint: str
    kpi_queries: dict[str, str] = {}
    performer_queries: dict[str, dict[str, str]] = {}
    generated_by_model: str = ""
    skipped: list[dict[str, str]] = []
    generated_at: str
    invalidated_at: str | None = None
