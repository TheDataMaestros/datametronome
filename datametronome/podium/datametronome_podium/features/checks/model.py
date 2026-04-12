"""Check domain model, DB row DTO, and severity types."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Check(BaseModel):
    """Minimal DB row DTO — fields map 1:1 to the checks table columns."""

    id: str
    stave_id: str
    clef_id: str
    check_type: str
    status: str
    message: str | None = None
    details: str | None = None  # JSON string
    timestamp: str
    execution_time: float | None = None
    anomalies_count: int = 0
    severity: str = "medium"


class CheckRun(BaseModel):
    """Legacy domain model for check execution tracking.

    Preserved for backward compatibility with services and tests that were
    written before the Check DTO was introduced.
    """

    id: int | None = None
    name: str = "default_check_run"
    stave_id: int
    clef_id: int
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    parameters: dict = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Severity types (musical metaphor: Harmony / Dissonance / Cacophony)
# ---------------------------------------------------------------------------


class SeverityLevel(Enum):
    """Three-tier severity classification for data quality results."""

    HARMONY = "harmony"
    DISSONANCE = "dissonance"
    CACOPHONY = "cacophony"

    def __str__(self) -> str:
        icons = {
            SeverityLevel.HARMONY: "✅",
            SeverityLevel.DISSONANCE: "⚠️",
            SeverityLevel.CACOPHONY: "❌",
        }
        return f"{icons[self]} {self.value.title()}"

    @property
    def icon(self) -> str:
        icons = {
            SeverityLevel.HARMONY: "✅",
            SeverityLevel.DISSONANCE: "⚠️",
            SeverityLevel.CACOPHONY: "❌",
        }
        return icons[self]

    @property
    def description(self) -> str:
        descriptions = {
            SeverityLevel.HARMONY: "All clear - data is healthy and behaving as expected",
            SeverityLevel.DISSONANCE: "Warning - non-critical issue detected, investigation recommended",
            SeverityLevel.CACOPHONY: "Critical error - severe, business-impacting issue requiring immediate attention",
        }
        return descriptions[self]

    @property
    def priority(self) -> int:
        priorities = {
            SeverityLevel.CACOPHONY: 3,
            SeverityLevel.DISSONANCE: 2,
            SeverityLevel.HARMONY: 1,
        }
        return priorities[self]


@dataclass
class SeverityThreshold:
    """Configurable thresholds that map numeric values to SeverityLevel."""

    harmony_condition: Optional[str] = None
    dissonance_condition: Optional[str] = None  # warn
    cacophony_condition: Optional[str] = None  # fail

    def evaluate(
        self, value: float, context: Optional[Dict[str, Any]] = None
    ) -> SeverityLevel:
        # Cacophony checked first (highest priority)
        if self.cacophony_condition and self._evaluate_condition(
            value, self.cacophony_condition
        ):
            return SeverityLevel.CACOPHONY
        if self.dissonance_condition and self._evaluate_condition(
            value, self.dissonance_condition
        ):
            return SeverityLevel.DISSONANCE
        return SeverityLevel.HARMONY

    def _evaluate_condition(self, value: float, condition: str) -> bool:
        condition = condition.strip()

        def _parse_threshold(s: str) -> float:
            s = s.strip()
            if s.endswith("%"):
                t = float(s[:-1].strip())
                return t / 100.0 if value <= 1.0 else t
            return float(s)

        if condition.startswith("<="):
            return value <= _parse_threshold(condition[2:])
        if condition.startswith(">="):
            return value >= _parse_threshold(condition[2:])
        if condition.startswith("<"):
            return value < _parse_threshold(condition[1:])
        if condition.startswith(">"):
            return value > _parse_threshold(condition[1:])
        if condition.startswith("=="):
            return value == _parse_threshold(condition[2:])
        if condition.startswith("!="):
            return value != _parse_threshold(condition[2:])
        if "=" in condition and not any(op in condition for op in ["<", ">", "!"]):
            return value == _parse_threshold(condition.split("=")[1])
        try:
            return value == _parse_threshold(condition)
        except ValueError:
            raise ValueError(f"Invalid condition format: {condition}")


class SeverityConfig:
    """Default severity threshold configurations for common check types."""

    DEFAULT_THRESHOLDS: Dict[str, SeverityThreshold] = {
        "row_count": SeverityThreshold(
            dissonance_condition="> 50000",
            cacophony_condition="< 1000",
        ),
        "null_percentage": SeverityThreshold(
            dissonance_condition="> 5%",
            cacophony_condition="> 20%",
        ),
        "uniqueness": SeverityThreshold(
            dissonance_condition="> 0",
            cacophony_condition="> 10",
        ),
        "range_violations": SeverityThreshold(
            dissonance_condition="> 1%",
            cacophony_condition="> 10%",
        ),
        "pattern_violations": SeverityThreshold(
            dissonance_condition="> 5%",
            cacophony_condition="> 25%",
        ),
    }

    @classmethod
    def get_threshold_for_check_type(cls, check_type: str) -> SeverityThreshold:
        return cls.DEFAULT_THRESHOLDS.get(check_type, SeverityThreshold())

    @classmethod
    def create_custom_threshold(
        cls,
        dissonance_condition: Optional[str] = None,
        cacophony_condition: Optional[str] = None,
        harmony_condition: Optional[str] = None,
    ) -> SeverityThreshold:
        return SeverityThreshold(
            dissonance_condition=dissonance_condition,
            cacophony_condition=cacophony_condition,
            harmony_condition=harmony_condition,
        )

    @classmethod
    def parse_from_yaml_config(cls, config: Dict[str, Any]) -> SeverityThreshold:
        return SeverityThreshold(
            dissonance_condition=config.get("warn"),
            cacophony_condition=config.get("fail"),
            harmony_condition=config.get("pass"),
        )


def evaluate_severity(
    value: float,
    dissonance_condition: Optional[str] = None,
    cacophony_condition: Optional[str] = None,
    harmony_condition: Optional[str] = None,
) -> SeverityLevel:
    """Evaluate a value against severity conditions without creating a threshold object."""
    threshold = SeverityThreshold(
        dissonance_condition=dissonance_condition,
        cacophony_condition=cacophony_condition,
        harmony_condition=harmony_condition,
    )
    return threshold.evaluate(value)
