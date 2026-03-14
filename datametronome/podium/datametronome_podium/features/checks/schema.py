"""Check API DTOs.

Ported from api/schemas/check.py — preserves all existing validators.
"""
import json
from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CheckBase(BaseModel):
    stave_id: str
    clef_id: str
    check_type: str
    status: str
    message: str | None = None
    details: dict[str, Any] | None = None
    timestamp: datetime
    execution_time: float | None = None
    anomalies_count: int = Field(default=0, ge=0)
    severity: str = "medium"

    @field_validator("details", mode="before")
    @classmethod
    def parse_details_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class CheckCreate(CheckBase):
    id: str


class CheckUpdate(BaseModel):
    status: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None
    execution_time: float | None = None
    anomalies_count: int | None = None
    severity: str | None = None


class CheckResponse(CheckBase):
    id: str
