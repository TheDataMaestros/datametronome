"""Unit tests for agent tool functions. DB is mocked."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_list_staves_returns_dict(mock_db):
    mock_db.query.return_value = [
        {"id": "s1", "name": "prod", "data_source_type": "postgres",
         "connection_config": '{"host": "localhost", "port": 5432}', "is_active": 1,
         "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z",
         "description": None}
    ]
    with patch("datametronome_podium.services.agent_tools.get_db", new_callable=AsyncMock) as mock_get_db:
        mock_get_db.return_value = mock_db
        from datametronome_podium.services.agent_tools import list_staves
        result = await list_staves()
        assert "staves" in result
        assert result["count"] == 1


@pytest.mark.asyncio
async def test_list_staves_empty(mock_db):
    mock_db.query.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_db", new_callable=AsyncMock) as mock_get_db:
        mock_get_db.return_value = mock_db
        from datametronome_podium.services.agent_tools import list_staves
        result = await list_staves(active_only=True)
        assert "staves" in result
        assert result["count"] == 0


@pytest.mark.asyncio
async def test_get_stave_not_found(mock_db):
    mock_db.query.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_db", new_callable=AsyncMock) as mock_get_db:
        mock_get_db.return_value = mock_db
        from datametronome_podium.services.agent_tools import get_stave
        result = await get_stave("nonexistent-id")
        assert "error" in result


@pytest.mark.asyncio
async def test_get_summary_report_returns_dict(mock_db):
    mock_db.query.return_value = [{"count": 5}]
    with patch("datametronome_podium.services.agent_tools.get_db", new_callable=AsyncMock) as mock_get_db:
        mock_get_db.return_value = mock_db
        from datametronome_podium.services.agent_tools import get_summary_report
        result = await get_summary_report()
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_list_clefs_returns_dict(mock_db):
    mock_db.query.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_db", new_callable=AsyncMock) as mock_get_db:
        mock_get_db.return_value = mock_db
        from datametronome_podium.services.agent_tools import list_clefs
        result = await list_clefs()
        assert "clefs" in result
        assert result["count"] == 0


@pytest.mark.asyncio
async def test_get_clef_not_found(mock_db):
    mock_db.query.return_value = []
    with patch("datametronome_podium.services.agent_tools.get_db", new_callable=AsyncMock) as mock_get_db:
        mock_get_db.return_value = mock_db
        from datametronome_podium.services.agent_tools import get_clef
        result = await get_clef("nonexistent-id")
        assert "error" in result


@pytest.mark.asyncio
async def test_list_checks_returns_list(mock_db):
    mock_db.query.return_value = [{"id": "c1", "status": "passed"}]
    with patch("datametronome_podium.services.agent_tools.get_db", new_callable=AsyncMock) as mock_get_db:
        mock_get_db.return_value = mock_db
        from datametronome_podium.services.agent_tools import list_checks
        result = await list_checks()
        assert isinstance(result, (list, dict))


def test_all_tools_list_has_11_entries():
    from datametronome_podium.services.agent_tools import ALL_TOOLS
    assert len(ALL_TOOLS) == 11
