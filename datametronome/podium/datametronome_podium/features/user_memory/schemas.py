"""User memory API DTOs and extraction models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UserMemoryResponse(BaseModel):
    id: str
    user_id: str
    category: str
    content: str
    source_conversation_id: str | None = None
    confidence: float
    active: bool
    superseded_by: str | None = None
    created_at: str
    updated_at: str


class UserMemoryProfileResponse(BaseModel):
    id: str
    user_id: str
    domain_summary: str
    expertise_summary: str
    investigation_summary: str
    memory_count: int
    last_rebuilt_at: str
    created_at: str


class UserMemoryCreate(BaseModel):
    category: Literal["domain_focus", "expertise", "investigation"]
    content: str
    confidence: float = 1.0


class UserMemoryUpdate(BaseModel):
    content: str | None = None
    active: bool | None = None


class MemoryExtraction(BaseModel):
    category: Literal["domain_focus", "expertise", "investigation"]
    content: str
    confidence: float
    action: Literal["new", "update", "invalidate"]
    # Required when action is "update" or "invalidate" — links back to the
    # existing memory row being superseded
    existing_memory_id: str | None = None
