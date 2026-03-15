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
    created_at: str


class InsightCreatedCheck(BaseModel):
    id: str
    report_id: str
    clef_id: str
    rationale: str
    created_at: str
