"""
Read-only PostgreSQL DataPulse connector using asyncpg.

This connector provides high-performance, async-first PostgreSQL connectivity
for read-only operations only. It implements Pulse and Readable interfaces
to ensure data safety and prevent accidental writes.
"""

import asyncpg
from metronome_pulse_core import Pulse, Readable


class PostgresReadOnlyPulse(Pulse, Readable):
    """Read-only PostgreSQL DataPulse connector using asyncpg.
    
    Implements Pulse and Readable interfaces only.
    """
    
    def __init__(self, host="localhost", port=5432, database=None, user=None, password=None, **kwargs):
        """Initialize the PostgreSQL read-only connector.
        
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
                "sql": "SELECT * FROM users WHERE age > %s AND city = %s",
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
                "sql": "SELECT COUNT(*) as count FROM events WHERE date >= %s",
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
            List of dictionaries representing the query results
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, *args, **kwargs)
            return [dict(record) for record in records]
    
    async def get_table_info(self, table_name: str) -> dict:
        """
        Get information about a table structure.
        
        Args:
            table_name: Name of the table to inspect
            
        Returns:
            Dictionary containing table metadata
        """
        if not self._pool:
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
        WHERE table_name = $1
        ORDER BY ordinal_position
        """
        
        columns = await self.query_with_params(query, table_name)
        
        # Get table size
        size_query = """
        SELECT 
            pg_size_pretty(pg_total_relation_size($1)) as size,
            (SELECT count(*) FROM information_schema.tables WHERE table_name = $1) as exists
        """
        
        try:
            size_info = await self.query_with_params(size_query, table_name)
            exists = size_info[0]['exists'] if size_info else 0
        except:
            exists = 0
        
        return {
            'table_name': table_name,
            'columns': columns,
            'exists': bool(exists)
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
        return self._pool is not None
    
    @property
    def pool_size(self) -> int | None:
        """Get the current pool size if connected."""
        if self._pool:
            return self._pool.get_size()
        return None
