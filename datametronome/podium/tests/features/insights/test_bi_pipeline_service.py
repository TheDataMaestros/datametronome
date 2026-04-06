"""Tests for the BI track additions to InsightPipelineService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_run_both_tracks_graceful_degradation():
    """If BI track fails, quality result is still returned."""
    from datametronome_podium.features.insights.service import InsightPipelineService

    mock_executor = AsyncMock()
    service = InsightPipelineService(executor=mock_executor)

    mock_snapshot = MagicMock()
    mock_profile = MagicMock()
    mock_profile.domain_type = "e-commerce"

    async def good_quality(*a, **kw):
        return {"health_score": 80, "summary": "ok", "dimensions": [], "anomalies": [],
                "suggestions": [], "key_findings": [], "report_type": "daily",
                "checks_to_create": []}

    async def bad_bi(*a, **kw):
        raise RuntimeError("BI exploded")

    with patch.object(service, "analyze_business", side_effect=good_quality), \
         patch.object(service, "_analyze_business_intelligence", side_effect=bad_bi):
        quality, bi = await service._run_both_tracks("stave-1", mock_snapshot, mock_profile)

    assert quality is not None
    assert quality["health_score"] == 80
    assert bi is None


@pytest.mark.asyncio
async def test_persist_business_report_called_when_bi_present():
    """persist_results calls _persist_business_report when bi_analysis is provided."""
    from datametronome_podium.features.insights.service import InsightPipelineService

    mock_executor = AsyncMock()
    service = InsightPipelineService(executor=mock_executor)

    mock_snapshot = MagicMock()
    mock_snapshot.id = "snap-1"

    bi_data = {
        "business_health_score": 75, "executive_summary": "Good.",
        "kpis": [], "top_performers": [], "bottom_performers": [],
        "trends": [], "opportunities": [], "risks": [],
    }

    with patch.object(service, "_upsert_profile", new_callable=AsyncMock), \
         patch.object(service.repo, "create_report", new_callable=AsyncMock), \
         patch.object(service, "_persist_suggestions", new_callable=AsyncMock), \
         patch.object(service, "_persist_auto_checks", new_callable=AsyncMock), \
         patch.object(service, "_persist_business_report", new_callable=AsyncMock) as mock_br:
        await service.persist_results("stave-1", mock_snapshot, None, bi_analysis=bi_data)

    mock_br.assert_called_once()
    call_args = mock_br.call_args
    assert call_args[0][0] == "stave-1"


@pytest.mark.asyncio
async def test_prune_old_snapshots_also_prunes_query_plans():
    """prune_old_snapshots must call repo.prune_old_plans to delete stave_query_plans rows."""
    from datametronome_podium.tasks.intelligence_tasks import _prune_snapshots_async

    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(return_value=1)

    with patch(
        "datametronome_podium.core.worker_db.worker_db_session"
    ) as mock_session, patch(
        "datametronome_podium.features.insights.repo.InsightsRepo.prune_old_plans",
        new_callable=AsyncMock,
    ) as mock_prune:
        mock_session.return_value.__aenter__ = AsyncMock(return_value=(None, mock_executor))
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        await _prune_snapshots_async()

    # repo.prune_old_plans must have been called with a cutoff timestamp
    mock_prune.assert_called_once()
    cutoff_arg = mock_prune.call_args[0][0]
    assert "2025" in cutoff_arg or "2026" in cutoff_arg
