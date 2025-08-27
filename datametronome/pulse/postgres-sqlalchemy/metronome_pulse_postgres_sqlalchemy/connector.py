"""
PostgreSQL DataPulse connector using SQLAlchemy.

This connector provides flexible, ORM-capable PostgreSQL connectivity
with full support for the DataPulse ecosystem and SQLAlchemy features.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy import text
from metronome_pulse_core import Pulse, Readable, Writable
from .sql_builder import PostgresSQLAlchemyBuilder


class PostgresSQLAlchemyPulse(Pulse, Readable, Writable):
    """Full-featured PostgreSQL DataPulse connector using SQLAlchemy.
    
    Implements all interfaces: Pulse, Readable, and Writable.
    """
    
    def __init__(self, host="localhost", port=5432, database=None, user=None, password=None, **kwargs):
        """Initialize the PostgreSQL SQLAlchemy connector.
        
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
        self._engine = None
        self._session_maker = None
        self._sql = PostgresSQLAlchemyBuilder()
    
    async def connect(self):
        """Establish connection to PostgreSQL using SQLAlchemy."""
        connection_string = f"postgresql+asyncpg://{self._user}:{self._password}@{self._host}:{self._port}/{self._database}"
        self._engine = create_async_engine(connection_string, **self._kwargs)
        self._session_maker = async_sessionmaker(self._engine, class_=AsyncSession)
    
    async def close(self):
        """Close the SQLAlchemy engine."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None
    
    async def is_connected(self):
        """Check if connected to the database."""
        return self._engine is not None
    
    async def write(self, data, destination: str, config: dict = None) -> None:
        """Write data to destination with optional configuration.
        
        Args:
            data: List of dictionaries to write
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
        if not self._engine:
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
        """Simple insert using SQLAlchemy."""
        if not data:
            return
        
        async with self._session_maker() as session:
            # Build INSERT statement
            columns = list(data[0].keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            insert_sql = f"INSERT INTO {destination} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Execute batch insert
            await session.execute(text(insert_sql), data)
            await session.commit()

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
                "sql": "SELECT * FROM users WHERE age > :age AND city = :city",
                "params": {"age": 18, "city": "New York"}
            })

            # Table info query
            results = await pulse.query({
                "type": "table_info",
                "table_name": "users"
            })

            # Custom query with options
            results = await pulse.query({
                "type": "custom",
                "sql": "SELECT COUNT(*) as count FROM events WHERE date >= :date",
                "params": {"date": "2025-01-01"},
                "timeout_ms": 5000
            })
        """
        if not self._engine:
            raise RuntimeError("Not connected to database. Call connect() first.")

        # Handle query configuration dict
        if isinstance(query_config, dict):
            query_type = query_config.get("type", "custom")
            
            if query_type == "parameterized":
                sql = query_config.get("sql")
                params = query_config.get("params", {})
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
                params = query_config.get("params", {})
                timeout_ms = query_config.get("timeout_ms")
                
                if not sql:
                    raise ValueError("Custom query must contain 'sql' key")
                
                # Apply timeout if specified
                if timeout_ms:
                    # Note: SQLAlchemy doesn't support statement_timeout per query
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

    async def _simple_query(self, sql: str) -> list:
        """Simple SQL query execution."""
        async with self._session_maker() as session:
            result = await session.execute(text(sql))
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    
    async def query_with_params(self, query: str, params: dict = None) -> list:
        """
        Execute a parameterized SQL query and return results.
        
        Args:
            query: SQL query string with named parameters
            params: Dictionary of parameters for the query
            
        Returns:
            List of dictionaries representing the query results
        """
        if not self._engine:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._session_maker() as session:
            result = await session.execute(text(query), params or {})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
    
    async def replace_using_values(
        self,
        destination: str,
        data: list,
        key_columns: list,
        *,
        defer_constraints: bool = False,
        lock_timeout_ms: int | None = None,
        statement_timeout_ms: int | None = None,
        synchronous_commit_off: bool = True,
    ) -> None:
        if not self._engine:
            raise RuntimeError("Not connected to database. Call connect() first.")
        if not data:
            return
        columns = list(data[0].keys())
        delete_sql = self._sql.delete_using_values(destination, key_columns, len(data))

        # Flatten params as dicts p1..pn according to builder numbering
        params: dict = {}
        p = 1
        for row in data:
            for k in key_columns:
                params[f"p{p}"] = row[k]
                p += 1

        async with self._session_maker() as session:
            # Optional session tuning (scoped to transaction)
            if synchronous_commit_off:
                await session.execute(text("SET LOCAL synchronous_commit TO OFF"))
            if defer_constraints:
                await session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            if lock_timeout_ms is not None:
                await session.execute(text(f"SET LOCAL lock_timeout = '{lock_timeout_ms}ms'"))
            if statement_timeout_ms is not None:
                await session.execute(text(f"SET LOCAL statement_timeout = '{statement_timeout_ms}ms'"))

            await session.execute(text(delete_sql), params)
            # batch insert
            placeholders = ", ".join([f":{c}" for c in columns])
            insert_sql = f"INSERT INTO {destination} ({', '.join(columns)}) VALUES ({placeholders})"
            await session.execute(text(insert_sql), data)
            await session.commit()

    async def replace_using_values_chunked(
        self,
        destination: str,
        data: list,
        key_columns: list,
        *,
        chunk_size: int = 5000,
        defer_constraints: bool = False,
        lock_timeout_ms: int | None = None,
        statement_timeout_ms: int | None = None,
        synchronous_commit_off: bool = True,
    ) -> None:
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
    
    async def execute(self, query: str, params: dict = None):
        """
        Execute a SQL command that doesn't return results.
        
        Args:
            query: SQL command to execute
            params: Optional parameters for the command
            
        Returns:
            Result object from the command
            
        Raises:
            RuntimeError: If not connected to the database
            Exception: If the command fails
        """
        if not self._engine:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._session_maker() as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return result
    
    async def execute_many(self, query: str, params_list: list) -> None:
        """
        Execute a SQL command multiple times with different parameters.
        
        Args:
            query: SQL command to execute
            params_list: List of parameter dictionaries
            
        Raises:
            RuntimeError: If not connected to the database
            Exception: If any command fails
        """
        if not self._engine:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._session_maker() as session:
            for params in params_list:
                await session.execute(text(query), params)
            await session.commit()

    # ----------------------- Operation list API -----------------------
    async def apply_operations(
        self,
        operations: list,
        *,
        insert_chunk_size: int = 10000,
    ) -> None:
        """Apply a list of operations; INSERT uses batched executes.

        Supported operations (dict):
        - {'type': 'insert', 'table': str, 'rows': list[dict], 'columns'?: list[str]}
        - {'type': 'delete', 'sql': str}
        - {'type': 'update', 'sql': str}
        - {'type': 'create_table', 'sql': str}
        - {'type': 'partition', 'sql': str}
        """
        if not self._engine:
            raise RuntimeError("Not connected to database. Call connect() first.")
        for op in operations:
            kind = op.get('type')
            if kind == 'insert':
                table = op['table']
                rows: list = op.get('rows', [])
                if not rows:
                    continue
                columns: list | None = op.get('columns')
                if columns is None:
                    columns = list(rows[0].keys())
                placeholders = ", ".join([f":{c}" for c in columns])
                insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                async with self._session_maker() as session:
                    for start in range(0, len(rows), insert_chunk_size):
                        end = min(start + insert_chunk_size, len(rows))
                        part = rows[start:end]
                        await session.execute(text(insert_sql), part)
                    await session.commit()
            elif kind in {'delete', 'update', 'create_table', 'partition'}:
                sql = op.get('sql')
                if not sql:
                    continue
                async with self._session_maker() as session:
                    await session.execute(text(sql))
                    await session.commit()
            else:
                raise ValueError(f"Unsupported operation type: {kind}")
    
    async def get_table_info(self, table_name: str) -> dict:
        """
        Get information about a table structure.
        
        Args:
            table_name: Name of the table to inspect
            
        Returns:
            Dictionary containing table metadata
        """
        if not self._engine:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        # Query to get table information
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = :table_name
        ORDER BY ordinal_position
        """
        
        columns = await self.query_with_params(query, {'table_name': table_name})
        
        # Get table size
        size_query = """
        SELECT 
            pg_size_pretty(pg_total_relation_size(:table_name)) as size,
            (SELECT count(*) FROM :table_name) as row_count
        """
        
        try:
            size_info = await self.query_with_params(size_query, {'table_name': table_name})
        except:
            size_info = [{'size': 'Unknown', 'row_count': 'Unknown'}]
        
        return {
            'table_name': table_name,
            'columns': columns,
            'size_info': size_info[0] if size_info else {}
        }
    
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
        return self._engine is not None
    
    @property
    def engine(self) -> AsyncEngine | None:
        """Get the SQLAlchemy engine instance."""
        return self._engine
    
    @property
    def session_maker(self) -> async_sessionmaker | None:
        """Get the SQLAlchemy session maker."""
        return self._session_maker
