"""Insights API router."""
import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from datametronome_podium.api.v1.endpoints.auth import get_current_user
from datametronome_podium.core.database import get_executor
from datametronome_podium.features.insights.repo import InsightsRepo
from datametronome_podium.features.insights.service import InsightPipelineService

from datametronome_podium.features.insights.model import Notification
from datametronome_podium.features.insights.schema import (
    DataProfileResponse,
    InsightReportResponse,
    DashboardResponse,
    SuggestionResponse,
    SnapshotResponse,
    AnalyzeRequest,
    DismissRequest,
    AssignRequest,
    NotificationResponse,
    BusinessReportResponse,
)

logger = logging.getLogger(__name__)

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
    business_report = await repo.get_latest_business_report(stave_id)

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
        business_report=business_report.model_dump() if business_report else None,
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


@router.post("/{stave_id}/suggestions/{suggestion_id}/read")
async def mark_suggestion_read(
    stave_id: str,
    suggestion_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Mark a suggestion as read by the authenticated user."""
    username: str = current_user["username"]
    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if sug.stave_id != stave_id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.mark_suggestion_read(suggestion_id, username)
    updated = await repo.get_suggestion(suggestion_id)
    return {"id": suggestion_id, "read_at": updated.read_at if updated else None, "read_by": username}


@router.post("/{stave_id}/suggestions/{suggestion_id}/assign")
async def assign_suggestion(
    stave_id: str,
    suggestion_id: str,
    body: AssignRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),  # noqa: ARG001 — enforces auth
):
    """Assign a suggestion to a user and create a notification."""
    from datetime import datetime, timezone
    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if sug.stave_id != stave_id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.assign_suggestion(suggestion_id, body.assigned_to)

    # Create notification for the assignee
    user = await repo.get_user_by_username(body.assigned_to)
    if user:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        notif = Notification(
            id=f"notif-{uuid.uuid4().hex[:12]}",
            user_id=user["id"],
            type="suggestion_assigned",
            title="New suggestion assigned to you",
            body=f"[{sug.priority.upper()}] {sug.action[:120]}",
            reference_type="suggestion",
            reference_id=suggestion_id,
            read_at=None,
            created_at=now,
        )
        await repo.create_notification(notif)

    return {"id": suggestion_id, "assigned_to": body.assigned_to}


@router.post("/{stave_id}/suggestions/{suggestion_id}/accept")
async def accept_suggestion(stave_id: str, suggestion_id: str):
    """Accept an insight suggestion. Auto-creates a clef if AI included a check_spec."""
    from datetime import datetime, timezone

    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if sug.stave_id != stave_id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.update_suggestion_status(suggestion_id, "accepted")

    check_created = False
    if sug.check_spec:
        try:
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            service = InsightPipelineService(executor=get_executor())
            await service._create_check_from_spec(
                stave_id, sug.report_id, sug.check_spec, now
            )
            check_created = True
        except Exception as exc:
            logger.warning(
                "Failed to create check from accepted suggestion %s: %s",
                suggestion_id, exc,
            )

    return {
        "id": suggestion_id,
        "status": "accepted",
        "check_created": check_created,
    }


@router.post("/{stave_id}/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(stave_id: str, suggestion_id: str, body: DismissRequest = DismissRequest()):
    """Dismiss an insight suggestion with an optional reason."""
    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if sug.stave_id != stave_id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.update_suggestion_status(suggestion_id, "dismissed", dismiss_reason=body.reason)
    return {"id": suggestion_id, "status": "dismissed", "reason": body.reason}


# --- Business Reports ---


@router.get(
    "/{stave_id}/business", response_model=BusinessReportResponse
)
async def get_business_report(stave_id: str):
    """Get the latest business intelligence report for a stave."""
    report = await _repo().get_latest_business_report(stave_id)
    if not report:
        raise HTTPException(
            status_code=404, detail="No business report found for this stave"
        )
    return report.model_dump()


@router.get(
    "/{stave_id}/business/history", response_model=list[BusinessReportResponse]
)
async def get_business_report_history(stave_id: str, limit: int = 20):
    """List business intelligence report history for a stave."""
    reports = await _repo().list_business_reports(stave_id, limit=limit)
    return [r.model_dump() for r in reports]


# --- Notifications ---


@router.get("/notifications/me", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List notifications for the authenticated user."""
    user_id: str = current_user["id"]
    results = await _repo().list_notifications(user_id, unread_only=unread_only)
    return [n.model_dump() for n in results]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    await _repo().mark_notification_read(notification_id)
    return {"id": notification_id, "read": True}
