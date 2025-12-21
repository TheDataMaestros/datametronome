"""
Mock CheckRun model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CheckRun(BaseModel):
    """Mock CheckRun model for backward compatibility."""

    id: int | None = None
    name: str = "default_check_run"
    stave_id: int
    clef_id: int
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    parameters: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v

    model_config = ConfigDict(extra="allow")
