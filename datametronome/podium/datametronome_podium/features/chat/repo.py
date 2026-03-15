"""Chat data access."""
from __future__ import annotations
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.chat.model import ChatMessage


class ChatRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def get_history(
        self, conversation_id: str, user_id: str, limit: int = 20
    ) -> list[ChatMessage]:
        rows = await self.db.query(
            "SELECT * FROM chat_messages WHERE conversation_id = ? AND user_id = ? ORDER BY created_at ASC LIMIT ?",
            [conversation_id, user_id, limit]
        )
        return [ChatMessage(**row) for row in rows]

    async def save_message(self, message: ChatMessage) -> int:
        return await self.db.insert("chat_messages", message.model_dump())

    async def list_conversations(self, user_id: str) -> list[dict]:
        rows = await self.db.query(
            "SELECT conversation_id, MAX(created_at) as last_message, "
            "SUBSTR(MIN(content), 1, 50) as title, COUNT(*) as message_count "
            "FROM chat_messages WHERE user_id = ? "
            "GROUP BY conversation_id ORDER BY last_message DESC",
            [user_id]
        )
        return [dict(row) for row in rows]

    async def delete_conversation(self, conversation_id: str, user_id: str) -> int:
        return await self.db.execute(
            "DELETE FROM chat_messages WHERE conversation_id = ? AND user_id = ?",
            [conversation_id, user_id]
        )
