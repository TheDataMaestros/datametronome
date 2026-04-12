"""Workflow data access."""
from __future__ import annotations

import json
import uuid
from typing import Any

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.timestamp_utils import now_utc_iso


class WorkflowRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def create_checkpoint(
        self, conversation_id: str, user_id: str, workflow_name: str
    ) -> str:
        cp_id = f"wf-{uuid.uuid4().hex[:12]}"
        now = now_utc_iso()
        await self.db.insert("workflow_checkpoints", {
            "id": cp_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "workflow_name": workflow_name,
            "current_node": None,
            "state_data": "{}",
            "status": "running",
            "parent_checkpoint_id": None,
            "created_at": now,
            "updated_at": now,
        })
        return cp_id

    async def load_checkpoint(self, checkpoint_id: str) -> dict | None:
        rows = await self.db.select("workflow_checkpoints", where={"id": checkpoint_id})
        return dict(rows[0]) if rows else None

    async def update_checkpoint(
        self, checkpoint_id: str, **kwargs: Any
    ) -> int:
        now = now_utc_iso()
        data = {k: v for k, v in kwargs.items() if v is not None}
        if "state_data" in data and isinstance(data["state_data"], dict):
            data["state_data"] = json.dumps(data["state_data"])
        data["updated_at"] = now
        return await self.db.update("workflow_checkpoints", data, where={"id": checkpoint_id})

    async def find_active_checkpoint(self, conversation_id: str) -> dict | None:
        rows = await self.db.query(
            "SELECT * FROM workflow_checkpoints "
            "WHERE conversation_id = ? AND status IN ('running', 'paused') "
            "ORDER BY created_at DESC LIMIT ?",
            [conversation_id, 1]
        )
        return dict(rows[0]) if rows else None

    async def log_event(
        self, checkpoint_id: str, event_type: str,
        node_name: str | None = None, event_data: dict | None = None
    ) -> str:
        evt_id = f"evt-{uuid.uuid4().hex[:12]}"
        now = now_utc_iso()
        await self.db.insert("workflow_events", {
            "id": evt_id,
            "checkpoint_id": checkpoint_id,
            "event_type": event_type,
            "node_name": node_name,
            "event_data": json.dumps(event_data) if event_data else None,
            "created_at": now,
        })
        return evt_id
