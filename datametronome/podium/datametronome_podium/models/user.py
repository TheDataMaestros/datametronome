"""
Mock User model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class User(BaseModel):
    """Mock User model for backward compatibility."""
    
    id: int | None = None
    username: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    full_name: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Username cannot be empty")
        if len(v) > 50:
            raise ValueError("Username too long")
        if ' ' in v or '@' in v:
            raise ValueError("Username cannot contain spaces or @ symbols")
        if v[0].isdigit():
            raise ValueError("Username cannot start with a number")
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v or '@' not in v or '.' not in v:
            raise ValueError("Invalid email format")
        return v
    
    model_config = ConfigDict(extra="allow")
