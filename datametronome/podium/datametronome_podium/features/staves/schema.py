"""Stave API DTOs."""
from pydantic import BaseModel, field_validator

# Only types create_connector can actually build. A stave whose type has no
# connector can be created and can even pass a connection test, but every check
# against it fails, which is worse than not offering it.
VALID_DATA_SOURCE_TYPES = ["postgres", "sqlite", "bigquery", "dbt"]


class StaveCreate(BaseModel):
    name: str
    description: str | None = None
    data_source_type: str
    connection_config: dict
    is_active: bool = True
    # Owning group. Optional when the caller belongs to exactly one group,
    # in which case the router fills it in.
    group_id: str | None = None

    @field_validator("data_source_type")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_DATA_SOURCE_TYPES:
            raise ValueError(f"Must be one of: {VALID_DATA_SOURCE_TYPES}")
        return v


class StaveUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    data_source_type: str | None = None
    connection_config: dict | None = None
    is_active: bool | None = None


class StaveResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    data_source_type: str
    connection_config: dict | str
    is_active: bool
    paused: bool = False
    # Without this the API never tells a client which group owns a stave, so
    # nothing outside the backend can show or manage ownership.
    group_id: str | None = None
    created_at: str
    updated_at: str
