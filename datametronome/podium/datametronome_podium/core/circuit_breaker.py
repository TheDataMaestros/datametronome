"""
Stave circuit breaker — pauses a stave after consecutive check failures.

State tracked in Redis (fast, shared across workers).
Pause/unpause persisted in Postgres (staves.paused column).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datametronome_podium.core.query import QueryExecutor

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "circuit"


class StaveCircuitBreaker:
    """Circuit breaker for stave check failures.

    After `threshold` consecutive failures, sets stave.paused = True.

    Args:
        redis_client: async Redis client (redis.asyncio)
        threshold: number of consecutive failures before tripping
        executor: QueryExecutor instance for updating staves.paused in Postgres
    """

    def __init__(
        self,
        redis_client: Any,
        threshold: int = 5,
        executor: QueryExecutor | None = None,
    ) -> None:
        self._redis = redis_client
        self._threshold = threshold
        self._executor = executor

    def _key(self, stave_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}:{stave_id}:failures"

    async def record_success(self, stave_id: str) -> None:
        """Reset failure counter on successful check."""
        await self._redis.delete(self._key(stave_id))

    async def record_failure(self, stave_id: str) -> bool:
        """Increment failure counter. Returns True if circuit just tripped."""
        key = self._key(stave_id)
        count = await self._redis.incr(key)
        await self._redis.expire(key, 86400)  # 24h TTL prevents unbounded key growth

        if count >= self._threshold:
            logger.warning(
                "Circuit breaker tripped for stave %s (%d consecutive failures)",
                stave_id, count,
            )
            if self._executor:
                await self._executor.execute(
                    "UPDATE staves SET paused = ? WHERE id = ?",
                    [True, stave_id],
                )
            return True

        return False

    async def is_tripped(self, stave_id: str) -> bool:
        """Check if the circuit breaker is currently tripped."""
        raw = await self._redis.get(self._key(stave_id))
        if raw is None:
            return False
        return int(raw) >= self._threshold

    async def reset(self, stave_id: str) -> None:
        """Reset circuit breaker and unpause the stave."""
        await self._redis.delete(self._key(stave_id))
        if self._executor:
            await self._executor.execute(
                "UPDATE staves SET paused = ? WHERE id = ?",
                [False, stave_id],
            )
        logger.info("Circuit breaker reset for stave %s", stave_id)
