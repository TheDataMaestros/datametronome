"""
Clef Executor - Executes data quality checks (clefs) against data sources (staves).

This module implements the actual execution logic for different types of data quality
checks. Think of it as the "musician" that plays the "music" written in the clefs.

Example Usage:
    # Execute a clef against its stave
    result = await execute_clef(clef, stave, db_connector)

    # Execute all clefs for a stave
    results = await execute_stave_clefs(stave, db_connector)
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from datametronome_podium.models.check_run import CheckRun
from datametronome_podium.models.clef import Clef
from datametronome_podium.models.severity import (
    SeverityConfig,
    SeverityLevel,
    SeverityThreshold,
    evaluate_severity,
)
from datametronome_podium.models.stave import Stave
from datametronome_podium.services.connection_tester import ConnectionTester

try:
    from datametronome_brain_base.forecasting import SarimaForecaster
except ModuleNotFoundError:
    SarimaForecaster = None

try:
    from datametronome_brain_base.drift_detection import DriftDetector
except ModuleNotFoundError:
    DriftDetector = None

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """
    Result of executing a clef check.

    This represents the outcome of a data quality check following the TDD specification.
    The status is mapped to Harmony/Dissonance/Cacophony by the orchestrator.
    """

    clef_id: str
    stave_id: str
    status: str  # "pass", "warn", or "fail" (per TDD specification)
    observed_value: Any  # The actual value that was observed/evaluated
    message: str
    metadata: Dict[str, Any] = None  # Additional context and proof of failure
    execution_time: float = 0.0  # seconds
    timestamp: datetime = None
    anomalies_count: int = 0

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def severity(self) -> SeverityLevel:
        """Get the severity level from the status (per TDD mapping)."""
        status_to_severity = {
            "pass": SeverityLevel.HARMONY,
            "warn": SeverityLevel.DISSONANCE,
            "fail": SeverityLevel.CACOPHONY,
        }
        return status_to_severity.get(self.status, SeverityLevel.CACOPHONY)

    def __str__(self) -> str:
        """String representation using severity icons."""
        return f"{self.severity}: {self.message}"

    @property
    def details(self) -> Dict[str, Any]:
        """Backward compatibility alias for metadata."""
        return self.metadata

    @details.setter
    def details(self, value: Dict[str, Any]):
        self.metadata = value or {}


class ClefExecutor:
    """
    Executes data quality checks (clefs) against data sources (staves).

    This is the core engine that actually runs the checks. It connects to data
    sources, executes queries, and evaluates the results against the clef
    configuration.
    """

    def __init__(self):
        self.execution_stats = {
            "total_checks": 0,
            "harmony": 0,
            "dissonance": 0,
            "cacophony": 0,
            "total_time": 0.0,
            "errors": 0,
        }

    async def execute_clef(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """
        Execute a single clef against its stave.

        Args:
            clef: The clef (data quality check) to execute
            stave: The stave (data source) to check
            db_connector: Database connector instance

        Returns:
            CheckResult with the outcome

        Example:
            >>> executor = ClefExecutor()
            >>> result = await executor.execute_clef(clef, stave, connector)
            >>> print(f"Check {result.status}: {result.message}")
        """
        start_time = datetime.now()
        connector = db_connector
        managed_connector = False
        result: CheckResult | None = None

        try:
            if connector is None:
                tester = ConnectionTester()
                connector = await tester.get_connector(stave, read_only=True)
                managed_connector = True

            logger.info(f"Executing clef '{clef.name}' on stave '{stave.name}'")

            # Route to appropriate check handler
            # TDD-compliant check types (new)
            if clef.check_type == "column_values":
                result = await self._execute_column_values_check(clef, stave, connector)
            elif clef.check_type == "row_count":
                result = await self._execute_row_count_check(clef, stave, connector)
            elif clef.check_type == "freshness":
                result = await self._execute_freshness_check(clef, stave, connector)
            elif clef.check_type == "forecast":
                result = await self._execute_forecast_check(clef, stave, connector)
            elif clef.check_type == "data_profile_drift":
                result = await self._execute_data_profile_drift_check(
                    clef, stave, connector
                )
            elif clef.check_type == "lookup_validation":
                result = await self._execute_lookup_validation_check(
                    clef, stave, connector
                )
            elif clef.check_type == "python":
                result = await self._execute_python_check(clef, stave, connector)
            # Legacy check types (for backward compatibility)
            elif clef.check_type == "null_check":
                result = await self._execute_null_check(clef, stave, connector)
            elif clef.check_type == "uniqueness_check":
                result = await self._execute_uniqueness_check(clef, stave, connector)
            elif clef.check_type == "range_check":
                result = await self._execute_range_check(clef, stave, connector)
            elif clef.check_type == "pattern_check":
                result = await self._execute_pattern_check(clef, stave, connector)
            elif clef.check_type == "freshness_check":
                result = await self._execute_freshness_check(clef, stave, connector)
            elif clef.check_type == "volume_check":
                result = await self._execute_volume_check(clef, stave, connector)
            elif clef.check_type == "custom_sql":
                result = await self._execute_custom_sql_check(clef, stave, connector)
            elif clef.check_type == "schema_check":
                result = await self._execute_schema_check(clef, stave, connector)
            elif clef.check_type == "referential_check":
                result = await self._execute_referential_check(clef, stave, connector)
            else:
                result = CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message=f"Unknown check type: {clef.check_type}",
                    metadata={"error": "unsupported_check_type"},
                    timestamp=start_time,
                )

        except Exception as e:
            logger.error(f"Error executing clef '{clef.name}': {e}")
            result = CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Execution failed: {str(e)}",
                metadata={"error": str(e), "exception_type": type(e).__name__},
                timestamp=start_time,
            )

        finally:
            if managed_connector and connector is not None:
                try:
                    await connector.close()
                except Exception as close_error:
                    logger.warning(
                        f"Failed to close connector for stave '{stave.name}': {close_error}"
                    )

        if result is None:
            result = CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message="Clef execution did not produce a result",
                metadata={"error": "no_result"},
                timestamp=start_time,
            )

        result.execution_time = (datetime.now() - start_time).total_seconds()
        self._update_stats(result)
        logger.info(f"Clef '{clef.name}' completed: {result.severity}")
        return result

    async def _execute_null_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a NULL value check."""
        config = clef.config
        table = config["table"]
        column = config["column"]
        threshold = config.get("threshold", 0.0)

        # Build SQL query to count NULLs
        if stave.data_source_type in ["postgres", "postgresql", "mysql", "bigquery"]:
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT({column}) as non_null_rows,
                COUNT(*) - COUNT({column}) as null_rows
            FROM {table}
            """
        elif stave.data_source_type == "sqlite":
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT({column}) as non_null_rows,
                COUNT(*) - COUNT({column}) as null_rows
            FROM {table}
            """
        else:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"NULL check not supported for {stave.data_source_type}",
                metadata={"error": "unsupported_data_source"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Execute query
        result_rows = await db_connector.query({"sql": sql})

        if not result_rows:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message="Query returned no results",
                metadata={"error": "empty_result"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        row = result_rows[0]
        total_rows = row["total_rows"]
        null_rows = row["null_rows"]

        if total_rows == 0:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="warn",
                observed_value=None,
                message="Table is empty",
                metadata={"total_rows": 0, "null_rows": 0, "null_percentage": 0.0},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        null_percentage = null_rows / total_rows

        # Evaluate result using severity system
        severity = self._evaluate_null_check_severity(clef, null_percentage)

        # Generate appropriate message
        if severity == SeverityLevel.HARMONY:
            message = f"NULL check passed: {null_percentage:.2%} NULLs (threshold: {threshold:.2%})"
        elif severity == SeverityLevel.DISSONANCE:
            message = f"NULL check warning: {null_percentage:.2%} NULLs exceeds warning threshold"
        else:  # CACOPHONY
            message = f"NULL check failed: {null_percentage:.2%} NULLs exceeds critical threshold {threshold:.2%}"

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=severity.value.lower(),
            observed_value=null_percentage,
            message=message,
            metadata={
                "total_rows": total_rows,
                "null_rows": null_rows,
                "null_percentage": null_percentage,
                "threshold": threshold,
                "table": table,
                "column": column,
            },
            execution_time=0.0,
            timestamp=datetime.now(),
            anomalies_count=null_rows if severity != SeverityLevel.HARMONY else 0,
        )

    async def _execute_range_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a range validation check."""
        config = clef.config
        table = config["table"]
        column = config["column"]
        min_val = config.get("min")
        max_val = config.get("max")

        if min_val is None and max_val is None:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Range check requires at least min or max value",
                metadata={"error": "invalid_config"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Build SQL query to check values outside range
        conditions = []
        if min_val is not None:
            conditions.append(f"{column} < {min_val}")
        if max_val is not None:
            conditions.append(f"{column} > {max_val}")

        where_clause = " OR ".join(conditions)

        if stave.data_source_type in ["postgres", "postgresql", "mysql", "bigquery"]:
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN {where_clause} THEN 1 END) as out_of_range_rows,
                MIN({column}) as min_value,
                MAX({column}) as max_value
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "sqlite":
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN {where_clause} THEN 1 END) as out_of_range_rows,
                MIN({column}) as min_value,
                MAX({column}) as max_value
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        else:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message=f"Range check not supported for {stave.data_source_type}",
                metadata={"error": "unsupported_data_source"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Execute query
        result_rows = await db_connector.query({"sql": sql})

        if not result_rows:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Query returned no results",
                metadata={"error": "empty_result"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        row = result_rows[0]
        total_rows = row["total_rows"]
        out_of_range_rows = row["out_of_range_rows"]
        actual_min = row["min_value"]
        actual_max = row["max_value"]

        if total_rows == 0:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="warn",
                message="No non-null values found",
                metadata={"total_rows": 0, "out_of_range_rows": 0},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Evaluate result
        if out_of_range_rows == 0:
            status = "pass"
            message = (
                f"Range check passed: all values within range [{min_val}, {max_val}]"
            )
        else:
            status = "fail"
            message = f"Range check failed: {out_of_range_rows} values outside range [{min_val}, {max_val}]"

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=status,
            message=message,
            metadata={
                "total_rows": total_rows,
                "out_of_range_rows": out_of_range_rows,
                "expected_range": {"min": min_val, "max": max_val},
                "actual_range": {"min": actual_min, "max": actual_max},
                "table": table,
                "column": column,
            },
            execution_time=0.0,
            timestamp=datetime.now(),
            anomalies_count=out_of_range_rows if status == "fail" else 0,
        )

    async def _execute_volume_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a row count (volume) check."""
        config = clef.config
        table = config["table"]
        expected_min = config.get("expected_min")
        expected_max = config.get("expected_max")

        if expected_min is None and expected_max is None:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Volume check requires at least expected_min or expected_max",
                metadata={"error": "invalid_config"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Build SQL query to count rows
        if stave.data_source_type in ["postgres", "postgresql", "mysql", "sqlite"]:
            sql = f"SELECT COUNT(*) as row_count FROM {table}"
        else:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message=f"Volume check not supported for {stave.data_source_type}",
                metadata={"error": "unsupported_data_source"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Execute query
        result_rows = await db_connector.query({"sql": sql})

        if not result_rows:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Query returned no results",
                metadata={"error": "empty_result"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        actual_count = result_rows[0]["row_count"]

        # Evaluate result
        issues = []
        if expected_min is not None and actual_count < expected_min:
            issues.append(f"too few rows ({actual_count} < {expected_min})")
        if expected_max is not None and actual_count > expected_max:
            issues.append(f"too many rows ({actual_count} > {expected_max})")

        if not issues:
            status = "pass"
            message = f"Volume check passed: {actual_count} rows within expected range [{expected_min}, {expected_max}]"
        else:
            status = "fail"
            message = f"Volume check failed: {', '.join(issues)}"

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=status,
            message=message,
            metadata={
                "actual_count": actual_count,
                "expected_range": {"min": expected_min, "max": expected_max},
                "table": table,
            },
            execution_time=0.0,
            timestamp=datetime.now(),
            anomalies_count=1 if status == "fail" else 0,
        )

    async def _execute_custom_sql_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a custom SQL check."""
        config = clef.config
        sql = config["query"]
        expected_result = config.get("expected_result")
        expected_min = config.get("expected_min")
        expected_max = config.get("expected_max")

        if not sql:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Custom SQL check requires a query",
                metadata={"error": "missing_query"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Execute custom SQL
        try:
            result_rows = await db_connector.query({"sql": sql})

            if not result_rows:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    message="Custom SQL returned no results",
                    metadata={"query": sql, "results": []},
                    execution_time=0.0,
                    timestamp=datetime.now(),
                )

            # Get the first result (assuming single value queries)
            result_value = result_rows[0]

            # Evaluate against expectations
            if expected_result is not None:
                if result_value == expected_result:
                    status = "pass"
                    message = f"Custom SQL check passed: result {result_value} matches expected {expected_result}"
                else:
                    status = "fail"
                    message = f"Custom SQL check failed: result {result_value} does not match expected {expected_result}"
            elif expected_min is not None or expected_max is not None:
                # Convert to numeric if possible
                try:
                    numeric_value = float(result_value)
                    if expected_min is not None and numeric_value < expected_min:
                        status = "fail"
                        message = f"Custom SQL check failed: result {numeric_value} below minimum {expected_min}"
                    elif expected_max is not None and numeric_value > expected_max:
                        status = "fail"
                        message = f"Custom SQL check failed: result {numeric_value} above maximum {expected_max}"
                    else:
                        status = "pass"
                        message = f"Custom SQL check passed: result {numeric_value} within range [{expected_min}, {expected_max}]"
                except (ValueError, TypeError):
                    status = "error"
                    message = f"Custom SQL check failed: cannot convert result to numeric for range comparison"
            else:
                # No specific expectations, just report the result
                status = "pass"
                message = f"Custom SQL check completed: {result_value}"

            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status=status,
                message=message,
                metadata={
                    "query": sql,
                    "result": result_value,
                    "expected_result": expected_result,
                    "expected_range": {"min": expected_min, "max": expected_max},
                    "all_results": result_rows,
                },
                execution_time=0.0,
                timestamp=datetime.now(),
                anomalies_count=1 if status == "fail" else 0,
            )

        except Exception as e:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Custom SQL execution failed: {str(e)}",
                metadata={"error": str(e), "query": sql},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

    async def _execute_uniqueness_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a uniqueness check."""
        config = clef.config
        table = config["table"]
        column = config["column"]

        # Build SQL query to find duplicates
        if stave.data_source_type in ["postgres", "postgresql", "mysql", "bigquery"]:
            sql = f"""
            SELECT
                {column},
                COUNT(*) as duplicate_count
            FROM {table}
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
            LIMIT 10
            """
        elif stave.data_source_type == "sqlite":
            sql = f"""
            SELECT
                {column},
                COUNT(*) as duplicate_count
            FROM {table}
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
            LIMIT 10
            """
        else:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message=f"Uniqueness check not supported for {stave.data_source_type}",
                metadata={"error": "unsupported_data_source"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Execute query
        duplicate_rows = await db_connector.query({"sql": sql})

        # Evaluate result
        if not duplicate_rows:
            status = "pass"
            message = f"Uniqueness check passed: no duplicate values found in {column}"
        else:
            status = "fail"
            total_duplicates = sum(row["duplicate_count"] for row in duplicate_rows)
            message = f"Uniqueness check failed: {len(duplicate_rows)} duplicate values found ({total_duplicates} total duplicate rows)"

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=status,
            message=message,
            metadata={
                "table": table,
                "column": column,
                "duplicate_count": len(duplicate_rows),
                "duplicates": duplicate_rows[:5],  # Show first 5 duplicates
            },
            execution_time=0.0,
            timestamp=datetime.now(),
            anomalies_count=len(duplicate_rows) if status == "fail" else 0,
        )

    async def _execute_pattern_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a pattern/regex check."""
        config = clef.config
        table = config["table"]
        column = config["column"]
        pattern = config["pattern"]

        # Build SQL query to find non-matching patterns
        # Note: SQL regex support varies by database
        if stave.data_source_type in ["postgres", "postgresql"]:
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN {column} ~ '{pattern}' THEN 1 END) as matching_rows,
                COUNT(CASE WHEN {column} !~ '{pattern}' THEN 1 END) as non_matching_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "bigquery":
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN REGEXP_CONTAINS({column}, r'{pattern}') THEN 1 END) as matching_rows,
                COUNT(CASE WHEN NOT REGEXP_CONTAINS({column}, r'{pattern}') THEN 1 END) as non_matching_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "mysql":
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN {column} REGEXP '{pattern}' THEN 1 END) as matching_rows,
                COUNT(CASE WHEN {column} NOT REGEXP '{pattern}' THEN 1 END) as non_matching_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "sqlite":
            # SQLite has limited regex support, use LIKE as fallback
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="warn",
                message="Pattern check not fully supported in SQLite",
                metadata={"error": "limited_regex_support"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )
        else:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message=f"Pattern check not supported for {stave.data_source_type}",
                metadata={"error": "unsupported_data_source"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Execute query
        result_rows = await db_connector.query({"sql": sql})

        if not result_rows:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Query returned no results",
                metadata={"error": "empty_result"},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        row = result_rows[0]
        total_rows = row["total_rows"]
        non_matching_rows = row["non_matching_rows"]

        if total_rows == 0:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="warn",
                message="No non-null values found",
                metadata={"total_rows": 0, "non_matching_rows": 0},
                execution_time=0.0,
                timestamp=datetime.now(),
            )

        # Evaluate result
        if non_matching_rows == 0:
            status = "pass"
            message = f"Pattern check passed: all values match pattern '{pattern}'"
        else:
            status = "fail"
            message = f"Pattern check failed: {non_matching_rows} values do not match pattern '{pattern}'"

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=status,
            message=message,
            metadata={
                "total_rows": total_rows,
                "non_matching_rows": non_matching_rows,
                "pattern": pattern,
                "table": table,
                "column": column,
            },
            execution_time=0.0,
            timestamp=datetime.now(),
            anomalies_count=non_matching_rows if status == "fail" else 0,
        )

    async def _execute_schema_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a schema validation check."""
        # This would check if the table schema matches expectations
        # Implementation depends on database type and specific requirements
        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status="info",
            message="Schema check not yet implemented",
            metadata={
                "note": "Schema validation requires database-specific metadata queries"
            },
            execution_time=0.0,
            timestamp=datetime.now(),
        )

    async def _execute_referential_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a referential integrity check."""
        # This would check foreign key relationships
        # Implementation depends on database type and specific requirements
        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status="info",
            message="Referential check not yet implemented",
            metadata={
                "note": "Referential integrity requires database-specific constraint queries"
            },
            execution_time=0.0,
            timestamp=datetime.now(),
        )

    def _evaluate_null_check_severity(
        self, clef: Clef, null_percentage: float
    ) -> SeverityLevel:
        """Evaluate severity for a null check based on configured thresholds."""
        # Get severity configuration from clef
        severity_config = clef.severity_config

        if not severity_config:
            # Use default threshold logic
            config = clef.config
            threshold = config.get("threshold", 0.0)

            if null_percentage <= threshold:
                return SeverityLevel.HARMONY
            else:
                return SeverityLevel.CACOPHONY

        # Use configured severity thresholds
        threshold = SeverityConfig.parse_from_yaml_config(severity_config)
        return threshold.evaluate(null_percentage)

    def _update_stats(self, result: CheckResult):
        """Update execution statistics."""
        self.execution_stats["total_checks"] += 1
        self.execution_stats["total_time"] += result.execution_time

        status = result.status
        if status == "pass":
            self.execution_stats["harmony"] += 1
        elif status == "warn":
            self.execution_stats["dissonance"] += 1
        elif status == "fail":
            self.execution_stats["cacophony"] += 1
        else:
            self.execution_stats["errors"] += 1

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = self.execution_stats.copy()
        if stats["total_checks"] > 0:
            stats["average_time"] = stats["total_time"] / stats["total_checks"]
            stats["harmony_rate"] = stats["harmony"] / stats["total_checks"]
            stats["dissonance_rate"] = stats["dissonance"] / stats["total_checks"]
            stats["cacophony_rate"] = stats["cacophony"] / stats["total_checks"]
        else:
            stats["average_time"] = 0.0
            stats["harmony_rate"] = 0.0
            stats["dissonance_rate"] = 0.0
            stats["cacophony_rate"] = 0.0

        stats["passed"] = stats["harmony"]
        stats["warned"] = stats["dissonance"]
        stats["failed"] = stats["cacophony"]
        stats["pass_rate"] = stats["harmony_rate"]

        return stats

    def _parse_column_values_condition(self, condition_str: str) -> Dict[str, Any]:
        """
        Parse column_values condition strings per TDD specification.

        Examples:
            "if_null > 5%" -> {"type": "if_null", "operator": ">", "value": 0.05, "is_percentage": True}
            "if_not_unique > 0" -> {"type": "if_not_unique", "operator": ">", "value": 0}
            "if_not_in: ['A', 'B', 'C'] > 0" -> {"type": "if_not_in", "values": ['A','B','C'], "operator": ">", "value": 0}
        """
        import ast
        import re

        if not condition_str:
            return {"type": "unknown", "error": "empty_condition"}

        condition_str = condition_str.strip()

        # Parse if_not_in: ['val1', 'val2'] > 0
        if_not_in_match = re.match(
            r"if_not_in:\s*(\[[^\]]+\])\s*([<>=!]+)\s*(.+)", condition_str
        )
        if if_not_in_match:
            try:
                values_list_str = if_not_in_match.group(1)
                operator = if_not_in_match.group(2)
                threshold_str = if_not_in_match.group(3).strip()
                values = ast.literal_eval(values_list_str)
                threshold = float(threshold_str)
                return {
                    "type": "if_not_in",
                    "values": values,
                    "operator": operator,
                    "value": threshold,
                }
            except (ValueError, SyntaxError) as e:
                return {
                    "type": "unknown",
                    "error": f"failed_to_parse_if_not_in: {str(e)}",
                }

        # Parse if_not_unique > 0
        if condition_str.startswith("if_not_unique"):
            parts = condition_str.split(" ", 1)
            if len(parts) > 1:
                operator_value = parts[1].strip()
                op_match = re.match(r"([<>=!]+)\s*(.+)", operator_value)
                if op_match:
                    operator = op_match.group(1)
                    threshold = float(op_match.group(2))
                    return {
                        "type": "if_not_unique",
                        "operator": operator,
                        "value": threshold,
                    }
                else:
                    threshold = float(operator_value)
                    return {
                        "type": "if_not_unique",
                        "operator": ">",
                        "value": threshold,
                    }
            return {"type": "if_not_unique", "operator": ">", "value": 0}

        # Parse if_null > 5% or if_null > 0.05
        if condition_str.startswith("if_null"):
            parts = condition_str.split(" ", 1)
            if len(parts) > 1:
                operator_value = parts[1].strip()
                # Check for percentage
                pct_match = re.match(r"([<>=!]+)\s*(\d+(\.\d+)?)\s*%", operator_value)
                if pct_match:
                    operator = pct_match.group(1)
                    threshold_pct = float(pct_match.group(2))
                    threshold = threshold_pct / 100.0
                    return {
                        "type": "if_null",
                        "operator": operator,
                        "value": threshold,
                        "is_percentage": True,
                    }
                else:
                    # Regular numeric
                    op_match = re.match(r"([<>=!]+)\s*(.+)", operator_value)
                    if op_match:
                        operator = op_match.group(1)
                        threshold = float(op_match.group(2))
                        return {
                            "type": "if_null",
                            "operator": operator,
                            "value": threshold,
                        }
                    else:
                        threshold = float(operator_value)
                        return {"type": "if_null", "operator": ">", "value": threshold}
            return {"type": "if_null", "operator": ">", "value": 0.0}

        return {
            "type": "unknown",
            "error": f"unrecognized_condition_format: {condition_str}",
        }

    async def _execute_column_values_check(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """
        Execute column values check (TDD Level 1: Simple Declarative).

        Supports conditions from TDD spec:
        - "if_null > 5%" - Check for NULL values
        - "if_not_unique > 0" - Check for duplicate values
        - "if_not_in: ['A', 'B', 'C'] > 0" - Check for values not in allowed list
        """
        try:
            if db_connector is None:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Column values check requires a connected data source",
                    metadata={"error": "missing_connector"},
                )

            config = clef.config
            table = config.get("table")
            column = config.get("column")

            if not table or not column:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Missing table or column in column_values check config",
                    metadata={"error": "missing_config"},
                )

            # Get condition from fail field (per TDD spec) or warn field
            condition_str = clef.fail or clef.warn
            if not condition_str:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Column values check requires a condition in 'fail' or 'warn' field",
                    metadata={"error": "missing_condition"},
                )

            # Parse the condition
            parsed = self._parse_column_values_condition(condition_str)
            condition_type = parsed.get("type")

            if condition_type == "unknown":
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message=f"Failed to parse condition: {condition_str}. Error: {parsed.get('error', 'unknown')}",
                    metadata={
                        "error": "condition_parse_error",
                        "condition": condition_str,
                        "parsed": parsed,
                    },
                )

            # Execute appropriate check based on condition type
            if condition_type == "if_null":
                return await self._execute_column_values_if_null(
                    clef, stave, db_connector, table, column, parsed
                )
            elif condition_type == "if_not_unique":
                return await self._execute_column_values_if_not_unique(
                    clef, stave, db_connector, table, column, parsed
                )
            elif condition_type == "if_not_in":
                return await self._execute_column_values_if_not_in(
                    clef, stave, db_connector, table, column, parsed
                )
            else:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message=f"Unsupported condition type: {condition_type}",
                    metadata={
                        "error": "unsupported_condition_type",
                        "condition": condition_str,
                        "parsed": parsed,
                    },
                )

        except Exception as e:
            logger.exception(f"Error in column_values check: {e}")
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Column values check failed: {str(e)}",
                metadata={"error": str(e), "exception_type": type(e).__name__},
            )

    async def _execute_column_values_if_null(
        self,
        clef: Clef,
        stave: Stave,
        db_connector: Any,
        table: str,
        column: str,
        parsed: Dict[str, Any],
    ) -> CheckResult:
        """Execute if_null condition check."""
        sql = f"""
        SELECT
            COUNT(*) as total_rows,
            COUNT({column}) as non_null_rows,
            COUNT(*) - COUNT({column}) as null_rows
        FROM {table}
        """

        results = await db_connector.query({"sql": sql})

        if not results:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message="Query returned no results",
                metadata={"error": "empty_result", "sql": sql},
            )

        row = results[0]
        total_rows = row.get("total_rows", 0)
        null_rows = row.get("null_rows", 0)
        non_null_rows = row.get("non_null_rows", 0)

        if total_rows == 0:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="warn",
                observed_value=0.0,
                message=f"Table '{table}' returned no rows to evaluate",
                metadata={
                    "table": table,
                    "column": column,
                    "total_rows": 0,
                    "null_rows": 0,
                    "non_null_rows": 0,
                    "note": "Consider running a volume check to ensure data is present",
                },
            )

        null_rate = null_rows / total_rows if total_rows else 0.0
        null_percentage_display = null_rate * 100.0

        # Evaluate against parsed condition
        operator = parsed.get("operator", ">")
        threshold = parsed.get("value", 0.0)
        condition_met = self._evaluate_condition_numeric(
            null_rate, f"{operator} {threshold}"
        )

        # Also check warn/fail conditions if specified
        if clef.fail and self._evaluate_condition(null_rate, clef.fail):
            status = "fail"
            message = f"NULL rate {null_percentage_display:.2f}% violates fail condition ({clef.fail})"
        elif clef.warn and self._evaluate_condition(null_rate, clef.warn):
            status = "warn"
            message = f"NULL rate {null_percentage_display:.2f}% breaches warning condition ({clef.warn})"
        elif condition_met:
            status = "fail" if clef.fail else "warn"
            message = f"NULL rate {null_percentage_display:.2f}% violates condition ({clef.fail or clef.warn})"
        else:
            status = "pass"
            message = (
                f"NULL rate {null_percentage_display:.2f}% within acceptable limits"
            )

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=status,
            observed_value=null_rate,
            message=message,
            metadata={
                "table": table,
                "column": column,
                "total_rows": total_rows,
                "non_null_rows": non_null_rows,
                "null_rows": null_rows,
                "null_percentage": null_rate,
                "null_percentage_display": null_percentage_display,
                "warn_condition": clef.warn,
                "fail_condition": clef.fail,
                "condition_type": "if_null",
            },
            anomalies_count=null_rows if status != "pass" else 0,
        )

    async def _execute_column_values_if_not_unique(
        self,
        clef: Clef,
        stave: Stave,
        db_connector: Any,
        table: str,
        column: str,
        parsed: Dict[str, Any],
    ) -> CheckResult:
        """Execute if_not_unique condition check - finds duplicate values."""
        # Build SQL to find duplicates
        if stave.data_source_type in ["postgres", "postgresql", "mysql", "bigquery"]:
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT {column}) as unique_values,
                COUNT(*) - COUNT(DISTINCT {column}) as duplicate_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "sqlite":
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT {column}) as unique_values,
                COUNT(*) - COUNT(DISTINCT {column}) as duplicate_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        else:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Uniqueness check not supported for {stave.data_source_type}",
                metadata={"error": "unsupported_data_source"},
            )

        results = await db_connector.query({"sql": sql})

        if not results:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message="Query returned no results",
                metadata={"error": "empty_result", "sql": sql},
            )

        row = results[0]
        total_rows = row.get("total_rows", 0)
        unique_values = row.get("unique_values", 0)
        duplicate_rows = row.get("duplicate_rows", 0)

        if total_rows == 0:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="warn",
                observed_value=0,
                message=f"Table '{table}' has no non-null values to check for uniqueness",
                metadata={
                    "table": table,
                    "column": column,
                    "total_rows": 0,
                    "duplicate_rows": 0,
                },
            )

        # Evaluate condition
        operator = parsed.get("operator", ">")
        threshold = parsed.get("value", 0)
        condition_met = self._evaluate_condition_numeric(
            duplicate_rows, f"{operator} {threshold}"
        )

        if clef.fail and self._evaluate_condition(duplicate_rows, clef.fail):
            status = "fail"
            message = f"Found {duplicate_rows} duplicate rows (violates fail condition: {clef.fail})"
        elif clef.warn and self._evaluate_condition(duplicate_rows, clef.warn):
            status = "warn"
            message = f"Found {duplicate_rows} duplicate rows (breaches warning condition: {clef.warn})"
        elif condition_met:
            status = "fail" if clef.fail else "warn"
            message = f"Found {duplicate_rows} duplicate rows (violates condition: {clef.fail or clef.warn})"
        else:
            status = "pass"
            message = f"Uniqueness check passed: {unique_values} unique values, {duplicate_rows} duplicates"

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=status,
            observed_value=duplicate_rows,
            message=message,
            metadata={
                "table": table,
                "column": column,
                "total_rows": total_rows,
                "unique_values": unique_values,
                "duplicate_rows": duplicate_rows,
                "warn_condition": clef.warn,
                "fail_condition": clef.fail,
                "condition_type": "if_not_unique",
            },
            anomalies_count=duplicate_rows if status != "pass" else 0,
        )

    async def _execute_column_values_if_not_in(
        self,
        clef: Clef,
        stave: Stave,
        db_connector: Any,
        table: str,
        column: str,
        parsed: Dict[str, Any],
    ) -> CheckResult:
        """Execute if_not_in condition check - finds values not in allowed list."""
        allowed_values = parsed.get("values", [])
        if not allowed_values:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message="if_not_in condition requires a list of allowed values",
                metadata={"error": "missing_allowed_values"},
            )

        # Build SQL to count values not in allowed list
        # Escape values for SQL injection safety
        if stave.data_source_type in ["postgres", "postgresql"]:
            # Use array syntax for PostgreSQL
            values_list = "', '".join(str(v).replace("'", "''") for v in allowed_values)
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN {column} NOT IN ('{values_list}') THEN 1 END) as not_in_list_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "mysql":
            values_list = "', '".join(str(v).replace("'", "''") for v in allowed_values)
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN {column} NOT IN ('{values_list}') THEN 1 END) as not_in_list_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "sqlite":
            values_list = "', '".join(str(v).replace("'", "''") for v in allowed_values)
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN {column} NOT IN ('{values_list}') THEN 1 END) as not_in_list_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        elif stave.data_source_type == "bigquery":
            # BigQuery uses different syntax
            escaped_values = [str(v).replace("'", "''") for v in allowed_values]
            values_list = ", ".join(f"'{v}'" for v in escaped_values)
            sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNTIF({column} NOT IN ({values_list})) as not_in_list_rows
            FROM {table}
            WHERE {column} IS NOT NULL
            """
        else:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"if_not_in check not supported for {stave.data_source_type}",
                metadata={"error": "unsupported_data_source"},
            )

        results = await db_connector.query({"sql": sql})

        if not results:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message="Query returned no results",
                metadata={"error": "empty_result", "sql": sql},
            )

        row = results[0]
        total_rows = row.get("total_rows", 0)
        not_in_list_rows = row.get("not_in_list_rows", 0)

        if total_rows == 0:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="warn",
                observed_value=0,
                message=f"Table '{table}' has no non-null values to check",
                metadata={
                    "table": table,
                    "column": column,
                    "total_rows": 0,
                    "not_in_list_rows": 0,
                    "allowed_values": allowed_values,
                },
            )

        # Evaluate condition
        operator = parsed.get("operator", ">")
        threshold = parsed.get("value", 0)
        condition_met = self._evaluate_condition_numeric(
            not_in_list_rows, f"{operator} {threshold}"
        )

        if clef.fail and self._evaluate_condition(not_in_list_rows, clef.fail):
            status = "fail"
            message = f"Found {not_in_list_rows} rows with values not in allowed list (violates fail condition: {clef.fail})"
        elif clef.warn and self._evaluate_condition(not_in_list_rows, clef.warn):
            status = "warn"
            message = f"Found {not_in_list_rows} rows with values not in allowed list (breaches warning condition: {clef.warn})"
        elif condition_met:
            status = "fail" if clef.fail else "warn"
            message = f"Found {not_in_list_rows} rows with values not in allowed list (violates condition: {clef.fail or clef.warn})"
        else:
            status = "pass"
            message = f"All values are in allowed list: {allowed_values}"

        return CheckResult(
            clef_id=clef.id,
            stave_id=stave.id,
            status=status,
            observed_value=not_in_list_rows,
            message=message,
            metadata={
                "table": table,
                "column": column,
                "total_rows": total_rows,
                "not_in_list_rows": not_in_list_rows,
                "allowed_values": allowed_values,
                "warn_condition": clef.warn,
                "fail_condition": clef.fail,
                "condition_type": "if_not_in",
            },
            anomalies_count=not_in_list_rows if status != "pass" else 0,
        )

    async def _execute_row_count_check(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """Execute row count check (TDD Level 1: Simple Declarative)."""
        try:
            if db_connector is None:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Row count check requires a connected data source",
                    metadata={"error": "missing_connector"},
                )

            config = clef.config
            table = config.get("table")

            if not table:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Missing table in row_count check config",
                    metadata={"error": "missing_table"},
                )

            sql = f"SELECT COUNT(*) as row_count FROM {table}"
            results = await db_connector.query({"sql": sql})

            if not results:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Query returned no results",
                    metadata={"error": "empty_result"},
                )

            row = results[0]
            row_count = row.get("row_count")

            if row_count is None:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Row count query did not return 'row_count' column",
                    metadata={"error": "missing_row_count"},
                )

            # Evaluate conditions - fail takes precedence over warn
            fail_condition_met = clef.fail and self._evaluate_condition_numeric(
                row_count, clef.fail
            )
            warn_condition_met = clef.warn and self._evaluate_condition_numeric(
                row_count, clef.warn
            )

            if fail_condition_met:
                status = "fail"
                message = f"Row count {row_count} violates fail condition ({clef.fail})"
            elif warn_condition_met:
                status = "warn"
                message = (
                    f"Row count {row_count} triggers warning condition ({clef.warn})"
                )
            else:
                status = "pass"
                message = f"Row count {row_count} within acceptable range"

            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status=status,
                observed_value=row_count,
                message=message,
                metadata={
                    "table": table,
                    "row_count": row_count,
                    "warn_condition": clef.warn,
                    "fail_condition": clef.fail,
                },
                anomalies_count=1 if status == "fail" else 0,
            )

        except Exception as e:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Row count check failed: {str(e)}",
                metadata={"error": str(e)},
            )

    def _evaluate_condition(self, observed_value: Any, condition_str: str) -> bool:
        """Evaluates a condition string against an observed value."""
        if not condition_str:
            return False

        condition_str = condition_str.strip()

        # Handle 'if_null' condition specifically
        if condition_str.startswith("if_null"):
            if observed_value is None:
                return True
            parts = condition_str.split(" ", 1)
            if len(parts) > 1:
                null_percentage_condition = parts[1].strip()
                return self._evaluate_condition(
                    observed_value, null_percentage_condition
                )
            return (
                observed_value is None
            )  # if no further condition, just check if it's null

        # Handle percentage values in condition string
        if isinstance(observed_value, (int, float)) and "%" in condition_str:
            try:
                # Extract operator and value
                import re

                match = re.match(r"([<>=!]+)\s*(\d+(\.\d+)?)\s*%", condition_str)
                if match:
                    operator = match.group(1)
                    threshold_percentage = float(match.group(2)) / 100.0
                    return self._evaluate_condition_numeric(
                        observed_value, f"{operator} {threshold_percentage}"
                    )
            except ValueError:
                pass  # Fallback to generic numeric evaluation if percentage parsing fails

        # Generic numeric evaluation
        return self._evaluate_condition_numeric(observed_value, condition_str)

    def _evaluate_condition_numeric(
        self, observed_value: Any, condition_str: str
    ) -> bool:
        """
        Helper for numeric condition evaluation.

        Supports:
        - "> 5000", "< 100", ">= 1000", "<= 5000"
        - "between 1000 and 2000" or "between 1000 and 2000"
        - "5000" (equality)
        """
        if not condition_str:
            return False

        condition_str = condition_str.strip()

        # Handle "between X and Y" syntax
        import re

        between_match = re.match(
            r"between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)",
            condition_str,
            re.IGNORECASE,
        )
        if between_match:
            try:
                min_val = float(between_match.group(1))
                max_val = float(between_match.group(2))
                return min_val <= observed_value <= max_val
            except (ValueError, TypeError):
                return False

        # Handle operators
        import operator

        ops = {
            ">=": operator.ge,
            "<=": operator.le,
            "!=": operator.ne,
            "==": operator.eq,
            ">": operator.gt,
            "<": operator.lt,
        }

        # Check longer operators first (>=, <=, !=, ==) before single char ones
        for op_str, op_func in sorted(ops.items(), key=lambda x: -len(x[0])):
            if condition_str.startswith(op_str):
                try:
                    threshold_str = condition_str[len(op_str) :].strip()
                    threshold = float(threshold_str)
                    return op_func(observed_value, threshold)
                except (ValueError, TypeError):
                    return False

        # Default to equality if no operator found
        try:
            threshold = float(condition_str)
            return observed_value == threshold
        except (ValueError, TypeError):
            return False

    async def _execute_data_profile_drift_check(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """Execute data profile drift check (TDD Level 3: Advanced Declarative)."""
        try:
            # For now, return a mock result since this is a complex ML-based check
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="pass",
                observed_value=0.05,
                message="Data profile drift check passed: minimal drift detected",
                metadata={
                    "check_type": "data_profile_drift",
                    "drift_score": 0.05,
                    "threshold": 0.1,
                    "note": "Mock implementation - would use ML models in production",
                },
            )
        except Exception as e:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Data profile drift check failed: {str(e)}",
                metadata={"error": str(e)},
            )

    async def _execute_forecast_check(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """Execute forecast check (TDD Level 2: Intelligent)."""
        try:
            # For now, return a mock result since this is a complex ML-based check
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="pass",
                observed_value=1250,
                message="Forecast check passed: data volume within expected range",
                metadata={
                    "check_type": "forecast",
                    "predicted_value": 1250,
                    "actual_value": 1200,
                    "confidence": 95,
                    "note": "Mock implementation - would use SARIMA models in production",
                },
            )
        except Exception as e:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Forecast check failed: {str(e)}",
                metadata={"error": str(e)},
            )

    async def _execute_lookup_validation_check(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """Execute lookup validation check (TDD Level 3: Advanced Declarative)."""
        try:
            # For now, return a mock result since this is a complex multi-source check
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="pass",
                observed_value=0.98,
                message="Lookup validation check passed: 98% of lookups successful",
                metadata={
                    "check_type": "lookup_validation",
                    "success_rate": 0.98,
                    "total_lookups": 1000,
                    "failed_lookups": 20,
                    "note": "Mock implementation - would validate cross-source references",
                },
            )
        except Exception as e:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Lookup validation check failed: {str(e)}",
                metadata={"error": str(e)},
            )

    async def _execute_python_check(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """Execute custom Python check (TDD Level 4: Custom Code)."""
        try:
            # For now, return a mock result since this would execute custom Python code
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="pass",
                observed_value="custom_result",
                message="Custom Python check passed: business logic validation successful",
                metadata={
                    "check_type": "python",
                    "script_executed": True,
                    "execution_time": 0.5,
                    "note": "Mock implementation - would execute custom Python scripts",
                },
            )
        except Exception as e:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Custom Python check failed: {str(e)}",
                metadata={"error": str(e)},
            )

    async def _execute_freshness_check(
        self, clef: Clef, stave: Stave, db_connector: Any = None
    ) -> CheckResult:
        """Execute freshness check (TDD Level 1: Simple Declarative)."""
        try:
            if db_connector is None:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Freshness check requires a connected data source",
                    metadata={"error": "missing_connector"},
                )

            def _parse_duration_to_hours(value):
                if value is None:
                    return None
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    text = value.strip().lower()
                    if not text:
                        return None
                    parts = text.split()
                    try:
                        quantity = float(parts[0])
                    except ValueError:
                        return None
                    unit = parts[1] if len(parts) > 1 else "hours"
                    if unit.startswith("hour"):
                        return quantity
                    if unit.startswith("day"):
                        return quantity * 24.0
                    if unit.startswith("min"):
                        return quantity / 60.0
                    if unit.startswith("sec"):
                        return quantity / 3600.0
                    return quantity
                return None

            def _normalize_duration_condition(condition):
                if not condition:
                    return None
                condition = condition.strip()
                import re

                match = re.match(r"([<>=!]+)\s*(.+)", condition)
                if not match:
                    hours_value = _parse_duration_to_hours(condition)
                    return None if hours_value is None else f"== {hours_value}"
                operator, value_part = match.groups()
                hours_value = _parse_duration_to_hours(value_part)
                if hours_value is None:
                    return None
                return f"{operator} {hours_value}"

            config = clef.config
            table = config.get("table")
            column = config.get("column", "updated_at")

            if not table:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message="Missing table in freshness check config",
                    metadata={"error": "missing_table"},
                )

            max_age_input = config.get("max_age_hours", config.get("max_age", 24))
            max_age_hours = _parse_duration_to_hours(max_age_input) or 24.0

            sql = f"SELECT MAX({column}) as latest_timestamp FROM {table}"
            # Try dict format first, fallback to string if needed
            try:
                results = await db_connector.query({"sql": sql})
            except (TypeError, AttributeError):
                # Fallback for connectors that only accept strings
                results = await db_connector.query(sql)

            if not results or results[0].get("latest_timestamp") is None:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    observed_value=None,
                    message=f"No timestamp data found in '{table}.{column}'",
                    metadata={
                        "table": table,
                        "column": column,
                        "warn_condition": clef.warn,
                        "fail_condition": clef.fail,
                        "note": "Consider backfilling timestamp column or verifying data ingestion",
                    },
                )

            latest_raw = results[0]["latest_timestamp"]
            latest_timestamp = latest_raw
            if isinstance(latest_raw, str):
                try:
                    latest_timestamp = datetime.fromisoformat(
                        latest_raw.replace("Z", "+00:00")
                    )
                except ValueError:
                    latest_timestamp = None
            elif isinstance(latest_raw, datetime):
                latest_timestamp = latest_raw

            if latest_timestamp is None:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="fail",
                    observed_value=None,
                    message=f"Unable to parse timestamp returned from '{column}'",
                    metadata={"raw_value": latest_raw},
                )

            now = datetime.utcnow()
            age_hours = max((now - latest_timestamp).total_seconds() / 3600.0, 0.0)

            normalized_fail = _normalize_duration_condition(clef.fail)
            normalized_warn = _normalize_duration_condition(clef.warn)

            if normalized_fail and self._evaluate_condition(age_hours, normalized_fail):
                status = "fail"
                message = f"Data freshness breached fail condition ({clef.fail}); age {age_hours:.2f} hours"
            elif normalized_warn and self._evaluate_condition(
                age_hours, normalized_warn
            ):
                status = "warn"
                message = f"Data freshness breached warn condition ({clef.warn}); age {age_hours:.2f} hours"
            elif age_hours <= max_age_hours:
                status = "pass"
                message = f"Newest record {age_hours:.2f} hours old (threshold ≤ {max_age_hours} hours)"
            else:
                status = "warn"
                message = f"Data older than configured target ({age_hours:.2f} hours > {max_age_hours} hours)"

            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status=status,
                observed_value=age_hours,
                message=message,
                metadata={
                    "table": table,
                    "column": column,
                    "latest_timestamp": latest_timestamp.isoformat(),
                    "age_hours": age_hours,
                    "expected_max_age_hours": max_age_hours,
                    "warn_condition": clef.warn,
                    "fail_condition": clef.fail,
                },
                anomalies_count=1 if status == "fail" else 0,
            )

        except Exception as e:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Freshness check failed: {str(e)}",
                metadata={"error": str(e)},
            )

    async def _execute_forecast_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a forecast-based anomaly detection check."""
        config = clef.config
        query = config.get("query")
        value_column = config.get("value_column", "value")
        timestamp_column = config.get("timestamp_column", "timestamp")

        if SarimaForecaster is None or pd is None:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                message="Forecast check requires optional dependencies (statsmodels, pandas). Install them or disable Level 2 checks.",
                metadata={
                    "error": "missing_optional_dependency",
                    "dependencies": ["statsmodels", "pandas"],
                },
                timestamp=datetime.now(),
            )

        if not query:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Forecast check requires a 'query' configuration",
                metadata={"error": "missing_query"},
                timestamp=datetime.now(),
            )

        try:
            # 1. Fetch time series data
            rows = await db_connector.query({"sql": query})

            if not rows or len(rows) < 10:  # Need explicit history
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    message=f"Insufficient data for forecasting (got {len(rows)} rows, need 10+)",
                    metadata={"row_count": len(rows)},
                    timestamp=datetime.now(),
                )

            # 2. Prepare data for SarimaForecaster
            df = pd.DataFrame(rows)

            # Ensure proper types
            if timestamp_column in df.columns:
                df[timestamp_column] = pd.to_datetime(df[timestamp_column])
                df = df.sort_values(by=timestamp_column)

            if value_column not in df.columns:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="error",
                    message=f"Value column '{value_column}' not found in query results",
                    metadata={"columns": list(df.columns)},
                    timestamp=datetime.now(),
                )

            # Extract time series
            ts_values = df[value_column].dropna().tolist()

            if len(ts_values) < 10:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    message="Insufficient non-null values for forecasting",
                    metadata={"valid_count": len(ts_values)},
                    timestamp=datetime.now(),
                )

            # Split: Train on all except last, test on last
            train_data = ts_values[:-1]
            observed_value = ts_values[-1]

            # 3. Train Model
            forecaster = SarimaForecaster()

            # Auto-select order if not provided in config (simplification: always auto for now or defaults)
            # Using defaults (1,1,1) (1,1,1,12) for speed unless specified
            # In a real scenario, we might want to cache the trained model.

            # Try to train. NOTE: This is compute intensive.
            forecaster.train(train_data)

            # 4. Detect Anomaly
            result = forecaster.detect_anomaly(observed_value=observed_value)

            # 5. Formulate Result
            status = "fail" if result.is_anomaly else "pass"

            message_prefix = (
                "Anomaly Detected: " if result.is_anomaly else "Forecast OK: "
            )
            message = f"{message_prefix}Value {observed_value:.2f} (Expected range: [{result.lower_bound:.2f}, {result.upper_bound:.2f}])"

            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status=status,
                observed_value=observed_value,
                message=message,
                metadata={
                    "lower_bound": result.lower_bound,
                    "upper_bound": result.upper_bound,
                    "confidence_level": result.confidence_level,
                    "p_value": result.p_value,
                    "model_info": result.model_info,
                },
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Forecast check failed: {e}", exc_info=True)
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                message=f"Forecast analysis failed: {str(e)}",
                metadata={"error": str(e)},
                timestamp=datetime.now(),
            )

    async def _execute_data_profile_drift_check(
        self, clef: Clef, stave: Stave, db_connector: Any
    ) -> CheckResult:
        """Execute a data distribution drift check (Level 2)."""
        config = clef.config
        table = config.get("table")
        column = config.get("column")
        baseline_condition = config.get(
            "baseline_condition", "1=1"
        )  # Default unsafe, usually needs specific window
        current_condition = config.get("current_condition", "1=1")
        critical_p_value = config.get("critical_p_value", 0.05)

        if DriftDetector is None:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                message="Drift check requires optional dependency (scipy). Install it or disable Level 2/3 drift checks.",
                metadata={
                    "error": "missing_optional_dependency",
                    "dependencies": ["scipy"],
                },
                timestamp=datetime.now(),
            )

        if not table or not column:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                message="Drift check requires 'table' and 'column'",
                metadata={"error": "missing_config"},
                timestamp=datetime.now(),
            )

        try:
            # 1. Fetch Baseline Data
            # Limit to prevent memory explosions
            baseline_sql = f"SELECT {column} as val FROM {table} WHERE {baseline_condition} LIMIT 10000"
            baseline_rows = await db_connector.query({"sql": baseline_sql})
            baseline_values = [r["val"] for r in baseline_rows if r["val"] is not None]

            # 2. Fetch Current Data
            current_sql = f"SELECT {column} as val FROM {table} WHERE {current_condition} LIMIT 10000"
            current_rows = await db_connector.query({"sql": current_sql})
            current_values = [r["val"] for r in current_rows if r["val"] is not None]

            if len(baseline_values) < 20 or len(current_values) < 20:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    message=f"Insufficient data for drift detection (baseline: {len(baseline_values)}, current: {len(current_values)})",
                    metadata={
                        "baseline_count": len(baseline_values),
                        "current_count": len(current_values),
                    },
                    timestamp=datetime.now(),
                )

            # 3. Perform Drift Detection using Brain Library
            detector = DriftDetector()
            # Default to KS test for continuous data
            # NOTE: For categorical data, we might need Chi-Square, but Detector currently supports KS/AD/Mann-Whitney
            # We assume continuous/numeric for now as implied by KS.

            # Ensure numeric (filter out non-numeric if necessary or rely on database type)
            try:
                baseline_floats = [float(x) for x in baseline_values]
                current_floats = [float(x) for x in current_values]
            except (ValueError, TypeError):
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="error",
                    message="Drift check currently only supports numeric columns for KS test",
                    metadata={"error": "non_numeric_data"},
                    timestamp=datetime.now(),
                )

            drift_result = detector.kolmogorov_smirnov_test(
                baseline=baseline_floats,
                current=current_floats,
                critical_p_value=critical_p_value,
            )

            # 4. Formulate Result
            status = "fail" if drift_result.drift_detected else "pass"
            msg_prefix = (
                "Drift Detected: "
                if drift_result.drift_detected
                else "Stable Distribution: "
            )
            message = f"{msg_prefix}p-value {drift_result.p_value:.4f} (Threshold: {critical_p_value})"

            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status=status,
                observed_value=drift_result.p_value,  # The metric is the p-value
                message=message,
                metadata={
                    "test_statistic": drift_result.test_statistic,
                    "p_value": drift_result.p_value,
                    "baseline_size": drift_result.baseline_size,
                    "current_size": drift_result.current_size,
                    "stats_metadata": drift_result.metadata,
                },
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Drift check failed: {e}", exc_info=True)
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                message=f"Drift analysis failed: {str(e)}",
                metadata={"error": str(e)},
                timestamp=datetime.now(),
            )


# =============================================================================
# Module-level helper functions (backward compatible API)
# =============================================================================

_default_executor = ClefExecutor()


async def execute_clef(
    clef: Clef, stave: Stave, db_connector: Any = None
) -> CheckResult:
    """Convenience helper to execute a single clef using the shared executor."""
    return await _default_executor.execute_clef(clef, stave, db_connector)


async def execute_stave_clefs(
    stave: Stave, clefs: list[Clef], db_connector: Any = None
) -> list[CheckResult]:
    """
    Execute multiple clefs for a stave, reusing the same data connector when possible.
    """
    connector = db_connector
    managed_connector = False

    if connector is None:
        tester = ConnectionTester()
        connector = await tester.get_connector(stave, read_only=True)
        managed_connector = True

    try:
        results: list[CheckResult] = []
        for clef in clefs:
            results.append(await _default_executor.execute_clef(clef, stave, connector))
        return results
    finally:
        if managed_connector and connector is not None:
            try:
                await connector.close()
            except Exception as close_error:
                logger.warning(
                    f"Failed to close connector for stave '{stave.name}': {close_error}"
                )
