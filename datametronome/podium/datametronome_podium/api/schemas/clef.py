"""
Pydantic schemas for Clef operations.
"""

from typing import Any
import re
from pydantic import BaseModel, Field, field_validator, ConfigDict


VALID_CHECK_TYPES = [
    "null_check",
    "uniqueness_check",
    "range_check",
    "pattern_check",
    "custom_sql",
    "freshness_check",
    "volume_check"
]


class ClefBase(BaseModel):
    """Base clef schema."""
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Check for NULL emails",
            "description": "Ensures all users have valid email addresses",
            "check_type": "null_check",
            "config": {
                "table": "users",
                "column": "email",
                "threshold": 0.01
            },
            "schedule": "0 * * * *",
            "is_active": True
        }
    })
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Human-readable name for the data quality check",
        examples=["Check for NULL emails", "Validate age range", "Check duplicate IDs"]
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Detailed description of what this check validates",
        examples=["Ensures all user records have valid, non-null email addresses"]
    )
    check_type: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description=f"Type of data quality check. Supported: {', '.join(VALID_CHECK_TYPES)}",
        examples=["null_check"]
    )
    config: dict[str, Any] = Field(
        ..., 
        description="Check-specific configuration parameters",
        examples=[{"table": "users", "column": "email", "threshold": 0.01}]
    )
    schedule: str | None = Field(
        None, 
        description="Cron expression for automatic scheduling (e.g., '0 * * * *' for hourly)",
        examples=["0 * * * *", "0 0 * * *", "*/15 * * * *"]
    )
    is_active: bool = Field(
        True,
        description="Whether this check is actively running"
    )
    
    @field_validator('check_type')
    @classmethod
    def validate_check_type(cls, v: str) -> str:
        """Validate check type is supported."""
        if v.lower() not in VALID_CHECK_TYPES:
            raise ValueError(
                f"check_type must be one of {VALID_CHECK_TYPES}, got '{v}'"
            )
        return v.lower()
    
    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: str | None) -> str | None:
        """Validate cron expression format."""
        if v is None:
            return v
        
        # Basic cron validation (5 or 6 fields separated by spaces)
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError(
                f"Invalid cron expression: '{v}'. Must have 5 or 6 fields. "
                "Example: '0 * * * *' (hourly) or '0 0 * * *' (daily)"
            )
        
        # Check if it's a shorthand like @hourly, @daily, etc.
        shorthands = ['@yearly', '@annually', '@monthly', '@weekly', '@daily', '@hourly']
        if v.startswith('@') and v.lower() not in shorthands:
            raise ValueError(
                f"Invalid cron shorthand: '{v}'. Supported: {', '.join(shorthands)}"
            )
        
        return v
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate config has required fields."""
        if not v:
            raise ValueError("config cannot be empty")
        return v


class ClefCreate(ClefBase):
    """Schema for creating a clef."""
    
    id: str
    stave_id: str = Field(..., description="ID of the associated stave")
    created_at: str
    updated_at: str


class ClefUpdate(BaseModel):
    """Schema for updating a clef."""
    
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    check_type: str | None = Field(None, min_length=1, max_length=100)
    config: dict[str, Any] | None = None
    schedule: str | None = None
    is_active: bool | None = None
    updated_at: str


class ClefResponse(ClefBase):
    """Schema for clef responses."""
    
    id: str
    stave_id: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True
