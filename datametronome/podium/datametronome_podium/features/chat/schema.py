"""Chat API DTOs."""
from typing import Any
from pydantic import BaseModel


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    callId: str
    result: Any
    error: str | None = None


class ChatRequest(BaseModel):
    message: str
    conversationId: str | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    message: str
    conversationId: str
    toolCalls: list[ToolCall] | None = None
    finishReason: str | None = None
    model: str | None = None
    intent: str | None = None
    agentType: str | None = None
    orchestrationMode: str | None = None
    agentChain: list[str] | None = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str | None = None
    tool_calls: list[ToolCall] | None = None
    model: str | None = None
