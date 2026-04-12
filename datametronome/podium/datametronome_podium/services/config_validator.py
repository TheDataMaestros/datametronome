"""
Configuration Validator - Detects dissonance and cacophony in stave configurations.

This module analyzes stave and clef configurations to detect:
- Conflicts between configurations
- Inconsistencies in data types or formats
- Missing dependencies or references
- Logical contradictions
- Resource conflicts

Think of it as a "conductor" that ensures all the "musical instruments" (staves)
are in harmony rather than creating cacophony.
"""

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

from datametronome_podium.features.clefs.model import SUPPORTED_CHECK_TYPES, Clef
from datametronome_podium.features.staves.model import SUPPORTED_DATA_SOURCES, Stave


class ConfigurationIssue:
    """Represents a configuration issue or conflict."""

    def __init__(
        self,
        severity: str,
        issue_type: str,
        message: str,
        affected_items: list[str] | None = None,
        suggestion: str | None = None,
    ):
        self.severity = severity  # "error", "warning", "info"
        self.issue_type = (
            issue_type  # "conflict", "missing", "inconsistent", "deprecated"
        )
        self.message = message
        self.affected_items = affected_items or []
        self.suggestion = suggestion
        self.timestamp = datetime.now(timezone.utc)

    def __str__(self) -> str:
        severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
            self.severity, "🔍"
        )

        items_str = (
            f" (affects: {', '.join(self.affected_items)})"
            if self.affected_items
            else ""
        )
        suggestion_str = (
            f"\n   💡 Suggestion: {self.suggestion}" if self.suggestion else ""
        )

        return f"{severity_icon} {self.issue_type.upper()}: {self.message}{items_str}{suggestion_str}"


class ConfigurationValidator:
    """
    Validates stave and clef configurations for conflicts and inconsistencies.

    This validator acts like a musical conductor, ensuring all configurations
    work together harmoniously without creating dissonance or cacophony.
    """

    def __init__(self):
        self.issues: List[ConfigurationIssue] = []
        self.staves_by_id: Dict[str, Stave] = {}
        self.clefs_by_id: Dict[str, Clef] = {}
        self.clefs_by_stave: Dict[str, List[Clef]] = defaultdict(list)

    def validate_configuration(
        self, staves: List[Stave], clefs: List[Clef]
    ) -> Dict[str, Any]:
        """
        Validate a complete configuration for conflicts and issues.

        Args:
            staves: List of staves to validate
            clefs: List of clefs to validate

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "issues": [ConfigurationIssue],
                "summary": str,
                "recommendations": [str]
            }
        """
        self.issues = []
        self.staves_by_id = {s.id: s for s in staves}
        self.clefs_by_id = {c.id: c for c in clefs}
        self.clefs_by_stave = defaultdict(list)

        for clef in clefs:
            self.clefs_by_stave[clef.stave_id].append(clef)

        # Run all validation checks
        self._check_missing_references()
        self._check_duplicate_ids()
        self._check_naming_conflicts()
        self._check_connection_conflicts()
        self._check_schedule_conflicts()
        self._check_data_type_inconsistencies()
        self._check_check_configuration_conflicts()
        self._check_resource_conflicts()
        self._check_deprecated_patterns()
        self._check_performance_issues()

        # Generate summary
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        info_count = sum(1 for i in self.issues if i.severity == "info")

        valid = error_count == 0

        summary = f"Configuration {'✅ VALID' if valid else '❌ INVALID'}: "
        summary += f"{error_count} errors, {warning_count} warnings, {info_count} info"

        recommendations = self._generate_recommendations()

        return {
            "valid": valid,
            "issues": self.issues,
            "summary": summary,
            "recommendations": recommendations,
            "stats": {
                "staves": len(staves),
                "clefs": len(clefs),
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count,
            },
        }

    def _check_missing_references(self):
        """Check for missing stave references in clefs."""
        for clef in self.clefs_by_id.values():
            if clef.stave_id not in self.staves_by_id:
                self.issues.append(
                    ConfigurationIssue(
                        severity="error",
                        issue_type="missing",
                        message=f"Clef '{clef.name}' references non-existent stave_id: {clef.stave_id}",
                        affected_items=[clef.name],
                        suggestion=f"Either create a stave with id '{clef.stave_id}' or update the clef's stave_id",
                    )
                )

    def _check_duplicate_ids(self):
        """Check for duplicate IDs across staves and clefs."""
        all_ids = []
        for stave in self.staves_by_id.values():
            all_ids.append((stave.id, f"stave '{stave.name}'"))
        for clef in self.clefs_by_id.values():
            all_ids.append((clef.id, f"clef '{clef.name}'"))

        id_counts = defaultdict(list)
        for id_val, name in all_ids:
            id_counts[id_val].append(name)

        for id_val, names in id_counts.items():
            if len(names) > 1:
                self.issues.append(
                    ConfigurationIssue(
                        severity="error",
                        issue_type="conflict",
                        message=f"Duplicate ID '{id_val}' found",
                        affected_items=names,
                        suggestion="Ensure all staves and clefs have unique IDs",
                    )
                )

    def _check_naming_conflicts(self):
        """Check for naming conflicts that might cause confusion."""
        # Check for duplicate stave names
        stave_names = defaultdict(list)
        for stave in self.staves_by_id.values():
            stave_names[stave.name.lower()].append(stave.name)

        for name_key, names in stave_names.items():
            if len(names) > 1:
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="conflict",
                        message=f"Similar stave names found: {', '.join(names)}",
                        affected_items=names,
                        suggestion="Use more distinctive names to avoid confusion",
                    )
                )

        # Check for duplicate clef names within the same stave
        for stave_id, clefs in self.clefs_by_stave.items():
            clef_names = defaultdict(list)
            for clef in clefs:
                clef_names[clef.name.lower()].append(clef.name)

            for name_key, names in clef_names.items():
                if len(names) > 1:
                    stave_name = self.staves_by_id[stave_id].name
                    self.issues.append(
                        ConfigurationIssue(
                            severity="warning",
                            issue_type="conflict",
                            message=f"Duplicate clef names in stave '{stave_name}': {', '.join(names)}",
                            affected_items=[f"{stave_name}: {name}" for name in names],
                            suggestion="Use unique names for clefs within each stave",
                        )
                    )

    def _check_connection_conflicts(self):
        """Check for conflicting connection configurations."""
        # Group staves by connection type
        by_type = defaultdict(list)
        for stave in self.staves_by_id.values():
            by_type[stave.data_source_type].append(stave)

        # Check for conflicting connection configs
        for data_type, staves in by_type.items():
            if data_type == "postgres":
                self._check_postgres_conflicts(staves)
            elif data_type == "mysql":
                self._check_mysql_conflicts(staves)
            elif data_type == "redis":
                self._check_redis_conflicts(staves)

    def _check_postgres_conflicts(self, staves: List[Stave]):
        """Check for PostgreSQL-specific conflicts."""
        # Check for same host/port/database combinations
        connections = defaultdict(list)
        for stave in staves:
            config = stave.connection_config
            key = (config.get("host"), config.get("port", 5432), config.get("database"))
            connections[key].append(stave)

        for (host, port, db), staves_list in connections.items():
            if len(staves_list) > 1 and all(v is not None for v in (host, port, db)):
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="conflict",
                        message=f"Multiple staves connect to same PostgreSQL database: {host}:{port}/{db}",
                        affected_items=[s.name for s in staves_list],
                        suggestion="Consider if you need separate staves or if they should be merged",
                    )
                )

    def _check_mysql_conflicts(self, staves: List[Stave]):
        """Check for MySQL-specific conflicts."""
        # Similar logic for MySQL
        connections = defaultdict(list)
        for stave in staves:
            config = stave.connection_config
            key = (config.get("host"), config.get("port", 3306), config.get("database"))
            connections[key].append(stave)

        for (host, port, db), staves_list in connections.items():
            if len(staves_list) > 1 and all(v is not None for v in (host, port, db)):
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="conflict",
                        message=f"Multiple staves connect to same MySQL database: {host}:{port}/{db}",
                        affected_items=[s.name for s in staves_list],
                        suggestion="Consider if you need separate staves or if they should be merged",
                    )
                )

    def _check_redis_conflicts(self, staves: List[Stave]):
        """Check for Redis-specific conflicts."""
        connections = defaultdict(list)
        for stave in staves:
            config = stave.connection_config
            key = (config.get("host"), config.get("port", 6379), config.get("db", 0))
            connections[key].append(stave)

        for (host, port, db), staves_list in connections.items():
            if len(staves_list) > 1 and all(v is not None for v in (host, port, db)):
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="conflict",
                        message=f"Multiple staves connect to same Redis instance: {host}:{port}/{db}",
                        affected_items=[s.name for s in staves_list],
                        suggestion="Consider if you need separate staves or if they should be merged",
                    )
                )

    def _check_schedule_conflicts(self):
        """Check for scheduling conflicts that might overload resources."""
        # Group clefs by schedule
        by_schedule = defaultdict(list)
        for clef in self.clefs_by_id.values():
            if clef.schedule:
                by_schedule[clef.schedule].append(clef)

        # Check for too many checks running at the same time
        for schedule, clefs in by_schedule.items():
            if len(clefs) > 10:  # Arbitrary threshold
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="conflict",
                        message=f"Many clefs scheduled for '{schedule}': {len(clefs)} checks",
                        affected_items=[c.name for c in clefs],
                        suggestion="Consider spreading checks across different schedules to avoid resource contention",
                    )
                )

        # Check for checks on the same stave with conflicting schedules
        for stave_id, clefs in self.clefs_by_stave.items():
            if len(clefs) > 5:  # If many checks on one stave
                schedules = [c.schedule for c in clefs if c.schedule]
                if (
                    len(set(schedules)) < len(schedules) * 0.3
                ):  # Too few unique schedules
                    stave_name = self.staves_by_id[stave_id].name
                    self.issues.append(
                        ConfigurationIssue(
                            severity="info",
                            issue_type="conflict",
                            message=f"Many clefs on stave '{stave_name}' have similar schedules",
                            affected_items=[f"{stave_name}: {c.name}" for c in clefs],
                            suggestion="Consider varying check schedules to reduce load spikes",
                        )
                    )

    def _check_data_type_inconsistencies(self):
        """Check for inconsistencies in data source types."""
        # Check if clefs expect certain data types but stave doesn't support it
        for clef in self.clefs_by_id.values():
            if clef.stave_id not in self.staves_by_id:
                continue  # Already caught in missing references

            stave = self.staves_by_id[clef.stave_id]

            # Check if clef type is appropriate for stave type
            if stave.data_source_type == "redis" and clef.check_type in [
                "null_check",
                "range_check",
            ]:
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="inconsistent",
                        message=f"Clef '{clef.name}' uses '{clef.check_type}' on Redis stave '{stave.name}'",
                        affected_items=[clef.name, stave.name],
                        suggestion="Redis checks should use volume_check or custom_sql instead",
                    )
                )

            if (
                stave.data_source_type == "sqlite"
                and clef.check_type == "freshness_check"
            ):
                self.issues.append(
                    ConfigurationIssue(
                        severity="info",
                        issue_type="inconsistent",
                        message=f"Freshness checks on SQLite may not be meaningful",
                        affected_items=[clef.name, stave.name],
                        suggestion="Consider if freshness_check is appropriate for SQLite databases",
                    )
                )

    def _check_check_configuration_conflicts(self):
        """Check for conflicts in check configurations."""
        for clef in self.clefs_by_id.values():
            if clef.check_type == "range_check":
                config = clef.config
                min_val = config.get("min")
                max_val = config.get("max")

                if min_val is not None and max_val is not None and min_val > max_val:
                    self.issues.append(
                        ConfigurationIssue(
                            severity="error",
                            issue_type="conflict",
                            message=f"Range check '{clef.name}' has min > max: {min_val} > {max_val}",
                            affected_items=[clef.name],
                            suggestion="Ensure min value is less than or equal to max value",
                        )
                    )

            elif clef.check_type == "volume_check":
                config = clef.config
                min_vol = config.get("expected_min")
                max_vol = config.get("expected_max")

                if min_vol is not None and max_vol is not None and min_vol > max_vol:
                    self.issues.append(
                        ConfigurationIssue(
                            severity="error",
                            issue_type="conflict",
                            message=f"Volume check '{clef.name}' has expected_min > expected_max: {min_vol} > {max_vol}",
                            affected_items=[clef.name],
                            suggestion="Ensure expected_min is less than or equal to expected_max",
                        )
                    )

            elif clef.check_type == "null_check":
                config = clef.config
                threshold = config.get("threshold")

                if threshold is not None and (threshold < 0 or threshold > 1):
                    self.issues.append(
                        ConfigurationIssue(
                            severity="error",
                            issue_type="conflict",
                            message=f"Null check '{clef.name}' has invalid threshold: {threshold} (should be 0-1)",
                            affected_items=[clef.name],
                            suggestion="Threshold should be between 0 and 1 (0 = no nulls, 1 = all nulls allowed)",
                        )
                    )

    def _check_resource_conflicts(self):
        """Check for potential resource conflicts."""
        # Check for too many connections to the same host
        host_connections = defaultdict(list)
        for stave in self.staves_by_id.values():
            if "host" in stave.connection_config:
                host = stave.connection_config["host"]
                host_connections[host].append(stave)

        for host, staves in host_connections.items():
            if len(staves) > 5:  # Arbitrary threshold
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="conflict",
                        message=f"Many staves connect to host '{host}': {len(staves)} connections",
                        affected_items=[s.name for s in staves],
                        suggestion="Consider connection pooling or fewer connections to avoid overwhelming the host",
                    )
                )

    def _check_deprecated_patterns(self):
        """Check for deprecated or problematic patterns."""
        for stave in self.staves_by_id.values():
            # Check for hardcoded passwords
            config = stave.connection_config
            for key, value in config.items():
                if (
                    "password" in key.lower()
                    and isinstance(value, str)
                    and not value.startswith("${")
                ):
                    self.issues.append(
                        ConfigurationIssue(
                            severity="warning",
                            issue_type="deprecated",
                            message=f"Stave '{stave.name}' has hardcoded password in {key}",
                            affected_items=[stave.name],
                            suggestion="Use environment variables like ${DB_PASSWORD} instead",
                        )
                    )

            # Check for localhost in production-like names
            if "localhost" in str(config.get("host", "")) and (
                "prod" in stave.name.lower() or "production" in stave.name.lower()
            ):
                self.issues.append(
                    ConfigurationIssue(
                        severity="warning",
                        issue_type="inconsistent",
                        message=f"Production stave '{stave.name}' uses localhost",
                        affected_items=[stave.name],
                        suggestion="Production staves should use remote hosts, not localhost",
                    )
                )

    def _check_performance_issues(self):
        """Check for potential performance issues."""
        # Check for too many checks on one stave
        for stave_id, clefs in self.clefs_by_stave.items():
            if len(clefs) > 20:  # Arbitrary threshold
                stave_name = self.staves_by_id[stave_id].name
                self.issues.append(
                    ConfigurationIssue(
                        severity="info",
                        issue_type="performance",
                        message=f"Stave '{stave_name}' has many clefs: {len(clefs)} checks",
                        affected_items=[stave_name],
                        suggestion="Consider if all checks are necessary or if some can be consolidated",
                    )
                )

        # Check for very frequent schedules
        frequent_schedules = []
        for clef in self.clefs_by_id.values():
            if clef.schedule and ("*/1" in clef.schedule or "@hourly" in clef.schedule):
                frequent_schedules.append(clef)

        if len(frequent_schedules) > 10:
            self.issues.append(
                ConfigurationIssue(
                    severity="warning",
                    issue_type="performance",
                    message=f"Many clefs run every hour or more frequently: {len(frequent_schedules)} checks",
                    affected_items=[c.name for c in frequent_schedules],
                    suggestion="Consider less frequent schedules for better performance",
                )
            )

    def _generate_recommendations(self) -> List[str]:
        """Generate general recommendations based on the configuration."""
        recommendations = []

        total_staves = len(self.staves_by_id)
        total_clefs = len(self.clefs_by_id)

        if total_staves == 0:
            recommendations.append(
                "No staves configured - consider adding data sources to monitor"
            )
        elif total_staves == 1:
            recommendations.append(
                "Single stave configuration - consider adding more data sources for comprehensive monitoring"
            )

        if total_clefs == 0:
            recommendations.append(
                "No clefs configured - add data quality checks to your staves"
            )
        elif total_clefs < total_staves * 2:
            recommendations.append(
                "Consider adding more data quality checks - aim for 2-5 checks per stave"
            )

        # Check for diversity in check types
        check_types = set(c.check_type for c in self.clefs_by_id.values())
        if len(check_types) < 3:
            recommendations.append(
                "Limited variety in check types - consider adding different types of data quality checks"
            )

        return recommendations


def validate_configuration(staves: List[Stave], clefs: List[Clef]) -> Dict[str, Any]:
    """
    Quick function to validate a configuration.

    Args:
        staves: List of staves to validate
        clefs: List of clefs to validate

    Returns:
        Validation results dict

    Example:
        >>> staves = [create_postgres_stave("DB", "localhost", "db", "user")]
        >>> clefs = [create_null_check("stave-1", "Email Check", "users", "email")]
        >>> result = validate_configuration(staves, clefs)
        >>> print(result["summary"])
    """
    validator = ConfigurationValidator()
    return validator.validate_configuration(staves, clefs)
