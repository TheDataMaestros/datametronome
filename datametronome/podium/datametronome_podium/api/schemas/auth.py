"""Authentication schemas for DataMetronome Podium."""

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user schema."""
    
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    full_name: str | None = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user."""
    
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login."""
    
    username: str
    password: str


class Token(BaseModel):
    """Schema for authentication token."""
    
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for token data."""
    
    username: str | None = None
