"""User API DTOs (request/response).

Ported from api/schemas/auth.py -- preserves all existing validators.
"""
from typing import Literal

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str
    email: str
    full_name: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


# ── Admin user management schemas ────────────────────────────────────────────


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    email: str
    password: str = Field(..., min_length=8)
    role: Literal["admin", "editor", "viewer"] = "viewer"


class UserUpdate(BaseModel):
    email: str | None = None
    role: Literal["admin", "editor", "viewer"] | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)


class UserDetailResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    role: str
    created_at: str
    updated_at: str
