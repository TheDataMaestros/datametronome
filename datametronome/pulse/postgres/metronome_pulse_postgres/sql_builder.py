"""
PostgreSQL SQL builder utilities for DataPulse connectors.

This module provides a small, focused class that only generates SQL strings.
It contains no I/O and can be unit-tested independently from database code.
"""

from __future__ import annotations




class PostgresSQLBuilder:
    """Utility to generate PostgreSQL SQL statements.

    This builder focuses on common high-performance write patterns:
    - Temporary table staging
    - Replace (delete + insert) from a staged table
    - Upsert (ON CONFLICT DO UPDATE) from a staged table
    - Partition creation helpers (RANGE and LIST)
    """

    def create_temp_table_like(self, temp_table: str, target_table: str) -> str:
        """Create a temp table with the same structure as the target table.

        The temp table will be dropped automatically at transaction end.
        """
        return (
            f"CREATE TEMP TABLE {temp_table} (LIKE {target_table} INCLUDING ALL) ON COMMIT DROP;"
        )

    def delete_using_temp(self, target_table: str, temp_table: str, key_columns: list[str]) -> str:
        """Delete rows from target that match keys present in temp via join."""
        on_clause = " AND ".join(
            [f"{target_table}.{col} = {temp_table}.{col}" for col in key_columns]
        )
        return f"DELETE FROM {target_table} USING {temp_table} WHERE {on_clause};"

    def insert_from_temp(self, target_table: str, temp_table: str, columns: list[str]) -> str:
        """Insert rows from temp into target (simple append)."""
        cols = ", ".join(columns)
        return f"INSERT INTO {target_table} ({cols}) SELECT {cols} FROM {temp_table};"

    def upsert_from_temp(
        self,
        target_table: str,
        temp_table: str,
        columns: list[str],
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> str:
        """Generate an INSERT..ON CONFLICT..DO UPDATE statement from temp.

        Args:
            target_table: Destination table name
            temp_table: Temporary staging table name
            columns: Ordered list of columns present in temp/target
            conflict_columns: Columns forming the unique key to resolve conflicts
            update_columns: Columns to update on conflict. Defaults to all non-conflict columns
        """
        cols = ", ".join(columns)
        conflict = ", ".join(conflict_columns)
        if update_columns is None:
            update_columns = [c for c in columns if c not in conflict_columns]
        set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_columns])
        return (
            f"INSERT INTO {target_table} ({cols}) "
            f"SELECT {cols} FROM {temp_table} "
            f"ON CONFLICT ({conflict}) DO UPDATE SET {set_clause};"
        )

    # -------------------- Partition helpers --------------------
    def create_range_partition(
        self,
        parent_table: str,
        partition_table: str,
        from_value,
        to_value,
    ) -> str:
        """Create a RANGE partition for values FROM .. TO .."""
        return (
            f"CREATE TABLE IF NOT EXISTS {partition_table} "
            f"PARTITION OF {parent_table} FOR VALUES FROM ('{from_value}') TO ('{to_value}');"
        )

    def create_list_partition(
        self,
        parent_table: str,
        partition_table: str,
        values: list,
    ) -> str:
        """Create a LIST partition for explicit values."""
        values_sql = ", ".join([f"'{v}'" for v in values])
        return (
            f"CREATE TABLE IF NOT EXISTS {partition_table} "
            f"PARTITION OF {parent_table} FOR VALUES IN ({values_sql});"
        )

    # -------------------- No-temp delete helpers --------------------
    def delete_using_values_asyncpg(
        self,
        target_table: str,
        key_columns: list[str],
        num_rows: int,
    ) -> str:
        """Build a DELETE .. USING (VALUES ...) for asyncpg ($1-style binds).

        Parameters are flattened row-major: (k1_row1, k2_row1, k1_row2, k2_row2, ...)
        """
        if num_rows <= 0:
            raise ValueError("num_rows must be > 0")
        cols = ", ".join(key_columns)
        tuple_size = len(key_columns)
        value_rows: list[str] = []
        param_index = 1
        for _ in range(num_rows):
            placeholders = ", ".join([f"${param_index + i}" for i in range(tuple_size)])
            value_rows.append(f"({placeholders})")
            param_index += tuple_size
        values_sql = ", ".join(value_rows)
        on_clause = " AND ".join([f"t.{c} = v.{c}" for c in key_columns])
        return (
            f"DELETE FROM {target_table} AS t USING (VALUES {values_sql}) AS v({cols}) "
            f"WHERE {on_clause};"
        )

    def delete_using_values_psycopg(
        self,
        target_table: str,
        key_columns: list[str],
        num_rows: int,
    ) -> str:
        """Build a DELETE .. USING (VALUES ...) for psycopg3 (%s-style binds)."""
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

    def delete_using_values_sqlalchemy(
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

    # -------------------- Session tuning helpers --------------------
    def set_local_synchronous_commit_off(self) -> str:
        return "SET LOCAL synchronous_commit TO OFF;"

    def set_constraints_all_deferred(self) -> str:
        return "SET CONSTRAINTS ALL DEFERRED;"

    def set_local_lock_timeout(self, ms: int) -> str:
        return f"SET LOCAL lock_timeout = '{ms}ms';"

    def set_local_statement_timeout(self, ms: int) -> str:
        return f"SET LOCAL statement_timeout = '{ms}ms';"


