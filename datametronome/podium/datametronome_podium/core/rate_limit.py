"""
Rate limiting for DataMetronome Podium API.

Prevents API abuse and ensures fair resource allocation.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


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


# Initialize limiter with Redis storage (optional) or in-memory
limiter = Limiter(
    key_func=get_identifier,
    default_limits=["100 per minute", "1000 per hour"],
    storage_uri="memory://",  # Change to redis://localhost:6379 for distributed rate limiting
    headers_enabled=True,  # Add rate limit headers to responses
)


# Custom rate limit configurations for different endpoints
RATE_LIMITS = {
    "auth": "5 per minute",  # Strict limit for login attempts
    "read": "60 per minute",  # Read operations
    "write": "30 per minute",  # Write operations
    "health": "100 per minute",  # Health checks
    "metrics": "20 per minute",  # Metrics endpoint
}


def get_rate_limit(endpoint_type: str = "default") -> str:
    """
    Get rate limit for specific endpoint type.

    Args:
        endpoint_type: Type of endpoint (auth, read, write, health, metrics)

    Returns:
        Rate limit string (e.g., "10 per minute")
    """
    return RATE_LIMITS.get(endpoint_type, "100 per minute")
