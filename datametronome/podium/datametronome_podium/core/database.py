"""
Database initialization and management for DataMetronome Podium.

Connector-agnostic: picks PostgresPulse or SQLitePulse based on database_url.
"""
import logging
from typing import Any
from urllib.parse import urlparse

from datametronome_podium.core.query_adapter import QueryAdapter

logger = logging.getLogger(__name__)

# Global state
connector: Any | None = None
dialect: str = "postgresql"
_adapter: QueryAdapter | None = None


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


def _get_adapter() -> QueryAdapter:
    """Get the QueryAdapter for the current dialect."""
    global _adapter
    if _adapter is None:
        _adapter = QueryAdapter(dialect)
    return _adapter


async def init_db() -> None:
    """Initialize database: create connector, run migrations, seed data."""
    global connector, dialect, _adapter

    from datametronome_podium.core.config import settings

    connector, dialect = await _create_connector(settings.database_url)
    _adapter = QueryAdapter(dialect)

    await connector.connect()
    logger.info("Database connected (dialect=%s)", dialect)

    # Run migrations (pass connector directly to avoid circular imports)
    from datametronome_podium.core.migrations.runner import run_migrations

    await run_migrations(connector, dialect)

    # Create default admin user
    await _create_default_admin()

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close the database connector."""
    global connector
    if connector:
        await connector.close()
        connector = None


async def get_db():
    """Get the DataPulse connector instance."""
    global connector
    if not connector:
        await init_db()
    return connector


# --- Normalized helper functions ---


async def execute_query(
    sql: str, params: list[Any] | None = None
) -> list[dict[str, Any]]:
    """Execute a query and return results as list of dicts."""
    adapter = _get_adapter()
    adapted_sql, adapted_params = adapter.adapt(sql, params)
    conn = await get_db()

    if adapted_params:
        return await conn.query({"sql": adapted_sql, "params": adapted_params})
    else:
        return await conn.query(adapted_sql)


async def execute_write(sql: str, params: list[Any] | None = None) -> bool:
    """Execute a write statement (INSERT/UPDATE/DELETE). Returns True on success."""
    adapter = _get_adapter()
    adapted_sql, adapted_params = adapter.adapt(sql, params)
    conn = await get_db()

    try:
        if dialect == "postgresql":
            await conn.execute(adapted_sql, *adapted_params) if adapted_params else await conn.execute(adapted_sql)
        else:
            await conn.execute(adapted_sql, adapted_params) if adapted_params else await conn.execute(adapted_sql)
        return True
    except Exception:
        logger.exception("execute_write failed")
        return False


async def insert_data(table: str, data: dict[str, Any]) -> bool:
    """Insert a single row into a table."""
    conn = await get_db()

    try:
        if dialect == "sqlite":
            result = await conn.write([data], table)
            return bool(result) if result is not None else True
        else:
            columns = list(data.keys())
            placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
            col_names = ", ".join(columns)
            sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
            values = list(data.values())
            await conn.execute(sql, *values)
            return True
    except Exception:
        logger.exception("insert_data failed for table=%s", table)
        return False


async def update_data(
    table: str, data: dict[str, Any], where_clause: str, where_params: list[Any]
) -> bool:
    """Update rows in a table."""
    adapter = _get_adapter()

    set_clauses = [f"{k} = ?" for k in data.keys()]
    set_values = list(data.values())
    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_clause}"
    all_params = set_values + where_params

    adapted_sql, adapted_params = adapter.adapt(sql, all_params)
    conn = await get_db()

    try:
        if dialect == "postgresql":
            await conn.execute(adapted_sql, *adapted_params)
        else:
            await conn.execute(adapted_sql, adapted_params)
        return True
    except Exception:
        logger.exception("update_data failed")
        return False


async def delete_data(table: str, where_clause: str, where_params: list[Any]) -> bool:
    """Delete rows from a table."""
    adapter = _get_adapter()
    adapted_where, adapted_params = adapter.adapt(
        f"DELETE FROM {table} WHERE {where_clause}", where_params
    )
    conn = await get_db()

    try:
        if dialect == "postgresql":
            await conn.execute(adapted_where, *adapted_params) if adapted_params else await conn.execute(adapted_where)
        else:
            await conn.execute(adapted_where, adapted_params) if adapted_params else await conn.execute(adapted_where)
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


async def _create_default_admin() -> None:
    """Create default admin user for development."""
    try:
        existing = await execute_query(
            "SELECT * FROM users WHERE username = ?", ["admin"]
        )
        if existing:
            logger.info("Admin user already exists")
            return

        from datametronome_podium.api.v1.endpoints.auth import get_password_hash

        await insert_data("users", {
            "id": "admin-001",
            "username": "admin",
            "email": "admin@datametronome.dev",
            "hashed_password": get_password_hash("admin"),
            "is_active": True,
            "is_superuser": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        })
        logger.info("Default admin user created (admin/admin)")
    except Exception as e:
        logger.warning("Could not create default admin user: %s", e)
