import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.chat.repo import ChatRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.execute = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    return executor


class TestChatRepo:
    @pytest.mark.asyncio
    async def test_get_history(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "msg-1", "conversation_id": "conv-1", "user_id": "u1",
             "role": "user", "content": "Hello", "tool_calls": None,
             "created_at": "2025-01-01T00:00:00Z"}
        ]
        repo = ChatRepo(mock_executor)
        result = await repo.get_history("conv-1", "u1", limit=20)
        assert len(result) == 1
        assert result[0].role == "user"

    @pytest.mark.asyncio
    async def test_save_message(self, mock_executor):
        from datametronome_podium.features.chat.model import ChatMessage
        repo = ChatRepo(mock_executor)
        msg = ChatMessage(
            id="msg-1", conversation_id="conv-1", user_id="u1",
            role="user", content="Hello",
            created_at="2025-01-01T00:00:00Z"
        )
        result = await repo.save_message(msg)
        assert result == 1
        mock_executor.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_conversations(self, mock_executor):
        mock_executor.query.return_value = [
            {"conversation_id": "conv-1", "last_message": "2025-01-01T00:00:00Z",
             "title": "Hello world", "message_count": 5}
        ]
        repo = ChatRepo(mock_executor)
        result = await repo.list_conversations("u1")
        assert len(result) == 1
        assert result[0]["conversation_id"] == "conv-1"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, mock_executor):
        repo = ChatRepo(mock_executor)
        result = await repo.delete_conversation("conv-1", "u1")
        assert result == 1
