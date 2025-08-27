"""
Database initialization and management for DataMetronome Podium.
"""

import asyncio
import logging
from typing import List, Dict, Any

from metronome_pulse_sqlite import SQLitePulse

logger = logging.getLogger(__name__)

# Global connector instance
sqlite_connector: SQLitePulse | None = None


async def init_db() -> None:
    """Initialize database with tables and default data."""
    global sqlite_connector
    
    try:
        # Create SQLite connector
        sqlite_connector = SQLitePulse("data/datametronome.db")
        
        # Connect to the database
        await sqlite_connector.connect()
        
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
        """
    ]
    
    for table_sql in tables:
        await sqlite_connector.execute(table_sql)


async def _create_default_admin() -> None:
    """Create default admin user for showcase and development."""
    try:
        # Check if admin user already exists
        existing_users = await sqlite_connector.query({
            "sql": "SELECT * FROM users WHERE username = ?",
            "params": ["admin"]
        })
        
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
            "updated_at": "2025-01-01T00:00:00Z"
        }
        
        success = await sqlite_connector.write([{"table": "users", **admin_user}], "users")
        
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
async def execute_query(sql: str, params: List[Any] = None) -> List[Dict[str, Any]]:
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
    return await connector.write([{"table": table, **data}], table)


async def update_data(table: str, data: Dict[str, Any], where_clause: str, where_params: List[Any]) -> bool:
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
