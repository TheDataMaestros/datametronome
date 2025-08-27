import sqlite3
import asyncio
import json
from pathlib import Path
# Removed typing imports as requested
from datetime import datetime

from metronome_pulse_core.interfaces import Pulse, Readable, Writable
from .readonly_connector import SQLiteReadonlyPulse
from .writeonly_connector import SQLiteWriteonlyPulse

class SQLitePulse(Pulse, Readable, Writable):
    """SQLite DataPulse connector for local storage.
    
    This connector ONLY provides the connection interface.
    Business logic, table creation, and DDL are handled by Podium.
    """
    
    def __init__(self, database_path: str = "datametronome.db"):
        self.database_path = database_path
        self.connection = None
        self._readonly = SQLiteReadonlyPulse(database_path)
        self._writeonly = SQLiteWriteonlyPulse(database_path)
    
    async def connect(self) -> None:
        """Connect to SQLite database."""
        try:
            # Ensure directory exists
            db_path = Path(self.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database (tables should already exist from Podium)
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            
            # Connect both readonly and writeonly connectors
            await self._readonly.connect()
            await self._writeonly.connect()
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQLite: {e}")
    
    async def close(self) -> None:
        """Close SQLite connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
        
        # Close both readonly and writeonly connectors
        await self._readonly.close()
        await self._writeonly.close()
    
    async def is_connected(self) -> bool:
        """Check if connected to SQLite."""
        return (self.connection is not None and 
                await self._readonly.is_connected() and 
                await self._writeonly.is_connected())
    
    # Readable interface methods - delegate to readonly connector
    async def query(self, query_config: str | Dict[str, Any]) -> list:
        """Query data from SQLite."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        return await self._readonly.query(query_config)
    
    async def query_with_params(self, sql, params):
        """Execute parameterized query."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        return await self._readonly.query_with_params(sql, params)
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        return await self._readonly.get_table_info(table_name)
    
    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        return await self._readonly.list_tables()
    
    # Writable interface methods - delegate to writeonly connector
    async def write(self, data, destination, config=None):
        """Write data to SQLite."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        # Add destination to each record if not present
        for record in data:
            if "table" not in record:
                record["table"] = destination
        
        return await self._writeonly.write(data, config)
    
    async def execute(self, sql, params=None):
        """Execute raw SQL."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        return await self._writeonly.execute(sql, params)
    
    async def copy_records(self, table_name, records):
        """Bulk insert records using SQLite's efficient INSERT."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        return await self._writeonly.copy_records(table_name, records)
