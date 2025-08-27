"""
Write-only PostgreSQL DataPulse connector using asyncpg.

This connector provides high-performance, async-first PostgreSQL connectivity
for write operations only. It implements Pulse and Writable interfaces
to ensure data safety and prevent accidental reads.
"""

import asyncpg
from metronome_pulse_core import Pulse, Writable
from .sql_builder import PostgresSQLBuilder


class PostgresWriteOnlyPulse(Pulse, Writable):
    """Write-only PostgreSQL DataPulse connector using asyncpg.
    
    Implements Pulse and Writable interfaces only.
    """
    
    def __init__(self, host="localhost", port=5432, database=None, user=None, password=None, **kwargs):
        """Initialize the PostgreSQL write-only connector.
        
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
        self._sql = PostgresSQLBuilder()
    
    async def connect(self):
        """Establish connection pool to PostgreSQL."""
        self._pool = await asyncpg.create_pool(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password,
            **self._kwargs
        )
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def is_connected(self):
        """Check if connected to the database."""
        return self._pool is not None
    
    async def write(self, data, destination: str, config: dict = None) -> None:
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
                    destination, data, key_columns,
                    chunk_size=chunk_size,
                    defer_constraints=defer_constraints,
                    lock_timeout_ms=lock_timeout_ms,
                    statement_timeout_ms=statement_timeout_ms,
                    synchronous_commit_off=synchronous_commit_off
                )
            else:
                await self.replace_using_values(
                    destination, data, key_columns,
                    defer_constraints=defer_constraints,
                    lock_timeout_ms=lock_timeout_ms,
                    statement_timeout_ms=statement_timeout_ms,
                    synchronous_commit_off=synchronous_commit_off
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
        
        columns = list(data[0].keys())
        records = [tuple(record[col] for col in columns) for record in data]
        
        async with self._pool.acquire() as conn:
            await conn.copy_records_to_table(
                destination,
                records=records,
                columns=columns,
            )
    
    async def execute(self, query: str, *args, **kwargs) -> str:
        """
        Execute a SQL command that doesn't return results.
        
        Args:
            query: SQL command to execute
            *args: Positional parameters
            **kwargs: Named parameters
            
        Returns:
            Status message from the command
            
        Raises:
            RuntimeError: If not connected to the database
            asyncpg.PostgresError: If the command fails
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)
    
    async def execute_many(self, query: str, args_list: list[tuple]) -> None:
        """
        Execute a SQL command multiple times with different parameters.
        
        Args:
            query: SQL command to execute
            args_list: list of parameter tuples
            
        Raises:
            RuntimeError: If not connected to the database
            asyncpg.PostgresError: If any command fails
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            await conn.executemany(query, args_list)
    
    async def create_table(self, table_name: str, columns: list[dict]) -> None:
        """
        Create a new table with specified columns.
        
        Args:
            table_name: Name of the table to create
            columns: list of column definitions with 'name', 'type', and optional 'constraints'
            
        Raises:
            RuntimeError: If not connected to the database
            asyncpg.PostgresError: If table creation fails
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        # Build CREATE TABLE statement
        column_defs = []
        for col in columns:
            col_def = f"{col['name']} {col['type']}"
            if 'constraints' in col:
                col_def += f" {col['constraints']}"
            column_defs.append(col_def)
        
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
        await self.execute(create_sql)
    
    async def truncate_table(self, table_name: str) -> None:
        """
        Truncate a table (remove all data).
        
        Args:
            table_name: Name of the table to truncate
            
        Raises:
            RuntimeError: If not connected to the database
            asyncpg.PostgresError: If truncate operation fails
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        await self.execute(f"TRUNCATE TABLE {table_name}")

    # ----------------------- Operation list API -----------------------
    async def apply_operations(
        self,
        operations: list[dict],
        *,
        insert_chunk_size: int = 10000,
    ) -> None:
        """Apply a list of operations.

        Supported operations (dict):
        - {'type': 'insert', 'table': str, 'rows': list[dict], 'columns'?: list[str]}
        - {'type': 'delete', 'sql': str}
        - {'type': 'update', 'sql': str}
        - {'type': 'create_table', 'sql': str}
        - {'type': 'partition', 'sql': str}
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        for op in operations:
            kind = op.get('type')
            if kind == 'insert':
                table = op['table']
                rows: list[dict] = op.get('rows', [])
                if not rows:
                    continue
                columns: list[str] | None = op.get('columns')
                if columns is None:
                    columns = list(rows[0].keys())
                # chunked COPY
                async with self._pool.acquire() as conn:
                    for start in range(0, len(rows), insert_chunk_size):
                        end = min(start + insert_chunk_size, len(rows))
                        part = rows[start:end]
                        records = [tuple(r[c] for c in columns) for r in part]
                        await conn.copy_records_to_table(table, records=records, columns=columns)
            elif kind in {'delete', 'update', 'create_table', 'partition'}:
                sql = op.get('sql')
                if not sql:
                    continue
                async with self._pool.acquire() as conn:
                    await conn.execute(sql)
            else:
                raise ValueError(f"Unsupported operation type: {kind}")

    # ----------------------- High-performance flows -----------------------
    async def replace_using_temp(
        self,
        destination: str,
        data: list[dict],
        key_columns: list[str],
    ) -> None:
        """High-performance REPLACE (delete + insert) using a temp table.

        The method performs within a single transaction:
        1) create temp table like destination
        2) bulk copy data into temp
        3) delete destination rows matching keys in temp
        4) insert from temp into destination
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        if not data:
            return

        columns = list(data[0].keys())
        temp_table = f"tmp_{destination}_staging"

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 1) Create temp table
                await conn.execute(self._sql.create_temp_table_like(temp_table, destination))

                # 2) Bulk copy into temp
                records = [tuple(record[col] for col in columns) for record in data]
                await conn.copy_records_to_table(temp_table, records=records, columns=columns)

                # 3) Delete matching rows
                await conn.execute(self._sql.delete_using_temp(destination, temp_table, key_columns))

                # 4) Insert from temp
                await conn.execute(self._sql.insert_from_temp(destination, temp_table, columns))

    async def replace_using_temp_chunked(
        self,
        destination: str,
        data: list[dict],
        key_columns: list[str],
        *,
        chunk_size: int = 10000,
    ) -> None:
        """Chunked high-performance REPLACE (delete + insert).

        Processes the payload in chunks, each in its own transaction, which:
        - keeps memory bounded,
        - limits lock times,
        - makes retries simpler for very large loads.

        Args:
            destination: Target table name
            data: Records to replace
            key_columns: Unique key columns used for matching deletes
            chunk_size: Number of rows per chunk/transaction
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        total = len(data)
        if total == 0:
            return
        for start in range(0, total, chunk_size):
            end = min(start + chunk_size, total)
            await self.replace_using_temp(destination, data[start:end], key_columns)

    # ----------------------- No-temp flows (VALUES) -----------------------
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
        """REPLACE using a VALUES clause instead of a temp table.

        1) DELETE target USING (VALUES ...) joined on key columns
        2) COPY new data into destination
        
        Note: VALUES has practical row limits; prefer chunked variant for large loads.
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        if not data:
            return

        columns = list(data[0].keys())
        # Build flattened params for DELETE USING (VALUES ...)
        delete_sql = self._sql.delete_using_values_asyncpg(destination, key_columns, len(data))
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
                    await conn.execute(self._sql.set_local_lock_timeout(lock_timeout_ms))
                if statement_timeout_ms is not None:
                    await conn.execute(self._sql.set_local_statement_timeout(statement_timeout_ms))

                # 1) delete matches
                await conn.execute(delete_sql, *flat_params)
                # 2) insert new rows (bulk)
                await conn.copy_records_to_table(destination, records=records, columns=columns)

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

    async def upsert_using_temp(
        self,
        destination: str,
        data: list[dict],
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> None:
        """High-performance UPSERT using a temp table and ON CONFLICT.

        The method performs within a single transaction:
        1) create temp table like destination
        2) bulk copy data into temp
        3) insert into destination with ON CONFLICT DO UPDATE
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        if not data:
            return

        columns = list(data[0].keys())
        temp_table = f"tmp_{destination}_staging"

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 1) Create temp table
                await conn.execute(self._sql.create_temp_table_like(temp_table, destination))

                # 2) Bulk copy into temp
                records = [tuple(record[col] for col in columns) for record in data]
                await conn.copy_records_to_table(temp_table, records=records, columns=columns)

                # 3) Upsert from temp
                upsert_sql = self._sql.upsert_from_temp(
                    destination, temp_table, columns, conflict_columns, update_columns
                )
                await conn.execute(upsert_sql)

    # ----------------------- Partition helpers -----------------------
    async def ensure_range_partition(
        self,
        parent_table: str,
        partition_table: str,
        from_value,
        to_value,
    ) -> None:
        """Create a RANGE partition if it does not exist."""
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        async with self._pool.acquire() as conn:
            await conn.execute(
                self._sql.create_range_partition(parent_table, partition_table, from_value, to_value)
            )

    async def ensure_list_partition(
        self,
        parent_table: str,
        partition_table: str,
        values: list,
    ) -> None:
        """Create a LIST partition if it does not exist."""
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        async with self._pool.acquire() as conn:
            await conn.execute(self._sql.create_list_partition(parent_table, partition_table, values))
    
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
