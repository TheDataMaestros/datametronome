"""Workflow domain models."""
from pydantic import BaseModel


class WorkflowCheckpoint(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    workflow_name: str
    current_node: str | None = None
    state_data: str | None = None  # JSON string
    status: str = "running"
    parent_checkpoint_id: str | None = None
    created_at: str
    updated_at: str


class WorkflowEvent(BaseModel):
    id: str
    checkpoint_id: str
    event_type: str
    node_name: str | None = None
    event_data: str | None = None  # JSON string
    created_at: str
