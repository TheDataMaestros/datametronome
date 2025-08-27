"""
Mock Clef model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from pydantic import BaseModel


class Clef(BaseModel):
    """Mock Clef model for backward compatibility."""
    
    id: int
    name: str
    symbol: str
