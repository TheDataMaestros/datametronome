"""Clef domain model and DB row DTO."""
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Check types organised by TDD levels
LEVEL_1_CHECKS = [
    "row_count",
    "freshness",
    "column_values",
]

LEVEL_2_CHECKS = [
    "forecast",
    "data_profile_drift",
]

LEVEL_3_CHECKS = [
    "lookup_validation",
]

LEVEL_4_CHECKS = [
    "python",
]

SUPPORTED_CHECK_TYPES = (
    LEVEL_1_CHECKS + LEVEL_2_CHECKS + LEVEL_3_CHECKS + LEVEL_4_CHECKS
)

CHECK_LEVEL_MAPPING = {
    **{check: 1 for check in LEVEL_1_CHECKS},
    **{check: 2 for check in LEVEL_2_CHECKS},
    **{check: 3 for check in LEVEL_3_CHECKS},
    **{check: 4 for check in LEVEL_4_CHECKS},
}

LEGACY_CHECK_MAPPING = {
    "volume_check": "row_count",
    "freshness_check": "freshness",
    "null_check": "column_values",
    "range_check": "column_values",
    "pattern_check": "column_values",
    "uniqueness_check": "column_values",
    "drift_detection": "data_profile_drift",
    "custom_python": "python",
}


class ClefRow(BaseModel):
    """Minimal DB row DTO — fields map 1:1 to the clefs table columns.

    config is stored as a JSON string in the DB.
    """

    id: str
    stave_id: str
    name: str
    description: str | None = None
    check_type: str
    config: str  # JSON string
    warn: str | None = None
    fail: str | None = None
    retry_config: str | None = None
    schedule: str | None = None
    is_active: bool = True
    created_at: str
    updated_at: str


class Clef(BaseModel):
    """Rich domain model for a Clef (data quality check definition).

    Used by the service layer.  config is a dict here; services use
    serialize_clef() from stave_service.py to convert to ClefRow for persisting.
    """

    id: str = Field(default="")
    stave_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    check_type: str = Field(
        ...,
        description=f"Type of check. Supported: {', '.join(SUPPORTED_CHECK_TYPES)}",
    )
    config: dict[str, Any] = Field(default_factory=dict)
    warn: str | None = None
    fail: str | None = None
    severity_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Legacy severity configuration (deprecated, use warn/fail instead)",
    )
    schedule: str | None = None
    retry_config: dict[str, Any] | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("check_type")
    @classmethod
    def validate_check_type(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in SUPPORTED_CHECK_TYPES:
            raise ValueError(
                f"Unsupported check type: '{v}'. "
                f"Supported types: {', '.join(SUPPORTED_CHECK_TYPES)}"
            )
        return v_lower

    @field_validator("config")
    @classmethod
    def validate_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v:
            raise ValueError(
                "config cannot be empty. "
                "Provide configuration parameters for the check."
            )
        return v

    @field_validator("severity_config")
    @classmethod
    def validate_severity_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v:
            return v
        valid_keys = {"warn", "fail", "pass", "dissonance", "cacophony", "harmony"}
        for key in v.keys():
            if key not in valid_keys:
                raise ValueError(
                    f"Invalid severity config key: '{key}'. "
                    f"Valid keys: {', '.join(valid_keys)}"
                )
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @model_validator(mode="after")
    def generate_id_if_missing(self):
        if not self.id:
            import uuid

            name_slug = self.name.lower().replace(" ", "-")[:30]
            self.id = f"clef-{self.check_type}-{name_slug}-{str(uuid.uuid4())[:8]}"
        return self

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        shorthands = [
            "@yearly", "@annually", "@monthly", "@weekly",
            "@daily", "@hourly", "@reboot",
        ]
        if v.startswith("@"):
            if v.lower() not in shorthands:
                raise ValueError(
                    f"Invalid cron shorthand: '{v}'. "
                    f"Supported: {', '.join(shorthands)}"
                )
            return v.lower()
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError(
                f"Invalid cron expression: '{v}'. Must have 5 or 6 fields."
            )
        return v

    @property
    def level(self) -> int:
        return CHECK_LEVEL_MAPPING.get(self.check_type, 4)

    @property
    def level_description(self) -> str:
        level_descriptions = {
            1: "Declarative Checks",
            2: "Intelligent Checks",
            3: "Advanced Declarative Checks",
            4: "Custom Code",
        }
        return level_descriptions.get(self.level, "Unknown")

    @property
    def tier(self) -> int:
        """Legacy alias for level."""
        return self.level

    @property
    def tier_description(self) -> str:
        """Legacy alias for level_description."""
        return self.level_description
