"""
Mock User model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from pydantic import BaseModel


class User(BaseModel):
    """Mock User model for backward compatibility."""
    
    id: int
    name: str
    email: str
    active: bool = True
