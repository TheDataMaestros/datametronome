import sqlite3
import asyncio
from pathlib import Path
# Removed typing imports as requested

from metronome_pulse_core.interfaces import Pulse, Writable

class SQLiteWriteonlyPulse(Pulse, Writable):
    """Write-only SQLite DataPulse connector.
    
    This connector ONLY provides write access to SQLite.
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
    
    async def write(self, data, config=None):
        """Write data to SQLite."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        if not config:
            config = {"type": "insert"}
        
        operation_type = config.get("type", "insert")
        
        try:
            if operation_type == "insert":
                return await self._insert_data(data)
            elif operation_type == "replace":
                return await self._replace_data(data)
            elif operation_type == "operations":
                return await self._execute_operations(data)
            else:
                raise ValueError(f"Unsupported operation type: {operation_type}")
        except Exception as e:
            raise RuntimeError(f"Write operation failed: {e}")
    
    async def _insert_data(self, data):
        """Insert data into tables (tables must already exist from Podium)."""
        try:
            for record in data:
                # Extract table name and data from record
                table_name = record.get("table")
                if not table_name:
                    print("No table name specified in record")
                    continue
                
                # Remove table name from data
                insert_data = {k: v for k, v in record.items() if k != "table"}
                
                # Build INSERT statement
                columns = list(insert_data.keys())
                placeholders = ", ".join(["?" for _ in columns])
                values = list(insert_data.values())
                
                sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                cursor = self.connection.cursor()
                cursor.execute(sql, values)
            
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            raise RuntimeError(f"Insert failed: {e}")
    
    async def _replace_data(self, data):
        """Replace data using delete and insert strategy."""
        try:
            for record in data:
                table_name = record.get("table")
                if not table_name:
                    continue
                
                # Extract primary key for deletion
                primary_key = record.get("id")
                if primary_key:
                    # Delete existing record
                    cursor = self.connection.cursor()
                    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (primary_key,))
            
            # Insert new data
            return await self._insert_data(data)
        except Exception as e:
            self.connection.rollback()
            raise RuntimeError(f"Replace failed: {e}")
    
    async def _execute_operations(self, operations):
        """Execute a list of mixed SQL operations."""
        try:
            for operation in operations:
                op_type = operation.get("type")
                sql = operation.get("sql", "")
                params = operation.get("params", [])
                
                cursor = self.connection.cursor()
                
                if op_type == "insert":
                    cursor.execute(sql, params)
                elif op_type == "delete":
                    cursor.execute(sql, params)
                elif op_type == "update":
                    cursor.execute(sql, params)
                elif op_type == "create_table":
                    cursor.execute(sql)
                elif op_type == "partition":
                    cursor.execute(sql)
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")
            
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            raise RuntimeError(f"Operations failed: {e}")
    
    async def execute(self, sql, params=None):
        """Execute raw SQL."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            raise RuntimeError(f"Execute failed: {e}")
    
    async def copy_records(self, table_name, records):
        """Bulk insert records using SQLite's efficient INSERT."""
        if not await self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        
        if not records:
            return True
        
        try:
            # Get column names from first record
            columns = list(records[0].keys())
            placeholders = ", ".join(["?" for _ in columns])
            
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            cursor = self.connection.cursor()
            
            # Prepare all values
            values = [[record.get(col) for col in columns] for record in records]
            
            # Execute batch insert
            cursor.executemany(sql, values)
            
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            raise RuntimeError(f"Copy records failed: {e}")



