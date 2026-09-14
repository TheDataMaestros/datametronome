"""Group API DTOs."""

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class GroupResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: str
    updated_at: str


class GroupMemberAdd(BaseModel):
    user_id: str


class GroupMemberResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
