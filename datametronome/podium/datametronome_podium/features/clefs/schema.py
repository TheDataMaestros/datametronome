"""Clef API DTOs.

Ported from api/schemas/clef.py — preserves all existing validators.
"""
from typing import Any
from pydantic import BaseModel, Field, field_validator

from datametronome_podium.features.clefs.model import SUPPORTED_CHECK_TYPES

# The API accepts exactly what the model supports. One list, not two that a
# test has to keep agreeing.
VALID_CHECK_TYPES = SUPPORTED_CHECK_TYPES


class ClefBase(BaseModel):
    stave_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    check_type: str = Field(..., min_length=1, max_length=100)
    config: dict[str, Any] = Field(...)
    schedule: str | None = None
    is_active: bool = True
    warn: str | None = None
    fail: str | None = None

    @field_validator("check_type")
    @classmethod
    def validate_check_type(cls, v):
        v = v.lower()
        if v not in VALID_CHECK_TYPES:
            raise ValueError(f"Must be one of: {VALID_CHECK_TYPES}")
        return v

    @field_validator("config")
    @classmethod
    def validate_config_not_empty(cls, v):
        if not v:
            raise ValueError("Config cannot be empty")
        return v

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v):
        if v is None:
            return v
        shorthands = {"@daily", "@hourly", "@yearly", "@monthly", "@weekly", "@minutely"}
        if v in shorthands:
            return v
        parts = v.split()
        if len(parts) not in (5, 6):
            raise ValueError("Schedule must be a valid cron expression (5-6 fields) or shorthand")
        return v


class ClefCreate(ClefBase):
    pass


class ClefUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    check_type: str | None = Field(default=None, min_length=1, max_length=100)
    config: dict[str, Any] | None = None
    schedule: str | None = None
    is_active: bool | None = None
    warn: str | None = None
    fail: str | None = None
    updated_at: str | None = None


class ClefResponse(BaseModel):
    id: str
    stave_id: str
    name: str
    description: str | None = None
    check_type: str
    config: dict[str, Any] | str
    schedule: str | None = None
    is_active: bool
    warn: str | None = None
    fail: str | None = None
    created_at: str
    updated_at: str
