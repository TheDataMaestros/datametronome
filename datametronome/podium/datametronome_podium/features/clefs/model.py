"""Clef domain model."""
from pydantic import BaseModel


class Clef(BaseModel):
    id: str
    stave_id: str
    name: str
    description: str | None = None
    check_type: str
    config: str  # JSON string
    warn: str | None = None
    fail: str | None = None
    retry_config: str | None = None
    schedule: str | None = None
    is_active: bool = True
    created_at: str
    updated_at: str
