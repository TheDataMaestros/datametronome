"""Stave API DTOs."""
from pydantic import BaseModel, field_validator

VALID_DATA_SOURCE_TYPES = [
    "postgres", "mysql", "mongodb", "sqlite", "redis", "snowflake", "bigquery"
]


class StaveCreate(BaseModel):
    name: str
    description: str | None = None
    data_source_type: str
    connection_config: dict
    is_active: bool = True

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
    created_at: str
    updated_at: str
