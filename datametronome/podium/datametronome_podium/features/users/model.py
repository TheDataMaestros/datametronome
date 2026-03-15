"""User domain model."""
from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: str
    updated_at: str
