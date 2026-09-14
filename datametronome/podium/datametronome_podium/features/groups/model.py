"""Group domain models."""

from pydantic import BaseModel


class GroupRow(BaseModel):
    """Raw DB row for a group."""

    id: str
    name: str
    description: str | None = None
    created_at: str
    updated_at: str
