"""Analytics API DTOs."""
from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    success_rate: float = 0.0
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    active_sources: int = 0
    total_clefs: int = 0
    scheduled_clefs: int = 0
    anomaly_count: int = 0


class CheckSummary(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    warning: int = 0
