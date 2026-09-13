"""Stave domain model and DB row DTO."""
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
    "dbt",
    "api",
    "http",
]


class StaveRow(BaseModel):
    """Minimal DB row DTO — fields map 1:1 to the staves table columns.

    connection_config is stored as a JSON string in the DB; the feature layer
    (repo, router) works with raw strings and deserialises only at the boundary.
    """

    id: str
    name: str
    description: str | None = None
    data_source_type: str
    connection_config: str  # JSON string
    is_active: bool = True
    paused: bool = False
    created_at: str
    updated_at: str


class Stave(BaseModel):
    """Rich domain model for a Stave (data source to monitor).

    Used by the service layer and any code that needs validated, typed access to
    stave data.  connection_config is a dict here; services use serialize_stave()
    from stave_service.py to convert to StaveRow before persisting.
    """

    id: str = Field(
        default="", description="Unique identifier (auto-generated if not provided)"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for the data source",
    )
    description: str | None = Field(None, max_length=1000)
    data_source_type: str = Field(
        ...,
        description=f"Type of data source. Supported: {', '.join(SUPPORTED_DATA_SOURCES)}",
    )
    connection_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Connection parameters specific to the data source type",
    )
    is_active: bool = Field(default=True)
    paused: bool = Field(
        default=False,
        description="Circuit breaker: True when stave has too many consecutive failures",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("data_source_type")
    @classmethod
    def validate_data_source_type(cls, v: str) -> str:
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
        if not v:
            raise ValueError(
                "connection_config cannot be empty. "
                "Provide connection parameters for the data source."
            )
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @model_validator(mode="after")
    def generate_id_if_missing(self):
        if not self.id:
            import uuid

            name_slug = self.name.lower().replace(" ", "-")[:30]
            self.id = f"stave-{name_slug}-{str(uuid.uuid4())[:8]}"
        return self

    def __repr__(self) -> str:
        return (
            f"Stave(name='{self.name}', "
            f"type='{self.data_source_type}', "
            f"active={self.is_active})"
        )
