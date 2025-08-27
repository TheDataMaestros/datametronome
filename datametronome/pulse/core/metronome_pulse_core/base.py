"""
Base connector interface for DataPulse connectors.
"""

from abc import ABC, abstractmethod
from datetime import datetime
# Removed typing imports as requested

import pandas as pd
from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    """Base configuration for data source connections."""
    
    host: object = None
    port: object = None
    database: object = None
    username: object = None
    password: object = None
    ssl_mode: object = None
    timeout: object = Field(default=30, ge=1)
    max_connections: object = Field(default=10, ge=1)
    
    class Config:
        extra = "allow"  # Allow additional fields for specific connectors


class QueryResult(BaseModel):
    """Result of a data query."""
    
    data: object
    row_count: object = Field(ge=0)
    column_count: object = Field(ge=0)
    execution_time: object = Field(ge=0.0)
    timestamp: object
    metadata: object = None
    
    class Config:
        arbitrary_types_allowed = True  # Allow pandas DataFrame


class BaseConnector(ABC):
    """Base class for all DataPulse connectors."""
    
    def __init__(self, config):
        """Initialize connector with configuration.
        
        Args:
            config: Connection configuration.
        """
        self.config = config
        self._connection_pool = None
        self._is_connected = False
    
    @abstractmethod
    async def connect(self):
        """Establish connection to the data source.
        
        Returns:
            True if connection successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection to the data source."""
        pass
    
    @abstractmethod
    async def test_connection(self):
        """Test if the connection is working.
        
        Returns:
            True if connection test successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def execute_query(self, query, params=None):
        """Execute a query and return results.
        
        Args:
            query: SQL or query string to execute.
            params: Query parameters.
            
        Returns:
            QueryResult containing the query results.
        """
        pass
    
    @abstractmethod
    async def get_schema(self, table_name=None):
        """Get schema information for tables.
        
        Args:
            table_name: Optional specific table name.
            
        Returns:
            Schema information dictionary.
        """
        pass
    
    @abstractmethod
    async def get_table_info(self, table_name):
        """Get detailed information about a specific table.
        
        Args:
            table_name: Name of the table.
            
        Returns:
            Table information dictionary.
        """
        pass
    
    @abstractmethod
    async def get_row_count(self, table_name):
        """Get the row count for a table.
        
        Args:
            table_name: Name of the table.
            
        Returns:
            Number of rows in the table.
        """
        pass
    
    @abstractmethod
    async def get_freshness(self, table_name, timestamp_column):
        """Get the most recent timestamp from a table.
        
        Args:
            table_name: Name of the table.
            timestamp_column: Name of the timestamp column.
            
        Returns:
            Most recent timestamp.
        """
        pass
    
    async def is_connected(self):
        """Check if connector is currently connected.
        
        Returns:
            True if connected, False otherwise.
        """
        return self._is_connected
    
    async def get_connection_info(self):
        """Get information about the current connection.
        
        Returns:
            Connection information dictionary.
        """
        return {
            "connected": self._is_connected,
            "config": self.config.model_dump(),
            "connection_pool_size": len(self._connection_pool) if self._connection_pool else 0
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class ConnectorRegistry:
    """Registry for available connectors."""
    
    _connectors: object = {}
    
    @classmethod
    def register(cls, name, connector_class):
        """Register a connector class.
        
        Args:
            name: Connector name.
            connector_class: Connector class to register.
            
        Raises:
            ValueError: If connector class doesn't inherit from BaseConnector.
        """
        if not issubclass(connector_class, BaseConnector):
            raise ValueError(f"Connector must inherit from BaseConnector: {connector_class}")
        cls._connectors[name] = connector_class
    
    @classmethod
    def get(cls, name):
        """Get a connector class by name.
        
        Args:
            name: Connector name.
            
        Returns:
            Connector class if found, None otherwise.
        """
        return cls._connectors.get(name)
    
    @classmethod
    def list_available(cls) -> list[str]:
        """List all available connector names.
        
        Returns:
            List of available connector names.
        """
        return list(cls._connectors.keys())
    
    @classmethod
    def create(cls, name, config):
        """Create a connector instance by name.
        
        Args:
            name: Connector name.
            config: Connection configuration.
            
        Returns:
            Connector instance if found, None otherwise.
        """
        connector_class = cls.get(name)
        if connector_class:
            return connector_class(config)
        return None
