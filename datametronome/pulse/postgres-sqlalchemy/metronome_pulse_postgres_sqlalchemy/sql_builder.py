"""
PostgreSQL SQL builder utilities for SQLAlchemy-based DataPulse connector.

This module only generates SQL strings and can be unit-tested independently.
"""

from __future__ import annotations


class PostgresSQLAlchemyBuilder:
    """Utility to generate PostgreSQL SQL statements (SQLAlchemy style)."""

    def delete_using_values(
        self,
        target_table: str,
        key_columns: list[str],
        num_rows: int,
    ) -> str:
        """Build a DELETE .. USING (VALUES ...) with named binds (:column_row, ...)."""
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
        for row_idx in range(num_rows):
            placeholders = ", ".join([f":{col}_{row_idx}" for col in key_columns])
            value_rows.append(f"({placeholders})")
        values_sql = ", ".join(value_rows)
        on_clause = " AND ".join([f"t.{c} = v.{c}" for c in key_columns])
        return (
            f"DELETE FROM {target_table} AS t USING (VALUES {values_sql}) AS v({cols}) "
            f"WHERE {on_clause};"
        )






