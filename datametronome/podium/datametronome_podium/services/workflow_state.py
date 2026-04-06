"""
Workflow state service — CRUD for agent checkpoints and event logging.

Provides the persistence layer for LangGraph-style stateful orchestration:
- Checkpoints: save/restore orchestrator execution state
- Events: full audit trail of every state transition
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from datametronome_podium.core.database import get_executor

logger = logging.getLogger(__name__)


async def create_checkpoint(
    conversation_id: str,
    user_id: str,
    workflow_name: str,
) -> str:
    """Create a new workflow checkpoint. Returns the checkpoint ID."""
    checkpoint_id = f"wf-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    await get_executor().insert("workflow_checkpoints", {
        "id": checkpoint_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "workflow_name": workflow_name,
        "current_node": None,
        "state_data": json.dumps({}),
        "status": "running",
        "parent_checkpoint_id": None,
        "created_at": now,
        "updated_at": now,
    })

    logger.info("Created checkpoint %s for %s", checkpoint_id, workflow_name)
    return checkpoint_id


async def update_checkpoint(
    checkpoint_id: str,
    *,
    current_node: str | None = None,
    state_data: dict | None = None,
    status: str | None = None,
) -> None:
    """Update a checkpoint's current state."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    set_parts = ["updated_at = ?"]
    params: list = [now]

    if current_node is not None:
        set_parts.append("current_node = ?")
        params.append(current_node)
    if state_data is not None:
        set_parts.append("state_data = ?")
        params.append(json.dumps(state_data))
    if status is not None:
        set_parts.append("status = ?")
        params.append(status)

    params.append(checkpoint_id)
    sql = f"UPDATE workflow_checkpoints SET {', '.join(set_parts)} WHERE id = ?"
    await get_executor().execute(sql, params)


async def load_checkpoint(checkpoint_id: str) -> dict | None:
    """Load a checkpoint by ID. Returns None if not found."""
    rows = await get_executor().query(
        "SELECT * FROM workflow_checkpoints WHERE id = ?", [checkpoint_id]
    )
    return rows[0] if rows else None


async def find_active_checkpoint(conversation_id: str) -> dict | None:
    """Find the latest running or paused checkpoint for a conversation."""
    rows = await get_executor().query(
        "SELECT * FROM workflow_checkpoints "
        "WHERE conversation_id = ? AND status IN ('running', 'paused') "
        "ORDER BY created_at DESC LIMIT 1",
        [conversation_id],
    )
    return rows[0] if rows else None


async def log_event(
    checkpoint_id: str,
    event_type: str,
    node_name: str | None,
    event_data: dict | None = None,
) -> None:
    """Log a workflow event (state transition, tool call, error, etc.)."""
    event_id = f"evt-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    await get_executor().insert("workflow_events", {
        "id": event_id,
        "checkpoint_id": checkpoint_id,
        "event_type": event_type,
        "node_name": node_name,
        "event_data": json.dumps(event_data) if event_data else None,
        "created_at": now,
    })
