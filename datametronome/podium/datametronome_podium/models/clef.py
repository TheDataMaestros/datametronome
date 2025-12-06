"""
Clef model - represents a data quality check.

A Clef is a single data quality check that runs against a Stave (data source).
Think of it as a test or validation rule that you want to apply to your data.

Example Usage:
    # Check for NULL values in email column
    clef = Clef(
        stave_id="stave-001",
        name="Email NULL Check",
        description="Ensure all users have email addresses",
        check_type="null_check",
        config={
            "table": "users",
            "column": "email",
            "threshold": 0.01  # Allow max 1% nulls
        },
        schedule="0 * * * *"  # Run every hour
    )
    
    # Custom SQL check
    clef = Clef(
        stave_id="stave-001",
        name="Active Users Check",
        check_type="custom_sql",
        config={
            "query": "SELECT COUNT(*) FROM users WHERE last_login > NOW() - INTERVAL '7 days'",
            "expected_min": 100
        }
    )
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Any


# Check types organized by TDD levels
LEVEL_1_CHECKS = [
    "row_count",           # Check total number of rows
    "freshness",           # Check data freshness (time since last update)
    "column_values",       # Validate values within a single column
]

LEVEL_2_CHECKS = [
    "forecast",            # ML-driven anomaly detection using time-series models
    "data_profile_drift",  # Statistical drift detection
]

LEVEL_3_CHECKS = [
    "lookup_validation",   # Cross-system integrity validation
]

LEVEL_4_CHECKS = [
    "python",              # Custom Python script (secure escape hatch)
]

# All supported check types
SUPPORTED_CHECK_TYPES = LEVEL_1_CHECKS + LEVEL_2_CHECKS + LEVEL_3_CHECKS + LEVEL_4_CHECKS

# Check level mapping (per TDD specification)
CHECK_LEVEL_MAPPING = {
    **{check: 1 for check in LEVEL_1_CHECKS},
    **{check: 2 for check in LEVEL_2_CHECKS},
    **{check: 3 for check in LEVEL_3_CHECKS},
    **{check: 4 for check in LEVEL_4_CHECKS}
}

# Legacy check type mappings (for backward compatibility)
LEGACY_CHECK_MAPPING = {
    "volume_check": "row_count",
    "freshness_check": "freshness",
    "null_check": "column_values",
    "range_check": "column_values",
    "pattern_check": "column_values",
    "uniqueness_check": "column_values",
    "drift_detection": "data_profile_drift",
    "custom_python": "python"
}


class Clef(BaseModel):
    """
    A Clef represents a data quality check.
    
    Think of a Clef in music - it tells you how to read the notes. Here, a Clef
    defines how to check data quality on a Stave (data source). Each Clef is
    a specific test or validation rule.
    
    Attributes:
        id: Unique identifier (generated automatically if not provided)
        stave_id: ID of the Stave this check belongs to
        name: Human-readable name for this check
        description: Optional detailed description
        check_type: Type of check to perform
        config: Configuration dict with check-specific parameters
        schedule: Optional cron expression for automatic scheduling
        is_active: Whether this check is active
        created_at: Timestamp when this check was created
        updated_at: Timestamp of last update
        
    Config Examples:
        Null Check: {"table": "users", "column": "email", "threshold": 0.01}
        Range Check: {"table": "orders", "column": "amount", "min": 0, "max": 10000}
        Pattern Check: {"table": "users", "column": "email", "pattern": "^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"}
        Volume Check: {"table": "events", "expected_min": 1000, "expected_max": 100000}
        Custom SQL: {"query": "SELECT ...", "expected_result": 0}
    """
    
    id: str | None = None
    stave_id: str = Field(
        ...,
        description="ID of the Stave (data source) this check belongs to"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for this check",
        examples=["Email NULL Check", "Age Range Validation", "Duplicate ID Check"]
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Optional description explaining what this check does"
    )
    check_type: str = Field(
        ...,
        description=f"Type of check to perform. Supported: {', '.join(SUPPORTED_CHECK_TYPES)}"
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Check-specific configuration parameters"
    )
    # TDD-compliant severity conditions (per TDD specification)
    warn: str | None = Field(
        None,
        description="Condition string that triggers a 'warn' status (e.g., '> 5000', '< 100')"
    )
    fail: str | None = Field(
        None,
        description="Condition string that triggers a 'fail' status (e.g., '> 10000', '< 50')"
    )
    # Legacy severity config (for backward compatibility)
    severity_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Legacy severity configuration (deprecated, use warn/fail instead)"
    )
    schedule: str | None = Field(
        None,
        description="Optional cron expression for automatic scheduling (e.g., '0 * * * *' for hourly)",
        examples=["0 * * * *", "@hourly", "@daily", "*/15 * * * *"]
    )
    retry_config: dict[str, Any] | None = Field(
        None,
        description="Retry configuration for failed executions",
        examples=[{"max_retries": 3, "backoff_factor": 2.0, "max_delay_seconds": 300}]
    )
    is_active: bool = Field(
        default=True,
        description="Whether this check is actively running"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this check was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this check was last updated"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "stave_id": "stave-001",
                    "name": "Email NULL Check",
                    "description": "Ensure all users have email addresses",
                    "check_type": "null_check",
                    "config": {
                        "table": "users",
                        "column": "email",
                        "threshold": 0.01
                    },
                    "schedule": "0 * * * *",
                    "is_active": True
                },
                {
                    "stave_id": "stave-001",
                    "name": "Order Amount Range",
                    "check_type": "range_check",
                    "config": {
                        "table": "orders",
                        "column": "amount",
                        "min": 0,
                        "max": 10000
                    },
                    "is_active": True
                }
            ]
        }
    )
    
    @field_validator('check_type')
    @classmethod
    def validate_check_type(cls, v: str) -> str:
        """Validate that the check type is supported."""
        v_lower = v.lower()
        if v_lower not in SUPPORTED_CHECK_TYPES:
            raise ValueError(
                f"Unsupported check type: '{v}'. "
                f"Supported types: {', '.join(SUPPORTED_CHECK_TYPES)}"
            )
        return v_lower
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that config is not empty."""
        if not v:
            raise ValueError(
                "config cannot be empty. "
                "Provide configuration parameters for the check."
            )
        return v
    
    @field_validator('severity_config')
    @classmethod
    def validate_severity_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate severity configuration format."""
        if not v:
            return v
        
        # Validate severity condition keys
        valid_keys = {"warn", "fail", "pass", "dissonance", "cacophony", "harmony"}
        for key in v.keys():
            if key not in valid_keys:
                raise ValueError(
                    f"Invalid severity config key: '{key}'. "
                    f"Valid keys: {', '.join(valid_keys)}"
                )
        
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()
    
    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: str | None) -> str | None:
        """Validate cron expression format if provided."""
        if v is None:
            return v
        
        v = v.strip()
        
        # Check for common cron shorthands
        shorthands = ['@yearly', '@annually', '@monthly', '@weekly', '@daily', '@hourly', '@reboot']
        if v.startswith('@'):
            if v.lower() not in shorthands:
                raise ValueError(
                    f"Invalid cron shorthand: '{v}'. "
                    f"Supported: {', '.join(shorthands)}"
                )
            return v.lower()
        
        # Basic cron validation (5 or 6 fields separated by spaces)
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError(
                f"Invalid cron expression: '{v}'. Must have 5 or 6 fields. "
                "Example: '0 * * * *' (hourly), '0 0 * * *' (daily)"
            )
        
        return v
    
    def __repr__(self) -> str:
        """Pretty representation for debugging."""
        return (
            f"Clef(name='{self.name}', "
            f"type='{self.check_type}', "
            f"stave='{self.stave_id}', "
            f"active={self.is_active})"
        )
    
    @property
    def level(self) -> int:
        """Get the level number for this check type (per TDD specification)."""
        return CHECK_LEVEL_MAPPING.get(self.check_type, 4)
    
    @property
    def level_description(self) -> str:
        """Get a description of this check's level (per TDD specification)."""
        level_descriptions = {
            1: "Declarative Checks",
            2: "Intelligent Checks", 
            3: "Advanced Declarative Checks",
            4: "Custom Code"
        }
        return level_descriptions.get(self.level, "Unknown")
    
    @property
    def tier(self) -> int:
        """Legacy property for backward compatibility."""
        return self.level
    
    @property
    def tier_description(self) -> str:
        """Legacy property for backward compatibility."""
        return self.level_description
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "🟢 Active" if self.is_active else "🔴 Inactive"
        schedule_str = f", scheduled: {self.schedule}" if self.schedule else ""
        level_str = f" (Level {self.level}: {self.level_description})"
        return f"{status} {self.name} ({self.check_type}{level_str}{schedule_str})"
