"""
QueryExecutor — single entry point for all database operations.

Wraps a Pulse connector + QueryAdapter. All application code goes through
this class. No dialect branching leaks beyond this boundary.
"""
from contextlib import asynccontextmanager
from typing import Any

from datametronome_podium.core.query_adapter import QueryAdapter


def quote_identifier(name: str, dialect: str = "ansi") -> str:
    """Safely quote a SQL identifier to prevent injection.

    Handles dot-separated names (e.g. ``schema.table``) by quoting each
    segment individually.  For BigQuery uses backtick quoting; all other
    dialects use ANSI double-quote quoting (PostgreSQL, SQLite, MySQL ANSI).
    """
    def _quote_segment(seg: str) -> str:
        seg = seg.strip()
        if not seg:
            raise ValueError(f"Empty segment in identifier: {name!r}")
        if dialect == "bigquery":
            return '`' + seg.replace('`', '\\`') + '`'
        return '"' + seg.replace('"', '""') + '"'

    if "." in name:
        return ".".join(_quote_segment(s) for s in name.split("."))
    return _quote_segment(name)


_VALID_DIRECTIONS = {"ASC", "DESC"}


def _safe_order_by(clause: str) -> str:
    """Quote column names in an ORDER BY clause while preserving direction.

    Accepts: "created_at DESC", "name", "created_at DESC, name ASC"
    """
    parts = []
    for term in clause.split(","):
        tokens = term.strip().split()
        col = quote_identifier(tokens[0])
        direction = tokens[1].upper() if len(tokens) > 1 else ""
        if direction and direction not in _VALID_DIRECTIONS:
            raise ValueError(f"Invalid ORDER BY direction: {direction}")
        parts.append(f"{col} {direction}".strip())
    return ", ".join(parts)


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
        cols = ", ".join(quote_identifier(c) for c in columns) if columns else "*"
        sql = f"SELECT {cols} FROM {quote_identifier(table)}"
        params: list[Any] = []

        if where:
            clauses = []
            for key, value in where.items():
                clauses.append(f"{quote_identifier(key)} = ?")
                params.append(value)
            sql += " WHERE " + " AND ".join(clauses)

        if order_by:
            sql += f" ORDER BY {_safe_order_by(order_by)}"
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
        col_names = ", ".join(quote_identifier(c) for c in columns)
        sql = f"INSERT INTO {quote_identifier(table)} ({col_names}) VALUES ({placeholders})"
        return await self.execute(sql, list(data.values()))

    async def update(
        self, table: str, data: dict[str, Any], where: dict[str, Any] | None = None
    ) -> int:
        """UPDATE rows in a table."""
        set_clauses = [f"{quote_identifier(k)} = ?" for k in data.keys()]
        params = list(data.values())
        sql = f"UPDATE {quote_identifier(table)} SET {', '.join(set_clauses)}"

        if where:
            where_clauses = [f"{quote_identifier(k)} = ?" for k in where.keys()]
            sql += " WHERE " + " AND ".join(where_clauses)
            params.extend(where.values())

        return await self.execute(sql, params)

    async def delete(self, table: str, where: dict[str, Any] | None = None) -> int:
        """DELETE rows from a table. Requires a WHERE clause to prevent accidental full-table deletes."""
        if not where:
            raise ValueError("delete() requires a where clause. Use execute() for unconditional deletes.")
        sql = f"DELETE FROM {quote_identifier(table)}"
        params: list[Any] = []
        clauses = [f"{quote_identifier(k)} = ?" for k in where.keys()]
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
