"""Shared async Redis client singleton."""
import redis.asyncio as aioredis

from datametronome_podium.core.config import settings

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """Return a cached async Redis client, creating one on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url)
    return _redis_client
