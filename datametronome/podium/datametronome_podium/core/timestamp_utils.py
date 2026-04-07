"""
Timestamp utilities for consistent UTC handling and locale display.
"""

from datetime import datetime, timezone
from typing import Any, Optional


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def to_utc_isoformat(dt: Optional[datetime] = None) -> str:
    """Convert datetime to UTC ISO format string with 'Z' suffix.

    Args:
        dt: Datetime object or string. If None, uses current UTC time.

    Returns:
        ISO format string in UTC (e.g., "2025-10-08T22:30:00Z")
    """
    if dt is None:
        dt = now_utc()
    elif isinstance(dt, str):
        # Parse string timestamp
        try:
            if dt.endswith("Z"):
                parsed_dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            else:
                parsed_dt = datetime.fromisoformat(dt)
            dt = parsed_dt
        except ValueError:
            # If parsing fails, return the original string
            return str(dt)

    # Ensure the datetime is timezone-aware
    if dt.tzinfo is None:
        # Assume it's UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        # Convert to UTC
        dt = dt.astimezone(timezone.utc)

    # Format with 'Z' suffix for UTC
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def add_timezone_info_to_response(response_data: dict[str, Any]) -> dict[str, Any]:
    """Add timezone metadata to API response data."""
    response_data["_timezone_info"] = {
        "backend_timezone": "UTC",
        "timestamp_format": "ISO 8601 with Z suffix (e.g., 2025-10-08T22:30:00Z)",
        "note": "All timestamps are stored and processed in UTC. Convert to local timezone for display.",
    }
    return response_data


