"""
Consolidated exception hierarchy for DataMetronome Podium.
"""

from typing import Any


class DataMetronomeError(Exception):
    """Base exception for all DataMetronome errors."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(DataMetronomeError):
    """Configuration-related errors."""
    pass


class DatabaseError(DataMetronomeError):
    """Database operation errors."""
    pass


class AuthenticationError(DataMetronomeError):
    """Authentication and authorization errors."""
    pass


class ValidationError(DataMetronomeError):
    """Data validation errors."""
    pass


class ConnectorError(DataMetronomeError):
    """Data connector errors."""
    pass


class CheckExecutionError(DataMetronomeError):
    """Check execution errors."""
    pass


class SchedulerError(DataMetronomeError):
    """Scheduler and job queue errors."""
    pass
