import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from metronome_pulse_core.interfaces import Pulse, Readable

class SQLiteReadonlyPulse(Pulse, Readable):
    """Read-only SQLite DataPulse connector.
    
    This connector ONLY provides read access to SQLite.
    Business logic and table creation are handled by Podium.
    """
    
    def __init__(self, database_path: str = "datametronome.db"):
        self.database_path = database_path
        self.connection = None
    
    async def connect(self) -> None:
        """Connect to SQLite database."""
        try:
            # Ensure directory exists
            db_path = Path(self.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database (tables should already exist from Podium)
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQLite: {e}")
    
    async def close(self) -> None:
        """Close SQLite connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    async def is_connected(self) -> bool:
        """Check if connected to SQLite."""
        return self.connection is not None
    
    async def query(self, query_config: str | Dict[str, Any]) -> list:
        """Query data from SQLite."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        try:
            if isinstance(query_config, str):
                # Simple SQL query
                cursor = self.connection.cursor()
                cursor.execute(query_config)
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                # Query with parameters
                sql = query_config.get("sql", "")
                params = query_config.get("params", [])
                
                cursor = self.connection.cursor()
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(f"Query failed: {e}")
    
    async def query_with_params(self, sql: str, params: List[Any]) -> List[Dict[str, Any]]:
        """Execute parameterized query."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(f"Parameterized query failed: {e}")
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            return [dict(col) for col in columns]
        except Exception as e:
            raise RuntimeError(f"Failed to get table info: {e}")
    
    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            return [table[0] for table in tables]
        except Exception as e:
            raise RuntimeError(f"Failed to list tables: {e}")



