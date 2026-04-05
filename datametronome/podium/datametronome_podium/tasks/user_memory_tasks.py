"""Celery tasks for user memory extraction and profile rebuilding.

These tasks run on the intelligence.default queue. The beat task polls for
conversations that are ready for extraction every 10 minutes, dispatching
individual extraction tasks per conversation so failures are isolated.
"""
import asyncio
import logging
from typing import Any

from datametronome_podium.core.celery_app import celery_app
from datametronome_podium.core.config import settings

logger = logging.getLogger(__name__)

# Minimum number of user messages before a conversation is worth extracting.
# Avoids wasting LLM calls on single-message conversations.
_MIN_USER_MESSAGES = 3

# Maximum conversations dispatched in a single poll cycle to prevent burst load.
_POLL_CAP = 50


def _run_async(coro):
    """Run an async coroutine in a fresh event loop (safe for Celery prefork workers).

    asyncio.set_event_loop(loop) is required so internal calls to
    asyncio.get_event_loop() (in httpx, asyncpg) get the new loop,
    not the closed loop from a previous task on the same worker process.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Celery task definitions
# ---------------------------------------------------------------------------


@celery_app.task(
    name="datametronome.poll_conversations_for_extraction",
    acks_late=True,
    max_retries=0,
)
def poll_conversations_for_extraction() -> dict[str, Any]:
    """Beat task: find idle conversations and dispatch per-conversation extraction tasks.

    Runs every 10 minutes. Caps dispatched conversations at _POLL_CAP per cycle
    to avoid flooding the queue after a long idle period.
    """
    try:
        return _run_async(_poll_async())
    except Exception as exc:
        logger.error("Conversation extraction poll failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


@celery_app.task(
    name="datametronome.extract_user_memories",
    bind=True,
    max_retries=1,
    default_retry_delay=120,
    acks_late=True,
)
def extract_user_memories(self, conversation_id: str, user_id: str) -> dict[str, Any]:
    """Extract memories from a single conversation and rebuild the user profile."""
    try:
        return _run_async(_extract_async(conversation_id, user_id))
    except Exception as exc:
        logger.error(
            "Memory extraction failed for conversation %s user %s: %s",
            conversation_id,
            user_id,
            exc,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="datametronome.rebuild_user_profile",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    acks_late=True,
)
def rebuild_user_profile(self, user_id: str) -> dict[str, Any]:
    """Rebuild the aggregated memory profile for a user from all active memories."""
    try:
        return _run_async(_rebuild_profile_async(user_id))
    except Exception as exc:
        logger.error("Profile rebuild failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Async implementation helpers
# ---------------------------------------------------------------------------


async def _poll_async() -> dict[str, Any]:
    """Find conversations needing extraction and dispatch individual tasks."""
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo

    dispatched = 0
    skipped = 0

    async with worker_db_session(settings.database_url) as (_, executor):
        repo = UserMemoryRepo(executor)
        candidates = await repo.find_conversations_needing_extraction(limit=_POLL_CAP)

        for row in candidates:
            conversation_id = row["conversation_id"]
            user_id = row["user_id"]

            # Guard: skip if the conversation doesn't have enough user turns yet.
            # This avoids extracting stub conversations with only a greeting.
            msg_count = await repo.count_user_messages(conversation_id)
            if msg_count < _MIN_USER_MESSAGES:
                skipped += 1
                continue

            # Atomic CAS: only dispatch if we successfully claim the row.
            # Another worker may have claimed it between the SELECT and now.
            rows_updated = await repo.mark_extraction_processing(conversation_id)
            if rows_updated == 0:
                skipped += 1
                continue

            extract_user_memories.delay(conversation_id, user_id)
            dispatched += 1

    logger.info(
        "Extraction poll complete: dispatched=%d skipped=%d", dispatched, skipped
    )
    return {"status": "completed", "dispatched": dispatched, "skipped": skipped}


async def _extract_async(conversation_id: str, user_id: str) -> dict[str, Any]:
    """Load conversation history, run extraction pipeline, mark done (or failed)."""
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.features.chat.repo import ChatRepo
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo
    from datametronome_podium.features.user_memory.service import UserMemoryService

    async with worker_db_session(settings.database_url) as (_, executor):
        chat_repo = ChatRepo(executor)
        memory_repo = UserMemoryRepo(executor)
        service = UserMemoryService(repo=memory_repo)

        # Use a high limit so we get a rich extraction context.
        messages = await chat_repo.get_history(conversation_id, user_id, limit=100)

        # Format messages as a readable transcript for the LLM.
        conversation_text = "\n".join(
            f"{msg.role.upper()}: {msg.content}" for msg in messages
        )

        try:
            await service.extract_and_rebuild(
                conversation_id=conversation_id,
                user_id=user_id,
                conversation=conversation_text,
            )
            await memory_repo.mark_extraction_done(conversation_id)
            logger.info(
                "Extraction done: conversation=%s user=%s", conversation_id, user_id
            )
            return {"status": "completed", "conversation_id": conversation_id}
        except Exception as exc:
            # Reset to idle so the next poll can retry rather than permanently
            # blocking this conversation.
            await memory_repo.mark_extraction_failed(conversation_id)
            logger.error(
                "Extraction pipeline failed for conversation %s: %s",
                conversation_id,
                exc,
            )
            raise


async def _rebuild_profile_async(user_id: str) -> dict[str, Any]:
    """Rebuild aggregated profile for a user from all active memories."""
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo
    from datametronome_podium.features.user_memory.service import UserMemoryService

    async with worker_db_session(settings.database_url) as (_, executor):
        repo = UserMemoryRepo(executor)
        service = UserMemoryService(repo=repo)
        await service.rebuild_profile(user_id)
        logger.info("Profile rebuilt for user %s", user_id)
        return {"status": "completed", "user_id": user_id}
