"""
Chat/Agent endpoints for DataMetronome Podium.

This module provides endpoints for interacting with AI agents using ADK (Agent Development Kit)
and AG-UI protocol. The agent can help users with data quality questions, configuration,
and troubleshooting.
"""

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from datametronome_podium.api.v1.endpoints.auth import get_current_user
from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_db
from datametronome_podium.core.metrics import record_chat_request
from datametronome_podium.services.adk_agent import ADKAgent
from datametronome_podium.services.agent_tracing import (
    record_agent_trace,
    trace_duration,
)
from datametronome_podium.services.intent_router import (
    classify_intent,
    resolve_model_for_intent,
)
from datametronome_podium.services.orchestrator import (
    MODE_CHAIN,
    MODE_PARALLEL,
    MODE_SINGLE,
    get_agent_config,
    plan_orchestration,
)
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


class ToolCall(BaseModel):
    """Tool call model for agent tool calling."""

    id: str
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """Tool result model."""

    callId: str
    result: Any
    error: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model."""

    id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: Optional[datetime] = None
    tool_calls: Optional[List[ToolCall]] = None
    model: Optional[str] = None  # Model name that generated the response
    finish_reason: Optional[str] = None  # Finish reason from the model


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    conversationId: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    conversationId: str
    toolCalls: Optional[List[ToolCall]] = None
    finishReason: Optional[str] = None
    model: Optional[str] = None  # Model name that generated the response
    intent: Optional[str] = None  # Classified intent (Phase 1 router)
    agentType: Optional[str] = None  # Specialized agent used (Phase 2)
    orchestrationMode: Optional[str] = None  # Phase 3: single, chain, parallel
    agentChain: Optional[List[str]] = None  # Phase 3: agents used when mode=chain


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

        # Phase 1: Intent classifier + router
        intent = classify_intent(request.message)
        resolved_model = resolve_model_for_intent(
            intent=intent,
            model_primary=settings.adk_model,
            model_quick=settings.adk_model_quick or None,
        )
        # Phase 3: Orchestrator (single vs chain)
        orchestration_mode, agent_types = plan_orchestration(intent, request.message)
        logger.info(
            "📋 Intent=%s → mode=%s agents=%s model=%s",
            intent,
            orchestration_mode,
            agent_types,
            resolved_model,
        )

        # Check if ADK API key is configured (only required for Gemini, not Ollama)
        model_name = resolved_model.lower()
        is_ollama = model_name.startswith("ollama_chat/")
        if not is_ollama and not settings.adk_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ADK API key not configured. Please set DATAMETRONOME_ADK_API_KEY environment variable.",
            )

        # Load conversation history for context
        db = await get_db()
        # Get user identifier - users table has 'id' field
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        logger.debug(
            f"Using user_id: {user_id} (user object keys: {list(current_user.keys()) if isinstance(current_user, dict) else 'not a dict'})"
        )

        history_messages = []
        if conversation_id:
            try:
                logger.info(
                    f"📚 Loading conversation history for conversation_id={conversation_id}, user_id={user_id}"
                )
                history = await db.query(
                    {
                        "sql": """
                            SELECT role, content, tool_calls, created_at
                            FROM chat_messages
                            WHERE conversation_id = ? AND user_id = ?
                            ORDER BY created_at ASC
                            LIMIT 20
                        """,
                        "params": [conversation_id, user_id],
                    }
                )
                logger.info(
                    f"📚 Found {len(history)} messages in database for conversation {conversation_id}"
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
                        except:
                            pass
                    history_messages.append(msg_dict)
                    logger.debug(
                        f"📚 Added message to history: role={msg_dict['role']}, content_preview={msg_dict['content'][:50]}..."
                    )
                logger.info(
                    f"✅ Loaded {len(history_messages)} messages into conversation history"
                )
            except Exception as e:
                logger.error(
                    f"❌ Could not load conversation history: {e}", exc_info=True
                )

        # Prepare context with history
        context = request.context or {}
        if history_messages:
            context["history"] = history_messages

        # Execute orchestration (single, chain, or parallel)
        if orchestration_mode == MODE_PARALLEL and len(agent_types) >= 2:
            # Parallel: run agents concurrently, combine outputs
            async def run_agent(atype: str):
                tool_names, instruction = get_agent_config(atype)
                agent = ADKAgent(
                    model=resolved_model,
                    api_key=settings.adk_api_key,
                    api_url=settings.adk_api_url,
                    tool_names=tool_names,
                    instruction=instruction,
                )
                return await agent.process_message(
                    message=request.message,
                    conversation_id=conversation_id,
                    context=context,
                )

            results = await asyncio.gather(
                *[run_agent(atype) for atype in agent_types],
                return_exceptions=True,
            )
            parts = []
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    parts.append(f"[{agent_types[i]} error: {r}]")
                else:
                    msg = r.get("message", "") or ""
                    if msg:
                        parts.append(f"**{agent_types[i].title()}:**\n{msg}")
            response_message_combined = "\n\n---\n\n".join(parts) if parts else "No responses."
            agent_response = {
                "message": response_message_combined,
                "toolCalls": [],
                "model": resolved_model,
            }
        elif orchestration_mode == MODE_CHAIN and len(agent_types) >= 2:
            # Chain: run agents in sequence, pass previous output to next
            shared_state = {}
            for i, atype in enumerate(agent_types):
                tool_names, instruction = get_agent_config(atype)
                agent = ADKAgent(
                    model=resolved_model,
                    api_key=settings.adk_api_key,
                    api_url=settings.adk_api_url,
                    tool_names=tool_names,
                    instruction=instruction,
                )
                if i == 0:
                    msg_to_send = request.message
                else:
                    prev = shared_state.get("previous_output", "")
                    msg_to_send = (
                        f"INVESTIGATION FINDINGS:\n{prev}\n\n"
                        f"USER'S REQUEST: {request.message}\n\n"
                        "Using the findings above, address the user's request (suggest fixes, "
                        "recommend checks, or propose remedial actions)."
                    )
                    context["orchestrator"] = shared_state
                resp = await agent.process_message(
                    message=msg_to_send,
                    conversation_id=conversation_id,
                    context=context,
                )
                shared_state["previous_output"] = resp.get("message", "")
                if i == len(agent_types) - 1:
                    agent_response = resp
        else:
            # Single agent
            agent_type = agent_types[0] if agent_types else "report"
            tool_names, instruction = get_agent_config(agent_type)
            agent = ADKAgent(
                model=resolved_model,
                api_key=settings.adk_api_key,
                api_url=settings.adk_api_url,
                tool_names=tool_names,
                instruction=instruction,
            )
            agent_response = await agent.process_message(
                message=request.message,
                conversation_id=conversation_id,
                context=context,
            )

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
        logger.info(
            f"💾 Saving message - user_id: {user_id}, conversation_id: {conversation_id}, user_keys: {list(current_user.keys()) if isinstance(current_user, dict) else 'not a dict'}"
        )

        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            await db.write(
                [
                    {
                        "table": "chat_messages",
                        "id": message_id,
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "role": "user",
                        "content": request.message,
                        "created_at": now,
                    }
                ],
                "chat_messages",
            )
            logger.info(f"✅ User message saved successfully - message_id: {message_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save user message: {e}", exc_info=True)
            raise

        # Save assistant response to database
        assistant_message_id = f"msg-{uuid.uuid4().hex[:12]}"
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        # Use current time for assistant message (after processing)
        assistant_now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            await db.write(
                [
                    {
                        "table": "chat_messages",
                        "id": assistant_message_id,
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "role": "assistant",
                        "content": response_message,
                        "tool_calls": tool_calls_json,
                        "created_at": assistant_now,
                    }
                ],
                "chat_messages",
            )
            logger.info(
                f"✅ Assistant message saved successfully - message_id: {assistant_message_id}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to save assistant message: {e}", exc_info=True)
            raise

        # Convert tool calls to response format
        response_tool_calls: list[ToolCall] | None = None
        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            tool_calls_list: list = tool_calls  # Type narrowing
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
            agentChain=agent_types if orchestration_mode in (MODE_CHAIN, MODE_PARALLEL) else None,
        )

    except Exception as e:
        duration_ms = trace_duration(start_time)
        try:
            err_user_id = current_user.get("id") or current_user.get("username") or "anonymous"
            err_conv_id = request.conversationId or "error-conv"
            err_msg = (request.message or "")[:500]
            err_intent = classify_intent(err_msg) if err_msg else "unknown"
            await record_agent_trace(
                conversation_id=err_conv_id,
                user_id=err_user_id,
                user_message=err_msg,
                intent=err_intent,
                model=None,
                tool_calls=None,
                duration_ms=duration_ms,
            )
            record_chat_request(status="error", duration_seconds=duration_ms / 1000.0, intent=err_intent)
        except Exception as trace_err:
            logger.warning(f"Failed to record error trace: {trace_err}")
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        detail = _user_friendly_error_detail(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


@router.get("/conversations/{conversation_id}", response_model=List[ChatMessage])
async def get_conversation_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> List[ChatMessage]:
    """
    Get conversation history for a specific conversation.

    Args:
        conversation_id: ID of the conversation
        current_user: Current authenticated user

    Returns:
        List of chat messages in the conversation
    """
    try:
        db = await get_db()
        # Get user identifier - users table has 'id' field
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        logger.debug(
            f"Using user_id: {user_id} (user object keys: {list(current_user.keys()) if isinstance(current_user, dict) else 'not a dict'})"
        )

        logger.debug(f"Loading conversation {conversation_id} for user_id: {user_id}")

        messages = await db.query(
            {
                "sql": """
                    SELECT id, role, content, tool_calls, created_at
                    FROM chat_messages
                    WHERE conversation_id = ? AND user_id = ?
                    ORDER BY created_at ASC
                """,
                "params": [conversation_id, user_id],
            }
        )

        logger.info(
            f"📨 Found {len(messages)} messages in conversation {conversation_id}"
        )

        # Get model name from settings for assistant messages
        model_name = settings.adk_model or "unknown"

        result = []
        first_message_timestamp = None  # Store first valid timestamp as fallback

        for idx, msg in enumerate(messages):
            tool_calls = None
            if msg.get("tool_calls"):
                try:
                    tool_calls = json.loads(msg["tool_calls"])
                except:
                    pass

            # Parse timestamp - handle various formats
            timestamp = None
            created_at = msg.get("created_at")
            logger.debug(
                f"📅 Parsing timestamp for message {msg.get('id')}: created_at={created_at} (type: {type(created_at)})"
            )

            if created_at:
                try:
                    # Handle ISO format with or without Z
                    if isinstance(created_at, str):
                        # Clean up the timestamp string
                        created_at_clean = created_at.strip()

                        # Handle the case where timestamp has both +00:00 and Z (invalid format)
                        # Example: 2025-12-24T16:41:43.558318+00:00Z
                        # Solution: Remove the Z, keep the timezone offset
                        if created_at_clean.endswith("Z"):
                            # Check if there's a timezone offset (+HH:MM) before the Z
                            # Use regex-like pattern matching: look for +HH:MM before Z
                            import re

                            # Pattern: + followed by digits, colon, digits before Z
                            tz_pattern = r"\+(\d{1,2}):(\d{2})Z$"
                            if re.search(tz_pattern, created_at_clean):
                                # Has both +XX:XX and Z - remove Z, keep offset
                                created_at_parsed = created_at_clean[:-1]
                            else:
                                # Only has Z, add +00:00
                                created_at_parsed = created_at_clean[:-1] + "+00:00"
                        elif "+" in created_at_clean or (
                            created_at_clean.count("-") >= 4
                            and ":" in created_at_clean[-6:]
                        ):
                            # Already has timezone offset, use as-is
                            created_at_parsed = created_at_clean
                        else:
                            # No timezone info, assume UTC
                            created_at_parsed = created_at_clean + "+00:00"

                        timestamp = datetime.fromisoformat(created_at_parsed)
                        # Ensure timezone-aware
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        logger.debug(f"✅ Parsed timestamp: {timestamp.isoformat()}")
                    elif isinstance(created_at, datetime):
                        timestamp = created_at
                        # Ensure timezone-aware
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        logger.debug(
                            f"✅ Using datetime object: {timestamp.isoformat()}"
                        )
                except (ValueError, AttributeError) as e:
                    logger.error(
                        f"❌ Failed to parse timestamp '{created_at}': {e}",
                        exc_info=True,
                    )
                    # Don't default to current time - this would show wrong timestamp
                    # Instead, log error and use a sentinel value that frontend can detect
                    timestamp = None

            # If timestamp is still None, use first message's timestamp as fallback
            if timestamp is None:
                logger.warning(
                    f"⚠️ Message {msg.get('id')} has invalid or missing created_at field: {created_at}"
                )
                # Use first message's timestamp if available, otherwise use epoch
                if first_message_timestamp:
                    timestamp = first_message_timestamp
                    logger.info(
                        f"📅 Using first message timestamp as fallback: {timestamp.isoformat()}"
                    )
                else:
                    timestamp = datetime.fromtimestamp(0, tz=timezone.utc)
                    logger.warning(f"📅 No fallback available, using epoch timestamp")

            # Store first valid timestamp for fallback
            if first_message_timestamp is None and timestamp:
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
        logger.error(f"Error fetching conversation history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation history: {str(e)}",
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
        db = await get_db()
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        # Check conversation exists and belongs to user
        existing = await db.query(
            {
                "sql": "SELECT COUNT(*) as cnt FROM chat_messages WHERE conversation_id = ? AND user_id = ?",
                "params": [conversation_id, user_id],
            }
        )
        cnt = (existing[0].get("cnt", 0) or 0) if existing else 0
        if cnt == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or already deleted",
            )
        await db.execute(
            "DELETE FROM chat_messages WHERE conversation_id = ? AND user_id = ?",
            [conversation_id, user_id],
        )
        logger.info(f"🗑️ Deleted conversation {conversation_id} for user {user_id} ({cnt} messages)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}",
        )


@router.get("/conversations", response_model=List[Dict[str, Any]])
async def list_conversations(
    current_user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    List all conversations for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        List of conversations with id, title, and updatedAt
    """
    try:
        db = await get_db()
        # Get user identifier - users table has 'id' field
        user_id = current_user.get("id") or current_user.get("username") or "anonymous"
        logger.debug(
            f"Using user_id: {user_id} (user object keys: {list(current_user.keys()) if isinstance(current_user, dict) else 'not a dict'})"
        )

        logger.info(f"📋 Listing conversations for user_id: {user_id}")

        # First, let's check what user_ids exist in the database
        all_users = await db.query(
            {
                "sql": "SELECT DISTINCT user_id FROM chat_messages",
                "params": [],
            }
        )
        logger.info(
            f"🔍 Found user_ids in database: {[u.get('user_id') for u in all_users]}"
        )

        conversations = await db.query(
            {
                "sql": """
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
                "params": [user_id],
            }
        )

        logger.info(
            f"✅ Found {len(conversations)} conversations for user_id: {user_id}"
        )

        # Log the raw conversations for debugging
        logger.info(f"📋 Raw conversations: {conversations}")

        result = []
        for conv in conversations:
            # SQLite returns column names as-is, so check both possible names
            # The SQL query uses MAX(created_at) as updated_at, so check for that
            updated_at_raw = (
                conv.get("updated_at")
                or conv.get("updatedAt")
                or conv.get("created_at")
                or conv.get("createdAt")
            )

            # Parse and format the timestamp properly
            updated_at = None
            if updated_at_raw:
                try:
                    # Handle datetime objects
                    if isinstance(updated_at_raw, datetime):
                        # Convert to UTC if timezone-aware, otherwise assume UTC
                        if updated_at_raw.tzinfo is not None:
                            dt_utc = updated_at_raw.astimezone(timezone.utc)
                        else:
                            dt_utc = updated_at_raw.replace(tzinfo=timezone.utc)
                        # Format as ISO with Z suffix (no +00:00)
                        updated_at = dt_utc.isoformat().replace("+00:00", "Z")
                    # Handle string timestamps from SQLite
                    elif isinstance(updated_at_raw, str):
                        # Try to parse and reformat to ensure ISO format
                        try:
                            # Clean up the timestamp string first
                            updated_at_clean = updated_at_raw.strip()

                            # Check if it has both +00:00 and Z (invalid format)
                            if (
                                "+00:00Z" in updated_at_clean
                                or updated_at_clean.endswith("+00:00Z")
                            ):
                                # Remove the Z, keep +00:00, then we'll convert to Z format
                                updated_at_clean = updated_at_clean.replace(
                                    "+00:00Z", "+00:00"
                                ).replace("Z", "")

                            # SQLite might return timestamps in various formats
                            if (
                                updated_at_clean.endswith("Z")
                                and "+" not in updated_at_clean
                            ):
                                # Already in ISO format with Z (and no +00:00)
                                updated_at = updated_at_clean
                            elif "+" in updated_at_clean:
                                # Has timezone info, parse and reformat
                                dt = datetime.fromisoformat(
                                    updated_at_clean.replace("Z", "+00:00")
                                )
                                updated_at = dt.isoformat().replace("+00:00", "Z")
                            else:
                                # No timezone, assume UTC and parse
                                dt = datetime.fromisoformat(updated_at_clean + "+00:00")
                                updated_at = dt.isoformat().replace("+00:00", "Z")
                        except (ValueError, AttributeError) as e:
                            logger.warning(
                                f"Failed to parse updated_at '{updated_at_raw}' for conversation {conv.get('id')}: {e}"
                            )
                            # Don't use current time - use the raw string or epoch
                            updated_at = updated_at_raw if updated_at_raw else None
                    else:
                        # Try to convert to string and parse
                        updated_at_str = str(updated_at_raw)
                        try:
                            dt = datetime.fromisoformat(
                                updated_at_str.replace("Z", "+00:00")
                            )
                            updated_at = dt.isoformat().replace("+00:00", "Z")
                        except:
                            updated_at = None
                except Exception as e:
                    logger.error(
                        f"Error processing updated_at for conversation {conv.get('id')}: {e}",
                        exc_info=True,
                    )
                    updated_at = None

            # If no valid updated_at, try to get the first message's timestamp
            if not updated_at:
                conversation_id = conv.get("id") or conv.get("conversation_id", "")
                logger.warning(
                    f"Conversation {conversation_id} has no valid updated_at - fetching first message timestamp"
                )
                try:
                    # Query the first message's timestamp for this conversation
                    first_message = await db.query(
                        {
                            "sql": """
                                SELECT created_at
                                FROM chat_messages
                                WHERE conversation_id = ? AND user_id = ?
                                ORDER BY created_at ASC
                                LIMIT 1
                            """,
                            "params": [conversation_id, user_id],
                        }
                    )
                    if first_message and len(first_message) > 0:
                        first_msg_created_at = first_message[0].get("created_at")
                        if first_msg_created_at:
                            try:
                                # Parse the first message timestamp
                                if isinstance(first_msg_created_at, datetime):
                                    if first_msg_created_at.tzinfo is not None:
                                        dt_utc = first_msg_created_at.astimezone(
                                            timezone.utc
                                        )
                                    else:
                                        dt_utc = first_msg_created_at.replace(
                                            tzinfo=timezone.utc
                                        )
                                    updated_at = dt_utc.isoformat().replace(
                                        "+00:00", "Z"
                                    )
                                elif isinstance(first_msg_created_at, str):
                                    # Parse string timestamp
                                    first_msg_clean = first_msg_created_at.strip()

                                    # Check if it has both +00:00 and Z (invalid format)
                                    if (
                                        "+00:00Z" in first_msg_clean
                                        or first_msg_clean.endswith("+00:00Z")
                                    ):
                                        # Remove the Z, keep +00:00, then we'll convert to Z format
                                        first_msg_clean = first_msg_clean.replace(
                                            "+00:00Z", "+00:00"
                                        ).replace("Z", "")

                                    if (
                                        first_msg_clean.endswith("Z")
                                        and "+" not in first_msg_clean
                                    ):
                                        # Already in ISO format with Z (and no +00:00)
                                        updated_at = first_msg_clean
                                    elif "+" in first_msg_clean:
                                        dt = datetime.fromisoformat(
                                            first_msg_clean.replace("Z", "+00:00")
                                        )
                                        updated_at = dt.isoformat().replace(
                                            "+00:00", "Z"
                                        )
                                    else:
                                        dt = datetime.fromisoformat(
                                            first_msg_clean + "+00:00"
                                        )
                                        updated_at = dt.isoformat().replace(
                                            "+00:00", "Z"
                                        )
                                else:
                                    # Try to convert to string and parse
                                    dt = datetime.fromisoformat(
                                        str(first_msg_created_at).replace("Z", "+00:00")
                                    )
                                    updated_at = dt.isoformat().replace("+00:00", "Z")
                                logger.info(
                                    f"✅ Using first message timestamp for conversation {conversation_id}: {updated_at}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to parse first message timestamp for conversation {conversation_id}: {e}"
                                )
                                updated_at = None
                except Exception as e:
                    logger.error(
                        f"Error fetching first message timestamp for conversation {conversation_id}: {e}",
                        exc_info=True,
                    )
                    updated_at = None

            # Final fallback to epoch if we still don't have a timestamp
            if not updated_at:
                logger.warning(
                    f"Conversation {conv.get('id')} has no valid timestamp - using epoch as last resort"
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

        logger.info(f"📤 Returning conversations: {result}")
        return result

    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}",
        )
