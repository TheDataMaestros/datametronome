"""
End-to-end tests for Level 1 checks via API.

These tests verify that Level 1 checks work correctly through the full API stack,
including database operations, connector setup, and result persistence.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from datametronome_podium.main import app
from datametronome_podium.models.clef import Clef
from datametronome_podium.models.stave import Stave
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.asyncio
class TestLevel1ChecksE2E:
    """End-to-end tests for Level 1 checks via API."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def async_client(self):
        """Create an async test client."""
        return AsyncClient(app=app, base_url="http://test")

    @pytest.fixture
    def mock_db(self):
        """Mock database for testing."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def test_stave_data(self):
        """Sample stave data."""
        return {
            "id": "stave-test-001",
            "name": "Test SQLite Database",
            "data_source_type": "sqlite",
            "config": json.dumps({"database": ":memory:"}),
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    @pytest.fixture
    def test_clef_row_count(self):
        """Sample row_count clef."""
        return {
            "id": "clef-rowcount-001",
            "stave_id": "stave-test-001",
            "name": "User Count Check",
            "check_type": "row_count",
            "config": json.dumps({"table": "users"}),
            "warn": "> 10000",
            "fail": "< 100",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    @pytest.fixture
    def test_clef_column_values(self):
        """Sample column_values clef."""
        return {
            "id": "clef-column-values-001",
            "stave_id": "stave-test-001",
            "name": "Email NULL Check",
            "check_type": "column_values",
            "config": json.dumps({"table": "users", "column": "email"}),
            "fail": "if_null > 5%",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    @pytest.fixture
    def test_clef_freshness(self):
        """Sample freshness clef."""
        return {
            "id": "clef-freshness-001",
            "stave_id": "stave-test-001",
            "name": "Data Freshness Check",
            "check_type": "freshness",
            "config": json.dumps(
                {"table": "events", "column": "updated_at", "max_age_hours": 24}
            ),
            "warn": "> 12 hours",
            "fail": "> 24 hours",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    @pytest.mark.asyncio
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.get_db")
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.insert_data")
    async def test_row_count_check_e2e(
        self,
        mock_insert,
        mock_get_db,
        async_client,
        mock_db,
        test_stave_data,
        test_clef_row_count,
    ):
        """Test row_count check end-to-end via API."""
        # Setup mocks
        mock_get_db.return_value = mock_db

        # Mock database queries
        mock_db.query.side_effect = [
            [test_clef_row_count],  # Get clef
            [test_stave_data],  # Get stave
        ]

        # Mock connector (will be created by ClefExecutor)
        mock_connector = AsyncMock()
        mock_connector.query.return_value = [{"row_count": 5000}]

        # Mock insert_data
        mock_insert.return_value = True

        # Mock connector creation
        with patch(
            "datametronome_podium.services.clef_executor.ConnectionTester"
        ) as mock_conn_tester:
            mock_conn_tester_instance = MagicMock()
            mock_conn_tester_instance.get_connector.return_value = mock_connector
            mock_conn_tester.return_value = mock_conn_tester_instance

            # Call API endpoint
            response = await async_client.post(
                f"/api/v1/clefs/{test_clef_row_count['id']}/run-now"
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "pass"
        assert data["observed_value"] == 5000
        assert "row_count" in data["metadata"]
        assert data["clef_id"] == test_clef_row_count["id"]
        assert data["stave_id"] == test_stave_data["id"]

        # Verify result was stored
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "checks"
        stored_data = call_args[0][1]
        assert stored_data["status"] == "pass"
        assert stored_data["clef_id"] == test_clef_row_count["id"]

    @pytest.mark.asyncio
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.get_db")
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.insert_data")
    async def test_column_values_if_null_e2e(
        self,
        mock_insert,
        mock_get_db,
        async_client,
        mock_db,
        test_stave_data,
        test_clef_column_values,
    ):
        """Test column_values if_null check end-to-end via API."""
        # Setup mocks
        mock_get_db.return_value = mock_db

        # Mock database queries
        mock_db.query.side_effect = [
            [test_clef_column_values],  # Get clef
            [test_stave_data],  # Get stave
        ]

        # Mock connector
        mock_connector = AsyncMock()
        mock_connector.query.return_value = [
            {"total_rows": 1000, "non_null_rows": 980, "null_rows": 20}
        ]

        mock_insert.return_value = True

        with patch(
            "datametronome_podium.services.clef_executor.ConnectionTester"
        ) as mock_conn_tester:
            mock_conn_tester_instance = MagicMock()
            mock_conn_tester_instance.get_connector.return_value = mock_connector
            mock_conn_tester.return_value = mock_conn_tester_instance

            # Call API endpoint
            response = await async_client.post(
                f"/api/v1/clefs/{test_clef_column_values['id']}/run-now"
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "pass"  # 2% nulls < 5% threshold
        assert data["observed_value"] == 0.02
        assert "null_percentage" in data["metadata"]
        assert data["metadata"]["null_rows"] == 20

    @pytest.mark.asyncio
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.get_db")
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.insert_data")
    async def test_column_values_if_not_unique_e2e(
        self, mock_insert, mock_get_db, async_client, mock_db, test_stave_data
    ):
        """Test column_values if_not_unique check end-to-end via API."""
        test_clef = {
            "id": "clef-unique-001",
            "stave_id": "stave-test-001",
            "name": "User ID Uniqueness Check",
            "check_type": "column_values",
            "config": json.dumps({"table": "users", "column": "id"}),
            "fail": "if_not_unique > 0",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        mock_get_db.return_value = mock_db
        mock_db.query.side_effect = [[test_clef], [test_stave_data]]

        mock_connector = AsyncMock()
        mock_connector.query.return_value = [
            {"total_rows": 1000, "unique_values": 995, "duplicate_rows": 5}
        ]

        mock_insert.return_value = True

        with patch(
            "datametronome_podium.services.clef_executor.ConnectionTester"
        ) as mock_conn_tester:
            mock_conn_tester_instance = MagicMock()
            mock_conn_tester_instance.get_connector.return_value = mock_connector
            mock_conn_tester.return_value = mock_conn_tester_instance

            response = await async_client.post(
                f"/api/v1/clefs/{test_clef['id']}/run-now"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "fail"  # Has duplicates
        assert data["observed_value"] == 5
        assert "duplicate_rows" in data["metadata"]

    @pytest.mark.asyncio
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.get_db")
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.insert_data")
    async def test_column_values_if_not_in_e2e(
        self, mock_insert, mock_get_db, async_client, mock_db, test_stave_data
    ):
        """Test column_values if_not_in check end-to-end via API."""
        test_clef = {
            "id": "clef-not-in-001",
            "stave_id": "stave-test-001",
            "name": "Status Value Check",
            "check_type": "column_values",
            "config": json.dumps({"table": "orders", "column": "status"}),
            "fail": "if_not_in: ['pending', 'completed', 'cancelled'] > 0",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        mock_get_db.return_value = mock_db
        mock_db.query.side_effect = [[test_clef], [test_stave_data]]

        mock_connector = AsyncMock()
        mock_connector.query.return_value = [
            {"total_rows": 1000, "not_in_list_rows": 15}
        ]

        mock_insert.return_value = True

        with patch(
            "datametronome_podium.services.clef_executor.ConnectionTester"
        ) as mock_conn_tester:
            mock_conn_tester_instance = MagicMock()
            mock_conn_tester_instance.get_connector.return_value = mock_connector
            mock_conn_tester.return_value = mock_conn_tester_instance

            response = await async_client.post(
                f"/api/v1/clefs/{test_clef['id']}/run-now"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "fail"  # Has invalid values
        assert data["observed_value"] == 15
        assert "allowed_values" in data["metadata"]
        assert data["metadata"]["allowed_values"] == [
            "pending",
            "completed",
            "cancelled",
        ]

    @pytest.mark.asyncio
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.get_db")
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.insert_data")
    async def test_freshness_check_e2e(
        self,
        mock_insert,
        mock_get_db,
        async_client,
        mock_db,
        test_stave_data,
        test_clef_freshness,
    ):
        """Test freshness check end-to-end via API."""
        mock_get_db.return_value = mock_db
        mock_db.query.side_effect = [[test_clef_freshness], [test_stave_data]]

        # Mock recent timestamp (2 hours ago)
        recent_time = datetime.utcnow() - timedelta(hours=2)
        mock_connector = AsyncMock()
        mock_connector.query.return_value = [{"latest_timestamp": recent_time}]

        mock_insert.return_value = True

        with patch(
            "datametronome_podium.services.clef_executor.ConnectionTester"
        ) as mock_conn_tester:
            mock_conn_tester_instance = MagicMock()
            mock_conn_tester_instance.get_connector.return_value = mock_connector
            mock_conn_tester.return_value = mock_conn_tester_instance

            response = await async_client.post(
                f"/api/v1/clefs/{test_clef_freshness['id']}/run-now"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "pass"  # 2 hours < 24 hours
        assert isinstance(data["observed_value"], (int, float))
        assert data["observed_value"] < 24
        assert "age_hours" in data["metadata"]

    @pytest.mark.asyncio
    @patch("datametronome_podium.api.v1.endpoints.clef_actions.get_db")
    async def test_clef_not_found(self, mock_get_db, async_client, mock_db):
        """Test API error handling when clef not found."""
        mock_get_db.return_value = mock_db
        mock_db.query.return_value = []  # No clef found

        response = await async_client.post("/api/v1/clefs/nonexistent-id/run-now")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


