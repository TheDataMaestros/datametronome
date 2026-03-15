"""Chat message domain model."""
from pydantic import BaseModel


class ChatMessage(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    role: str
    content: str
    tool_calls: str | None = None  # JSON string
    created_at: str
