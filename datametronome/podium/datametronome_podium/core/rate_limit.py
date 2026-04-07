"""
Rate limiting for DataMetronome Podium API.

Prevents API abuse and ensures fair resource allocation.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from datametronome_podium.core.config import settings


def get_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting.

    Uses remote address as primary identifier.
    Can be extended to use API keys or user IDs.

    Args:
        request: FastAPI request object

    Returns:
        Identifier string for rate limiting
    """
    # Try to get real IP from headers (for reverse proxy scenarios)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fallback to direct remote address
    return get_remote_address(request)


# Use Redis when available for distributed rate limiting across multiple workers.
# Falls back to in-memory storage for local dev or when Redis is not configured.
_storage_uri = settings.redis_url if settings.redis_url else "memory://"

limiter = Limiter(
    key_func=get_identifier,
    default_limits=["100 per minute", "1000 per hour"],
    storage_uri=_storage_uri,
    headers_enabled=True,  # Add rate limit headers to responses
)
