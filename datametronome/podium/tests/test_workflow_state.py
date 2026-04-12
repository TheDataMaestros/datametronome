"""Tests for workflow state service."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datametronome_podium.services.workflow_state import (
    create_checkpoint,
    update_checkpoint,
    load_checkpoint,
    find_active_checkpoint,
    log_event,
)


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    executor.insert = AsyncMock(return_value=1)
    executor.execute = AsyncMock(return_value=1)
    executor.query = AsyncMock(return_value=[])
    return executor


@pytest.mark.asyncio
async def test_create_checkpoint(mock_executor):
    """create_checkpoint should insert a row and return the checkpoint ID."""
    with patch(
        "datametronome_podium.services.workflow_state.get_executor",
        return_value=mock_executor,
    ):
        cp_id = await create_checkpoint("conv-1", "user-1", "chain:inv→report")

        assert cp_id is not None
        assert isinstance(cp_id, str)
        mock_executor.insert.assert_called_once()
        call_args = mock_executor.insert.call_args
        assert call_args[0][0] == "workflow_checkpoints"
        data = call_args[0][1]
        assert data["conversation_id"] == "conv-1"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_update_checkpoint(mock_executor):
    """update_checkpoint should update status and state_data."""
    with patch(
        "datametronome_podium.services.workflow_state.get_executor",
        return_value=mock_executor,
    ):
        await update_checkpoint(
            "cp-1", current_node="investigation", state_data={"step": 1}, status="running"
        )
        mock_executor.execute.assert_called_once()
        sql = mock_executor.execute.call_args[0][0]
        assert "UPDATE workflow_checkpoints" in sql


@pytest.mark.asyncio
async def test_load_checkpoint(mock_executor):
    """load_checkpoint should return the checkpoint dict."""
    fake_row = {
        "id": "cp-1",
        "conversation_id": "conv-1",
        "workflow_name": "single:report",
        "current_node": "report",
        "state_data": '{"step": 1}',
        "status": "running",
    }
    mock_executor.query.return_value = [fake_row]
    with patch(
        "datametronome_podium.services.workflow_state.get_executor",
        return_value=mock_executor,
    ):
        result = await load_checkpoint("cp-1")
        assert result is not None
        assert result["id"] == "cp-1"
        assert result["status"] == "running"


@pytest.mark.asyncio
async def test_find_active_checkpoint_found(mock_executor):
    """find_active_checkpoint should return latest running/paused checkpoint."""
    fake_row = {"id": "cp-2", "status": "paused", "workflow_name": "chain:inv→report"}
    mock_executor.query.return_value = [fake_row]
    with patch(
        "datametronome_podium.services.workflow_state.get_executor",
        return_value=mock_executor,
    ):
        result = await find_active_checkpoint("conv-1")
        assert result is not None
        assert result["id"] == "cp-2"


@pytest.mark.asyncio
async def test_find_active_checkpoint_none(mock_executor):
    """find_active_checkpoint should return None when no active checkpoint."""
    mock_executor.query.return_value = []
    with patch(
        "datametronome_podium.services.workflow_state.get_executor",
        return_value=mock_executor,
    ):
        result = await find_active_checkpoint("conv-1")
        assert result is None


@pytest.mark.asyncio
async def test_log_event(mock_executor):
    """log_event should insert a workflow_events row."""
    with patch(
        "datametronome_podium.services.workflow_state.get_executor",
        return_value=mock_executor,
    ):
        await log_event("cp-1", "node_entered", "investigation", {"message": "start"})

        mock_executor.insert.assert_called_once()
        call_args = mock_executor.insert.call_args
        assert call_args[0][0] == "workflow_events"
        data = call_args[0][1]
        assert data["checkpoint_id"] == "cp-1"
        assert data["event_type"] == "node_entered"
