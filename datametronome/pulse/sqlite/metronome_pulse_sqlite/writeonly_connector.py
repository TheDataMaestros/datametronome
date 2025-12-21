import asyncio
import json
import sqlite3
import time
from pathlib import Path

from metronome_pulse_core.interfaces import Pulse, Writable

# Removed typing imports as requested


class SQLiteWriteonlyPulse(Pulse, Writable):
    """Write-only SQLite DataPulse connector.

    This connector ONLY provides write access to SQLite.
    Business logic and table creation are handled by Podium.
    """

    def __init__(self, database_path="datametronome.db"):
        self.database_path = database_path
        self.connection = None
        # Serialize writes to avoid "database is locked" under concurrent access.
        self._write_lock = asyncio.Lock()

    # region agent log
    def _agent_log(
        self, hypothesis_id: str, location: str, message: str, data: dict
    ) -> None:
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
            if not self.connection:
                raise ConnectionError("Failed to establish connection")
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

    async def write(self, data, destination: str, config: dict | None = None):
        """Write data to SQLite."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")

        if not config:
            config = {"type": "insert"}

        operation_type = config.get("type", "insert")

        async with self._write_lock:
            try:
                # region agent log
                tables = []
                try:
                    tables = sorted(
                        {
                            str((r or {}).get("table"))
                            for r in (data or [])
                            if (r or {}).get("table")
                        }
                    )
                except Exception:
                    tables = []
                first_id = None
                try:
                    first_id = (data or [{}])[0].get("id")
                except Exception:
                    first_id = None
                self._agent_log(
                    "H_SQLITE_WRITE",
                    "metronome_pulse_sqlite/writeonly_connector.py:write",
                    "sqlite write called",
                    {
                        "db_path": str(self.database_path),
                        "operation_type": operation_type,
                        "records": len(data) if data is not None else None,
                        "tables": tables,
                        "first_id": first_id,
                    },
                )
                # endregion
                if operation_type == "insert":
                    return await self._insert_data(data)
                elif operation_type == "replace":
                    return await self._replace_data(data)
                elif operation_type == "operations":
                    return await self._execute_operations(data)
                else:
                    raise ValueError(f"Unsupported operation type: {operation_type}")
            except Exception as e:
                # region agent log
                self._agent_log(
                    "H_SQLITE_WRITE_EXCEPTION",
                    "metronome_pulse_sqlite/writeonly_connector.py:write",
                    "sqlite write raised exception",
                    {
                        "db_path": str(self.database_path),
                        "operation_type": operation_type,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                )
                # endregion
                raise RuntimeError(f"Write operation failed: {e}")

    async def _insert_data(self, data):
        """Insert data into tables (tables must already exist from Podium)."""
        try:
            # region agent log
            tables = []
            try:
                tables = sorted(
                    {
                        str((r or {}).get("table"))
                        for r in (data or [])
                        if (r or {}).get("table")
                    }
                )
            except Exception:
                tables = []
            self._agent_log(
                "H_SQLITE_INSERT",
                "metronome_pulse_sqlite/writeonly_connector.py:_insert_data",
                "sqlite insert starting",
                {
                    "db_path": str(self.database_path),
                    "records": len(data) if data is not None else None,
                    "tables": tables,
                },
            )
            # endregion
            for record in data:
                # Extract table name and data from record
                table_name = record.get("table")
                if not table_name:
                    print("No table name specified in record")
                    continue

                # Remove table name from data
                insert_data = {k: v for k, v in record.items() if k != "table"}

                # Build INSERT statement
                columns = list(insert_data.keys())
                placeholders = ", ".join(["?" for _ in columns])
                values = list(insert_data.values())

                sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                if not self.connection:
                    raise RuntimeError("Not connected")
                cursor = self.connection.cursor()
                cursor.execute(sql, values)

            if not self.connection:
                raise RuntimeError("Not connected to database")
            self.connection.commit()
            return True
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            # region agent log
            self._agent_log(
                "H_SQLITE_INSERT_EXCEPTION",
                "metronome_pulse_sqlite/writeonly_connector.py:_insert_data",
                "sqlite insert failed",
                {
                    "db_path": str(self.database_path),
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            # endregion
            raise RuntimeError(f"Insert failed: {e}")

    async def _replace_data(self, data):
        """Replace data using delete and insert strategy."""
        try:
            for record in data:
                table_name = record.get("table")
                if not table_name:
                    continue

                # Extract primary key for deletion
                primary_key = record.get("id")
                if primary_key:
                    # Delete existing record
                    if not self.connection:
                        raise RuntimeError("Not connected")
                    cursor = self.connection.cursor()
                    cursor.execute(
                        f"DELETE FROM {table_name} WHERE id = ?", (primary_key,)
                    )

            # Insert new data
            return await self._insert_data(data)
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise RuntimeError(f"Replace failed: {e}")

    async def _execute_operations(self, operations):
        """Execute a list of mixed SQL operations."""
        try:
            for operation in operations:
                op_type = operation.get("type")
                sql = operation.get("sql", "")
                params = operation.get("params", [])

                if not self.connection:
                    raise RuntimeError("Not connected")
                cursor = self.connection.cursor()

                if op_type == "insert":
                    cursor.execute(sql, params)
                elif op_type == "delete":
                    cursor.execute(sql, params)
                elif op_type == "update":
                    cursor.execute(sql, params)
                elif op_type == "create_table":
                    cursor.execute(sql)
                elif op_type == "partition":
                    cursor.execute(sql)
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")

            if not self.connection:
                raise RuntimeError("Not connected to database")
            self.connection.commit()
            return True
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise RuntimeError(f"Operations failed: {e}")

    async def execute(self, sql, params=None):
        """Execute raw SQL."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")

        async with self._write_lock:
            try:
                if not self.connection:
                    raise RuntimeError("Not connected")
                cursor = self.connection.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                if not self.connection:
                    raise RuntimeError("Not connected to database")
                self.connection.commit()
                return True
            except Exception as e:
                if self.connection:
                    self.connection.rollback()
                raise RuntimeError(f"Execute failed: {e}")

    async def copy_records(self, table_name, records):
        """Bulk insert records using SQLite's efficient INSERT."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")

        if not records:
            return True

        async with self._write_lock:
            try:
                # Get column names from first record
                columns = list(records[0].keys())
                placeholders = ", ".join(["?" for _ in columns])

                sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                if not self.connection:
                    raise RuntimeError("Not connected")
                cursor = self.connection.cursor()

                # Prepare all values
                values = [[record.get(col) for col in columns] for record in records]

                # Execute batch insert
                cursor.executemany(sql, values)

                if not self.connection:
                    raise RuntimeError("Not connected to database")
                self.connection.commit()
                return True
            except Exception as e:
                if self.connection:
                    self.connection.rollback()
                raise RuntimeError(f"Copy records failed: {e}")
