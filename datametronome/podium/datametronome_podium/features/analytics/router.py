"""Analytics API router — dashboard aggregates and recent activity."""

from fastapi import APIRouter, Query

from datametronome_podium.core.database import get_executor
from datametronome_podium.features.analytics.repo import AnalyticsRepo
from datametronome_podium.features.analytics.schema import CheckSummary, DashboardMetrics

router = APIRouter()


def _repo() -> AnalyticsRepo:
    return AnalyticsRepo(get_executor())


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics():
    """Aggregate dashboard metrics: success rate, counts, anomalies."""
    repo = _repo()
    summary = await repo.get_check_summary()
    active_sources = await repo.get_active_sources_count()
    anomalies = await repo.get_anomaly_count()

    total = summary.get("total", 0) or 0
    passed = summary.get("passed", 0) or 0
    success_rate = (passed / total * 100) if total > 0 else 0.0

    return DashboardMetrics(
        success_rate=round(success_rate, 1),
        total_checks=total,
        passed_checks=passed,
        failed_checks=summary.get("failed", 0) or 0,
        active_sources=active_sources,
        anomaly_count=anomalies,
    )


@router.get("/summary", response_model=CheckSummary)
async def get_check_summary():
    """Check status summary: total, passed, failed, warning."""
    repo = _repo()
    summary = await repo.get_check_summary()
    return CheckSummary(
        total=summary.get("total", 0) or 0,
        passed=summary.get("passed", 0) or 0,
        failed=summary.get("failed", 0) or 0,
        warning=summary.get("warning", 0) or 0,
    )


@router.get("/recent-checks")
async def get_recent_checks(limit: int = Query(default=20, ge=1, le=100)):
    """Recent check executions with stave/clef names."""
    repo = _repo()
    return await repo.get_recent_checks(limit=limit)
