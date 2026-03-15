import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.traces.repo import TraceRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.insert = AsyncMock(return_value=1)
    executor.query = AsyncMock(return_value=[])
    executor.select = AsyncMock(return_value=[])
    return executor


class TestTraceRepo:
    @pytest.mark.asyncio
    async def test_record_trace(self, mock_executor):
        repo = TraceRepo(mock_executor)
        trace_id = await repo.record(
            conversation_id="conv-1",
            user_id="u1",
            user_message="Hello, how are you?",
            intent="quick",
            model="claude-3",
            tool_calls=[{"name": "list_staves"}],
            duration_ms=150.5,
        )
        assert trace_id.startswith("trace-")
        mock_executor.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_trace_truncates_long_message(self, mock_executor):
        repo = TraceRepo(mock_executor)
        long_msg = "x" * 600
        await repo.record(
            conversation_id="conv-1",
            user_id="u1",
            user_message=long_msg,
            intent="investigation",
        )
        call_args = mock_executor.insert.call_args[0]
        data = call_args[1]
        assert len(data["user_message_preview"]) <= 503  # 500 + "..."

    @pytest.mark.asyncio
    async def test_list_by_conversation(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "trace-1", "conversation_id": "conv-1", "user_id": "u1",
             "user_message_preview": "Hello", "intent": "quick",
             "model": "claude-3", "tool_calls": None,
             "duration_ms": 100.0, "created_at": "2025-01-01T00:00:00Z"}
        ]
        repo = TraceRepo(mock_executor)
        result = await repo.list_by_conversation("conv-1")
        assert len(result) == 1
        assert result[0].intent == "quick"

    @pytest.mark.asyncio
    async def test_record_with_no_optional_fields(self, mock_executor):
        repo = TraceRepo(mock_executor)
        trace_id = await repo.record(
            conversation_id="conv-1",
            user_id="u1",
            user_message="Hi",
            intent="quick",
        )
        assert trace_id.startswith("trace-")
        call_args = mock_executor.insert.call_args[0]
        data = call_args[1]
        assert data["model"] is None
        assert data["tool_calls"] is None
