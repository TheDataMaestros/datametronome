"""
Mock Stave model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class Stave(BaseModel):
    """Mock Stave model for backward compatibility."""
    
    id: int | None = None
    name: str
    description: str | None = None
    stave_type: str
    config: dict = {}
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('stave_type')
    @classmethod
    def validate_stave_type(cls, v):
        valid_types = ['postgres_monitor', 'mysql_monitor', 'sqlite_monitor']
        if v not in valid_types:
            raise ValueError(f"Invalid stave type: {v}")
        return v
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v):
        if isinstance(v, dict):
            if 'host' in v and (not v['host'] or v['host'].strip() == ''):
                raise ValueError("Host cannot be empty")
            if 'port' in v and (not isinstance(v['port'], int) or v['port'] <= 0):
                raise ValueError("Port must be a positive integer")
        return v
    
    model_config = ConfigDict(extra="allow")
