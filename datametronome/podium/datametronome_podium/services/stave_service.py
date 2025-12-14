"""
Stave Service - Helper functions for working with Staves.

This module provides easy-to-use helper functions for creating, managing,
and working with Staves (data sources). Use these functions to make your
life easier when building with DataMetronome.

Example Usage:
    # Create a PostgreSQL stave
    stave = create_postgres_stave(
        name="Production DB",
        host="db.example.com",
        database="prod",
        user="monitor",
        password="secret"
    )

    # Create a SQLite stave
    stave = create_sqlite_stave(
        name="Local Analytics",
        path="/data/analytics.db"
    )

    # Serialize for database storage
    stave_dict = serialize_stave(stave)

    # Deserialize from database
    stave = deserialize_stave(stave_dict)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.models.clef import SUPPORTED_CHECK_TYPES, Clef
from datametronome_podium.models.stave import SUPPORTED_DATA_SOURCES, Stave

# =============================================================================
# Stave Creation Helpers
# =============================================================================


def generate_stave_id() -> str:
    """Generate a unique stave ID."""
    return f"stave-{uuid.uuid4().hex[:12]}"


def generate_clef_id() -> str:
    """Generate a unique clef ID."""
    return f"clef-{uuid.uuid4().hex[:12]}"


def create_stave(
    name: str,
    data_source_type: str,
    connection_config: dict[str, Any],
    description: str | None = None,
    is_active: bool = True,
) -> Stave:
    """
    Create a new Stave with auto-generated ID and timestamps.

    Args:
        name: Human-readable name for the data source
        data_source_type: Type of data source (postgres, mysql, sqlite, etc.)
        connection_config: Connection parameters dict
        description: Optional description
        is_active: Whether monitoring is active

    Returns:
        Stave instance ready to be saved

    Example:
        >>> stave = create_stave(
        ...     name="Production Database",
        ...     data_source_type="postgres",
        ...     connection_config={
        ...         "host": "db.example.com",
        ...         "port": 5432,
        ...         "database": "prod",
        ...         "user": "monitor"
        ...     }
        ... )
    """
    return Stave(
        id=generate_stave_id(),
        name=name,
        description=description,
        data_source_type=data_source_type,
        connection_config=connection_config,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def create_postgres_stave(
    name: str,
    host: str,
    database: str,
    user: str,
    password: str | None = None,
    port: int = 5432,
    description: str | None = None,
    **kwargs,
) -> Stave:
    """
    Create a PostgreSQL Stave with sensible defaults.

    Example:
        >>> stave = create_postgres_stave(
        ...     name="Production DB",
        ...     host="db.example.com",
        ...     database="prod",
        ...     user="monitor",
        ...     password="secret"
        ... )
    """
    config = {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
    }
    if password:
        config["password"] = password
    config.update(kwargs)

    return create_stave(
        name=name,
        data_source_type="postgres",
        connection_config=config,
        description=description,
    )


def create_sqlite_stave(
    name: str, path: str, description: str | None = None, **kwargs
) -> Stave:
    """
    Create a SQLite Stave.

    Example:
        >>> stave = create_sqlite_stave(
        ...     name="Local Analytics",
        ...     path="/data/analytics.db"
        ... )
    """
    config = {"path": path}
    config.update(kwargs)

    return create_stave(
        name=name,
        data_source_type="sqlite",
        connection_config=config,
        description=description,
    )


def create_mysql_stave(
    name: str,
    host: str,
    database: str,
    user: str,
    password: str | None = None,
    port: int = 3306,
    description: str | None = None,
    **kwargs,
) -> Stave:
    """
    Create a MySQL Stave with sensible defaults.

    Example:
        >>> stave = create_mysql_stave(
        ...     name="MySQL DB",
        ...     host="mysql.example.com",
        ...     database="app",
        ...     user="monitor"
        ... )
    """
    config = {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
    }
    if password:
        config["password"] = password
    config.update(kwargs)

    return create_stave(
        name=name,
        data_source_type="mysql",
        connection_config=config,
        description=description,
    )


# =============================================================================
# Clef Creation Helpers
# =============================================================================


def create_clef(
    stave_id: str,
    name: str,
    check_type: str,
    config: dict[str, Any],
    description: str | None = None,
    schedule: str | None = None,
    is_active: bool = True,
    warn: str | None = None,
    fail: str | None = None,
) -> Clef:
    """
    Create a new Clef with auto-generated ID and timestamps.

    Args:
        stave_id: ID of the Stave this check belongs to
        name: Human-readable name for the check
        check_type: Type of check (null_check, range_check, etc.)
        config: Check configuration parameters
        description: Optional description
        schedule: Optional cron expression for scheduling
        is_active: Whether check is active

    Returns:
        Clef instance ready to be saved

    Example:
        >>> clef = create_clef(
        ...     stave_id="stave-123",
        ...     name="Email NULL Check",
        ...     check_type="null_check",
        ...     config={"table": "users", "column": "email", "threshold": 0.01}
        ... )
    """
    return Clef(
        id=generate_clef_id(),
        stave_id=stave_id,
        name=name,
        description=description,
        check_type=check_type,
        config=config,
        schedule=schedule,
        is_active=is_active,
        warn=warn,
        fail=fail,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def create_null_check(
    stave_id: str,
    name: str,
    table: str,
    column: str,
    threshold: float = 0.0,
    schedule: str | None = None,
) -> Clef:
    """
    Create a NULL value check.

    Args:
        stave_id: ID of the Stave
        name: Name for this check
        table: Table name to check
        column: Column name to check
        threshold: Maximum allowed percentage of NULL values (0.0 = no NULLs allowed)
        schedule: Optional cron schedule

    Example:
        >>> check = create_null_check(
        ...     stave_id="stave-123",
        ...     name="Email NULL Check",
        ...     table="users",
        ...     column="email",
        ...     threshold=0.01  # Allow max 1% NULLs
        ... )
    """
    return create_clef(
        stave_id=stave_id,
        name=name,
        check_type="column_values",
        config={"table": table, "column": column, "condition": "if_null"},
        warn=f"if_null > {threshold * 100:.1f}%" if threshold > 0 else None,
        fail="if_null > 0%" if threshold == 0 else None,
        schedule=schedule,
    )


def create_range_check(
    stave_id: str,
    name: str,
    table: str,
    column: str,
    min_value: float | None = None,
    max_value: float | None = None,
    schedule: str | None = None,
) -> Clef:
    """
    Create a range validation check.

    Args:
        stave_id: ID of the Stave
        name: Name for this check
        table: Table name to check
        column: Column name to check
        min_value: Minimum allowed value (optional)
        max_value: Maximum allowed value (optional)
        schedule: Optional cron schedule

    Example:
        >>> check = create_range_check(
        ...     stave_id="stave-123",
        ...     name="Age Range Check",
        ...     table="users",
        ...     column="age",
        ...     min_value=0,
        ...     max_value=150
        ... )
    """
    config = {"table": table, "column": column}
    if min_value is not None:
        config["min"] = min_value
    if max_value is not None:
        config["max"] = max_value

    return create_clef(
        stave_id=stave_id,
        name=name,
        check_type="column_values",
        config=config,
        schedule=schedule,
    )


def create_volume_check(
    stave_id: str,
    name: str,
    table: str,
    expected_min: int | None = None,
    expected_max: int | None = None,
    schedule: str | None = None,
) -> Clef:
    """
    Create a row count check.

    Args:
        stave_id: ID of the Stave
        name: Name for this check
        table: Table name to check
        expected_min: Minimum expected row count (optional)
        expected_max: Maximum expected row count (optional)
        schedule: Optional cron schedule

    Example:
        >>> check = create_volume_check(
        ...     stave_id="stave-123",
        ...     name="Daily Events Volume",
        ...     table="events",
        ...     expected_min=1000,
        ...     expected_max=100000
        ... )
    """
    config = {"table": table}
    if expected_min is not None:
        config["expected_min"] = expected_min
    if expected_max is not None:
        config["expected_max"] = expected_max

    return create_clef(
        stave_id=stave_id,
        name=name,
        check_type="row_count",
        config=config,
        schedule=schedule,
    )


# =============================================================================
# Serialization Helpers (for database storage)
# =============================================================================


def serialize_stave(stave: Stave) -> dict[str, Any]:
    """
    Serialize a Stave for database storage.

    Converts connection_config dict to JSON string for TEXT column storage.

    Args:
        stave: Stave instance

    Returns:
        Dict ready for database insertion

    Example:
        >>> stave = create_postgres_stave("DB", "localhost", "db", "user")
        >>> data = serialize_stave(stave)
        >>> # data["connection_config"] is now a JSON string
    """
    data = stave.model_dump()
    # Convert connection_config dict to JSON string
    data["connection_config"] = json.dumps(data["connection_config"])
    # Convert datetime objects to ISO strings
    data["created_at"] = data["created_at"].isoformat()
    data["updated_at"] = data["updated_at"].isoformat()
    return data


def deserialize_stave(data: dict[str, Any]) -> Stave:
    """
    Deserialize a Stave from database storage.

    Converts connection_config JSON string back to dict.

    Args:
        data: Database row dict

    Returns:
        Stave instance

    Example:
        >>> db_row = {"id": "...", "connection_config": "{...}", ...}
        >>> stave = deserialize_stave(db_row)
    """
    # Make a copy so we don't modify the original
    data = dict(data)

    # Convert connection_config JSON string to dict
    if isinstance(data.get("connection_config"), str):
        data["connection_config"] = json.loads(data["connection_config"])

    # Keep datetime fields as strings for API compatibility
    # (The API schemas expect strings, not datetime objects)

    return Stave(**data)


def serialize_clef(clef: Clef) -> dict[str, Any]:
    """
    Serialize a Clef for database storage.

    Converts config dict to JSON string for TEXT column storage.
    Only includes fields that exist in the database schema.

    Args:
        clef: Clef instance

    Returns:
        Dict ready for database insertion
    """
    # Only include fields that exist in the database schema
    data = {
        "id": clef.id,
        "stave_id": clef.stave_id,
        "name": clef.name,
        "description": clef.description,
        "check_type": clef.check_type,
        "config": json.dumps(clef.config),
        "schedule": clef.schedule,
        "is_active": clef.is_active,
        "warn": clef.warn,
        "fail": clef.fail,
        "created_at": clef.created_at.isoformat(),
        "updated_at": clef.updated_at.isoformat(),
    }
    # Add retry_config if present
    if clef.retry_config:
        data["retry_config"] = json.dumps(clef.retry_config)
    return data


def deserialize_clef(data: dict[str, Any]) -> Clef:
    """
    Deserialize a Clef from database storage.

    Converts config and retry_config JSON strings back to dicts.

    Args:
        data: Database row dict

    Returns:
        Clef instance
    """
    # Make a copy so we don't modify the original
    data = dict(data)

    # Convert config JSON string to dict
    if isinstance(data.get("config"), str):
        data["config"] = json.loads(data["config"])

    # Convert retry_config JSON string to dict if present
    if "retry_config" in data and isinstance(data.get("retry_config"), str):
        try:
            data["retry_config"] = json.loads(data["retry_config"])
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, set to None
            data["retry_config"] = None

    # Keep datetime fields as strings for API compatibility
    # (The API schemas expect strings, not datetime objects)

    return Clef(**data)


# =============================================================================
# Validation Helpers
# =============================================================================


def is_valid_data_source_type(data_source_type: str) -> bool:
    """Check if a data source type is supported."""
    return data_source_type.lower() in SUPPORTED_DATA_SOURCES


def is_valid_check_type(check_type: str) -> bool:
    """Check if a check type is supported."""
    return check_type.lower() in SUPPORTED_CHECK_TYPES


def get_supported_data_sources() -> list[str]:
    """Get list of all supported data source types."""
    return list(SUPPORTED_DATA_SOURCES)


def get_supported_check_types() -> list[str]:
    """Get list of all supported check types."""
    return list(SUPPORTED_CHECK_TYPES)
