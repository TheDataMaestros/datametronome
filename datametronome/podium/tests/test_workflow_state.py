"""Tests for workflow state service."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from datametronome_podium.services.workflow_state import (
    create_checkpoint,
    update_checkpoint,
    load_checkpoint,
    find_active_checkpoint,
    log_event,
)


@pytest.mark.asyncio
async def test_create_checkpoint():
    """create_checkpoint should insert a row and return the checkpoint ID."""
    with patch(
        "datametronome_podium.services.workflow_state.insert_data",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_insert:
        cp_id = await create_checkpoint("conv-1", "user-1", "chain:inv→report")

        assert cp_id is not None
        assert isinstance(cp_id, str)
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "workflow_checkpoints"
        data = call_args[0][1]
        assert data["conversation_id"] == "conv-1"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_update_checkpoint():
    """update_checkpoint should update status and state_data."""
    with patch(
        "datametronome_podium.services.workflow_state.execute_write",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_write:
        await update_checkpoint(
            "cp-1", current_node="investigation", state_data={"step": 1}, status="running"
        )
        mock_write.assert_called_once()
        sql = mock_write.call_args[0][0]
        assert "UPDATE workflow_checkpoints" in sql


@pytest.mark.asyncio
async def test_load_checkpoint():
    """load_checkpoint should return the checkpoint dict."""
    fake_row = {
        "id": "cp-1",
        "conversation_id": "conv-1",
        "workflow_name": "single:report",
        "current_node": "report",
        "state_data": '{"step": 1}',
        "status": "running",
    }
    with patch(
        "datametronome_podium.services.workflow_state.execute_query",
        new_callable=AsyncMock,
        return_value=[fake_row],
    ):
        result = await load_checkpoint("cp-1")
        assert result["id"] == "cp-1"
        assert result["status"] == "running"


@pytest.mark.asyncio
async def test_find_active_checkpoint_found():
    """find_active_checkpoint should return latest running/paused checkpoint."""
    fake_row = {"id": "cp-2", "status": "paused", "workflow_name": "chain:inv→report"}
    with patch(
        "datametronome_podium.services.workflow_state.execute_query",
        new_callable=AsyncMock,
        return_value=[fake_row],
    ):
        result = await find_active_checkpoint("conv-1")
        assert result is not None
        assert result["id"] == "cp-2"


@pytest.mark.asyncio
async def test_find_active_checkpoint_none():
    """find_active_checkpoint should return None when no active checkpoint."""
    with patch(
        "datametronome_podium.services.workflow_state.execute_query",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await find_active_checkpoint("conv-1")
        assert result is None


@pytest.mark.asyncio
async def test_log_event():
    """log_event should insert a workflow_events row."""
    with patch(
        "datametronome_podium.services.workflow_state.insert_data",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_insert:
        await log_event("cp-1", "node_entered", "investigation", {"message": "start"})

        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "workflow_events"
        data = call_args[0][1]
        assert data["checkpoint_id"] == "cp-1"
        assert data["event_type"] == "node_entered"
