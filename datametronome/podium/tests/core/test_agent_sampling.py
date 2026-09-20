"""The agent tools sample tables through the shared, dialect-aware helper.

They used to hand-build `SELECT * FROM ... LIMIT n` for three of the seven
source types, with the limit interpolated into the string and the other four
falling through to a default that is wrong for BigQuery and dbt. If someone
reintroduces per-dialect SQL here, these fail.
"""

from unittest.mock import AsyncMock, patch

import pytest

from datametronome_podium.features.staves.model import Stave
from datametronome_podium.services import agent_tools

STAVE = Stave(
    id="s1", name="s", data_source_type="bigquery",
    connection_config={"project_id": "p", "dataset": "d"},
)
ROW = type("Row", (), {"model_dump": lambda self: {"id": "s1"}})()


@pytest.fixture
def stave_loaded():
    with patch.object(agent_tools, "StaveRepo") as repo, \
         patch.object(agent_tools, "get_executor", return_value=object()), \
         patch("datametronome_podium.services.stave_service.deserialize_stave",
               return_value=STAVE):
        repo.return_value.get = AsyncMock(return_value=ROW)
        yield


@pytest.mark.asyncio
async def test_get_table_sample_delegates_to_the_shared_helper(stave_loaded):
    with patch(
        "datametronome_podium.features.staves.service.fetch_sample_rows",
        new=AsyncMock(return_value=[{"a": 1, "b": 2}]),
    ) as fetch:
        result = await agent_tools.get_table_sample("s1", "orders", limit=50)

    fetch.assert_awaited_once_with(STAVE, "orders", 50)
    assert result["row_count"] == 1
    assert result["columns"] == ["a", "b"]


@pytest.mark.asyncio
async def test_a_sampling_failure_does_not_sink_the_whole_tool(stave_loaded):
    """One unreadable table must not lose the schema-based suggestions."""
    with patch(
        "datametronome_podium.features.staves.service.fetch_sample_rows",
        new=AsyncMock(side_effect=RuntimeError("permission denied")),
    ):
        result = await agent_tools.get_table_sample("s1", "orders")

    assert "error" in result
    assert "permission denied" in str(result["error"])
