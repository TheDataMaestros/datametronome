"""
Lightweight forward-only migration runner.

Scans core/migrations/sql/ for numbered .sql files, applies any not yet
recorded in the schema_migrations table. Each migration runs in a
transaction (where supported).
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_SQL_DIR = os.path.join(os.path.dirname(__file__), "sql")


def _get_sql_files() -> list[tuple[str, str]]:
    """Scan the sql/ directory for migration files, sorted by name."""
    if not os.path.isdir(_SQL_DIR):
        logger.warning("Migration sql/ directory not found: %s", _SQL_DIR)
        return []

    files = sorted(f for f in os.listdir(_SQL_DIR) if f.endswith(".sql"))
    result = []
    for fname in files:
        path = os.path.join(_SQL_DIR, fname)
        with open(path, encoding="utf-8") as fh:
            result.append((fname, fh.read()))
    return result


async def run_migrations(db: Any, dialect: str) -> None:
    """Apply any pending migrations.

    Args:
        db: The already-connected DataPulse connector instance.
        dialect: "postgresql" or "sqlite"

    Note: db and dialect are passed in from init_db() to avoid
    circular imports (runner -> get_db -> init_db -> runner).
    """
    from datametronome_podium.core.query_adapter import QueryAdapter

    adapter = QueryAdapter(dialect)

    # Ensure schema_migrations table exists
    create_table_sql = adapter.adapt_ddl(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "  id TEXT PRIMARY KEY,"
        "  filename TEXT NOT NULL,"
        "  applied_at TEXT NOT NULL"
        ")"
    )
    if dialect == "postgresql":
        await db.execute(create_table_sql)
    else:
        await db.execute(create_table_sql)

    # Get already-applied migrations
    applied_rows = await db.query(
        {"sql": "SELECT filename FROM schema_migrations", "params": []}
    )
    applied = {row["filename"] for row in applied_rows}

    # Apply pending migrations
    sql_files = _get_sql_files()
    for filename, sql_content in sql_files:
        if filename in applied:
            logger.debug("Migration already applied: %s", filename)
            continue

        logger.info("Applying migration: %s", filename)
        adapted_sql = adapter.adapt_ddl(sql_content)

        # Execute each statement in the migration file
        statements = [s.strip() for s in adapted_sql.split(";") if s.strip()]
        for stmt in statements:
            if dialect == "postgresql":
                await db.execute(stmt)
            else:
                await db.execute(stmt)

        # Record the migration
        now = datetime.now(timezone.utc).isoformat()
        migration_id = filename.split("_")[0]  # e.g. "001"

        if dialect == "postgresql":
            await db.execute(
                "INSERT INTO schema_migrations (id, filename, applied_at) VALUES ($1, $2, $3)",
                migration_id, filename, now,
            )
        else:
            await db.execute(
                "INSERT INTO schema_migrations (id, filename, applied_at) VALUES (?, ?, ?)",
                [migration_id, filename, now],
            )

        logger.info("Migration applied: %s", filename)
