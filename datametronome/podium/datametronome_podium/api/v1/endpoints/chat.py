"""
Chat/Agent endpoints for DataMetronome Podium.

This module provides endpoints for interacting with AI agents via Pydantic AI.
The agent can help users with data quality questions, configuration,
and troubleshooting.
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.api.v1.endpoints.auth import get_current_user
from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.metrics import record_chat_request
from datametronome_podium.services.agent_tracing import (
    record_agent_trace,
    trace_duration,
)
from datametronome_podium.services.orchestrator import run_chat
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


def _user_friendly_error_detail(exc: Exception) -> str:
    """Convert known errors to user-friendly messages."""
    msg = str(exc).lower()
    if "connect" in msg and ("11434" in msg or "ollama" in msg):
        return (
            "Cannot connect to Ollama. Is it running? "
            "For Docker: ensure Ollama runs on the host and OLLAMA_API_BASE=http://host.docker.internal:11434 is set."
        )
    if "connection" in msg or "connection refused" in msg:
        return "Connection failed. Check that the AI service (Ollama or API) is running and reachable."
    if "rate limit" in msg or "429" in msg or "quota" in msg:
        return "Rate limit or quota exceeded. Please try again in a few moments."
    return f"Failed to process chat message: {str(exc)[:200]}"


def _parse_timestamp(raw: str | datetime | None) -> datetime | None:
    """Normalise a raw DB timestamp value to a UTC-aware datetime.

    Handles the several malformed formats that SQLite and Postgres can return:
    - Pure Z suffix:          "2025-12-24T16:41:43Z"          → UTC datetime
    - Offset + Z (invalid):  "2025-12-24T16:41:43+00:00Z"    → strip trailing Z
    - Offset only:            "2025-12-24T16:41:43+00:00"     → parse as-is
    - No TZ info:             "2025-12-24T16:41:43"           → assume UTC
    - datetime object:        already a datetime               → ensure tz-aware
    Returns None on any parse failure so callers can apply their own fallback.
    """
    if raw is None:
        return None

    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw

    if not isinstance(raw, str):
        # Unexpected type — attempt coercion via str
        raw = str(raw)

    cleaned = raw.strip()

    # Strip invalid "+HH:MM Z" double-suffix: keep the offset, drop trailing Z
    if re.search(r"\+\d{1,2}:\d{2}Z$", cleaned):
        cleaned = cleaned[:-1]  # remove trailing Z; offset is already present
    elif cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    elif "+" not in cleaned and (cleaned.count("-") < 4 or ":" not in cleaned[-6:]):
        # No timezone information at all — assume UTC
        cleaned = cleaned + "+00:00"

    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _format_timestamp_z(raw: str | datetime | None) -> str | None:
    """Parse a raw timestamp and return an ISO-8601 string ending with 'Z'.

    Used when the caller needs a serialisable string (e.g. JSON response).
    Returns None only when the input cannot be parsed at all.
    """
    dt = _parse_timestamp(raw)
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


class ChatMessage(BaseModel):
    """Chat message model."""

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


@router.post("/", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """
    Send a message to the AI agent and get a response.

    This endpoint integrates with ADK (Agent Development Kit) to provide
    intelligent assistance for data quality management, configuration help,
    and troubleshooting.

    Args:
        request: Chat request with message and optional conversation context
        current_user: Current authenticated user (from dependency)

    Returns:
        Chat response with agent's message and optional tool calls

    Example Request:
        {
            "message": "What data sources do I have configured?",
            "conversationId": "conv-123",
            "context": {}
        }

    Example Response:
        {
            "message": "You have 3 data sources configured: PostgreSQL, BigQuery, and SQLite.",
            "conversationId": "conv-123",
            "toolCalls": [
                {
                    "id": "call-1",
                    "name": "list_staves",
                    "arguments": {}
                }
            ],
            "finishReason": "stop"
        }
    """
    start_time = time.perf_counter()
    try:
        # Generate or use existing conversation ID
        conversation_id = request.conversationId or f"conv-{uuid.uuid4().hex[:12]}"

        # Get user identifier - users table has 'id' field
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        logger.debug(
            "Using user_id: %s (user object keys: %s)",
            user_id,
            list(current_user.keys()) if isinstance(current_user, dict) else "not a dict",
        )

        history_messages = []
        if conversation_id:
            try:
                logger.info(
                    "Loading conversation history for conversation_id=%s, user_id=%s",
                    conversation_id, user_id,
                )
                history = await get_executor().query(
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
                    len(history), conversation_id,
                )
                history_messages = []
                for msg in history:
                    msg_dict = {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                    # Include tool_calls if available to provide full context
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
                        msg_dict["role"], msg_dict["content"][:50],
                    )
                logger.info(
                    "Loaded %d messages into conversation history", len(history_messages)
                )
            except Exception as e:
                logger.error("Could not load conversation history: %s", e, exc_info=True)

        # Run the AI pipeline (router → sub-agents)
        agent_result = await run_chat(
            message=request.message,
            history=history_messages,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        intent = agent_result["intent"]
        orchestration_mode = agent_result["mode"]
        agent_types = agent_result["agents"]
        resolved_model = agent_result.get("model", "pydantic-ai")

        logger.info(
            "Intent=%s mode=%s agents=%s",
            intent, orchestration_mode, agent_types,
        )

        agent_response = {
            "message": agent_result["message"],
            "toolCalls": None,
            "model": resolved_model,
        }

        duration_ms = trace_duration(start_time)
        user_id_for_trace = current_user.get("id") or current_user.get("username") or "anonymous"
        tool_calls_for_trace = agent_response.get("toolCalls")
        model_for_trace = agent_response.get("model") or resolved_model or "unknown"

        await record_agent_trace(
            conversation_id=conversation_id,
            user_id=user_id_for_trace,
            user_message=request.message,
            intent=intent,
            model=model_for_trace,
            tool_calls=tool_calls_for_trace,
            duration_ms=duration_ms,
        )
        record_chat_request(
            status="success",
            duration_seconds=duration_ms / 1000.0,
            intent=intent,
            tool_calls=tool_calls_for_trace,
        )

        msg_value = agent_response.get("message", "")
        response_message: str = str(msg_value) if msg_value else ""
        tool_calls = agent_response.get("toolCalls")

        # Ensure model_name is always a string or None
        model_raw = agent_response.get("model")
        if model_raw:
            model_name: str | None = str(model_raw)
        elif resolved_model:
            model_name = str(resolved_model)
        else:
            model_name = "unknown"

        # Ensure finish_reason is always a string or None
        finish_reason_raw = agent_response.get("finishReason")
        if finish_reason_raw:
            finish_reason: str | None = str(finish_reason_raw)
        else:
            finish_reason = "stop"

        # Save user message to database
        # Get user identifier - users table has 'id' field
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        logger.debug(
            "Saving messages for user_id=%s conversation_id=%s",
            user_id, conversation_id,
        )

        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            await get_executor().insert(
                "chat_messages",
                {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": "user",
                    "content": request.message,
                    "created_at": now,
                    "tool_calls": None,
                },
            )
            logger.info("User message saved - message_id: %s", message_id)
        except Exception as e:
            logger.error("Failed to save user message: %s", e, exc_info=True)
            raise

        # Track conversation for memory extraction — non-critical, extraction
        # falls back to polling all recent conversations if this upsert fails.
        try:
            await get_executor().execute(
                "INSERT INTO conversation_extraction_status (conversation_id, user_id, status) "
                "VALUES (?, ?, 'idle') ON CONFLICT (conversation_id) DO NOTHING",
                [conversation_id, user_id],
            )
        except Exception:
            pass  # Non-critical — extraction will still work, just with delayed discovery

        # Save assistant response to database
        assistant_message_id = f"msg-{uuid.uuid4().hex[:12]}"
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        # Use current time for assistant message (after processing)
        assistant_now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            await get_executor().insert(
                "chat_messages",
                {
                    "id": assistant_message_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": response_message,
                    "tool_calls": tool_calls_json,
                    "created_at": assistant_now,
                },
            )
            logger.info("Assistant message saved - message_id: %s", assistant_message_id)
        except Exception as e:
            logger.error("Failed to save assistant message: %s", e, exc_info=True)
            raise

        # Convert tool calls to response format
        response_tool_calls: list[ToolCall] | None = None
        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            tool_calls_list = [dict(tc) for tc in tool_calls]  # ty: ignore[call-overload]  # ty:ignore[ignore-comment-unknown-rule]
            response_tool_calls = [
                ToolCall(
                    id=str(tc.get("id", f"call-{i}")),
                    name=str(tc.get("name", "")),
                    arguments=tc.get("arguments", {}) or {},
                )
                for i, tc in enumerate(tool_calls_list)
            ]

        # agent_type for response: primary in single, last in chain
        response_agent_type = agent_types[-1] if agent_types else "report"

        return ChatResponse(
            message=response_message,
            conversationId=conversation_id,
            toolCalls=response_tool_calls,
            finishReason=finish_reason,
            model=model_name,
            intent=intent,
            agentType=response_agent_type,
            orchestrationMode=orchestration_mode,
            agentChain=agent_types if orchestration_mode in ("chain", "parallel") else None,
        )

    except Exception as e:
        duration_ms = trace_duration(start_time)
        try:
            err_user_id = current_user.get("id") or current_user.get("username") or "anonymous"
            err_conv_id = request.conversationId or "error-conv"
            err_msg = (request.message or "")[:500]
            await record_agent_trace(
                conversation_id=err_conv_id,
                user_id=err_user_id,
                user_message=err_msg,
                intent="unknown",
                model=None,
                tool_calls=None,
                duration_ms=duration_ms,
            )
            record_chat_request(status="error", duration_seconds=duration_ms / 1000.0, intent="unknown")
        except Exception as trace_err:
            logger.warning("Failed to record error trace: %s", trace_err)
        logger.error("Error processing chat message: %s", e, exc_info=True)
        detail = _user_friendly_error_detail(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


@router.get("/conversations/{conversation_id}", response_model=list[ChatMessage])
async def get_conversation_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> list[ChatMessage]:
    """
    Get conversation history for a specific conversation.

    Args:
        conversation_id: ID of the conversation
        current_user: Current authenticated user

    Returns:
        List of chat messages in the conversation
    """
    try:
        # Get user identifier - users table has 'id' field
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        logger.debug(
            "Using user_id: %s (user object keys: %s)",
            user_id,
            list(current_user.keys()) if isinstance(current_user, dict) else "not a dict",
        )

        logger.debug("Loading conversation %s for user_id: %s", conversation_id, user_id)

        messages = await get_executor().query(
            """
            SELECT id, role, content, tool_calls, created_at
            FROM chat_messages
            WHERE conversation_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            [conversation_id, user_id],
        )

        logger.info("Found %d messages in conversation %s", len(messages), conversation_id)

        # Get model name from settings for assistant messages
        model_name = settings.ai_model or "unknown"

        result = []
        first_message_timestamp: datetime | None = None  # fallback for unparseable rows

        for idx, msg in enumerate(messages):
            tool_calls = None
            if msg.get("tool_calls"):
                try:
                    tool_calls = json.loads(msg["tool_calls"])
                except (json.JSONDecodeError, TypeError):
                    tool_calls = None

            timestamp = _parse_timestamp(msg.get("created_at"))

            # Apply fallback chain when the stored value cannot be parsed
            if timestamp is None:
                logger.warning(
                    "Message %s has invalid or missing created_at: %s",
                    msg.get("id"), msg.get("created_at"),
                )
                if first_message_timestamp is not None:
                    timestamp = first_message_timestamp
                else:
                    timestamp = datetime.fromtimestamp(0, tz=timezone.utc)
                    logger.warning("No fallback available, using epoch timestamp")

            if first_message_timestamp is None:
                first_message_timestamp = timestamp

            # Create message with all required fields
            result.append(
                ChatMessage(
                    id=msg.get("id") or f"msg-{conversation_id}-{idx}",
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=timestamp,
                    tool_calls=tool_calls,
                    model=model_name
                    if msg["role"] == "assistant"
                    else None,  # Only for assistant messages
                )
            )
        return result

    except Exception as e:
        logger.error("Error fetching conversation history: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch conversation history",
        )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    """
    Delete a conversation and all its messages for the current user.
    """
    try:
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        # Check conversation exists and belongs to user
        existing = await get_executor().query(
            "SELECT COUNT(*) as cnt FROM chat_messages WHERE conversation_id = ? AND user_id = ?",
            [conversation_id, user_id],
        )
        cnt = (existing[0].get("cnt", 0) or 0) if existing else 0
        if cnt == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or already deleted",
            )
        await get_executor().execute(
            "DELETE FROM chat_messages WHERE conversation_id = ? AND user_id = ?",
            [conversation_id, user_id],
        )
        logger.info(
            "Deleted conversation %s for user %s (%d messages)",
            conversation_id, user_id, cnt,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting conversation: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation",
        )


@router.get("/conversations", response_model=list[dict[str, Any]])
async def list_conversations(
    current_user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    List all conversations for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        List of conversations with id, title, and updatedAt
    """
    try:
        # Get user identifier - users table has 'id' field
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        logger.debug(
            "Using user_id: %s (user object keys: %s)",
            user_id,
            list(current_user.keys()) if isinstance(current_user, dict) else "not a dict",
        )

        logger.info("Listing conversations for user_id: %s", user_id)

        conversations = await get_executor().query(
            """
            SELECT
                conversation_id as id,
                MAX(created_at) as updated_at,
                SUBSTR(
                    (SELECT content FROM chat_messages cm2
                     WHERE cm2.conversation_id = chat_messages.conversation_id
                     ORDER BY cm2.created_at DESC LIMIT 1),
                    1, 50
                ) as title
            FROM chat_messages
            WHERE user_id = ?
            GROUP BY conversation_id
            ORDER BY MAX(created_at) DESC
            LIMIT 50
            """,
            [user_id],
        )

        logger.info("Found %d conversations for user_id: %s", len(conversations), user_id)

        result = []
        for conv in conversations:
            # SQLite returns column names as-is; the SQL alias is updated_at but
            # fall back to other names just in case the driver remaps them.
            updated_at_raw = (
                conv.get("updated_at")
                or conv.get("updatedAt")
                or conv.get("created_at")
                or conv.get("createdAt")
            )

            updated_at = _format_timestamp_z(updated_at_raw)

            # If MAX(created_at) came back unparseable, fetch the earliest message
            # timestamp as a best-effort fallback before reaching epoch.
            if not updated_at:
                conversation_id = conv.get("id") or conv.get("conversation_id", "")
                logger.warning(
                    "Conversation %s has no valid updated_at — fetching first message timestamp",
                    conversation_id,
                )
                try:
                    first_message = await get_executor().query(
                        """
                        SELECT created_at
                        FROM chat_messages
                        WHERE conversation_id = ? AND user_id = ?
                        ORDER BY created_at ASC
                        LIMIT 1
                        """,
                        [conversation_id, user_id],
                    )
                    if first_message:
                        updated_at = _format_timestamp_z(
                            first_message[0].get("created_at")
                        )
                        if updated_at:
                            logger.info(
                                "Using first message timestamp for conversation %s: %s",
                                conversation_id, updated_at,
                            )
                except Exception as e:
                    logger.error(
                        "Error fetching first message timestamp for conversation %s: %s",
                        conversation_id, e, exc_info=True,
                    )

            # Final fallback: epoch — frontend can detect and display "unknown date"
            if not updated_at:
                logger.warning(
                    "Conversation %s has no valid timestamp — using epoch as last resort",
                    conv.get("id"),
                )
                updated_at = (
                    datetime.fromtimestamp(0, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )

            result.append(
                {
                    "id": conv.get("id") or conv.get("conversation_id", ""),
                    "title": (conv.get("title") or "").strip() or "New Conversation",
                    "updatedAt": updated_at,
                }
            )

        return result

    except Exception as e:
        logger.error("Error listing conversations: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list conversations",
        )
