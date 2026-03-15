"""Agent trace domain model."""
from pydantic import BaseModel


class AgentTrace(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    user_message_preview: str
    intent: str
    model: str | None = None
    tool_calls: str | None = None  # JSON string
    duration_ms: float | None = None
    created_at: str
