"""
Chat/Agent router for DataMetronome Podium.

Thin HTTP layer — all persistence goes through ChatRepo, all AI logic
goes through services/orchestrator.py.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from datametronome_podium.core.auth import get_current_user
from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.metrics import record_chat_request
from datametronome_podium.core.timestamp_utils import (
    format_timestamp_z,
    parse_timestamp,
    to_utc_isoformat,
)
from datametronome_podium.features.chat.repo import ChatRepo
from datametronome_podium.features.chat.schema import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ToolCall,
)
from datametronome_podium.services.agent_tracing import record_agent_trace, trace_duration
from datametronome_podium.services.orchestrator import run_chat

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_user_id(current_user: dict) -> str:
    """Extract a stable user identifier from the current-user dict.

    The users table stores a numeric 'id', but some callers only have
    'username' available (e.g. during registration before an id is assigned).
    Fallback to 'anonymous' so callers never receive None.
    """
    return current_user.get("id") or current_user.get("username") or "anonymous"


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
    """
    start_time = time.perf_counter()
    try:
        conversation_id = request.conversationId or f"conv-{uuid.uuid4().hex[:12]}"
        user_id = _get_user_id(current_user)
        logger.debug(
            "Using user_id: %s (user object keys: %s)",
            user_id,
            list(current_user.keys()) if isinstance(current_user, dict) else "not a dict",
        )

        repo = ChatRepo(get_executor())
        history_messages = await repo.load_history(conversation_id, user_id)

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

        logger.info("Intent=%s mode=%s agents=%s", intent, orchestration_mode, agent_types)

        agent_response = {
            "message": agent_result["message"],
            "toolCalls": None,
            "model": resolved_model,
        }

        duration_ms = trace_duration(start_time)
        tool_calls_for_trace = agent_response.get("toolCalls")
        model_for_trace = agent_response.get("model") or resolved_model or "unknown"

        await record_agent_trace(
            conversation_id=conversation_id,
            user_id=user_id,
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
        finish_reason: str | None = str(finish_reason_raw) if finish_reason_raw else "stop"

        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        logger.debug("Saving messages for user_id=%s conversation_id=%s", user_id, conversation_id)
        await repo.persist_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=request.message,
            assistant_message=response_message,
            tool_calls_json=tool_calls_json,
        )

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
            err_user_id = _get_user_id(current_user)
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
            record_chat_request(
                status="error", duration_seconds=duration_ms / 1000.0, intent="unknown"
            )
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
    """Get conversation history for a specific conversation."""
    try:
        user_id = _get_user_id(current_user)
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

            timestamp = parse_timestamp(msg.get("created_at"))

            # Apply fallback chain when the stored value cannot be parsed
            if timestamp is None:
                logger.warning(
                    "Message %s has invalid or missing created_at: %s",
                    msg.get("id"),
                    msg.get("created_at"),
                )
                if first_message_timestamp is not None:
                    timestamp = first_message_timestamp
                else:
                    timestamp = datetime.fromtimestamp(0, tz=timezone.utc)
                    logger.warning("No fallback available, using epoch timestamp")

            if first_message_timestamp is None:
                first_message_timestamp = timestamp

            result.append(
                ChatMessage(
                    id=msg.get("id") or f"msg-{conversation_id}-{idx}",
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=timestamp,
                    tool_calls=tool_calls,
                    model=model_name if msg["role"] == "assistant" else None,
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
    """Delete a conversation and all its messages for the current user."""
    try:
        user_id = _get_user_id(current_user)
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
            conversation_id,
            user_id,
            cnt,
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
    """List all conversations for the current user."""
    try:
        user_id = _get_user_id(current_user)
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

            updated_at = format_timestamp_z(updated_at_raw)

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
                        updated_at = format_timestamp_z(first_message[0].get("created_at"))
                        if updated_at:
                            logger.info(
                                "Using first message timestamp for conversation %s: %s",
                                conversation_id,
                                updated_at,
                            )
                except Exception as e:
                    logger.error(
                        "Error fetching first message timestamp for conversation %s: %s",
                        conversation_id,
                        e,
                        exc_info=True,
                    )

            # Final fallback: epoch — frontend can detect and display "unknown date"
            if not updated_at:
                logger.warning(
                    "Conversation %s has no valid timestamp — using epoch as last resort",
                    conv.get("id"),
                )
                updated_at = to_utc_isoformat(datetime.fromtimestamp(0, tz=timezone.utc))

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
