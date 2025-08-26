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
