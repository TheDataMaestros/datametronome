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
        """Build a DELETE .. USING (VALUES ...) with named binds (:p1, :p2, ...)."""
        if num_rows <= 0:
            raise ValueError("num_rows must be > 0")
        cols = ", ".join(key_columns)
        tuple_size = len(key_columns)
        value_rows: list[str] = []
        p = 1
        for _ in range(num_rows):
            placeholders = ", ".join([f":p{p+i}" for i in range(tuple_size)])
            value_rows.append(f"({placeholders})")
            p += tuple_size
        values_sql = ", ".join(value_rows)
        on_clause = " AND ".join([f"t.{c} = v.{c}" for c in key_columns])
        return (
            f"DELETE FROM {target_table} AS t USING (VALUES {values_sql}) AS v({cols}) "
            f"WHERE {on_clause};"
        )






