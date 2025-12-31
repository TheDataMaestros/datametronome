"""
Chat/Agent endpoints for DataMetronome Podium.

This module provides endpoints for interacting with AI agents using ADK (Agent Development Kit)
and AG-UI protocol. The agent can help users with data quality questions, configuration,
and troubleshooting.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from datametronome_podium.api.v1.endpoints.auth import get_current_user
from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_db
from datametronome_podium.services.adk_agent import ADKAgent
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


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
    try:
        # Generate or use existing conversation ID
        conversation_id = request.conversationId or f"conv-{uuid.uuid4().hex[:12]}"

        # Check if ADK API key is configured
        if not settings.adk_api_key:
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
                history = await db.query(
                    {
                        "sql": """
                            SELECT role, content, created_at
                            FROM chat_messages
                            WHERE conversation_id = ? AND user_id = ?
                            ORDER BY created_at ASC
                            LIMIT 10
                        """,
                        "params": [conversation_id, user_id],
                    }
                )
                history_messages = [
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                    for msg in history
                ]
            except Exception as e:
                logger.warning(f"Could not load conversation history: {e}")

        # Initialize and use ADK agent
        agent = ADKAgent(
            model=settings.adk_model,
            api_key=settings.adk_api_key,
            api_url=settings.adk_api_url,
        )

        # Prepare context with history
        context = request.context or {}
        if history_messages:
            context["history"] = history_messages

        # Process message with ADK agent
        agent_response = await agent.process_message(
            message=request.message,
            conversation_id=conversation_id,
            context=context,
        )

        msg_value = agent_response.get("message", "")
        response_message: str = str(msg_value) if msg_value else ""
        tool_calls = agent_response.get("toolCalls")

        # Ensure model_name is always a string or None
        model_raw = agent_response.get("model")
        if model_raw:
            model_name: str | None = str(model_raw)
        elif settings.adk_model:
            model_name = str(settings.adk_model)
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
        now = datetime.now(timezone.utc).isoformat() + "Z"

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
        assistant_now = datetime.now(timezone.utc).isoformat() + "Z"

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

        return ChatResponse(
            message=response_message,
            conversationId=conversation_id,
            toolCalls=response_tool_calls,
            finishReason=finish_reason,
            model=model_name,  # Include model name in response
        )

    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}",
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
                        updated_at = updated_at_raw.isoformat() + "Z"
                    # Handle string timestamps from SQLite
                    elif isinstance(updated_at_raw, str):
                        # Try to parse and reformat to ensure ISO format
                        try:
                            # SQLite might return timestamps in various formats
                            if updated_at_raw.endswith("Z"):
                                # Already in ISO format with Z
                                updated_at = updated_at_raw
                            elif (
                                "+" in updated_at_raw or updated_at_raw.count("-") >= 3
                            ):
                                # Has timezone info, parse and reformat
                                dt = datetime.fromisoformat(
                                    updated_at_raw.replace("Z", "+00:00")
                                )
                                updated_at = dt.isoformat().replace("+00:00", "Z")
                            else:
                                # No timezone, assume UTC and parse
                                dt = datetime.fromisoformat(updated_at_raw + "+00:00")
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

            # Only use current time if we absolutely cannot parse the timestamp
            # This should rarely happen if the database has proper timestamps
            if not updated_at:
                logger.warning(
                    f"Conversation {conv.get('id')} has no valid updated_at - using epoch timestamp"
                )
                updated_at = (
                    datetime.fromtimestamp(0, tz=timezone.utc).isoformat() + "Z"
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
