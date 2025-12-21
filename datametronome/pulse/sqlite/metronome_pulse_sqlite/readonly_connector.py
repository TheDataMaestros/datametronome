import re
import sqlite3
from pathlib import Path

from metronome_pulse_core.interfaces import Pulse, Readable


class SQLiteReadonlyPulse(Pulse, Readable):
    """Read-only SQLite DataPulse connector.

    This connector ONLY provides read access to SQLite.
    Business logic and table creation are handled by Podium.

    Features:
    - Enforced read-only operations (SELECT, WITH, PRAGMA, EXPLAIN only)
    - Connection health validation
    - Context manager support for automatic resource cleanup
    - Improved error handling with specific exception types
    - SQL injection protection via parameterized queries
    - Optimized concurrency settings (WAL mode, busy timeout)

    Example:
        async with SQLiteReadonlyPulse("mydb.db") as pulse:
            await pulse.connect()
            results = await pulse.query("SELECT * FROM users")
    """

    # Allowed read-only SQL statement prefixes
    _READ_ONLY_PREFIXES = ("select", "with", "pragma", "explain")

    def __init__(self, database_path="datametronome.db"):
        """Initialize the read-only SQLite connector.

        Args:
            database_path: Path to the SQLite database file
        """
        self.database_path = database_path
        self.connection = None

    async def connect(self) -> None:
        """Connect to SQLite database with optimized settings.

        Raises:
            ConnectionError: If connection cannot be established
            OSError: If database path is invalid or inaccessible
        """
        if self.connection is not None:
            # Already connected, verify connection is still valid
            try:
                self.connection.execute("SELECT 1").fetchone()
                return
            except (sqlite3.Error, AttributeError):
                # Connection is stale, reset it
                self.connection = None

        try:
            # Ensure directory exists
            db_path = Path(self.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database (tables should already exist from Podium)
            self.connection = sqlite3.connect(
                str(db_path), timeout=30, check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access

            # Optimize concurrency behavior for read-heavy workloads
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA foreign_keys=OFF")  # Disable FK checks for read-only

        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to SQLite database: {e}")
        except OSError as e:
            raise ConnectionError(f"Database path error: {e}")

    async def close(self) -> None:
        """Close SQLite connection safely.

        Handles connection cleanup and ensures resources are released.
        """
        if self.connection:
            try:
                self.connection.close()
            except sqlite3.Error:
                # Ignore errors during close
                pass
            finally:
                self.connection = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def is_connected(self) -> bool:
        """Check if connected to SQLite and connection is healthy.

        Returns:
            True if connected and connection is valid, False otherwise
        """
        if self.connection is None:
            return False

        try:
            # Verify connection is actually working
            self.connection.execute("SELECT 1").fetchone()
            return True
        except (sqlite3.Error, AttributeError):
            # Connection exists but is invalid
            self.connection = None
            return False

    def _validate_read_only_sql(self, sql: str) -> None:
        """Validate that SQL statement is read-only.

        Args:
            sql: SQL statement to validate

        Raises:
            RuntimeError: If SQL statement is not read-only
        """
        if not sql or not sql.strip():
            raise RuntimeError("Empty SQL statement provided")

        # Remove SQL comments and normalize whitespace
        # Remove single-line comments (-- comment)
        sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        # Remove multi-line comments (/* comment */)
        sql_clean = re.sub(r"/\*.*?\*/", "", sql_clean, flags=re.DOTALL)
        # Normalize whitespace
        sql_clean = " ".join(sql_clean.split())

        sql_op = sql_clean.lstrip().lower()

        # Check if statement starts with allowed read-only prefix
        if not any(sql_op.startswith(prefix) for prefix in self._READ_ONLY_PREFIXES):
            raise RuntimeError(
                f"Readonly SQLite connector cannot execute write statements. "
                f"Detected operation: {sql_op.split()[0] if sql_op else 'unknown'}. "
                f"Only SELECT, WITH, PRAGMA, and EXPLAIN statements are allowed. "
                f"Use db.execute/db.write instead for write operations."
            )

    def _ensure_connected(self) -> None:
        """Ensure connection exists and is valid.

        Raises:
            RuntimeError: If not connected to SQLite database
        """
        if not self.connection:
            raise RuntimeError(
                "Not connected to SQLite database. Call connect() first."
            )

    async def query(self, query_config):
        """Query data from SQLite.

        Args:
            query_config: Can be:
                - str: Direct SQL query string
                - dict: Query configuration with 'sql' and optional 'params' keys

        Returns:
            List of dictionaries representing query results (one dict per row)

        Raises:
            RuntimeError: If not connected or query validation fails
            sqlite3.Error: If SQLite operation fails
        """
        self._ensure_connected()

        # Parse query_config
        if isinstance(query_config, str):
            sql = query_config
            params = None
        elif isinstance(query_config, dict):
            sql = query_config.get("sql", "")
            params = query_config.get("params")
        else:
            raise RuntimeError(
                f"Invalid query_config type: {type(query_config).__name__}. "
                "Expected str or dict."
            )

        if not sql:
            raise RuntimeError("SQL query cannot be empty")

        # Validate read-only
        self._validate_read_only_sql(sql)

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except sqlite3.Error as e:
            raise RuntimeError(f"Query execution failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during query: {e}")

    async def query_with_params(self, sql, params):
        """Execute parameterized query (convenience method).

        Args:
            sql: SQL query string with placeholders
            params: Parameters for the query (list, tuple, or dict)

        Returns:
            List of dictionaries representing query results

        Raises:
            RuntimeError: If not connected or query validation fails
            sqlite3.Error: If SQLite operation fails
        """
        return await self.query({"sql": sql, "params": params})

    async def get_table_info(self, table_name):
        """Get table schema information.

        Args:
            table_name: Name of the table to inspect

        Returns:
            List of dictionaries with column information:
            - cid: Column ID
            - name: Column name
            - type: Column type
            - notnull: Not null constraint (0 or 1)
            - dflt_value: Default value
            - pk: Primary key (0 or 1)

        Raises:
            RuntimeError: If not connected or table doesn't exist
            sqlite3.Error: If SQLite operation fails
        """
        self._ensure_connected()

        if not table_name or not isinstance(table_name, str):
            raise RuntimeError("Table name must be a non-empty string")

        # Sanitize table name to prevent SQL injection
        # Only allow alphanumeric, underscore, and dot characters
        if not re.match(r"^[a-zA-Z0-9_.]+$", table_name):
            raise RuntimeError(
                f"Invalid table name: {table_name}. "
                "Only alphanumeric characters, underscores, and dots are allowed."
            )

        try:
            cursor = self.connection.cursor()
            # Use parameterized query for safety (though table names can't be parameterized in PRAGMA)
            # So we validate the table name above instead
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            return [dict(col) for col in columns]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get table info for '{table_name}': {e}")

    async def list_tables(self):
        """List all tables in the database.

        Returns:
            List of table names (strings)

        Raises:
            RuntimeError: If not connected
            sqlite3.Error: If SQLite operation fails
        """
        self._ensure_connected()

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = cursor.fetchall()
            return [table[0] for table in tables]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to list tables: {e}")

    async def test_connection(self) -> bool:
        """Test if connection is working by executing a simple query.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not await self.is_connected():
                return False
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:
            return False
