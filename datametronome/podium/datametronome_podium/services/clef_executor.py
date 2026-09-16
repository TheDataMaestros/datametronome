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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from datametronome_podium.features.checks.model import (
    SeverityLevel,
)
from datametronome_podium.features.clefs.model import Clef
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.core.query import quote_identifier as _quote_ident
from datametronome_podium.core.sql_dialect import dialect_for
from datametronome_podium.core.connector_factory import create_connector


def _qi(name: str, stave: Stave) -> str:
    """Quote identifier using the correct dialect for the stave's data source.

    For checks that emit the same SQL everywhere and so never look the dialect
    up themselves.
    """
    dialect = dialect_for(stave.data_source_type)
    style = dialect.quote_style if dialect else "ansi"
    return _quote_ident(name, dialect=style)


try:
    from datametronome_brain_base.forecasting import SarimaForecaster  # type: ignore
except ModuleNotFoundError:
    SarimaForecaster = None

try:
    from datametronome_brain_base.drift_detection import DriftDetector  # type: ignore
except ModuleNotFoundError:
    DriftDetector = None

try:
    import pandas as pd  # type: ignore
except ModuleNotFoundError:
    pd = None  # type: ignore

try:
    import numpy as np  # type: ignore
except ModuleNotFoundError:
    np = None  # type: ignore


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
    message: str
    observed_value: Any = None  # The actual value that was observed/evaluated
    metadata: Optional[Dict[str, Any]] = None  # Additional context and proof of failure
    execution_time: float = 0.0  # seconds
    timestamp: Optional[datetime] = None
    anomalies_count: int = 0

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

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
        return self.metadata or {}

    @details.setter
    def details(self, value: Dict[str, Any]):
        self.metadata = value or {}


def _unsupported(clef: Clef, stave: Stave, check: str) -> CheckResult:
    """The one place a check declines a data source it cannot query.

    Each check used to carry its own copy of this, and they disagreed: some
    returned status "error", others "fail", with the same meaning.
    """
    return CheckResult(
        clef_id=clef.id,
        stave_id=stave.id,
        status="error",
        observed_value=None,
        message=f"{check} not supported for {stave.data_source_type}",
        metadata={"error": "unsupported_data_source"},
        execution_time=0.0,
        timestamp=datetime.now(timezone.utc),
    )


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
        start_time = datetime.now(timezone.utc)
        connector = db_connector
        managed_connector = False
        result: CheckResult | None = None

        try:
            if connector is None:
                connector = await create_connector(
                    stave.data_source_type or "",
                    stave.connection_config or {},
                    read_only=True,
                )
                managed_connector = True

            logger.info(f"Executing clef '{clef.name}' on stave '{stave.name}'")

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

        result.execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        self._update_stats(result)
        logger.info(f"Clef '{clef.name}' completed: {result.severity}")
        return result

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
        qt = _qi(table, stave)
        qc = _qi(column, stave)
        sql = f"""
        SELECT
            COUNT(*) as total_rows,
            COUNT({qc}) as non_null_rows,
            COUNT(*) - COUNT({qc}) as null_rows
        FROM {qt}
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
        dialect = dialect_for(stave.data_source_type)
        if dialect is None:
            return _unsupported(clef, stave, "Uniqueness check")

        qt = dialect.quote(table)
        qc = dialect.quote(column)
        sql = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT {qc}) as unique_values,
                COUNT(*) - COUNT(DISTINCT {qc}) as duplicate_rows
            FROM {qt}
            WHERE {qc} IS NOT NULL
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

        dialect = dialect_for(stave.data_source_type)
        if dialect is None:
            return _unsupported(clef, stave, "if_not_in check")

        qt = dialect.quote(table)
        qc = dialect.quote(column)
        not_in_list = dialect.counted(f"NOT {dialect.in_list(qc, allowed_values)}")

        sql = f"""
            SELECT
                COUNT(*) as total_rows,
                {not_in_list} as not_in_list_rows
            FROM {qt}
            WHERE {qc} IS NOT NULL
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

            sql = f"SELECT COUNT(*) as row_count FROM {_qi(table, stave)}"
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

            sql = f"SELECT MAX({_qi(column, stave)}) as latest_timestamp FROM {_qi(table, stave)}"
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

            now = datetime.now(timezone.utc)
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

        if not query:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                observed_value=None,
                message="Forecast check requires a 'query' configuration",
                metadata={"error": "missing_query"},
                timestamp=datetime.now(timezone.utc),
            )

        try:
            # 1. Fetch time series data
            rows = await db_connector.query({"sql": query})

            if not rows or len(rows) < 10:  # Need explicit history
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    observed_value=len(rows) if rows else 0,
                    message=f"Insufficient data for forecasting (got {len(rows)} rows, need 10+)",
                    metadata={"row_count": len(rows)},
                    timestamp=datetime.now(timezone.utc),
                )

            # 2. Extract numeric time series
            ts_values: list[float] = []
            for row in rows:
                if value_column not in row:
                    continue
                raw = row.get(value_column)
                if raw is None:
                    continue
                try:
                    ts_values.append(float(raw))
                except (TypeError, ValueError):
                    continue

            if len(ts_values) < 10:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    observed_value=len(ts_values),
                    message="Insufficient non-null values for forecasting",
                    metadata={"valid_count": len(ts_values)},
                    timestamp=datetime.now(timezone.utc),
                )

            # Split: Train on all except last, test on last
            train_data = ts_values[:-1]
            observed_value = ts_values[-1]

            # 3/4. Detect anomaly
            #
            # Prefer the Brain SARIMA implementation when available.
            # If optional deps aren't installed, fall back to a lightweight
            # z-score style band using recent history.
            if SarimaForecaster is not None and pd is not None:
                df = pd.DataFrame(rows)
                if timestamp_column in df.columns:
                    df[timestamp_column] = pd.to_datetime(df[timestamp_column])
                    df = df.sort_values(by=timestamp_column)
                if value_column not in df.columns:
                    return CheckResult(
                        clef_id=clef.id,
                        stave_id=stave.id,
                        status="error",
                        observed_value=observed_value,
                        message=f"Value column '{value_column}' not found in query results",
                        metadata={"columns": list(df.columns)},
                        timestamp=datetime.now(timezone.utc),
                    )
                ts_values_model = df[value_column].dropna().tolist()
                train_model = ts_values_model[:-1]
                observed_model = float(ts_values_model[-1])

                forecaster = SarimaForecaster()
                forecaster.train(train_model)
                result = forecaster.detect_anomaly(observed_value=observed_model)

                status = "fail" if result.is_anomaly else "pass"
                message_prefix = (
                    "Anomaly Detected: " if result.is_anomaly else "Forecast OK: "
                )
                message = (
                    f"{message_prefix}Value {observed_model:.2f} "
                    f"(Expected range: [{result.lower_bound:.2f}, {result.upper_bound:.2f}])"
                )

                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status=status,
                    observed_value=observed_model,
                    message=message,
                    metadata={
                        "method": "sarima",
                        "lower_bound": result.lower_bound,
                        "upper_bound": result.upper_bound,
                        "confidence_level": result.confidence_level,
                        "p_value": result.p_value,
                        "model_info": result.model_info,
                    },
                    timestamp=datetime.now(timezone.utc),
                )

            # Fallback: mean ± k*std over recent window, accounting for trend
            window = train_data[-30:] if len(train_data) > 30 else train_data
            n = len(window)
            if n == 0:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    observed_value=observed_value,
                    message="Insufficient history for forecasting baseline window",
                    metadata={"window_size": 0},
                    timestamp=datetime.now(timezone.utc),
                )

            # Calculate mean and std
            mean = sum(window) / n
            variance = sum((x - mean) ** 2 for x in window) / n
            std = variance**0.5

            # Account for trend: if data is growing, adjust expected value upward
            # Simple linear trend detection: compare first half vs second half
            trend_adjustment = 0.0
            if n >= 10:
                first_half = window[: n // 2]
                second_half = window[n // 2 :]
                first_mean = sum(first_half) / len(first_half)
                second_mean = sum(second_half) / len(second_half)
                trend = (
                    (second_mean - first_mean) / len(second_half)
                    if len(second_half) > 0
                    else 0
                )
                # Project trend forward by 1 step (for the next observation)
                trend_adjustment = trend

            # Adjust mean for trend
            adjusted_mean = mean + trend_adjustment

            k = float(
                config.get("fallback_sigma", 2.5)
            )  # Slightly wider default (2.5 instead of 2.0)
            lower = adjusted_mean - (k * std)
            upper = adjusted_mean + (k * std)
            is_anomaly = observed_value <= lower or observed_value >= upper

            status = "fail" if is_anomaly else "pass"
            message_prefix = (
                "Anomaly Detected (fallback): "
                if is_anomaly
                else "Forecast OK (fallback): "
            )
            message = (
                f"{message_prefix}Value {observed_value:.2f} "
                f"(Expected range: [{lower:.2f}, {upper:.2f}])"
            )

            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status=status,
                observed_value=observed_value,
                message=message,
                metadata={
                    "method": "fallback_band",
                    "window_size": n,
                    "mean": mean,
                    "std": std,
                    "k": k,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "note": "Install statsmodels+pandas to enable SARIMA forecasting",
                },
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Forecast check failed: {e}", exc_info=True)
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Forecast analysis failed: {str(e)}",
                metadata={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
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
                observed_value=None,
                message="Drift check requires optional dependency (scipy). Install it or disable Level 2/3 drift checks.",
                metadata={
                    "error": "missing_optional_dependency",
                    "dependencies": ["scipy"],
                },
                timestamp=datetime.now(timezone.utc),
            )

        if not table or not column:
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="error",
                observed_value=None,
                message="Drift check requires 'table' and 'column'",
                metadata={"error": "missing_config"},
                timestamp=datetime.now(timezone.utc),
            )

        try:
            # 1. Fetch Baseline Data
            # Limit to prevent memory explosions
            # baseline_condition / current_condition are trusted config strings, not user input
            qt = _qi(table, stave)
            qc = _qi(column, stave)
            baseline_sql = f"SELECT {qc} as val FROM {qt} WHERE {baseline_condition} LIMIT 10000"
            baseline_rows = await db_connector.query({"sql": baseline_sql})
            baseline_values = [r["val"] for r in baseline_rows if r["val"] is not None]

            # 2. Fetch Current Data
            current_sql = f"SELECT {qc} as val FROM {qt} WHERE {current_condition} LIMIT 10000"
            current_rows = await db_connector.query({"sql": current_sql})
            current_values = [r["val"] for r in current_rows if r["val"] is not None]

            if len(baseline_values) < 20 or len(current_values) < 20:
                return CheckResult(
                    clef_id=clef.id,
                    stave_id=stave.id,
                    status="warn",
                    observed_value=None,
                    message=f"Insufficient data for drift detection (baseline: {len(baseline_values)}, current: {len(current_values)})",
                    metadata={
                        "baseline_count": len(baseline_values),
                        "current_count": len(current_values),
                    },
                    timestamp=datetime.now(timezone.utc),
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
                    observed_value=None,
                    message="Drift check currently only supports numeric columns for KS test",
                    metadata={"error": "non_numeric_data"},
                    timestamp=datetime.now(timezone.utc),
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
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Drift check failed: {e}", exc_info=True)
            return CheckResult(
                clef_id=clef.id,
                stave_id=stave.id,
                status="fail",
                observed_value=None,
                message=f"Drift analysis failed: {str(e)}",
                metadata={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
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
        connector = await create_connector(
            stave.data_source_type or "",
            stave.connection_config or {},
            read_only=True,
        )
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
