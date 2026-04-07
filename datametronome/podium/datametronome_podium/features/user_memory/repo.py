"""User memory data access."""
from __future__ import annotations

import uuid

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.timestamp_utils import now_utc_iso


def _gen_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class UserMemoryRepo:
    """CRUD for user_memories, user_memory_profiles, and conversation_extraction_status."""

    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    # --- user_memories ---

    async def create_memory(
        self,
        *,
        id: str,
        user_id: str,
        category: str,
        content: str,
        source_conversation_id: str | None,
        confidence: float,
        created_at: str,
        updated_at: str,
    ) -> str:
        """Insert a new memory row and return its id."""
        await self.db.insert(
            "user_memories",
            {
                "id": id,
                "user_id": user_id,
                "category": category,
                "content": content,
                "source_conversation_id": source_conversation_id,
                "confidence": confidence,
                "active": 1,
                "superseded_by": None,
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )
        return id

    async def get_memory(self, memory_id: str) -> dict | None:
        rows = await self.db.select("user_memories", where={"id": memory_id})
        return dict(rows[0]) if rows else None

    async def list_active_memories(
        self, user_id: str, category: str | None = None, limit: int = 200
    ) -> list[dict]:
        """Return active memories for a user, optionally filtered by category."""
        if category:
            rows = await self.db.query(
                "SELECT * FROM user_memories "
                "WHERE user_id = ? AND active = 1 AND category = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                [user_id, category, limit],
            )
        else:
            rows = await self.db.query(
                "SELECT * FROM user_memories "
                "WHERE user_id = ? AND active = 1 "
                "ORDER BY updated_at DESC LIMIT ?",
                [user_id, limit],
            )
        return [dict(row) for row in rows]

    async def search_memories(
        self,
        user_id: str,
        q: str | None = None,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[dict]:
        """Search memories by content substring and/or category."""
        conditions = ["user_id = ?"]
        params: list = [user_id]

        if active_only:
            conditions.append("active = 1")
        if category:
            conditions.append("category = ?")
            params.append(category)
        if q:
            # LIKE search on content; caller supplies plain text, we add wildcards
            conditions.append("content LIKE ?")
            params.append(f"%{q}%")

        where_clause = " AND ".join(conditions)
        rows = await self.db.query(
            f"SELECT * FROM user_memories WHERE {where_clause} ORDER BY updated_at DESC",
            params,
        )
        return [dict(row) for row in rows]

    async def update_memory(self, memory_id: str, data: dict) -> int:
        """Partial update of a memory row. Always stamps updated_at."""
        data = {**data, "updated_at": now_utc_iso()}
        return await self.db.update("user_memories", data, where={"id": memory_id})

    async def supersede_memory(self, old_id: str, new_id: str) -> None:
        """Deactivate old_id and record which memory replaced it."""
        now = now_utc_iso()
        await self.db.update(
            "user_memories",
            {"active": 0, "superseded_by": new_id, "updated_at": now},
            where={"id": old_id},
        )

    async def delete_memory(self, memory_id: str) -> int:
        return await self.db.execute(
            "DELETE FROM user_memories WHERE id = ?", [memory_id]
        )

    async def count_active_memories(self, user_id: str) -> int:
        rows = await self.db.query(
            "SELECT COUNT(*) AS cnt FROM user_memories WHERE user_id = ? AND active = 1",
            [user_id],
        )
        return rows[0]["cnt"] if rows else 0

    # --- user_memory_profiles ---

    async def get_profile(self, user_id: str) -> dict | None:
        rows = await self.db.select("user_memory_profiles", where={"user_id": user_id})
        return dict(rows[0]) if rows else None

    async def upsert_profile(
        self,
        *,
        user_id: str,
        domain_summary: str,
        expertise_summary: str,
        investigation_summary: str,
        memory_count: int,
        now: str | None = None,
    ) -> None:
        """Insert or update the user's aggregated memory profile."""
        ts = now or now_utc_iso()
        existing = await self.get_profile(user_id)
        if existing:
            await self.db.update(
                "user_memory_profiles",
                {
                    "domain_summary": domain_summary,
                    "expertise_summary": expertise_summary,
                    "investigation_summary": investigation_summary,
                    "memory_count": memory_count,
                    "last_rebuilt_at": ts,
                },
                where={"user_id": user_id},
            )
        else:
            await self.db.insert(
                "user_memory_profiles",
                {
                    "id": _gen_id("prof-"),
                    "user_id": user_id,
                    "domain_summary": domain_summary,
                    "expertise_summary": expertise_summary,
                    "investigation_summary": investigation_summary,
                    "memory_count": memory_count,
                    "last_rebuilt_at": ts,
                    "created_at": ts,
                },
            )

    # --- conversation_extraction_status ---

    async def upsert_extraction_status(
        self, conversation_id: str, user_id: str
    ) -> None:
        """Register a conversation for extraction. Silently skips if already present."""
        # ON CONFLICT DO NOTHING: avoids re-registering mid-processing conversations
        await self.db.execute(
            "INSERT INTO conversation_extraction_status (conversation_id, user_id, status) "
            "VALUES (?, ?, 'idle') ON CONFLICT(conversation_id) DO NOTHING",
            [conversation_id, user_id],
        )

    async def find_conversations_needing_extraction(
        self, limit: int = 50
    ) -> list[dict]:
        """Return idle conversations where last_extracted_at is NULL or oldest.

        Reads only conversation_extraction_status — no join to chat_messages.
        Returns at most `limit` rows, prioritizing never-extracted conversations
        (NULL last_extracted_at comes first).
        """
        rows = await self.db.query(
            "SELECT ces.conversation_id, ces.user_id, ces.last_extracted_at "
            "FROM conversation_extraction_status ces "
            "WHERE ces.status = 'idle' "
            "ORDER BY (ces.last_extracted_at IS NULL) DESC, ces.last_extracted_at ASC "
            "LIMIT ?",
            [limit],
        )
        return [dict(row) for row in rows]

    async def mark_extraction_processing(self, conversation_id: str) -> int:
        """Atomically move status from idle → processing. Returns rows updated (0 if already taken)."""
        return await self.db.execute(
            "UPDATE conversation_extraction_status "
            "SET status = 'processing' "
            "WHERE conversation_id = ? AND status = 'idle'",
            [conversation_id],
        )

    async def mark_extraction_done(self, conversation_id: str) -> None:
        """Reset status to idle and record extraction timestamp."""
        now = now_utc_iso()
        await self.db.execute(
            "UPDATE conversation_extraction_status "
            "SET status = 'idle', last_extracted_at = ? "
            "WHERE conversation_id = ?",
            [now, conversation_id],
        )

    async def mark_extraction_failed(self, conversation_id: str) -> None:
        """Reset status to idle on failure so the next poll can retry."""
        await self.db.execute(
            "UPDATE conversation_extraction_status "
            "SET status = 'idle' "
            "WHERE conversation_id = ?",
            [conversation_id],
        )

    async def count_user_messages(self, conversation_id: str) -> int:
        """Count messages where role='user' in a conversation."""
        rows = await self.db.query(
            "SELECT COUNT(*) AS cnt FROM chat_messages "
            "WHERE conversation_id = ? AND role = 'user'",
            [conversation_id],
        )
        return rows[0]["cnt"] if rows else 0
