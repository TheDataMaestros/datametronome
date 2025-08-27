"""
Integration tests for DataPulse SQLite connector.

These tests use actual SQLite database connections to verify
real-world functionality and data operations.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from pathlib import Path

from metronome_pulse_sqlite import SQLitePulse, SQLiteReadonlyPulse, SQLiteWriteonlyPulse


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest_asyncio.fixture
async def sqlite_pulse(temp_db_path):
    """Create a SQLitePulse instance with temporary database."""
    pulse = SQLitePulse(temp_db_path)
    await pulse.connect()
    
    # Create test tables
    await pulse.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await pulse.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            event_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    yield pulse
    
    await pulse.close()


@pytest_asyncio.fixture
async def readonly_pulse(temp_db_path):
    """Create a SQLiteReadonlyPulse instance with temporary database."""
    # First create the database with tables
    pulse = SQLitePulse(temp_db_path)
    await pulse.connect()
    
    await pulse.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            active BOOLEAN DEFAULT 1
        )
    """)
    
    # Insert some test data
    await pulse.write([
        {"name": "Alice", "email": "alice@example.com", "active": True},
        {"name": "Bob", "email": "bob@example.com", "active": False},
        {"name": "Charlie", "email": "charlie@example.com", "active": True}
    ], "users")
    
    await pulse.close()
    
    # Now create readonly connector
    readonly = SQLiteReadonlyPulse(temp_db_path)
    await readonly.connect()
    
    yield readonly
    
    await readonly.close()


@pytest_asyncio.fixture
async def writeonly_pulse(temp_db_path):
    """Create a SQLiteWriteonlyPulse instance with temporary database."""
    # First create the database with tables
    pulse = SQLitePulse(temp_db_path)
    await pulse.connect()
    
    await pulse.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            active BOOLEAN DEFAULT 1
        )
    """)
    
    await pulse.close()
    
    # Now create writeonly connector
    writeonly = SQLiteWriteonlyPulse(temp_db_path)
    await writeonly.connect()
    
    yield writeonly
    
    await writeonly.close()


class TestSQLitePulseIntegration:
    """Integration tests for the main SQLitePulse connector."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_cycle_operations(self, sqlite_pulse):
        """Test complete read-write cycle with real database."""
        # Insert data
        users_data = [
            {"name": "Alice", "email": "alice@example.com", "active": True},
            {"name": "Bob", "email": "bob@example.com", "active": False},
            {"name": "Charlie", "email": "charlie@example.com", "active": True}
        ]
        
        await sqlite_pulse.write(users_data, "users")
        
        # Query data
        results = await sqlite_pulse.query("SELECT * FROM users ORDER BY name")
        
        assert len(results) == 3
        assert results[0]["name"] == "Alice"
        assert results[1]["name"] == "Bob"
        assert results[2]["name"] == "Charlie"
        
        # Test parameterized query
        active_users = await sqlite_pulse.query_with_params(
            "SELECT * FROM users WHERE active = ?", [True]
        )
        assert len(active_users) == 2
        
        # Test table operations
        tables = await sqlite_pulse.list_tables()
        assert "users" in tables
        assert "events" in tables
        
        # Test table info
        user_table_info = await sqlite_pulse.get_table_info("users")
        assert len(user_table_info) == 5  # id, name, email, active, created_at
        
        # Test custom SQL execution
        result = await sqlite_pulse.execute(
            "UPDATE users SET active = ? WHERE name = ?", [False, "Alice"]
        )
        assert result is True
        
        # Verify update
        alice = await sqlite_pulse.query_with_params(
            "SELECT * FROM users WHERE name = ?", ["Alice"]
        )
        assert len(alice) == 1
        assert alice[0]["active"] == 0  # SQLite stores booleans as 0/1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bulk_operations(self, sqlite_pulse):
        """Test bulk insert and copy operations."""
        # Test bulk insert
        large_dataset = [
            {"name": f"User{i}", "email": f"user{i}@example.com", "active": True}
            for i in range(100)
        ]
        
        await sqlite_pulse.write(large_dataset, "users")
        
        # Verify all records were inserted
        count_result = await sqlite_pulse.query("SELECT COUNT(*) as count FROM users")
        assert count_result[0]["count"] == 100
        
        # Test copy_records
        additional_users = [
            {"name": f"ExtraUser{i}", "email": f"extra{i}@example.com", "active": False}
            for i in range(50)
        ]
        
        result = await sqlite_pulse.copy_records("users", additional_users)
        assert result is True
        
        # Verify total count
        final_count = await sqlite_pulse.query("SELECT COUNT(*) as count FROM users")
        assert final_count[0]["count"] == 150

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transaction_handling(self, sqlite_pulse):
        """Test transaction support and rollback."""
        # Start with clean state
        await sqlite_pulse.execute("DELETE FROM users")
        
        # Insert initial data
        await sqlite_pulse.write([
            {"name": "Alice", "email": "alice@example.com", "active": True}
        ], "users")
        
        # Verify initial state
        initial_count = await sqlite_pulse.query("SELECT COUNT(*) as count FROM users")
        assert initial_count[0]["count"] == 1
        
        try:
            # Attempt to insert invalid data (duplicate email)
            await sqlite_pulse.write([
                {"name": "Bob", "email": "alice@example.com", "active": True}
            ], "users")
            assert False, "Should have raised an error"
        except Exception:
            # Expected error due to unique constraint violation
            pass
        
        # Verify rollback occurred (count should still be 1)
        final_count = await sqlite_pulse.query("SELECT COUNT(*) as count FROM users")
        assert final_count[0]["count"] == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_management(self, temp_db_path):
        """Test connection lifecycle and reconnection."""
        pulse = SQLitePulse(temp_db_path)
        
        # Test initial connection
        assert not await pulse.is_connected()
        
        await pulse.connect()
        assert await pulse.is_connected()
        
        # Test reconnection
        await pulse.close()
        assert not await pulse.is_connected()
        
        await pulse.connect()
        assert await pulse.is_connected()
        
        await pulse.close()


class TestSQLiteReadonlyPulseIntegration:
    """Integration tests for the SQLiteReadonlyPulse connector."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_read_operations(self, readonly_pulse):
        """Test read-only operations with real data."""
        # Test basic query
        all_users = await readonly_pulse.query("SELECT * FROM users ORDER BY name")
        assert len(all_users) == 3
        
        # Test parameterized query
        active_users = await readonly_pulse.query_with_params(
            "SELECT * FROM users WHERE active = ?", [True]
        )
        assert len(active_users) == 2
        
        # Test complex query
        user_stats = await readonly_pulse.query_with_params("""
            SELECT 
                active,
                COUNT(*) as user_count,
                GROUP_CONCAT(name) as names
            FROM users 
            GROUP BY active
            ORDER BY active DESC
        """, [])
        
        assert len(user_stats) == 2
        assert user_stats[0]["active"] == 1  # Active users first
        assert user_stats[0]["user_count"] == 2
        
        # Test table operations
        tables = await readonly_pulse.list_tables()
        assert "users" in tables
        
        table_info = await readonly_pulse.get_table_info("users")
        assert len(table_info) == 4  # id, name, email, active

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_error_handling(self, readonly_pulse):
        """Test error handling for invalid queries."""
        # Test invalid SQL
        with pytest.raises(Exception):
            await readonly_pulse.query("SELECT * FROM non_existent_table")
        
        # Test invalid table name in get_table_info (SQLite returns empty list for non-existent tables)
        table_info = await readonly_pulse.get_table_info("non_existent_table")
        assert table_info == []


class TestSQLiteWriteonlyPulseIntegration:
    """Integration tests for the SQLiteWriteonlyPulse connector."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_write_operations(self, writeonly_pulse):
        """Test write operations with real database."""
        # Test basic insert
        users_data = [
            {"name": "Alice", "email": "alice@example.com", "active": True},
            {"name": "Bob", "email": "bob@example.com", "active": False}
        ]
        
        # Add table name to each record for writeonly connector
        users_data_with_table = [
            {**user, "table": "users"} for user in users_data
        ]
        await writeonly_pulse.write(users_data_with_table)
        
        # Verify data was written (using a temporary readonly connection)
        temp_pulse = SQLitePulse(writeonly_pulse.database_path)
        await temp_pulse.connect()
        
        count_result = await temp_pulse.query("SELECT COUNT(*) as count FROM users")
        assert count_result[0]["count"] == 2
        
        await temp_pulse.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_operations(self, writeonly_pulse):
        """Test custom SQL execution."""
        # Test INSERT
        result = await writeonly_pulse.execute(
            "INSERT INTO users (name, email, active) VALUES (?, ?, ?)",
            ["Charlie", "charlie@example.com", True]
        )
        assert result is True
        
        # Test UPDATE
        result = await writeonly_pulse.execute(
            "UPDATE users SET active = ? WHERE name = ?",
            [False, "Charlie"]
        )
        assert result is True
        
        # Test DELETE
        result = await writeonly_pulse.execute(
            "DELETE FROM users WHERE name = ?",
            ["Charlie"]
        )
        assert result is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_copy_records(self, writeonly_pulse):
        """Test bulk copy operations."""
        # Test bulk copy
        large_dataset = [
            {"name": f"BulkUser{i}", "email": f"bulk{i}@example.com", "active": True}
            for i in range(100)
        ]
        
        result = await writeonly_pulse.copy_records("users", large_dataset)
        assert result is True
        
        # Verify all records were copied
        temp_pulse = SQLitePulse(writeonly_pulse.database_path)
        await temp_pulse.connect()
        
        count_result = await temp_pulse.query("SELECT COUNT(*) as count FROM users")
        assert count_result[0]["count"] == 100
        
        await temp_pulse.close()


class TestSQLitePerformance:
    """Performance tests for the SQLite connector."""

    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, temp_db_path):
        """Test performance of bulk insert operations."""
        pulse = SQLitePulse(temp_db_path)
        await pulse.connect()
        
        # Create table
        await pulse.execute("""
            CREATE TABLE performance_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Generate large dataset
        large_dataset = [
            {"name": f"Item{i}", "value": i}
            for i in range(10000)
        ]
        
        # Measure bulk insert performance
        import time
        start_time = time.time()
        
        await pulse.write(large_dataset, "performance_test")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all records were inserted
        count_result = await pulse.query("SELECT COUNT(*) as count FROM performance_test")
        assert count_result[0]["count"] == 10000
        
        # Performance assertion (should complete in reasonable time)
        assert duration < 10.0, f"Bulk insert took {duration:.2f} seconds, expected < 10s"
        
        await pulse.close()

    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_performance(self, temp_db_path):
        """Test performance of query operations."""
        pulse = SQLitePulse(temp_db_path)
        await pulse.connect()
        
        # Create and populate table
        await pulse.execute("""
            CREATE TABLE query_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        test_data = [
            {"category": f"cat{i % 10}", "value": float(i)}
            for i in range(10000)
        ]
        await pulse.write(test_data, "query_test")
        
        # Test query performance
        import time
        start_time = time.time()
        
        # Complex analytical query
        results = await pulse.query("""
            SELECT 
                category,
                COUNT(*) as count,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value
            FROM query_test 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify results
        assert len(results) == 10  # 10 categories
        assert results[0]["count"] == 1000  # Each category should have 1000 items
        
        # Performance assertion
        assert duration < 5.0, f"Complex query took {duration:.2f} seconds, expected < 5s"
        
        await pulse.close()
