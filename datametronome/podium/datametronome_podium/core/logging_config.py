"""
Logging configuration for DataMetronome Podium.

Provides both human-readable and JSON-structured logging formats
for development and production environments.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger import json as jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields.

    Adds standard fields for better log analysis:
    - timestamp: ISO 8601 timestamp
    - level: Log level name
    - logger: Logger name
    - message: Log message
    - service: Service name
    """

    def add_fields(self, log_data: Any, record: Any, message_dict: Any) -> None:  # ty: ignore[override]  # ty:ignore[ignore-comment-unknown-rule, invalid-method-override]
        """Add custom fields to log record."""
        super().add_fields(log_data, record, message_dict)

        # Add service identifier
        log_data["service"] = "datametronome-podium"

        # Add timestamp in ISO format
        log_data["timestamp"] = self.formatTime(record, self.datefmt)

        # Add level name
        log_data["level"] = record.levelname

        # Add logger name
        log_data["logger"] = record.name

        # Add filename and line number for debugging
        log_data["file"] = record.filename
        log_data["line"] = record.lineno

        # Add function name
        if record.funcName:
            log_data["function"] = record.funcName


def setup_logging(log_level: str = "INFO", log_format: str = "text") -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('text' for development, 'json' for production)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    if log_format.lower() == "json":
        # JSON formatter for production
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set log level for specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Log configuration
    root_logger.info(
        f"Logging configured: level={log_level}, format={log_format}",
        extra={"log_level": log_level, "log_format": log_format},
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    **extra,
) -> None:
    """
    Log an API request with structured data.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        **extra: Additional context fields
    """
    log_level = logging.INFO if status_code < 400 else logging.WARNING

    logger.log(
        log_level,
        f"{method} {path} -> {status_code} ({duration:.3f}s)",
        extra={
            "event_type": "api_request",
            "http_method": method,
            "http_path": path,
            "http_status_code": status_code,
            "duration_seconds": duration,
            **extra,
        },
    )


