"""
PostgreSQL SQL builder utilities for psycopg3-based DataPulse connector.

This module only generates SQL strings and can be unit-tested independently.
"""

from __future__ import annotations


class PostgresPsycopgSQLBuilder:
    """Utility to generate PostgreSQL SQL statements (psycopg3 style)."""

    def delete_using_values(
        self,
        target_table: str,
        key_columns: list[str],
        num_rows: int,
    ) -> str:
        """Build a DELETE .. USING (VALUES ...) with %s binds (psycopg3).

        Parameters are flattened row-major: (k1_row1, k2_row1, k1_row2, k2_row2, ...)
        """
        # Parameter validation
        if target_table is None:
            raise ValueError("target_table cannot be None")
        if key_columns is None:
            raise ValueError("key_columns cannot be None")
        if len(key_columns) == 0:
            raise ValueError("key_columns cannot be empty")
        if num_rows <= 0:
            raise ValueError("num_rows must be > 0")
            
        cols = ", ".join(key_columns)
        tuple_size = len(key_columns)
        value_rows: list[str] = []
        for _ in range(num_rows):
            placeholders = ", ".join(["%s" for _ in range(tuple_size)])
            value_rows.append(f"({placeholders})")
        values_sql = ", ".join(value_rows)
        on_clause = " AND ".join([f"t.{c} = v.{c}" for c in key_columns])
        return (
            f"DELETE FROM {target_table} AS t USING (VALUES {values_sql}) AS v({cols}) "
            f"WHERE {on_clause};"
        )

    # Session tuning helpers (executed with SET LOCAL inside transactions)
    def set_local_synchronous_commit_off(self) -> str:
        return "SET LOCAL synchronous_commit TO OFF;"

    def set_constraints_all_deferred(self) -> str:
        return "SET CONSTRAINTS ALL DEFERRED;"

    def set_local_lock_timeout(self, ms: int) -> str:
        return f"SET LOCAL lock_timeout = '{ms}ms';"

    def set_local_statement_timeout(self, ms: int) -> str:
        return f"SET LOCAL statement_timeout = '{ms}ms';"


