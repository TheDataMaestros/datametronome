"""
PostgreSQL DataPulse connector using asyncpg.

This connector provides high-performance, async-first PostgreSQL connectivity
with connection pooling and full support for the DataPulse ecosystem.
"""

import asyncpg
from metronome_pulse_core import Pulse, Readable, Writable


class PostgresPulse(Pulse, Readable, Writable):
    """Full-featured PostgreSQL DataPulse connector using asyncpg.

    Implements all interfaces: Pulse, Readable, and Writable.
    """

    def __init__(
        self,
        host="localhost",
        port=5432,
        database=None,
        user=None,
        password=None,
        **kwargs,
    ):
        """Initialize the PostgreSQL connector.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database username
            password: Database password
            **kwargs: Additional connection parameters
        """
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._kwargs = kwargs
        self._pool = None
        self._txn_conn = None  # Transaction connection
        self._txn = None       # Transaction object

    async def _get_conn(self):
        """Get the active transaction connection, or acquire from pool."""
        if self._txn_conn is not None:
            return self._txn_conn, False  # (conn, should_release)
        conn = await self._pool.acquire()
        return conn, True

    async def _release_conn(self, conn, should_release):
        """Release connection back to pool if not in a transaction."""
        if should_release:
            await self._pool.release(conn)

    async def begin_transaction(self) -> None:
        """Begin a transaction. Acquires a dedicated connection from the pool."""
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        if self._txn_conn is not None:
            raise RuntimeError("Transaction already active.")
        self._txn_conn = await self._pool.acquire()
        self._txn = self._txn_conn.transaction()
        await self._txn.start()

    async def commit_transaction(self) -> None:
        """Commit the current transaction and release the connection."""
        if self._txn is None:
            raise RuntimeError("No active transaction to commit.")
        try:
            await self._txn.commit()
        finally:
            if self._pool and self._txn_conn:
                await self._pool.release(self._txn_conn)
            self._txn = None
            self._txn_conn = None

    async def rollback_transaction(self) -> None:
        """Roll back the current transaction and release the connection."""
        if self._txn is None:
            raise RuntimeError("No active transaction to rollback.")
        try:
            await self._txn.rollback()
        finally:
            if self._pool and self._txn_conn:
                await self._pool.release(self._txn_conn)
            self._txn = None
            self._txn_conn = None

    async def connect(self):
        """Establish connection pool to PostgreSQL."""
        self._pool = await asyncpg.create_pool(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password,
            **self._kwargs,
        )

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def is_connected(self):
        """Check if connected to the database."""
        return self._pool is not None

    async def write(self, data, destination: str, config: dict | None = None) -> None:
        """Write data to destination with optional configuration.

        Args:
            data: list of dictionaries to write
            destination: Target table name
            config: Optional configuration dict for advanced operations

        Examples:
            # Simple insert (default)
            await pulse.write([{"id": 1, "name": "Alice"}], "users")

            # Replace operation
            await pulse.write(
                [{"id": 1, "name": "Alice Updated"}],
                "users",
                config={
                    "type": "replace",
                    "key_columns": ["id"],
                    "chunk_size": 5000,
                    "defer_constraints": True
                }
            )

            # Mixed operations
            await pulse.write(
                [],  # No data needed for operations
                "users",
                config={
                    "type": "operations",
                    "operations": [
                        {"type": "delete", "sql": "DELETE FROM users WHERE id < 0"},
                        {"type": "insert", "table": "users", "rows": [{"id": 1, "name": "Alice"}]}
                    ]
                }
            )
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")

        if config is None:
            # Default behavior: simple insert
            await self._simple_insert(data, destination)
            return

        op_type = config.get("type", "insert")

        if op_type == "replace":
            key_columns = config.get("key_columns", [])
            chunk_size = config.get("chunk_size", 5000)
            defer_constraints = config.get("defer_constraints", False)
            lock_timeout_ms = config.get("lock_timeout_ms")
            statement_timeout_ms = config.get("statement_timeout_ms")
            synchronous_commit_off = config.get("synchronous_commit_off", True)

            if chunk_size > 1:
                await self.replace_using_values_chunked(
                    destination,
                    data,
                    key_columns,
                    chunk_size=chunk_size,
                    defer_constraints=defer_constraints,
                    lock_timeout_ms=lock_timeout_ms,
                    statement_timeout_ms=statement_timeout_ms,
                    synchronous_commit_off=synchronous_commit_off,
                )
            else:
                await self.replace_using_values(
                    destination,
                    data,
                    key_columns,
                    defer_constraints=defer_constraints,
                    lock_timeout_ms=lock_timeout_ms,
                    statement_timeout_ms=statement_timeout_ms,
                    synchronous_commit_off=synchronous_commit_off,
                )

        elif op_type == "operations":
            operations = config.get("operations", [])
            insert_chunk_size = config.get("insert_chunk_size", 10000)
            await self.apply_operations(operations, insert_chunk_size=insert_chunk_size)

        else:
            # Fallback to simple insert
            await self._simple_insert(data, destination)

    async def _simple_insert(self, data, destination: str) -> None:
        """Simple insert using COPY."""
        if not data:
            return

        # Strip "table" key from records — it's metadata, not a column
        columns = [k for k in data[0].keys() if k != "table"]
        records = [tuple(record[col] for col in columns) for record in data]

        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.copy_records_to_table(
                destination,
                records=records,
                columns=columns,
            )

    async def query(self, query_config) -> list | dict:
        """Dynamic query method supporting multiple query types.

        Args:
            query_config: Can be:
                - str: Direct SQL query (default behavior)
                - dict: Query configuration with 'type' and parameters

        Examples:
            # Simple SQL query
            results = await pulse.query("SELECT * FROM users WHERE active = true")

            # Parameterized query
            results = await pulse.query({
                "type": "parameterized",
                "sql": "SELECT * FROM users WHERE age > $1 AND city = $2",
                "params": [18, "New York"]
            })

            # Table info query
            results = await pulse.query({
                "type": "table_info",
                "table_name": "users"
            })

            # Custom query with options
            results = await pulse.query({
                "type": "custom",
                "sql": "SELECT COUNT(*) as count FROM events WHERE date >= $1",
                "params": ["2025-01-01"],
                "timeout_ms": 5000
            })
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")

        # Handle query configuration dict
        if isinstance(query_config, dict):
            query_type = query_config.get("type", "custom")

            if query_type == "parameterized":
                sql = query_config.get("sql")
                params = query_config.get("params", [])
                if not sql:
                    raise ValueError("Query config dict must contain 'sql' key")
                return await self.query_with_params(sql, params if params else None)

            elif query_type == "table_info":
                table_name = query_config.get("table_name")
                if not table_name:
                    raise ValueError("Table info query must specify 'table_name'")
                return await self.get_table_info(table_name)

            elif query_type == "custom":
                sql = query_config.get("sql")
                params = query_config.get("params", [])
                timeout_ms = query_config.get("timeout_ms")

                if not sql:
                    raise ValueError("Custom query must contain 'sql' key")

                # Apply timeout if specified
                if timeout_ms:
                    # Note: asyncpg doesn't support statement_timeout per query
                    # This would need to be set at connection level
                    pass

                if params:
                    return await self.query_with_params(sql, params)
                else:
                    return await self._simple_query(sql)

            else:
                raise ValueError(f"Unsupported query type: {query_type}")

        else:
            # Handle simple SQL string (default behavior)
            return await self._simple_query(query_config)

    async def get_table_info(self, table_name: str) -> list[dict]:
        """Fetch column information for a table."""
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """
        return await self.query_with_params(sql, [table_name])

    async def list_tables(self, schema: str = "public") -> list[str]:
        """
        List all tables in the database.

        Args:
            schema: Schema name to list tables from (default: 'public')

        Returns:
            List of table names

        Raises:
            RuntimeError: If not connected to database
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")

        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = $1
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        results = await self.query_with_params(query, [schema])
        return [row["table_name"] for row in results]

    async def apply_operations(
        self, operations: list[dict], insert_chunk_size: int = 10000
    ) -> None:
        """Apply multiple operations in a single transaction."""
        if not self._pool:
            raise RuntimeError("Not connected")
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for op in operations:
                    op_type = op.get("type")
                    if op_type == "insert":
                        table = op.get("table")
                        rows = op.get("rows", [])
                        if table and rows:
                            columns = list(rows[0].keys())
                            records = [
                                tuple(row[col] for col in columns) for row in rows
                            ]
                            await conn.copy_records_to_table(
                                table, records=records, columns=columns
                            )
                    elif op_type == "delete":
                        sql = op.get("sql")
                        params = op.get("params", [])
                        if sql:
                            await conn.execute(sql, *params)

    async def _simple_query(self, sql: str) -> list:
        """Simple SQL query execution."""
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            records = await conn.fetch(sql)
            return [dict(record) for record in records]

    @staticmethod
    def _rewrite_placeholders(sql: str) -> str:
        """Replace ? placeholders with $1, $2, ... for asyncpg.

        Skips ? inside string literals.
        """
        if "?" not in sql:
            return sql
        result = []
        param_index = 0
        in_string = False
        i = 0
        while i < len(sql):
            char = sql[i]
            if char == "'":
                if in_string and i + 1 < len(sql) and sql[i + 1] == "'":
                    result.append("''")
                    i += 2
                    continue
                in_string = not in_string
                result.append(char)
            elif char == "?" and not in_string:
                param_index += 1
                result.append(f"${param_index}")
            else:
                result.append(char)
            i += 1
        return "".join(result)

    async def query_with_params(self, sql: str, params: list | None = None) -> list:
        """Execute a parameterized query. Returns list of dicts.

        Args:
            sql: SQL string with $1/$2 or ? placeholders.
            params: Parameter list. Unpacked as positional args for asyncpg.
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        sql = self._rewrite_placeholders(sql)
        conn, should_release = await self._get_conn()
        try:
            if params:
                rows = await conn.fetch(sql, *params)
            else:
                rows = await conn.fetch(sql)
            return [dict(row) for row in rows]
        finally:
            await self._release_conn(conn, should_release)

    async def execute(self, sql: str, params: list | None = None) -> int:
        """Execute a SQL statement. Returns rows affected.

        Args:
            sql: SQL string with $1/$2 or ? placeholders.
            params: Parameter list. Unpacked as positional args for asyncpg.

        Returns:
            Number of rows affected. 0 for DDL statements.
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        sql = self._rewrite_placeholders(sql)
        conn, should_release = await self._get_conn()
        try:
            if params:
                status = await conn.execute(sql, *params)
            else:
                status = await conn.execute(sql)
            return self._parse_rows_affected(status)
        finally:
            await self._release_conn(conn, should_release)

    @staticmethod
    def _parse_rows_affected(status: str) -> int:
        """Parse rows affected from asyncpg status string.

        Examples: 'INSERT 0 1' -> 1, 'DELETE 3' -> 3, 'CREATE TABLE' -> 0
        """
        parts = status.split()
        if len(parts) >= 2:
            try:
                return int(parts[-1])
            except ValueError:
                return 0
        return 0

    async def execute_many(self, sql: str, params_list: list[list]) -> None:
        """Execute a SQL command multiple times with different parameters."""
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")

        conn, should_release = await self._get_conn()
        try:
            await conn.executemany(sql, params_list)
        finally:
            await self._release_conn(conn, should_release)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @property
    def is_connected(self) -> bool:
        """Check if the connector is connected to the database."""
        return self._pool is not None

    @property
    def pool_size(self) -> int | None:
        """Get the current pool size if connected."""
        if self._pool:
            return self._pool.get_size()
        return None

    # Import SQL builder for replace operations
    from .sql_builder import PostgresSQLBuilder

    _sql = PostgresSQLBuilder()

    async def replace_using_values(
        self,
        destination: str,
        data: list[dict],
        key_columns: list[str],
        *,
        defer_constraints: bool = False,
        lock_timeout_ms: int | None = None,
        statement_timeout_ms: int | None = None,
        synchronous_commit_off: bool = True,
    ) -> None:
        """REPLACE using a VALUES clause instead of a temp table."""
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        if not data:
            return

        columns = list(data[0].keys())
        # Build flattened params for DELETE USING (VALUES ...)
        delete_sql = self._sql.delete_using_values_asyncpg(
            destination, key_columns, len(data)
        )
        flat_params: list = []
        for row in data:
            for k in key_columns:
                flat_params.append(row[k])

        records = [tuple(row[c] for c in columns) for row in data]

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Session tuning (optional, scoped to transaction)
                if synchronous_commit_off:
                    await conn.execute(self._sql.set_local_synchronous_commit_off())
                if defer_constraints:
                    await conn.execute(self._sql.set_constraints_all_deferred())
                if lock_timeout_ms is not None:
                    await conn.execute(
                        self._sql.set_local_lock_timeout(lock_timeout_ms)
                    )
                if statement_timeout_ms is not None:
                    await conn.execute(
                        self._sql.set_local_statement_timeout(statement_timeout_ms)
                    )

                # 1) delete matches
                await conn.execute(delete_sql, *flat_params)
                # 2) insert new rows (bulk)
                await conn.copy_records_to_table(
                    destination, records=records, columns=columns
                )

    async def replace_using_values_chunked(
        self,
        destination: str,
        data: list[dict],
        key_columns: list[str],
        *,
        chunk_size: int = 5000,
        defer_constraints: bool = False,
        lock_timeout_ms: int | None = None,
        statement_timeout_ms: int | None = None,
        synchronous_commit_off: bool = True,
    ) -> None:
        """Chunked REPLACE using VALUES-based delete and bulk insert per chunk."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        total = len(data)
        if total == 0:
            return
        for start in range(0, total, chunk_size):
            end = min(start + chunk_size, total)
            await self.replace_using_values(
                destination,
                data[start:end],
                key_columns,
                defer_constraints=defer_constraints,
                lock_timeout_ms=lock_timeout_ms,
                statement_timeout_ms=statement_timeout_ms,
                synchronous_commit_off=synchronous_commit_off,
            )
