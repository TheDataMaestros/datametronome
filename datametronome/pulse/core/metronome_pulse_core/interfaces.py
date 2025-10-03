"""
Core interfaces for DataPulse connectors.

This module defines the abstract base classes that all DataPulse connectors must implement.
Each interface has a single, clear responsibility to prevent misuse.
"""

from abc import ABC, abstractmethod


class Pulse(ABC):
    """Base interface for all DataPulse connectors.
    
    Defines the core lifecycle methods that every connector must implement.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source.
        
        Raises:
            ConnectionError: If connection cannot be established
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connection to the data source.
        
        Should be called when the connector is no longer needed.
        """
        pass
    
    # Alias for backward compatibility
    async def disconnect(self) -> None:
        """Disconnect from the data source (alias for close method)."""
        await self.close()
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the connector is currently connected.
        
        Returns:
            True if connected, False otherwise
        """
        pass


class Readable(ABC):
    """Interface for connectors that can read data.
    
    Defines the query method for retrieving data from the source.
    """
    
    @abstractmethod
    async def query(self, query_config) -> list:
        """Execute a query and return results.
        
        Args:
            query_config: Can be:
                - str: Direct SQL query (default behavior)
                - dict: Query configuration with 'type' and parameters
                
                Supported query types:
                - "parameterized": SQL with parameters
                - "table_info": Get table metadata
                - "custom": Custom query with options
        
        Returns:
            List of dictionaries representing the query results
            
        Raises:
            RuntimeError: If not connected to the data source
            Exception: If the query fails
        """
        pass
    
    # Additional convenience methods for backward compatibility
    async def execute_query(self, query: str, params: dict = None) -> list:
        """Execute a query and return results (alias for query method)."""
        return await self.query(query)
    
    async def fetch_one(self, query: str, params: dict = None) -> dict | None:
        """Fetch a single result from a query."""
        results = await self.query(query)
        return results[0] if results else None
    
    async def fetch_all(self, query: str, params: dict = None) -> list:
        """Fetch all results from a query (alias for query method)."""
        return await self.query(query)
    
    # Additional methods for backward compatibility
    async def get_freshness(self) -> str:
        """Get data freshness information (default implementation)."""
        return "unknown"
    
    async def get_row_count(self) -> int:
        """Get total row count (default implementation)."""
        return 0
    
    async def get_schema(self) -> dict:
        """Get table schema (default implementation)."""
        return {}
    
    async def get_table_info(self, table_name: str) -> list:
        """Get table information (default implementation)."""
        return []
    
    async def test_connection(self) -> bool:
        """Test if connection is working (default implementation)."""
        return await self.is_connected()


class Writable(ABC):
    """Interface for connectors that can write data.
    
    Defines the write method for inserting, updating, or replacing data.
    """
    
    @abstractmethod
    async def write(self, data, destination: str, config: dict = None) -> None:
        """Write data to the destination with optional configuration.
        
        Args:
            data: List of dictionaries to write
            destination: Target table name
            config: Optional configuration dict for advanced operations
            
            Supported operation types in config:
            - "replace": Delete then insert (upsert)
            - "operations": Mixed SQL operations
            - "insert": Simple insert (default)
            
        Raises:
            RuntimeError: If not connected to the data source
            Exception: If the write operation fails
        """
        pass
    
    # Additional convenience methods for backward compatibility
    async def execute_write(self, query: str, params: dict = None) -> dict:
        """Execute a write query and return result (alias for write method)."""
        # This is a simplified version for backward compatibility
        await self.write([params] if params else [], "temp_table")
        return {"affected_rows": 1}
    
    async def execute_batch(self, queries: list[str], params: list[dict] = None) -> dict:
        """Execute multiple write queries in batch (alias for write method)."""
        # This is a simplified version for backward compatibility
        if params:
            for param in params:
                await self.write([param], "temp_table")
        return {"affected_rows": len(queries) if queries else 0}
    
    async def begin_transaction(self) -> bool:
        """Begin a transaction (default implementation)."""
        return True
    
    async def commit_transaction(self) -> bool:
        """Commit a transaction (default implementation)."""
        return True
    
    async def rollback_transaction(self) -> bool:
        """Rollback a transaction (default implementation)."""
        return True


# Additional interface classes for backward compatibility
class ReadOnlyConnector(Pulse, Readable):
    """Interface for read-only connectors (backward compatibility)."""
    pass


class WriteOnlyConnector(Pulse, Writable):
    """Interface for write-only connectors (backward compatibility)."""
    pass


class ReadWriteConnector(Pulse, Readable, Writable):
    """Interface for read-write connectors (backward compatibility)."""
    pass
