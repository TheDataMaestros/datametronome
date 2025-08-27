"""
Mock CheckRun model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from pydantic import BaseModel
from datetime import datetime


class CheckRun(BaseModel):
    """Mock CheckRun model for backward compatibility."""
    
    id: int
    name: str
    status: str
    created_at: datetime
