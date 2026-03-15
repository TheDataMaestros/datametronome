"""Insights API router."""
from fastapi import APIRouter, HTTPException

from datametronome_podium.core.database import get_executor
from datametronome_podium.features.insights.repo import InsightsRepo
from datametronome_podium.features.insights.schema import (
    DataProfileResponse,
    InsightReportResponse,
    DashboardResponse,
    SuggestionResponse,
    SnapshotResponse,
    AnalyzeRequest,
)

router = APIRouter()


def _repo() -> InsightsRepo:
    """Build InsightsRepo with the current database executor."""
    return InsightsRepo(get_executor())


# --- Profile ---


@router.get("/{stave_id}/profile", response_model=DataProfileResponse)
async def get_profile(stave_id: str):
    """Get the data profile for a stave."""
    profile = await _repo().get_profile(stave_id)
    if not profile:
        raise HTTPException(
            status_code=404, detail="No profile found for this stave"
        )
    return profile.model_dump()


# --- Reports ---


@router.get("/{stave_id}/latest", response_model=InsightReportResponse)
async def get_latest_report(stave_id: str):
    """Get the most recent insight report for a stave."""
    report = await _repo().get_latest_report(stave_id)
    if not report:
        raise HTTPException(
            status_code=404, detail="No reports found for this stave"
        )
    return report.model_dump()


@router.get("/{stave_id}/history", response_model=list[InsightReportResponse])
async def get_report_history(
    stave_id: str, limit: int = 20, offset: int = 0
):
    """List report history for a stave."""
    reports = await _repo().list_reports(stave_id, limit=limit, offset=offset)
    return [r.model_dump() for r in reports]


# --- Snapshots ---


@router.get("/{stave_id}/snapshots", response_model=list[SnapshotResponse])
async def get_snapshots(stave_id: str, days: int = 7):
    """List baseline snapshots for a stave."""
    snapshots = await _repo().list_snapshots(stave_id, days=days)
    return [s.model_dump() for s in snapshots]


# --- Dashboard ---


@router.get("/{stave_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(stave_id: str):
    """Aggregate dashboard view for a stave."""
    repo = _repo()
    report = await repo.get_latest_report(stave_id)
    if not report:
        raise HTTPException(
            status_code=404, detail="No reports found for this stave"
        )

    suggestions = await repo.list_suggestions(stave_id, status="pending")
    check_links = await repo.list_check_links(report.id)
    trend = await _compute_health_trend(repo, stave_id)

    return DashboardResponse(
        stave_id=stave_id,
        health_score=report.health_score,
        health_trend=trend,
        dimensions=report.dimensions,
        active_anomalies=[
            a for a in report.anomalies
            if a.get("severity") in ("high", "critical")
        ],
        pending_suggestions=[s.model_dump() for s in suggestions],
        ai_created_checks=[c.model_dump() for c in check_links],
        last_analyzed_at=report.created_at,
    )


async def _compute_health_trend(
    repo: InsightsRepo, stave_id: str
) -> str:
    """Compare latest two reports to determine trend direction."""
    reports = await repo.list_reports(stave_id, limit=2)
    if len(reports) < 2:
        return "stable"
    delta = reports[0].health_score - reports[1].health_score
    if delta > 0:
        return "improving"
    if delta < 0:
        return "declining"
    return "stable"


# --- Analysis trigger ---


@router.post("/{stave_id}/analyze")
async def trigger_analysis(
    stave_id: str, request: AnalyzeRequest = AnalyzeRequest()
):
    """Trigger on-demand intelligence analysis. Returns task ID for polling."""
    try:
        from datametronome_podium.tasks.intelligence_tasks import run_on_demand_analysis
        task = run_on_demand_analysis.delay(stave_id)
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch analysis: {e}")


@router.get("/{stave_id}/analyze/{task_id}")
async def get_analysis_status(stave_id: str, task_id: str):
    """Poll on-demand analysis status."""
    try:
        from datametronome_podium.core.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)
        if result.ready():
            output = result.get(timeout=1)
            return {
                "task_id": task_id,
                "status": "completed",
                "report_id": output.get("report_id") if isinstance(output, dict) else None,
            }
        return {"task_id": task_id, "status": "running"}
    except Exception:
        return {"task_id": task_id, "status": "unknown"}


# --- Overview ---


@router.get("/overview")
async def get_overview():
    """Cross-stave intelligence overview."""
    return {"staves": [], "total_health": 0}


# --- Suggestions ---


@router.get(
    "/{stave_id}/suggestions", response_model=list[SuggestionResponse]
)
async def list_suggestions(stave_id: str, status: str | None = None):
    """List suggestions for a stave, optionally filtered by status."""
    results = await _repo().list_suggestions(stave_id, status=status)
    return [s.model_dump() for s in results]


@router.post("/{stave_id}/suggestions/{suggestion_id}/accept")
async def accept_suggestion(stave_id: str, suggestion_id: str):
    """Accept an insight suggestion."""
    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.update_suggestion_status(suggestion_id, "accepted")
    return {"id": suggestion_id, "status": "accepted"}


@router.post("/{stave_id}/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(stave_id: str, suggestion_id: str):
    """Dismiss an insight suggestion."""
    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.update_suggestion_status(suggestion_id, "dismissed")
    return {"id": suggestion_id, "status": "dismissed"}
