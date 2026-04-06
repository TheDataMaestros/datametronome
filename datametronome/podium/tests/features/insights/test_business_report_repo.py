"""Integration tests for BusinessReport repo methods."""
import pytest
from datametronome_podium.features.insights.model import BusinessReport
from datametronome_podium.features.insights.repo import InsightsRepo


@pytest.fixture
def mock_executor(mocker):
    """Minimal executor mock."""
    ex = mocker.AsyncMock()
    ex.insert = mocker.AsyncMock(return_value=1)
    ex.query = mocker.AsyncMock(return_value=[])
    ex.update = mocker.AsyncMock(return_value=1)
    return ex


@pytest.mark.asyncio
async def test_create_business_report(mock_executor):
    repo = InsightsRepo(mock_executor)
    br = BusinessReport(
        id="br-1", stave_id="s1", snapshot_id="snap-1", tenant_id="default",
        business_health_score=80, executive_summary="All good.",
        kpis=[], top_performers=[], bottom_performers=[],
        trends=[], opportunities=[], risks=[],
        generated_at="2026-03-15T06:00:00Z",
    )
    await repo.create_business_report(br)
    mock_executor.insert.assert_called_once()
    call_args = mock_executor.insert.call_args
    assert call_args[0][0] == "business_reports"


@pytest.mark.asyncio
async def test_get_latest_business_report_none(mock_executor):
    repo = InsightsRepo(mock_executor)
    result = await repo.get_latest_business_report("s1")
    assert result is None


@pytest.mark.asyncio
async def test_list_business_reports_empty(mock_executor):
    repo = InsightsRepo(mock_executor)
    result = await repo.list_business_reports("s1")
    assert result == []
