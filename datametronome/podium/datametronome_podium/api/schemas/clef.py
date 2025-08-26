"""
Pydantic schemas for Clef operations.
"""

from typing import Any

from pydantic import BaseModel, Field


class ClefBase(BaseModel):
    """Base clef schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    check_type: str = Field(..., min_length=1, max_length=100)
    config: dict[str, Any] = Field(..., description="Check-specific configuration")
    schedule: str | None = Field(None, description="Cron expression for scheduling")
    is_active: bool = True


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
