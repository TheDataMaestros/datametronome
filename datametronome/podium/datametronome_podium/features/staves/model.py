"""Stave domain model."""
from pydantic import BaseModel


class Stave(BaseModel):
    id: str
    name: str
    description: str | None = None
    data_source_type: str
    connection_config: str  # JSON string
    is_active: bool = True
    paused: bool = False
    created_at: str
    updated_at: str
