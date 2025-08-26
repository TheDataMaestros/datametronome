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
    
    def __init__(self, host="localhost", port=5432, database=None, user=None, password=None, **kwargs):
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

    async def query(self, query_config) -> list:
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
                return await self.query_with_params(sql, params)
            
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
                    return await self.query_with_params(sql, *params)
                else:
                    return await self._simple_query(sql)
            
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
        
        else:
            # Handle simple SQL string (default behavior)
            return await self._simple_query(query_config)

    async def _simple_query(self, sql: str) -> list:
        """Simple SQL query execution."""
        async with self._pool.acquire() as conn:
            records = await conn.fetch(sql)
            return [dict(record) for record in records]
    
    async def query_with_params(self, query: str, *args, **kwargs) -> list:
        """
        Execute a parameterized SQL query and return results.
        
        Args:
            query: SQL query string with placeholders
            *args: Positional parameters for the query
            **kwargs: Named parameters for the query
            
        Returns:
            list of dictionaries representing the query results
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, *args, **kwargs)
            return [dict(record) for record in records]
    
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
    
    async def execute_many(self, query: str, args_list: list) -> None:
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
