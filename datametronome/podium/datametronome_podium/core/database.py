"""
Database initialization and connection lifecycle.

This module only manages the connection lifecycle. Query execution
goes through QueryExecutor (core/query.py).
"""
import logging
from typing import Any
from urllib.parse import urlparse

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.query_adapter import QueryAdapter

logger = logging.getLogger(__name__)

# Global state
connector: Any | None = None
dialect: str = "postgresql"
_executor: QueryExecutor | None = None


def _parse_pg_url(url: str) -> dict[str, Any]:
    """Parse a postgresql:// URL into PostgresPulse constructor kwargs."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") or None,
        "user": parsed.username or None,
        "password": parsed.password or None,
    }


def _parse_sqlite_path(url: str) -> str:
    """Extract file path from a sqlite:// URL."""
    import os

    path = (
        url.replace("sqlite+aiosqlite:///", "")
        .replace("sqlite:///", "")
        .replace("./", "")
    )
    if not os.path.isabs(path):
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        podium_dir = os.path.dirname(os.path.dirname(current_file_dir))
        path = os.path.abspath(os.path.join(podium_dir, path))
    return path


async def _create_connector(database_url: str) -> tuple[Any, str]:
    """Create the appropriate DataPulse connector from the database URL."""
    if database_url.startswith("postgresql"):
        from metronome_pulse_postgres import PostgresPulse

        kwargs = _parse_pg_url(database_url)
        conn = PostgresPulse(**kwargs)
        return conn, "postgresql"
    else:
        from metronome_pulse_sqlite import SQLitePulse

        path = _parse_sqlite_path(database_url)
        conn = SQLitePulse(path)
        return conn, "sqlite"


async def init_db() -> None:
    """Initialize database: create connector, create executor, run seeding."""
    global connector, dialect, _executor

    from datametronome_podium.core.config import settings

    connector, dialect = await _create_connector(settings.database_url)
    adapter = QueryAdapter(dialect)
    _executor = QueryExecutor(connector, adapter)

    await connector.connect()
    logger.info("Database connected (dialect=%s)", dialect)

    # Run migrations (pass connector directly to avoid circular imports)
    from datametronome_podium.core.migrations.runner import run_migrations

    await run_migrations(connector, dialect)

    # Seed default data
    from datametronome_podium.core.seeding import create_default_admin
    await create_default_admin(_executor)

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close the database connector."""
    global connector, _executor
    if connector:
        await connector.close()
        connector = None
        _executor = None


async def get_db():
    """Get the raw DataPulse connector instance (for edge cases)."""
    global connector
    if not connector:
        await init_db()
    return connector


def get_executor() -> QueryExecutor:
    """Get the QueryExecutor instance. Primary way to access the database."""
    if _executor is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _executor


# --- Backward compatibility (deprecated, will be removed in feature slice migration) ---
# These functions allow existing code to keep working during the transition.


async def execute_query(sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    """DEPRECATED: Use get_executor().query() instead."""
    return await get_executor().query(sql, params)


async def execute_write(sql: str, params: list[Any] | None = None) -> bool:
    """DEPRECATED: Use get_executor().execute() instead."""
    try:
        await get_executor().execute(sql, params)
        return True
    except Exception:
        logger.exception("execute_write failed")
        return False


async def insert_data(table: str, data: dict[str, Any]) -> bool:
    """DEPRECATED: Use get_executor().insert() instead."""
    try:
        await get_executor().insert(table, data)
        return True
    except Exception:
        logger.exception("insert_data failed for table=%s", table)
        return False


async def update_data(
    table: str, data: dict[str, Any], where_clause: str, where_params: list[Any]
) -> bool:
    """DEPRECATED: Use get_executor().update() instead."""
    set_clauses = [f"{k} = ?" for k in data.keys()]
    set_values = list(data.values())
    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_clause}"
    all_params = set_values + where_params
    try:
        await get_executor().execute(sql, all_params)
        return True
    except Exception:
        logger.exception("update_data failed")
        return False


async def delete_data(table: str, where_clause: str, where_params: list[Any]) -> bool:
    """DEPRECATED: Use get_executor().execute() instead."""
    try:
        await get_executor().execute(
            f"DELETE FROM {table} WHERE {where_clause}", where_params
        )
        return True
    except Exception:
        logger.exception("delete_data failed")
        return False


async def get_db_connection_status() -> bool:
    """Check database connection health."""
    global connector
    try:
        if not connector:
            return False
        result = await connector.query("SELECT 1")
        return result is not None
    except Exception:
        logger.error("Database health check failed", exc_info=True)
        return False
