"""Unit tests for agent tool functions. DB is mocked."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Minimal raw DB row shapes used across tests
_STAVE_ROW = {
    "id": "s1",
    "name": "prod",
    "data_source_type": "postgres",
    "connection_config": '{"host": "localhost", "port": 5432}',
    "is_active": True,
    "paused": False,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z",
    "description": None,
}

_CLEF_ROW = {
    "id": "c1",
    "stave_id": "s1",
    "name": "Row Count",
    "description": None,
    "check_type": "row_count",
    "config": '{"table": "orders"}',
    "warn": None,
    "fail": None,
    "retry_config": None,
    "schedule": "@daily",
    "is_active": True,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z",
}


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    # query is used by report tools and filtered list_checks
    executor.query = AsyncMock(return_value=[])
    # select is used by repos (StaveRepo, ClefRepo, CheckRepo)
    executor.select = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.execute = AsyncMock()
    return executor


@pytest.mark.asyncio
async def test_list_staves_returns_dict(mock_executor):
    mock_executor.select.return_value = [_STAVE_ROW]
    with patch("datametronome_podium.services.agent_tools.get_executor", return_value=mock_executor):
        from datametronome_podium.services.agent_tools import list_staves
        result = await list_staves()
        assert "staves" in result
        assert result["count"] == 1


@pytest.mark.asyncio
async def test_list_staves_empty(mock_executor):
    mock_executor.select.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_executor", return_value=mock_executor):
        from datametronome_podium.services.agent_tools import list_staves
        result = await list_staves(active_only=True)
        assert "staves" in result
        assert result["count"] == 0


@pytest.mark.asyncio
async def test_get_stave_not_found(mock_executor):
    mock_executor.select.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_executor", return_value=mock_executor):
        from datametronome_podium.services.agent_tools import get_stave
        result = await get_stave("nonexistent-id")
        assert "error" in result


@pytest.mark.asyncio
async def test_get_summary_report_returns_dict(mock_executor):
    # get_summary_report uses executor.query directly for COUNT queries
    mock_executor.query.return_value = [{"count": 5}]
    with patch("datametronome_podium.services.agent_tools.get_executor", return_value=mock_executor):
        from datametronome_podium.services.agent_tools import get_summary_report
        result = await get_summary_report()
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_list_clefs_returns_dict(mock_executor):
    mock_executor.select.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_executor", return_value=mock_executor):
        from datametronome_podium.services.agent_tools import list_clefs
        result = await list_clefs()
        assert "clefs" in result
        assert result["count"] == 0


@pytest.mark.asyncio
async def test_get_clef_not_found(mock_executor):
    mock_executor.select.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_executor", return_value=mock_executor):
        from datametronome_podium.services.agent_tools import get_clef
        result = await get_clef("nonexistent-id")
        assert "error" in result


@pytest.mark.asyncio
async def test_list_checks_returns_list(mock_executor):
    mock_executor.query.return_value = [{"id": "c1", "status": "passed"}]
    with patch("datametronome_podium.services.agent_tools.get_executor", return_value=mock_executor):
        from datametronome_podium.services.agent_tools import list_checks
        result = await list_checks()
        assert isinstance(result, (list, dict))


def test_all_tools_list_has_13_entries():
    from datametronome_podium.services.agent_tools import ALL_TOOLS
    assert len(ALL_TOOLS) == 13


def test_insight_tools_list_has_9_entries():
    from datametronome_podium.services.agent_tools import INSIGHT_TOOLS
    assert len(INSIGHT_TOOLS) == 9
