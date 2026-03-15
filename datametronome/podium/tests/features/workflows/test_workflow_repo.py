import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.workflows.repo import WorkflowRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    return executor


class TestWorkflowRepo:
    @pytest.mark.asyncio
    async def test_create_checkpoint(self, mock_executor):
        repo = WorkflowRepo(mock_executor)
        cp_id = await repo.create_checkpoint("conv-1", "u1", "agent_workflow")
        assert cp_id.startswith("wf-")
        mock_executor.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_checkpoint(self, mock_executor):
        mock_executor.select.return_value = [
            {"id": "wf-1", "conversation_id": "conv-1", "user_id": "u1",
             "workflow_name": "agent_workflow", "current_node": "router",
             "state_data": '{}', "status": "running",
             "parent_checkpoint_id": None,
             "created_at": "2025-01-01T00:00:00Z",
             "updated_at": "2025-01-01T00:00:00Z"}
        ]
        repo = WorkflowRepo(mock_executor)
        result = await repo.load_checkpoint("wf-1")
        assert result is not None
        assert result["workflow_name"] == "agent_workflow"

    @pytest.mark.asyncio
    async def test_load_checkpoint_not_found(self, mock_executor):
        repo = WorkflowRepo(mock_executor)
        result = await repo.load_checkpoint("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_checkpoint(self, mock_executor):
        repo = WorkflowRepo(mock_executor)
        result = await repo.update_checkpoint("wf-1", current_node="executor", status="running")
        assert result == 1

    @pytest.mark.asyncio
    async def test_find_active_checkpoint(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "wf-1", "conversation_id": "conv-1", "user_id": "u1",
             "workflow_name": "agent_workflow", "current_node": "router",
             "state_data": '{}', "status": "running",
             "parent_checkpoint_id": None,
             "created_at": "2025-01-01T00:00:00Z",
             "updated_at": "2025-01-01T00:00:00Z"}
        ]
        repo = WorkflowRepo(mock_executor)
        result = await repo.find_active_checkpoint("conv-1")
        assert result is not None
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_log_event(self, mock_executor):
        repo = WorkflowRepo(mock_executor)
        evt_id = await repo.log_event("wf-1", "state_transition", node_name="router", event_data={"key": "val"})
        assert evt_id.startswith("evt-")
        mock_executor.insert.assert_called_once()
