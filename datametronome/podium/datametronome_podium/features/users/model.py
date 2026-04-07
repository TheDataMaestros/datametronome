"""User domain model and DB row DTO."""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRow(BaseModel):
    """Minimal DB row DTO — fields map 1:1 to the users table columns."""

    id: str
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    # role is the primary RBAC control; is_superuser kept until migration 010 backfill is stable
    role: str = "viewer"
    created_at: str
    updated_at: str


class User(BaseModel):
    """Rich domain model for a User.

    Used by tests and legacy service code that validates user fields without
    hashed passwords.  The DB layer uses UserRow instead.
    """

    id: int | None = None
    username: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    full_name: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Username cannot be empty")
        if len(v) > 50:
            raise ValueError("Username too long")
        if " " in v or "@" in v:
            raise ValueError("Username cannot contain spaces or @ symbols")
        if v[0].isdigit():
            raise ValueError("Username cannot start with a number")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v or "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v

    model_config = ConfigDict(extra="allow")
