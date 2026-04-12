"""Chat data access."""
from __future__ import annotations

import json
import logging
import uuid

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.timestamp_utils import now_utc_iso
from datametronome_podium.features.chat.model import ChatMessage

logger = logging.getLogger(__name__)


class ChatRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def get_history(
        self, conversation_id: str, user_id: str, limit: int = 20
    ) -> list[ChatMessage]:
        rows = await self.db.query(
            "SELECT * FROM chat_messages WHERE conversation_id = ? AND user_id = ? ORDER BY created_at ASC LIMIT ?",
            [conversation_id, user_id, limit],
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
            [user_id],
        )
        return [dict(row) for row in rows]

    async def delete_conversation(self, conversation_id: str, user_id: str) -> int:
        return await self.db.execute(
            "DELETE FROM chat_messages WHERE conversation_id = ? AND user_id = ?",
            [conversation_id, user_id],
        )

    async def load_history(self, conversation_id: str, user_id: str) -> list[dict]:
        """Load the last 20 messages for a conversation from the database.

        Returns an empty list on any error so the chat pipeline can still proceed
        without history rather than failing the whole request.
        """
        try:
            logger.info(
                "Loading conversation history for conversation_id=%s, user_id=%s",
                conversation_id,
                user_id,
            )
            history = await self.db.query(
                """
                SELECT role, content, tool_calls, created_at
                FROM chat_messages
                WHERE conversation_id = ? AND user_id = ?
                ORDER BY created_at ASC
                LIMIT 20
                """,
                [conversation_id, user_id],
            )
            logger.info(
                "Found %d messages in database for conversation %s",
                len(history),
                conversation_id,
            )
            history_messages = []
            for msg in history:
                msg_dict: dict = {"role": msg["role"], "content": msg["content"]}
                # Include tool_calls to give the agent full prior context
                if msg.get("tool_calls"):
                    try:
                        tool_calls = json.loads(msg["tool_calls"])
                        if tool_calls:
                            msg_dict["tool_calls"] = tool_calls
                    except (json.JSONDecodeError, TypeError):
                        logger.debug(
                            "Skip invalid tool_calls JSON for message in %s",
                            conversation_id,
                        )
                history_messages.append(msg_dict)
                logger.debug(
                    "Added message to history: role=%s, content_preview=%s...",
                    msg_dict["role"],
                    msg_dict["content"][:50],
                )
            logger.info("Loaded %d messages into conversation history", len(history_messages))
            return history_messages
        except Exception as e:
            logger.error("Could not load conversation history: %s", e, exc_info=True)
            return []

    async def persist_messages(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        assistant_message: str,
        tool_calls_json: str | None,
    ) -> None:
        """Save the user and assistant turns to chat_messages, then track the
        conversation for memory extraction.

        Raises on insert failures so the caller can surface them to the client —
        a lost message is worse than a 500 error from the caller's perspective.
        """
        now = now_utc_iso()

        user_message_id = f"msg-{uuid.uuid4().hex[:12]}"
        try:
            await self.db.insert(
                "chat_messages",
                {
                    "id": user_message_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": "user",
                    "content": user_message,
                    "created_at": now,
                    "tool_calls": None,
                },
            )
            logger.info("User message saved - message_id: %s", user_message_id)
        except Exception as e:
            logger.error("Failed to save user message: %s", e, exc_info=True)
            raise

        # Track conversation for memory extraction — non-critical, extraction
        # falls back to polling all recent conversations if this upsert fails.
        try:
            await self.db.execute(
                "INSERT INTO conversation_extraction_status (conversation_id, user_id, status) "
                "VALUES (?, ?, 'idle') ON CONFLICT (conversation_id) DO NOTHING",
                [conversation_id, user_id],
            )
        except Exception:
            pass  # Non-critical — extraction will still work, just with delayed discovery

        # Use a fresh timestamp for the assistant turn (captures actual processing time)
        assistant_now = now_utc_iso()
        assistant_message_id = f"msg-{uuid.uuid4().hex[:12]}"
        try:
            await self.db.insert(
                "chat_messages",
                {
                    "id": assistant_message_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": assistant_message,
                    "tool_calls": tool_calls_json,
                    "created_at": assistant_now,
                },
            )
            logger.info("Assistant message saved - message_id: %s", assistant_message_id)
        except Exception as e:
            logger.error("Failed to save assistant message: %s", e, exc_info=True)
            raise
