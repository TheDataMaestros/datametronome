"""Check schemas for DataMetronome Podium."""

from datetime import datetime
from typing import Any
import json

from pydantic import BaseModel, Field, field_validator


class CheckBase(BaseModel):
    """Base check schema."""
    
    stave_id: str
    clef_id: str
    check_type: str
    status: str
    message: str | None = None
    details: dict[str, Any] | None = None
    timestamp: datetime
    execution_time: float | None = None
    anomalies_count: int = 0
    severity: str = "medium"

    @field_validator("details", mode="before")
    @classmethod
    def parse_details(cls, value):
        """Allow JSON strings persisted in the database."""
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Return original string if it is not valid JSON
                return {"raw": value}
        return value


class CheckCreate(CheckBase):
    """Schema for creating a check."""
    
    id: str


class CheckUpdate(BaseModel):
    """Schema for updating a check."""
    
    status: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None
    execution_time: float | None = None
    anomalies_count: int | None = None
    severity: str | None = None


class CheckResponse(CheckBase):
    """Schema for check response."""
    
    id: str


class CheckRunBase(BaseModel):
    """Base check run schema."""
    
    clef_id: str
    status: str = Field(..., description="Check status: success, failure, error")
    started_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    error_message: str | None = None


class CheckRunCreate(CheckRunBase):
    """Schema for creating a check run."""
    
    pass


class CheckRunResponse(CheckRunBase):
    """Schema for check run response."""
    
    id: str




