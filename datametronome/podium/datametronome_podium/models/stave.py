"""
Mock Stave model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from pydantic import BaseModel


class Stave(BaseModel):
    """Mock Stave model for backward compatibility."""
    
    id: int
    name: str
    description: str | None = None
