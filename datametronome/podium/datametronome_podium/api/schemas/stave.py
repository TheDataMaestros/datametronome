"""
Pydantic schemas for Stave operations.
"""

from typing import Any

from pydantic import BaseModel, Field


class StaveBase(BaseModel):
    """Base stave schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    data_source_type: str = Field(..., min_length=1, max_length=100)
    connection_config: dict[str, Any] = Field(..., description="Connection parameters")
    is_active: bool = True


class StaveCreate(StaveBase):
    """Schema for creating a stave."""
    
    id: str
    created_at: str
    updated_at: str


class StaveUpdate(BaseModel):
    """Schema for updating a stave."""
    
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    data_source_type: str | None = Field(None, min_length=1, max_length=100)
    connection_config: dict[str, Any] | None = None
    is_active: bool | None = None
    updated_at: str


class StaveResponse(StaveBase):
    """Schema for stave responses."""
    
    id: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True
