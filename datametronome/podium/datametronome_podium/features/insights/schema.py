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
    read_at: str | None = None
    read_by: str | None = None
    dismiss_reason: str | None = None
    assigned_to: str | None = None
    assigned_at: str | None = None
    created_at: str
    check_spec: dict | None = None


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    body: str
    reference_type: str
    reference_id: str | None = None
    read_at: str | None = None
    created_at: str


class DismissRequest(BaseModel):
    reason: str | None = None


class AssignRequest(BaseModel):
    assigned_to: str


class KPIResultResponse(BaseModel):
    name: str
    label: str
    value: float
    unit: str
    vs_benchmark: str | None = None
    trend_direction: str


class PerformerInsightResponse(BaseModel):
    entity_type: str
    entity_name: str
    metric: str
    value: float
    unit: str
    vs_average: float
    drill_down_explanation: str


class TrendInsightResponse(BaseModel):
    metric: str
    direction: str
    magnitude: float
    timeframe: str
    explanation: str


class BusinessReportResponse(BaseModel):
    id: str
    stave_id: str
    snapshot_id: str
    business_health_score: int
    executive_summary: str
    kpis: list[dict] = []
    top_performers: list[dict] = []
    bottom_performers: list[dict] = []
    trends: list[dict] = []
    opportunities: list[str] = []
    risks: list[str] = []
    generated_at: str


class DashboardResponse(BaseModel):
    stave_id: str
    health_score: int
    health_trend: str
    dimensions: list[dict] = []
    active_anomalies: list[dict] = []
    pending_suggestions: list[dict] = []
    ai_created_checks: list[dict] = []
    last_analyzed_at: str | None = None
    business_report: BusinessReportResponse | None = None


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
