"""
Mock Clef model for backward compatibility.
This model has been refactored but tests still expect it.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class Clef(BaseModel):
    """Mock Clef model for backward compatibility."""
    
    id: int | None = None
    name: str
    description: str | None = None
    clef_type: str
    symbol: str = "♩"  # Default symbol
    config: dict = {}
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('clef_type')
    @classmethod
    def validate_clef_type(cls, v):
        valid_types = ['postgres_quality', 'mysql_quality', 'sqlite_quality']
        if v not in valid_types:
            raise ValueError(f"Invalid clef type: {v}")
        return v
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v):
        if isinstance(v, dict):
            if 'table_name' in v and (not v['table_name'] or v['table_name'].strip() == ''):
                raise ValueError("Table name cannot be empty")
            if 'checks' in v and isinstance(v['checks'], list):
                for check in v['checks']:
                    if isinstance(check, dict) and 'type' in check:
                        valid_check_types = ['null_check', 'range_check', 'format_check']
                        if check['type'] not in valid_check_types:
                            raise ValueError(f"Invalid check type: {check['type']}")
        return v
    
    model_config = ConfigDict(extra="allow")
