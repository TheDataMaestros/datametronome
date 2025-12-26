"""
Database initialization and management for DataMetronome Podium.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List

from metronome_pulse_sqlite import SQLitePulse

logger = logging.getLogger(__name__)


# region agent log
def _agent_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        payload = {
            "sessionId": "debug-session",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(
            "/Users/totolasso/repos/personal/datametronome/.cursor/debug.log",
            "a",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


# endregion

# Global connector instance
sqlite_connector: SQLitePulse | None = None


async def init_db() -> None:
    """Initialize database with tables and default data."""
    global sqlite_connector

    try:
        # Create SQLite connector using configured database URL
        import os

        from datametronome_podium.core.config import settings

        db_path = (
            settings.database_url.replace("sqlite+aiosqlite:///", "")
            .replace("sqlite:///", "")
            .replace("./", "")
        )
        full_path = os.path.abspath(db_path)
        print(f"DEBUG: init_db using path: {full_path}")
        print(f"DEBUG: File exists? {os.path.exists(full_path)}")
        # region agent log
        _agent_log(
            "H_DB_PATH",
            "datametronome_podium/core/database.py:init_db",
            "init_db resolved sqlite path",
            {
                "database_url_scheme": "sqlite"
                if settings.database_url.startswith("sqlite")
                else "non-sqlite",
                "db_path": db_path,
                "full_path": full_path,
                "exists": bool(os.path.exists(full_path)),
            },
        )
        # endregion
        sqlite_connector = SQLitePulse(db_path)

        # Connect to the database
        await sqlite_connector.connect()
        print(f"DEBUG: Connected. Connector path: {sqlite_connector.database_path}")

        # Check columns of clefs table
        try:
            cols = await sqlite_connector.query(
                {"sql": "PRAGMA table_info(clefs)", "params": []}
            )
            print(f"DEBUG: Clefs table columns: {[c['name'] for c in cols]}")
        except Exception as e:
            print(f"DEBUG: Could not check schema: {e}")

        # Immediately check if clefs table has data
        try:
            test_count = await sqlite_connector.query(
                {"sql": "SELECT COUNT(*) as count FROM clefs", "params": []}
            )
            print(
                f"DEBUG: Clefs in database RIGHT AFTER CONNECT: {test_count[0]['count']}"
            )
            staves_count = await sqlite_connector.query(
                {"sql": "SELECT COUNT(*) as count FROM staves", "params": []}
            )
            print(
                f"DEBUG: Staves in database RIGHT AFTER CONNECT: {staves_count[0]['count']}"
            )
        except Exception as e:
            print(f"DEBUG: Could not check data counts: {e}")

        # Create tables
        await _create_tables()

        # Create default admin user
        await _create_default_admin()

        logger.info("✅ Database initialized successfully")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def _create_tables() -> None:
    """Create database tables."""
    tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS staves (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            data_source_type TEXT NOT NULL,
            connection_config TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS clefs (
            id TEXT PRIMARY KEY,
            stave_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            check_type TEXT NOT NULL,
            config TEXT NOT NULL,
            warn TEXT,
            fail TEXT,
            retry_config TEXT,
            schedule TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (stave_id) REFERENCES staves (id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS checks (
            id TEXT PRIMARY KEY,
            stave_id TEXT NOT NULL,
            clef_id TEXT NOT NULL,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            details TEXT,
            timestamp TEXT NOT NULL,
            execution_time REAL,
            anomalies_count INTEGER DEFAULT 0,
            severity TEXT DEFAULT 'medium',
            FOREIGN KEY (stave_id) REFERENCES staves (id),
            FOREIGN KEY (clef_id) REFERENCES clefs (id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS scheduler_jobs (
            id TEXT PRIMARY KEY,
            clef_id TEXT NOT NULL,
            schedule TEXT NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            last_run_time TEXT,
            next_run_time TEXT,
            execution_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS job_executions (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            clef_id TEXT NOT NULL,
            status TEXT NOT NULL,
            execution_time REAL,
            error_message TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (job_id) REFERENCES scheduler_jobs (id) ON DELETE CASCADE,
            FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS anomalies (
            id TEXT PRIMARY KEY,
            check_id TEXT NOT NULL,
            table_name TEXT,
            column_name TEXT,
            anomaly_type TEXT NOT NULL,
            description TEXT,
            severity TEXT DEFAULT 'medium',
            detected_at TEXT NOT NULL,
            data_sample TEXT,
            resolution_status TEXT DEFAULT 'investigating',
            FOREIGN KEY (check_id) REFERENCES checks (id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            tool_calls TEXT,
            tool_results TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """,
    ]

    for table_sql in tables:
        assert sqlite_connector is not None
        await sqlite_connector.execute(table_sql)

    # Create indexes for chat_messages
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at)",
    ]
    for index_sql in indexes:
        assert sqlite_connector is not None
        try:
            await sqlite_connector.execute(index_sql)
        except Exception as e:
            # Index might already exist, ignore
            logger.debug(f"Index creation (may already exist): {e}")


async def _create_default_admin() -> None:
    """Create default admin user for showcase and development."""
    try:
        # Check if admin user already exists
        assert sqlite_connector is not None
        existing_users = await sqlite_connector.query(
            {"sql": "SELECT * FROM users WHERE username = ?", "params": ["admin"]}
        )

        if existing_users:
            logger.info("Admin user already exists")
            return

        # Import here to avoid circular imports
        from datametronome_podium.api.v1.endpoints.auth import get_password_hash

        # Create admin user
        admin_user = {
            "id": "admin-001",
            "username": "admin",
            "email": "admin@datametronome.dev",
            "hashed_password": get_password_hash("admin"),
            "is_active": True,
            "is_superuser": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        assert sqlite_connector is not None
        success = await sqlite_connector.write(
            [{"table": "users", **admin_user}], "users"
        )

        if success:
            logger.info("✅ Default admin user created successfully")
            logger.info("   Username: admin")
            logger.info("   Password: admin")
            logger.info("   Email: admin@datametronome.dev")
        else:
            logger.warning("⚠️ Failed to create default admin user")

    except Exception as e:
        logger.warning(f"⚠️ Could not create default admin user: {e}")


async def get_db():
    """Get DataPulse SQLite connector instance."""
    global sqlite_connector
    if not sqlite_connector:
        await init_db()
    return sqlite_connector


async def close_db():
    """Close DataPulse SQLite connector."""
    global sqlite_connector
    if sqlite_connector:
        await sqlite_connector.close()
        sqlite_connector = None


# Helper functions for common database operations
async def execute_query(
    sql: str, params: List[Any] | None = None
) -> List[Dict[str, Any]]:
    """Execute a query and return results."""
    connector = await get_db()
    if params:
        return await connector.query({"sql": sql, "params": params})
    else:
        return await connector.query(sql)


async def execute_write(operations: List[Dict[str, Any]]) -> bool:
    """Execute write operations."""
    connector = await get_db()
    return await connector.write(operations, "operations")


async def insert_data(table: str, data: Dict[str, Any]) -> bool:
    """Insert data into a table."""
    connector = await get_db()
    # region agent log
    _agent_log(
        "H_INSERT_DATA",
        "datametronome_podium/core/database.py:insert_data",
        "insert_data called",
        {"table": table, "id": data.get("id"), "keys": sorted(list(data.keys()))},
    )
    # endregion
    return await connector.write([{"table": table, **data}], table)


async def update_data(
    table: str, data: Dict[str, Any], where_clause: str, where_params: List[Any]
) -> bool:
    """Update data in a table."""
    # Build UPDATE SQL
    set_clauses = [f"{k} = ?" for k in data.keys()]
    set_values = list(data.values())

    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_clause}"
    params = set_values + where_params

    connector = await get_db()
    return await connector.execute(sql, params)


async def delete_data(table: str, where_clause: str, where_params: List[Any]) -> bool:
    """Delete data from a table."""
    sql = f"DELETE FROM {table} WHERE {where_clause}"
    connector = await get_db()
    return await connector.execute(sql, where_params)


async def get_db_connection_status() -> bool:
    """
    Check database connection health.

    Returns:
        bool: True if database is connected and responsive, False otherwise.
    """
    global sqlite_connector
    try:
        if not sqlite_connector:
            return False

        # Try a simple query to verify connectivity
        result = await sqlite_connector.query("SELECT 1")
        return result is not None
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
