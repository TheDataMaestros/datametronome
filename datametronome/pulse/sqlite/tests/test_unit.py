"""
Unit tests for DataPulse SQLite connector.

These tests focus on isolated component testing without database dependencies.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from metronome_pulse_sqlite import SQLitePulse, SQLiteReadonlyPulse, SQLiteWriteonlyPulse


class TestSQLitePulse:
    """Test the main SQLitePulse connector class."""

    def test_init_default_path(self):
        """Test initialization with default database path."""
        pulse = SQLitePulse()
        assert pulse.database_path == "datametronome.db"
        assert pulse.connection is None
        assert isinstance(pulse._readonly, SQLiteReadonlyPulse)
        assert isinstance(pulse._writeonly, SQLiteWriteonlyPulse)

    def test_init_custom_path(self):
        """Test initialization with custom database path."""
        custom_path = "/custom/path/database.db"
        pulse = SQLitePulse(custom_path)
        assert pulse.database_path == custom_path

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to SQLite database."""
        pulse = SQLitePulse(":memory:")
        
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('sqlite3.connect') as mock_connect:
                mock_connection = Mock()
                mock_connect.return_value = mock_connection
                
                # Mock the readonly and writeonly connectors
                pulse._readonly.connect = AsyncMock()
                pulse._writeonly.connect = AsyncMock()
                
                await pulse.connect()
                
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_connect.assert_called_once_with(":memory:")
                assert pulse.connection == mock_connection
                assert mock_connection.row_factory == sqlite3.Row
                pulse._readonly.connect.assert_called_once()
                pulse._writeonly.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling."""
        pulse = SQLitePulse("invalid/path/db.db")
        
        with patch('sqlite3.connect', side_effect=Exception("Connection failed")):
            with pytest.raises(ConnectionError, match="Failed to connect to SQLite: Connection failed"):
                await pulse.connect()

    @pytest.mark.asyncio
    async def test_close_success(self):
        """Test successful connection closure."""
        pulse = SQLitePulse()
        mock_connection = Mock()
        pulse.connection = mock_connection
        
        # Mock the readonly and writeonly connectors
        pulse._readonly.close = AsyncMock()
        pulse._writeonly.close = AsyncMock()
        
        await pulse.close()
        
        mock_connection.close.assert_called_once()
        assert pulse.connection is None
        pulse._readonly.close.assert_called_once()
        pulse._writeonly.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_connection(self):
        """Test closing when no connection exists."""
        pulse = SQLitePulse()
        pulse.connection = None
        
        # Mock the readonly and writeonly connectors
        pulse._readonly.close = AsyncMock()
        pulse._writeonly.close = AsyncMock()
        
        await pulse.close()
        
        pulse._readonly.close.assert_called_once()
        pulse._writeonly.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_connected_true(self):
        """Test connection status when fully connected."""
        pulse = SQLitePulse()
        pulse.connection = Mock()
        pulse._readonly.is_connected = AsyncMock(return_value=True)
        pulse._writeonly.is_connected = AsyncMock(return_value=True)
        
        result = await pulse.is_connected()
        
        assert result is True
        pulse._readonly.is_connected.assert_called_once()
        pulse._writeonly.is_connected.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_connected_false(self):
        """Test connection status when not connected."""
        pulse = SQLitePulse()
        pulse.connection = None
        
        result = await pulse.is_connected()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_query_delegation(self):
        """Test that query operations are delegated to readonly connector."""
        pulse = SQLitePulse()
        pulse._readonly.query = AsyncMock(return_value=[{"id": 1}])
        pulse._readonly.is_connected = AsyncMock(return_value=True)
        pulse._writeonly.is_connected = AsyncMock(return_value=True)
        pulse.connection = Mock()
        
        query_config = "SELECT * FROM users"
        result = await pulse.query(query_config)
        
        pulse._readonly.query.assert_called_once_with(query_config)
        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_query_not_connected(self):
        """Test query when not connected."""
        pulse = SQLitePulse()
        pulse.connection = None
        
        with pytest.raises(RuntimeError, match="Not connected to SQLite database"):
            await pulse.query("SELECT * FROM users")

    @pytest.mark.asyncio
    async def test_write_delegation(self):
        """Test that write operations are delegated to writeonly connector."""
        pulse = SQLitePulse()
        pulse._writeonly.write = AsyncMock()
        pulse._readonly.is_connected = AsyncMock(return_value=True)
        pulse._writeonly.is_connected = AsyncMock(return_value=True)
        pulse.connection = Mock()
        
        data = [{"name": "Alice"}, {"name": "Bob"}]
        destination = "users"
        
        await pulse.write(data, destination)
        
        # Check that table field was added to each record
        expected_data = [
            {"name": "Alice", "table": "users"},
            {"name": "Bob", "table": "users"}
        ]
        pulse._writeonly.write.assert_called_once_with(expected_data, None)

    @pytest.mark.asyncio
    async def test_write_with_existing_table_field(self):
        """Test write when table field already exists in data."""
        pulse = SQLitePulse()
        pulse._writeonly.write = AsyncMock()
        pulse._readonly.is_connected = AsyncMock(return_value=True)
        pulse._writeonly.is_connected = AsyncMock(return_value=True)
        pulse.connection = Mock()
        
        data = [{"name": "Alice", "table": "custom_table"}]
        destination = "users"
        
        await pulse.write(data, destination)
        
        # Should not override existing table field
        pulse._writeonly.write.assert_called_once_with(data, None)

    @pytest.mark.asyncio
    async def test_execute_delegation(self):
        """Test that execute operations are delegated to writeonly connector."""
        pulse = SQLitePulse()
        pulse._writeonly.execute = AsyncMock(return_value=True)
        pulse._readonly.is_connected = AsyncMock(return_value=True)
        pulse._writeonly.is_connected = AsyncMock(return_value=True)
        pulse.connection = Mock()
        
        sql = "INSERT INTO users (name) VALUES (?)"
        params = ["Alice"]
        
        result = await pulse.execute(sql, params)
        
        pulse._writeonly.execute.assert_called_once_with(sql, params)
        assert result is True

    @pytest.mark.asyncio
    async def test_copy_records_delegation(self):
        """Test that copy_records operations are delegated to writeonly connector."""
        pulse = SQLitePulse()
        pulse._writeonly.copy_records = AsyncMock(return_value=True)
        pulse._readonly.is_connected = AsyncMock(return_value=True)
        pulse._writeonly.is_connected = AsyncMock(return_value=True)
        pulse.connection = Mock()
        
        table_name = "users"
        records = [{"name": "Alice"}, {"name": "Bob"}]
        
        result = await pulse.copy_records(table_name, records)
        
        pulse._writeonly.copy_records.assert_called_once_with(table_name, records)
        assert result is True


class TestSQLiteReadonlyPulse:
    """Test the SQLiteReadonlyPulse connector class."""

    def test_init(self):
        """Test readonly connector initialization."""
        readonly = SQLiteReadonlyPulse("test.db")
        assert readonly.database_path == "test.db"
        assert readonly.connection is None

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful readonly connection."""
        readonly = SQLiteReadonlyPulse(":memory:")
        
        with patch('sqlite3.connect') as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection
            
            await readonly.connect()
            
            mock_connect.assert_called_once_with(":memory:")
            assert readonly.connection == mock_connection
            assert mock_connection.row_factory == sqlite3.Row

    @pytest.mark.asyncio
    async def test_close(self):
        """Test readonly connection closure."""
        readonly = SQLiteReadonlyPulse("test.db")
        mock_connection = Mock()
        readonly.connection = mock_connection
        
        await readonly.close()
        
        mock_connection.close.assert_called_once()
        assert readonly.connection is None

    @pytest.mark.asyncio
    async def test_is_connected_true(self):
        """Test readonly connection status when connected."""
        readonly = SQLiteReadonlyPulse("test.db")
        readonly.connection = Mock()
        
        result = await readonly.is_connected()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_connected_false(self):
        """Test readonly connection status when not connected."""
        readonly = SQLiteReadonlyPulse("test.db")
        readonly.connection = None
        
        result = await readonly.is_connected()
        
        assert result is False


class TestSQLiteWriteonlyPulse:
    """Test the SQLiteWriteonlyPulse connector class."""

    def test_init(self):
        """Test writeonly connector initialization."""
        writeonly = SQLiteWriteonlyPulse("test.db")
        assert writeonly.database_path == "test.db"
        assert writeonly.connection is None

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful writeonly connection."""
        writeonly = SQLiteWriteonlyPulse(":memory:")
        
        with patch('sqlite3.connect') as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection
            
            await writeonly.connect()
            
            mock_connect.assert_called_once_with(":memory:")
            assert writeonly.connection == mock_connection
            assert mock_connection.row_factory == sqlite3.Row

    @pytest.mark.asyncio
    async def test_close(self):
        """Test writeonly connection closure."""
        writeonly = SQLiteWriteonlyPulse("test.db")
        mock_connection = Mock()
        writeonly.connection = mock_connection
        
        await writeonly.close()
        
        mock_connection.close.assert_called_once()
        assert writeonly.connection is None

    @pytest.mark.asyncio
    async def test_is_connected_true(self):
        """Test writeonly connection status when connected."""
        writeonly = SQLiteWriteonlyPulse("test.db")
        writeonly.connection = Mock()
        
        result = await writeonly.is_connected()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_connected_false(self):
        """Test writeonly connection status when not connected."""
        writeonly = SQLiteWriteonlyPulse("test.db")
        writeonly.connection = None
        
        result = await writeonly.is_connected()
        
        assert result is False


# Import sqlite3 for the tests
import sqlite3
