"""Agent trace data access. Write-heavy, read-light."""
from __future__ import annotations
import json
import uuid
from typing import Any

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.timestamp_utils import now_utc_iso
from datametronome_podium.features.traces.model import AgentTrace


class TraceRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def record(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        intent: str,
        model: str | None = None,
        tool_calls: list[dict] | None = None,
        duration_ms: float | None = None,
    ) -> str:
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        now = now_utc_iso()
        preview = user_message[:500] + "..." if len(user_message) > 500 else user_message
        await self.db.insert("agent_traces", {
            "id": trace_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_message_preview": preview,
            "intent": intent,
            "model": model,
            "tool_calls": json.dumps(tool_calls) if tool_calls else None,
            "duration_ms": duration_ms,
            "created_at": now,
        })
        return trace_id

    async def list_by_conversation(self, conversation_id: str) -> list[AgentTrace]:
        rows = await self.db.query(
            "SELECT * FROM agent_traces WHERE conversation_id = ? ORDER BY created_at DESC",
            [conversation_id]
        )
        return [AgentTrace(**row) for row in rows]
