"""Tests for intelligence-specific agent tools."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from datametronome_podium.services.agent_tools import (
    get_stave_intelligence,
    trigger_stave_analysis,
)


@pytest.mark.asyncio
async def test_get_stave_intelligence_no_profile():
    mock_repo = MagicMock()
    mock_repo.get_profile = AsyncMock(return_value=None)
    mock_repo.get_latest_report = AsyncMock(return_value=None)
    mock_repo.list_suggestions = AsyncMock(return_value=[])

    with (
        patch(
            "datametronome_podium.core.database.get_executor",
            return_value=MagicMock(),
        ),
        patch(
            "datametronome_podium.features.insights.repo.InsightsRepo",
            return_value=mock_repo,
        ),
    ):
        result = await get_stave_intelligence("stave-123")

    assert result["stave_id"] == "stave-123"
    assert result.get("profile") is None
    assert "No intelligence profile" in result.get("message", "")  # ty: ignore[unsupported-operator]


@pytest.mark.asyncio
async def test_get_stave_intelligence_with_profile():
    mock_profile = MagicMock()
    mock_profile.domain_type = "e-commerce"
    mock_profile.domain_confidence = 0.92
    mock_profile.domain_context = {"vertical": "retail"}
    mock_profile.entity_roles = {"orders": "transaction"}
    mock_profile.learned_patterns = {"weekend_spike": True}

    mock_report = MagicMock()
    mock_report.health_score = 87.5
    mock_report.report_type = "scheduled"
    mock_report.summary = "Looking good"
    mock_report.key_findings = ["Revenue up"]
    mock_report.anomalies = []
    mock_report.dimensions = {"rows": 1000}
    mock_report.created_at = "2026-03-15T00:00:00Z"

    mock_repo = MagicMock()
    mock_repo.get_profile = AsyncMock(return_value=mock_profile)
    mock_repo.get_latest_report = AsyncMock(return_value=mock_report)
    mock_repo.list_suggestions = AsyncMock(return_value=[])

    with (
        patch(
            "datametronome_podium.core.database.get_executor",
            return_value=MagicMock(),
        ),
        patch(
            "datametronome_podium.features.insights.repo.InsightsRepo",
            return_value=mock_repo,
        ),
    ):
        result = await get_stave_intelligence("stave-456")

    assert result["domain_type"] == "e-commerce"
    assert result["health_score"] == 87.5
    assert "profile" not in result  # profile key only set when None


@pytest.mark.asyncio
async def test_get_stave_intelligence_error_handling():
    with patch(
        "datametronome_podium.core.database.get_executor",
        side_effect=RuntimeError("DB not initialized"),
    ):
        result = await get_stave_intelligence("stave-err")

    assert result["stave_id"] == "stave-err"
    assert "error" in result


@pytest.mark.asyncio
async def test_trigger_stave_analysis_queues_task():
    with patch(
        "datametronome_podium.tasks.intelligence_tasks.run_on_demand_analysis"
    ) as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-abc")
        result = await trigger_stave_analysis("stave-123")

    assert result["status"] == "queued"
    assert result["task_id"] == "task-abc"
    mock_task.delay.assert_called_once_with("stave-123")


@pytest.mark.asyncio
async def test_trigger_stave_analysis_celery_unavailable():
    """When the Celery import itself fails, the tool returns an error."""
    with patch.dict("sys.modules", {"datametronome_podium.tasks.intelligence_tasks": None}):
        result = await trigger_stave_analysis("stave-err")

    assert result["status"] == "error"
    assert "error" in result
