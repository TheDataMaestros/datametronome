"""
Stave model - represents a data source to be monitored.

A Stave is the core unit of monitoring in DataMetronome. It represents a single
data source (database, API, file, etc.) that you want to monitor for quality issues.

Example Usage:
    # Create a Stave for a PostgreSQL database
    stave = Stave(
        name="Production Users DB",
        description="Main production database for user data",
        data_source_type="postgres",
        connection_config={
            "host": "prod-db.example.com",
            "port": 5432,
            "database": "users",
            "user": "monitor_user",
            "password": "secure_password"
        }
    )

    # Create a Stave for a SQLite database
    stave = Stave(
        name="Local Analytics DB",
        data_source_type="sqlite",
        connection_config={"path": "/data/analytics.db"}
    )
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Supported data source types
SUPPORTED_DATA_SOURCES = [
    "postgres",
    "postgresql",
    "mysql",
    "sqlite",
    "mongodb",
    "redis",
    "snowflake",
    "bigquery",
    "api",
    "http",
]


class Stave(BaseModel):
    """
    A Stave represents a data source to be monitored.

    Think of a Stave as a musical staff where you write notes - here, it's where
    you define what data source to monitor. Each Stave can have multiple Clefs
    (data quality checks) attached to it.

    Attributes:
        id: Unique identifier (generated automatically if not provided)
        name: Human-readable name for this data source
        description: Optional detailed description
        data_source_type: Type of data source (postgres, mysql, sqlite, etc.)
        connection_config: Configuration dict with connection parameters
        is_active: Whether monitoring is active for this source
        created_at: Timestamp when this stave was created
        updated_at: Timestamp of last update

    Connection Config Examples:
        Postgres/MySQL: {"host": "...", "port": 5432, "database": "...", "user": "...", "password": "..."}
        SQLite: {"path": "/path/to/database.db"}
        MongoDB: {"uri": "mongodb://...", "database": "..."}
        Redis: {"host": "...", "port": 6379, "db": 0}
        API: {"base_url": "https://api.example.com", "api_key": "..."}
    """

    id: str = Field(
        default="", description="Unique identifier (auto-generated if not provided)"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for the data source",
        examples=["Production Database", "User Service API", "Analytics Cache"],
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Optional description explaining what this data source is for",
    )
    data_source_type: str = Field(
        ...,
        description=f"Type of data source. Supported: {', '.join(SUPPORTED_DATA_SOURCES)}",
    )
    connection_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Connection parameters specific to the data source type",
    )
    is_active: bool = Field(
        default=True, description="Whether monitoring is active for this data source"
    )
    paused: bool = Field(
        default=False, description="Circuit breaker: True when stave has too many consecutive failures"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this stave was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this stave was last updated",
    )

    model_config = ConfigDict(
        extra="forbid",  # Don't allow extra fields
        json_schema_extra={
            "examples": [
                {
                    "name": "Production PostgreSQL",
                    "description": "Main production database",
                    "data_source_type": "postgres",
                    "connection_config": {
                        "host": "db.example.com",
                        "port": 5432,
                        "database": "prod_db",
                        "user": "monitor",
                    },
                    "is_active": True,
                },
                {
                    "name": "Local SQLite",
                    "data_source_type": "sqlite",
                    "connection_config": {"path": "./data.db"},
                    "is_active": True,
                },
            ]
        },
    )

    @field_validator("data_source_type")
    @classmethod
    def validate_data_source_type(cls, v: str) -> str:
        """Validate that the data source type is supported."""
        v_lower = v.lower()
        if v_lower not in SUPPORTED_DATA_SOURCES:
            raise ValueError(
                f"Unsupported data source type: '{v}'. "
                f"Supported types: {', '.join(SUPPORTED_DATA_SOURCES)}"
            )
        return v_lower

    @field_validator("connection_config")
    @classmethod
    def validate_connection_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that connection config is not empty."""
        if not v:
            raise ValueError(
                "connection_config cannot be empty. "
                "Provide connection parameters for the data source."
            )
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @model_validator(mode="after")
    def generate_id_if_missing(self):
        """Generate ID if not provided."""
        if not self.id:
            import uuid

            # Generate ID from name slug + uuid
            name_slug = self.name.lower().replace(" ", "-")[:30]
            self.id = f"stave-{name_slug}-{str(uuid.uuid4())[:8]}"
        return self

    def __repr__(self) -> str:
        """Pretty representation for debugging."""
        return (
            f"Stave(name='{self.name}', "
            f"type='{self.data_source_type}', "
            f"active={self.is_active})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "🟢 Active" if self.is_active else "🔴 Inactive"
        return f"{status} {self.name} ({self.data_source_type})"
