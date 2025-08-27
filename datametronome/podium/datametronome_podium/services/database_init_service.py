import asyncio
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import uuid

from metronome_pulse_sqlite import SQLitePulse

class DatabaseInitService:
    """Service for initializing and managing the SQLite database schema.
    
    This service handles all business logic for database setup.
    DataPulse connectors only provide the connection interface.
    """
    
    def __init__(self, database_path: str = "datametronome.db"):
        self.database_path = database_path
        self.connector = SQLitePulse(database_path)
    
    async def initialize_database(self) -> bool:
        """Initialize the complete database schema."""
        try:
            await self.connector.connect()
            
            # Create all required tables
            await self._create_staves_table()
            await self._create_clefs_table()
            await self._create_checks_table()
            await self._create_anomalies_table()
            await self._create_users_table()
            
            # Insert default data
            await self._insert_default_data()
            
            print("✅ Database initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
        finally:
            await self.connector.close()
    
    async def _create_staves_table(self):
        """Create the staves table."""
        sql = """
        CREATE TABLE IF NOT EXISTS staves (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            connection_config TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
        await self.connector.execute(sql)
    
    async def _create_clefs_table(self):
        """Create the clefs table."""
        sql = """
        CREATE TABLE IF NOT EXISTS clefs (
            id TEXT PRIMARY KEY,
            stave_id TEXT NOT NULL,
            name TEXT NOT NULL,
            check_type TEXT NOT NULL,
            parameters TEXT,
            thresholds TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (stave_id) REFERENCES staves (id)
        )
        """
        await self.connector.execute(sql)
    
    async def _create_checks_table(self):
        """Create the checks table."""
        sql = """
        CREATE TABLE IF NOT EXISTS checks (
            id TEXT PRIMARY KEY,
            stave_id TEXT NOT NULL,
            clef_id TEXT NOT NULL,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            details TEXT,
            timestamp TEXT NOT NULL,
            execution_time REAL,
            anomalies_count INTEGER DEFAULT 0,
            severity TEXT DEFAULT 'medium',
            FOREIGN KEY (stave_id) REFERENCES staves (id),
            FOREIGN KEY (clef_id) REFERENCES clefs (id)
        )
        """
        await self.connector.execute(sql)
    
    async def _create_anomalies_table(self):
        """Create the anomalies table."""
        sql = """
        CREATE TABLE IF NOT EXISTS anomalies (
            id TEXT PRIMARY KEY,
            check_id TEXT NOT NULL,
            table_name TEXT,
            column_name TEXT,
            anomaly_type TEXT NOT NULL,
            description TEXT,
            severity TEXT DEFAULT 'medium',
            detected_at TEXT NOT NULL,
            data_sample TEXT,
            resolution_status TEXT DEFAULT 'investigating',
            FOREIGN KEY (check_id) REFERENCES checks (id)
        )
        """
        await self.connector.execute(sql)
    
    async def _create_users_table(self):
        """Create the users table."""
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
        await self.connector.execute(sql)
    
    async def _insert_default_data(self):
        """Insert default data into the database."""
        now = datetime.now().isoformat()
        
        # Insert default admin user
        admin_user = {
            "table": "users",
            "id": "admin",
            "username": "admin",
            "email": "admin@datametronome.dev",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uO.G",  # admin
            "is_active": True,
            "is_superuser": True,
            "created_at": now,
            "updated_at": now
        }
        
        await self.connector.write([admin_user])
        
        # Insert default stave
        default_stave = {
            "table": "staves",
            "id": str(uuid.uuid4()),
            "name": "Default SQLite Monitor",
            "description": "Default monitoring stave for local development",
            "connection_config": '{"database_path": "datametronome.db"}',
            "created_at": now,
            "updated_at": now
        }
        
        await self.connector.write([default_stave])
        
        # Insert default clef
        default_clef = {
            "table": "clefs",
            "id": str(uuid.uuid4()),
            "stave_id": default_stave["id"],
            "name": "Basic Health Check",
            "check_type": "health_check",
            "parameters": '{"check_interval": 300}',
            "thresholds": '{"max_response_time": 5.0}',
            "created_at": now,
            "updated_at": now
        }
        
        await self.connector.write([default_clef])
        
        print("✅ Default data inserted successfully")
    
    async def get_database_status(self) -> Dict[str, Any]:
        """Get database status and table information."""
        try:
            await self.connector.connect()
            
            tables = await self.connector.list_tables()
            status = {
                "database_path": self.database_path,
                "tables": tables,
                "table_count": len(tables),
                "status": "connected"
            }
            
            # Get record counts for each table
            for table in tables:
                try:
                    result = await self.connector.query(f"SELECT COUNT(*) as count FROM {table}")
                    if result:
                        status[f"{table}_count"] = result[0]["count"]
                except Exception:
                    status[f"{table}_count"] = 0
            
            return status
            
        except Exception as e:
            return {
                "database_path": self.database_path,
                "status": "error",
                "error": str(e)
            }
        finally:
            await self.connector.close()
    
    async def reset_database(self) -> bool:
        """Reset the database by dropping all tables and recreating them."""
        try:
            await self.connector.connect()
            
            # Drop all tables
            tables = await self.connector.list_tables()
            for table in tables:
                await self.connector.execute(f"DROP TABLE IF EXISTS {table}")
            
            print("🗑️ All tables dropped")
            
            # Reinitialize
            return await self.initialize_database()
            
        except Exception as e:
            print(f"❌ Database reset failed: {e}")
            return False
        finally:
            await self.connector.close()




