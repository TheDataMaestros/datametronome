"""
QueryExecutor — single entry point for all database operations.

Wraps a Pulse connector + QueryAdapter. All application code goes through
this class. No dialect branching leaks beyond this boundary.
"""
from contextlib import asynccontextmanager
from typing import Any

from datametronome_podium.core.query_adapter import QueryAdapter


class QueryExecutor:
    """Database-agnostic query executor.

    Uses ? placeholders in all SQL. QueryAdapter translates to $1, $2, ...
    for PostgreSQL. Connector handles driver-level execution.
    """

    def __init__(self, connector: Any, adapter: QueryAdapter) -> None:
        self.connector = connector
        self.adapter = adapter

    # --- Core operations ---

    async def query(self, sql: str, params: list[Any] | None = None) -> list[dict]:
        """Execute a SELECT query. Returns list of dicts."""
        adapted_sql, adapted_params = self.adapter.adapt(sql, params)
        return await self.connector.query_with_params(adapted_sql, adapted_params)

    async def execute(self, sql: str, params: list[Any] | None = None) -> int:
        """Execute INSERT/UPDATE/DELETE. Returns rows affected."""
        adapted_sql, adapted_params = self.adapter.adapt(sql, params)
        return await self.connector.execute(adapted_sql, adapted_params if adapted_params else None)

    async def execute_ddl(self, sql: str) -> None:
        """Execute DDL. Adapts types (JSONB->TEXT etc.) per dialect."""
        adapted_sql = self.adapter.adapt_ddl(sql)
        await self.connector.execute(adapted_sql)

    # --- CRUD helpers (single-table convenience) ---

    async def select(
        self,
        table: str,
        columns: list[str] | None = None,
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """SELECT from a single table."""
        cols = ", ".join(columns) if columns else "*"
        sql = f"SELECT {cols} FROM {table}"
        params: list[Any] = []

        if where:
            clauses = []
            for key, value in where.items():
                clauses.append(f"{key} = ?")
                params.append(value)
            sql += " WHERE " + " AND ".join(clauses)

        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        if offset is not None:
            sql += " OFFSET ?"
            params.append(offset)

        return await self.query(sql, params)

    async def insert(self, table: str, data: dict[str, Any]) -> int:
        """INSERT a single row. Callers must generate IDs before calling."""
        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(columns)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        return await self.execute(sql, list(data.values()))

    async def update(
        self, table: str, data: dict[str, Any], where: dict[str, Any] | None = None
    ) -> int:
        """UPDATE rows in a table."""
        set_clauses = [f"{k} = ?" for k in data.keys()]
        params = list(data.values())
        sql = f"UPDATE {table} SET {', '.join(set_clauses)}"

        if where:
            where_clauses = [f"{k} = ?" for k in where.keys()]
            sql += " WHERE " + " AND ".join(where_clauses)
            params.extend(where.values())

        return await self.execute(sql, params)

    async def delete(self, table: str, where: dict[str, Any] | None = None) -> int:
        """DELETE rows from a table."""
        sql = f"DELETE FROM {table}"
        params: list[Any] = []

        if where:
            clauses = [f"{k} = ?" for k in where.keys()]
            sql += " WHERE " + " AND ".join(clauses)
            params.extend(where.values())

        return await self.execute(sql, params)

    # --- Transaction support ---

    @asynccontextmanager
    async def transaction(self):
        """Context manager for atomic operations.

        Usage:
            async with executor.transaction():
                await executor.insert(...)
                await executor.update(...)
        """
        await self.connector.begin_transaction()
        try:
            yield
            await self.connector.commit_transaction()
        except Exception:
            await self.connector.rollback_transaction()
            raise
