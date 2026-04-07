"""
Agent tracing service for DataMetronome chat/agent observability.

Provides structured tracing of chat requests for multi-agent Phase 0:
- user message preview
- inferred intent (placeholder until Phase 1 router)
- tool calls
- model used
- duration
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Max chars to store for message preview
MESSAGE_PREVIEW_MAX_LEN = 500


async def record_agent_trace(
    conversation_id: str,
    user_id: str,
    user_message: str,
    intent: str,
    model: str | None,
    tool_calls: list | None,
    duration_ms: float,
) -> None:
    """Record an agent trace to the database.

    Args:
        conversation_id: Conversation ID
        user_id: User ID
        user_message: Raw user message (will be truncated for storage)
        intent: Classified intent (e.g. quick, config, investigation)
        model: Model name used
        tool_calls: List of tool calls made
        duration_ms: Request duration in milliseconds
    """
    try:
        from datametronome_podium.core.database import get_executor

        executor = get_executor()
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        preview = (
            (user_message[:MESSAGE_PREVIEW_MAX_LEN] + "...")
            if len(user_message) > MESSAGE_PREVIEW_MAX_LEN
            else user_message
        )
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None

        await executor.insert(
            "agent_traces",
            {
                "id": trace_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_message_preview": preview,
                "intent": intent,
                "model": model,
                "tool_calls": tool_calls_json,
                "duration_ms": duration_ms,
                "created_at": now,
            },
        )
        logger.debug(
            "Recorded agent trace %s intent=%s duration=%.0fms", trace_id, intent, duration_ms
        )
    except Exception as e:
        logger.warning("Failed to record agent trace: %s", e)


def trace_duration(start_time: float) -> float:
    """Return duration in milliseconds since start_time (from time.perf_counter())."""
    return (time.perf_counter() - start_time) * 1000.0
