"""
Severity Levels - The foundational classification system for data health.

This module defines the three-tier severity system that classifies the health
of any Stave after its checks have run. It provides immediate, intuitive
understanding of data quality issues.

The Musical Metaphor:
- Harmony (✅) = All clear, data is healthy
- Dissonance (⚠️) = Warning, something is off-key but not critical
- Cacophony (❌) = Critical error, immediate attention required
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class SeverityLevel(Enum):
    """
    The three-tier severity system for data quality classification.
    
    This provides an immediate, intuitive understanding of the seriousness
    of any data quality issue.
    """
    
    HARMONY = "harmony"
    DISSONANCE = "dissonance" 
    CACOPHONY = "cacophony"
    
    def __str__(self) -> str:
        """String representation with icon."""
        icons = {
            SeverityLevel.HARMONY: "✅",
            SeverityLevel.DISSONANCE: "⚠️",
            SeverityLevel.CACOPHONY: "❌"
        }
        return f"{icons[self]} {self.value.title()}"
    
    @property
    def icon(self) -> str:
        """Get the icon for this severity level."""
        icons = {
            SeverityLevel.HARMONY: "✅",
            SeverityLevel.DISSONANCE: "⚠️",
            SeverityLevel.CACOPHONY: "❌"
        }
        return icons[self]
    
    @property
    def description(self) -> str:
        """Get a description of this severity level."""
        descriptions = {
            SeverityLevel.HARMONY: "All clear - data is healthy and behaving as expected",
            SeverityLevel.DISSONANCE: "Warning - non-critical issue detected, investigation recommended",
            SeverityLevel.CACOPHONY: "Critical error - severe, business-impacting issue requiring immediate attention"
        }
        return descriptions[self]
    
    @property
    def priority(self) -> int:
        """Get priority level (higher = more urgent)."""
        priorities = {
            SeverityLevel.CACOPHONY: 3,  # Highest priority
            SeverityLevel.DISSONANCE: 2,  # Medium priority
            SeverityLevel.HARMONY: 1      # Lowest priority
        }
        return priorities[self]


@dataclass
class SeverityThreshold:
    """
    Defines thresholds for when to trigger different severity levels.
    
    This allows users to configure their checks to trigger different
    severity levels based on their business requirements.
    """
    
    harmony_condition: Optional[str] = None
    dissonance_condition: Optional[str] = None  # warn
    cacophony_condition: Optional[str] = None   # fail
    
    def evaluate(self, value: float, context: Dict[str, Any] = None) -> SeverityLevel:
        """
        Evaluate a value against the configured thresholds.
        
        Args:
            value: The value to evaluate
            context: Additional context for evaluation
            
        Returns:
            The appropriate severity level
            
        Example:
            >>> threshold = SeverityThreshold(
            ...     dissonance_condition="> 5000",
            ...     cacophony_condition="< 1000"
            ... )
            >>> threshold.evaluate(1500)  # Returns CACOPHONY
            >>> threshold.evaluate(3000)  # Returns HARMONY
            >>> threshold.evaluate(6000)  # Returns DISSONANCE
        """
        # Check cacophony first (highest priority)
        if self.cacophony_condition and self._evaluate_condition(value, self.cacophony_condition):
            return SeverityLevel.CACOPHONY
        
        # Check dissonance second
        if self.dissonance_condition and self._evaluate_condition(value, self.dissonance_condition):
            return SeverityLevel.DISSONANCE
        
        # Default to harmony if no conditions match
        return SeverityLevel.HARMONY
    
    def _evaluate_condition(self, value: float, condition: str) -> bool:
        """Evaluate a single condition string against a value."""
        condition = condition.strip()
        
        # Parse different condition formats
        if condition.startswith("<="):
            threshold_str = condition[2:].strip()
            if threshold_str.endswith('%'):
                threshold = float(threshold_str[:-1].strip())
                if value <= 1.0:
                    threshold = threshold / 100.0
            else:
                threshold = float(threshold_str)
            return value <= threshold
        elif condition.startswith(">="):
            threshold_str = condition[2:].strip()
            if threshold_str.endswith('%'):
                threshold = float(threshold_str[:-1].strip())
                if value <= 1.0:
                    threshold = threshold / 100.0
            else:
                threshold = float(threshold_str)
            return value >= threshold
        elif condition.startswith("<"):
            threshold_str = condition[1:].strip()
            if threshold_str.endswith('%'):
                threshold = float(threshold_str[:-1].strip())
                if value <= 1.0:
                    threshold = threshold / 100.0
            else:
                threshold = float(threshold_str)
            return value < threshold
        elif condition.startswith(">"):
            threshold_str = condition[1:].strip()
            if threshold_str.endswith('%'):
                threshold = float(threshold_str[:-1].strip())
                if value <= 1.0:
                    threshold = threshold / 100.0
            else:
                threshold = float(threshold_str)
            return value > threshold
        elif condition.startswith("=="):
            threshold_str = condition[2:].strip()
            if threshold_str.endswith('%'):
                threshold = float(threshold_str[:-1].strip())
                if value <= 1.0:
                    threshold = threshold / 100.0
            else:
                threshold = float(threshold_str)
            return value == threshold
        elif condition.startswith("!="):
            threshold_str = condition[2:].strip()
            if threshold_str.endswith('%'):
                threshold = float(threshold_str[:-1].strip())
                if value <= 1.0:
                    threshold = threshold / 100.0
            else:
                threshold = float(threshold_str)
            return value != threshold
        elif "=" in condition and not any(op in condition for op in ["<", ">", "!"]):
            threshold_part = condition.split("=")[1].strip()
            if threshold_part.endswith('%'):
                threshold = float(threshold_part[:-1].strip())
                if value <= 1.0:
                    threshold = threshold / 100.0
            else:
                threshold = float(threshold_part)
            return value == threshold
        else:
            # Default to equality
            try:
                if condition.endswith('%'):
                    threshold = float(condition[:-1].strip())
                    if value <= 1.0:
                        threshold = threshold / 100.0
                else:
                    threshold = float(condition)
                return value == threshold
            except ValueError:
                raise ValueError(f"Invalid condition format: {condition}")
    
    def __str__(self) -> str:
        """String representation of the threshold configuration."""
        parts = []
        if self.harmony_condition:
            parts.append(f"Harmony: {self.harmony_condition}")
        if self.dissonance_condition:
            parts.append(f"Dissonance: {self.dissonance_condition}")
        if self.cacophony_condition:
            parts.append(f"Cacophony: {self.cacophony_condition}")
        
        return " | ".join(parts) if parts else "Default (Harmony)"


class SeverityConfig:
    """
    Configuration for severity thresholds across different check types.
    
    This provides default configurations and validation for different
    types of data quality checks.
    """
    
    # Default thresholds for common check types
    DEFAULT_THRESHOLDS = {
        "row_count": SeverityThreshold(
            dissonance_condition="> 50000",  # Too many rows (warning)
            cacophony_condition="< 1000"     # Too few rows (critical)
        ),
        "null_percentage": SeverityThreshold(
            dissonance_condition="> 5%",     # Too many nulls (warning)
            cacophony_condition="> 20%"      # Way too many nulls (critical)
        ),
        "uniqueness": SeverityThreshold(
            dissonance_condition="> 0",      # Any duplicates (warning)
            cacophony_condition="> 10"       # Many duplicates (critical)
        ),
        "range_violations": SeverityThreshold(
            dissonance_condition="> 1%",     # Some out of range (warning)
            cacophony_condition="> 10%"      # Many out of range (critical)
        ),
        "pattern_violations": SeverityThreshold(
            dissonance_condition="> 5%",     # Some pattern violations (warning)
            cacophony_condition="> 25%"      # Many pattern violations (critical)
        )
    }
    
    @classmethod
    def get_threshold_for_check_type(cls, check_type: str) -> SeverityThreshold:
        """Get default severity threshold for a check type."""
        return cls.DEFAULT_THRESHOLDS.get(check_type, SeverityThreshold())
    
    @classmethod
    def create_custom_threshold(
        cls,
        dissonance_condition: str = None,
        cacophony_condition: str = None,
        harmony_condition: str = None
    ) -> SeverityThreshold:
        """Create a custom severity threshold."""
        return SeverityThreshold(
            dissonance_condition=dissonance_condition,
            cacophony_condition=cacophony_condition,
            harmony_condition=harmony_condition
        )
    
    @classmethod
    def parse_from_yaml_config(cls, config: Dict[str, Any]) -> SeverityThreshold:
        """
        Parse severity configuration from YAML config.
        
        Args:
            config: Dictionary with 'warn' and/or 'fail' keys
            
        Example:
            >>> config = {"warn": "> 5000", "fail": "< 1000"}
            >>> threshold = SeverityConfig.parse_from_yaml_config(config)
        """
        return SeverityThreshold(
            dissonance_condition=config.get("warn"),
            cacophony_condition=config.get("fail"),
            harmony_condition=config.get("pass")
        )


# Convenience functions
def evaluate_severity(
    value: float,
    dissonance_condition: str = None,
    cacophony_condition: str = None,
    harmony_condition: str = None
) -> SeverityLevel:
    """
    Quick function to evaluate severity without creating a threshold object.
    
    Args:
        value: Value to evaluate
        dissonance_condition: Warning condition (e.g., "> 5000")
        cacophony_condition: Failure condition (e.g., "< 1000")
        harmony_condition: Success condition (e.g., "== 0")
        
    Returns:
        SeverityLevel
        
    Example:
        >>> severity = evaluate_severity(
        ...     value=1500,
        ...     dissonance_condition="> 5000",
        ...     cacophony_condition="< 1000"
        ... )
        >>> print(severity)  # ❌ Cacophony
    """
    threshold = SeverityThreshold(
        dissonance_condition=dissonance_condition,
        cacophony_condition=cacophony_condition,
        harmony_condition=harmony_condition
    )
    return threshold.evaluate(value)


def get_severity_icon(severity: SeverityLevel) -> str:
    """Get the icon for a severity level."""
    return severity.icon


def get_severity_description(severity: SeverityLevel) -> str:
    """Get the description for a severity level."""
    return severity.description


def compare_severities(severity1: SeverityLevel, severity2: SeverityLevel) -> int:
    """
    Compare two severity levels.
    
    Returns:
        -1 if severity1 < severity2 (lower priority)
         0 if severity1 == severity2 (same priority)
         1 if severity1 > severity2 (higher priority)
    """
    if severity1.priority < severity2.priority:
        return -1
    elif severity1.priority > severity2.priority:
        return 1
    else:
        return 0


def get_worst_severity(severities: list[SeverityLevel]) -> SeverityLevel:
    """Get the worst (highest priority) severity from a list."""
    if not severities:
        return SeverityLevel.HARMONY
    
    return max(severities, key=lambda s: s.priority)
