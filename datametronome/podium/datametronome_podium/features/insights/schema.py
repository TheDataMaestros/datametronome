"""Insights API DTOs."""
from pydantic import BaseModel


class DataProfileResponse(BaseModel):
    id: str
    stave_id: str
    domain_type: str
    domain_confidence: float
    domain_context: dict = {}
    schema_map: dict = {}
    entity_roles: dict = {}
    learned_patterns: dict = {}
    profile_version: int
    created_at: str
    updated_at: str


class InsightReportResponse(BaseModel):
    id: str
    stave_id: str
    snapshot_id: str | None = None
    report_type: str
    health_score: int
    dimensions: list[dict] = []
    anomalies: list[dict] = []
    suggestions: list[dict] = []
    summary: str
    key_findings: list[str] = []
    created_at: str


class SuggestionResponse(BaseModel):
    id: str
    stave_id: str
    report_id: str
    priority: str
    category: str
    action: str
    reasoning: str
    based_on: str
    status: str
    resolved_at: str | None = None
    created_at: str


class DashboardResponse(BaseModel):
    stave_id: str
    health_score: int
    health_trend: str
    dimensions: list[dict] = []
    active_anomalies: list[dict] = []
    pending_suggestions: list[dict] = []
    ai_created_checks: list[dict] = []
    last_analyzed_at: str | None = None


class SnapshotResponse(BaseModel):
    id: str
    stave_id: str
    snapshot_type: str
    table_metrics: dict = {}
    column_stats: dict = {}
    captured_at: str


class AnalyzeRequest(BaseModel):
    force: bool = False


class AnalyzeStatusResponse(BaseModel):
    task_id: str
    status: str
    report_id: str | None = None
