"""Chat API DTOs."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ToolCall(BaseModel):
    """Tool call model for agent tool calling."""

    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """Tool result model."""

    callId: str
    result: Any
    error: str | None = None


# HTTP response model for conversation history — uses datetime for proper
# serialisation; the endpoint converts raw DB strings via parse_timestamp.
class ChatMessage(BaseModel):
    """Chat message HTTP response model."""

    id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime | None = None
    tool_calls: list[ToolCall] | None = None
    model: str | None = None  # Model name that generated the response
    finish_reason: str | None = None  # Finish reason from the model


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    conversationId: str | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    conversationId: str
    toolCalls: list[ToolCall] | None = None
    finishReason: str | None = None
    model: str | None = None  # Model name that generated the response
    intent: str | None = None  # Classified intent (Phase 1 router)
    agentType: str | None = None  # Specialized agent used (Phase 2)
    orchestrationMode: str | None = None  # Phase 3: single, chain, parallel
    agentChain: list[str] | None = None  # Phase 3: agents used when mode=chain


# Kept for backward compatibility with any callers that imported ChatMessageResponse.
# New code should use ChatMessage instead.
class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str | None = None
    tool_calls: list[ToolCall] | None = None
    model: str | None = None
