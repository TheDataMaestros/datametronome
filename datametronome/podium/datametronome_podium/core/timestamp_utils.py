"""
Timestamp utilities for consistent UTC handling and locale display.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json


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
            if dt.endswith('Z'):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(dt)
        except ValueError:
            # If parsing fails, return the original string
            return dt
    
    # Ensure the datetime is timezone-aware
    if dt.tzinfo is None:
        # Assume it's UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        # Convert to UTC
        dt = dt.astimezone(timezone.utc)
    
    # Format with 'Z' suffix for UTC
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_timestamp_for_display(utc_timestamp: str, include_timezone: bool = True) -> str:
    """Format a UTC timestamp string for display with timezone information.
    
    Args:
        utc_timestamp: UTC timestamp string (e.g., "2025-10-08T22:30:00Z")
        include_timezone: Whether to include timezone info in the display
        
    Returns:
        Formatted timestamp string (e.g., "2025-10-08 22:30:00 UTC" or "2025-10-08 22:30:00")
    """
    try:
        # Parse the UTC timestamp
        dt = datetime.fromisoformat(utc_timestamp.replace('Z', '+00:00'))
        
        if include_timezone:
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        # If parsing fails, return the original string
        return str(utc_timestamp)


def ensure_utc_timestamps_in_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all timestamp fields in a dictionary are in UTC ISO format.
    
    Args:
        data: Dictionary that may contain timestamp fields
        
    Returns:
        Dictionary with timestamp fields converted to UTC ISO format
    """
    timestamp_fields = ['created_at', 'updated_at', 'timestamp', 'next_run', 'last_run']
    
    for field in timestamp_fields:
        if field in data and data[field] is not None:
            value = data[field]
            
            if isinstance(value, datetime):
                data[field] = to_utc_isoformat(value)
            elif isinstance(value, str):
                # Try to parse and reformat as UTC
                try:
                    if value.endswith('Z'):
                        # Already in UTC format
                        data[field] = value
                    else:
                        # Parse and convert to UTC format
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        data[field] = to_utc_isoformat(dt)
                except (ValueError, AttributeError):
                    # Keep original value if parsing fails
                    pass
    
    return data


def add_timezone_info_to_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add timezone information to API response data.
    
    Args:
        response_data: API response data
        
    Returns:
        Response data with timezone information added
    """
    # Add timezone information to the response
    response_data['_timezone_info'] = {
        'backend_timezone': 'UTC',
        'timestamp_format': 'ISO 8601 with Z suffix (e.g., 2025-10-08T22:30:00Z)',
        'note': 'All timestamps are stored and processed in UTC. Convert to local timezone for display.'
    }
    
    return response_data
