"""
Timestamp utilities for consistent UTC handling and locale display.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def now_utc_iso() -> str:
    """Return current UTC time as ISO-8601 string with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def to_utc_isoformat(dt: Optional[datetime] = None) -> str:
    """Convert datetime to UTC ISO format string with 'Z' suffix.

    Uses .isoformat() to preserve microsecond precision (strftime would truncate).

    Args:
        dt: Datetime object or string. If None, uses current UTC time.

    Returns:
        ISO format string in UTC (e.g., "2025-10-08T22:30:00.123456Z")
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

    return dt.isoformat().replace("+00:00", "Z")


def parse_timestamp(raw: "str | datetime | None") -> "datetime | None":
    """Normalise a raw DB timestamp value to a UTC-aware datetime.

    Handles the several malformed formats that SQLite and Postgres can return:
    - Pure Z suffix:          "2025-12-24T16:41:43Z"          → UTC datetime
    - Offset + Z (invalid):  "2025-12-24T16:41:43+00:00Z"    → strip trailing Z
    - Offset only:            "2025-12-24T16:41:43+00:00"     → parse as-is
    - No TZ info:             "2025-12-24T16:41:43"           → assume UTC
    - datetime object:        already a datetime               → ensure tz-aware
    Returns None on any parse failure so callers can apply their own fallback.
    """
    if raw is None:
        return None

    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw

    if not isinstance(raw, str):
        # Unexpected type — attempt coercion via str
        raw = str(raw)

    cleaned = raw.strip()

    # Strip invalid "+HH:MM Z" double-suffix: keep the offset, drop trailing Z
    if re.search(r"\+\d{1,2}:\d{2}Z$", cleaned):
        cleaned = cleaned[:-1]  # remove trailing Z; offset is already present
    elif cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    elif "+" not in cleaned and (cleaned.count("-") < 4 or ":" not in cleaned[-6:]):
        # No timezone information at all — assume UTC
        cleaned = cleaned + "+00:00"

    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def format_timestamp_z(raw: "str | datetime | None") -> "str | None":
    """Parse a raw timestamp and return an ISO-8601 string ending with 'Z'.

    Used when the caller needs a serialisable string (e.g. JSON response).
    Returns None only when the input cannot be parsed at all.
    """
    dt = parse_timestamp(raw)
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def add_timezone_info_to_response(response_data: dict[str, Any]) -> dict[str, Any]:
    """Add timezone metadata to API response data."""
    response_data["_timezone_info"] = {
        "backend_timezone": "UTC",
        "timestamp_format": "ISO 8601 with Z suffix (e.g., 2025-10-08T22:30:00Z)",
        "note": "All timestamps are stored and processed in UTC. Convert to local timezone for display.",
    }
    return response_data
