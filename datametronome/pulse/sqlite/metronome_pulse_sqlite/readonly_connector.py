import asyncio
import sqlite3
from pathlib import Path

from metronome_pulse_core.interfaces import Pulse, Readable

# Removed typing imports as requested


class SQLiteReadonlyPulse(Pulse, Readable):
    """Read-only SQLite DataPulse connector.

    This connector ONLY provides read access to SQLite.
    Business logic and table creation are handled by Podium.
    """

    def __init__(self, database_path="datametronome.db"):
        self.database_path = database_path
        self.connection = None

    async def connect(self) -> None:
        """Connect to SQLite database."""
        try:
            # Ensure directory exists
            db_path = Path(self.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database (tables should already exist from Podium)
            self.connection = sqlite3.connect(self.database_path, timeout=30)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            # Improve concurrency behavior (best-effort)
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQLite: {e}")

    async def close(self) -> None:
        """Close SQLite connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    async def is_connected(self) -> bool:
        """Check if connected to SQLite."""
        return self.connection is not None

    async def query(self, query_config):
        """Query data from SQLite."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")

        try:
            if isinstance(query_config, str):
                sql = query_config
                sql_op = sql.lstrip().lower()
                # Guardrail: this connector should only be used for read statements.
                if not (
                    sql_op.startswith("select")
                    or sql_op.startswith("with")
                    or sql_op.startswith("pragma")
                    or sql_op.startswith("explain")
                ):
                    raise RuntimeError(
                        "Readonly SQLite connector cannot execute write statements. "
                        "Use db.execute/db.write instead."
                    )

                cursor = self.connection.cursor()
                cursor.execute(sql)
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                # Query with parameters
                sql = query_config.get("sql", "")
                params = query_config.get("params", [])

                sql_op = sql.lstrip().lower()
                if not (
                    sql_op.startswith("select")
                    or sql_op.startswith("with")
                    or sql_op.startswith("pragma")
                    or sql_op.startswith("explain")
                ):
                    raise RuntimeError(
                        "Readonly SQLite connector cannot execute write statements. "
                        "Use db.execute/db.write instead."
                    )

                cursor = self.connection.cursor()
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(f"Query failed: {e}")

    async def query_with_params(self, sql, params):
        """Execute parameterized query."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")

        try:
            sql_op = sql.lstrip().lower()
            if not (
                sql_op.startswith("select")
                or sql_op.startswith("with")
                or sql_op.startswith("pragma")
                or sql_op.startswith("explain")
            ):
                raise RuntimeError(
                    "Readonly SQLite connector cannot execute write statements. "
                    "Use db.execute/db.write instead."
                )

            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(f"Parameterized query failed: {e}")

    async def get_table_info(self, table_name):
        """Get table schema information."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            return [dict(col) for col in columns]
        except Exception as e:
            raise RuntimeError(f"Failed to get table info: {e}")

    async def list_tables(self):
        """List all tables in the database."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")

        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            return [table[0] for table in tables]
        except Exception as e:
            raise RuntimeError(f"Failed to list tables: {e}")
