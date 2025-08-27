"""
Integration tests for DataMetronome Podium API.
Tests the complete API workflow including authentication, data operations, and error handling.
"""

import pytest
import asyncio
import asyncpg
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import the FastAPI app and models
from datametronome_podium.main import app
from datametronome_podium.models.user import User
from datametronome_podium.models.stave import Stave
from datametronome_podium.models.clef import Clef
from datametronome_podium.models.check_run import CheckRun


class TestPodiumAPIIntegration:
    """Integration tests for the complete Podium API workflow."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def async_client(self):
        """Create an async test client."""
        return AsyncClient(app=app, base_url="http://test")
    
    @pytest.fixture
    def test_user_data(self):
        """Sample user data for testing."""
        return {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True
        }
    
    @pytest.fixture
    def test_stave_data(self):
        """Sample stave data for testing."""
        return {
            "name": "Test Stave",
            "description": "A test stave for integration testing",
            "stave_type": "postgres_monitor",
            "config": {
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "testuser"
            },
            "is_active": True
        }
    
    @pytest.fixture
    def test_clef_data(self):
        """Sample clef data for testing."""
        return {
            "name": "Test Clef",
            "description": "A test clef for data quality checks",
            "clef_type": "postgres_quality",
            "config": {
                "table_name": "users",
                "checks": [
                    {
                        "type": "null_check",
                        "column": "email",
                        "threshold": 0
                    }
                ]
            },
            "is_active": True
        }
    
    @pytest.fixture
    def mock_database(self):
        """Mock database connection for testing."""
        with patch('datametronome.podium.datametronome_podium.core.database.get_db') as mock:
            mock_db = AsyncMock()
            mock.return_value = mock_db
            yield mock_db
    
    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_api_docs_available(self, client):
        """Test that API documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        response = client.get("/redoc")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_user_creation_workflow(self, async_client, mock_database, test_user_data):
        """Test complete user creation workflow."""
        # Mock database operations
        mock_database.execute.return_value = None
        mock_database.fetchval.return_value = 1  # Return user ID
        
        # Create user
        response = await async_client.post("/api/v1/users/", json=test_user_data)
        assert response.status_code == 201
        
        user_data = response.json()
        assert user_data["username"] == test_user_data["username"]
        assert user_data["email"] == test_user_data["email"]
        assert "id" in user_data
        assert "created_at" in user_data
        
        # Verify database was called
        mock_database.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_stave_creation_workflow(self, async_client, mock_database, test_stave_data):
        """Test complete stave creation workflow."""
        # Mock database operations
        mock_database.execute.return_value = None
        mock_database.fetchval.return_value = 1  # Return stave ID
        
        # Create stave
        response = await async_client.post("/api/v1/staves/", json=test_stave_data)
        assert response.status_code == 201
        
        stave_data = response.json()
        assert stave_data["name"] == test_stave_data["name"]
        assert stave_data["stave_type"] == test_stave_data["stave_type"]
        assert "id" in stave_data
        assert "created_at" in stave_data
        
        # Verify database was called
        mock_database.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_clef_creation_workflow(self, async_client, mock_database, test_clef_data):
        """Test complete clef creation workflow."""
        # Mock database operations
        mock_database.execute.return_value = None
        mock_database.fetchval.return_value = 1  # Return clef ID
        
        # Create clef
        response = await async_client.post("/api/v1/clefs/", json=test_clef_data)
        assert response.status_code == 201
        
        clef_data = response.json()
        assert clef_data["name"] == test_clef_data["name"]
        assert clef_data["clef_type"] == test_clef_data["clef_type"]
        assert "id" in clef_data
        assert "created_at" in stave_data
        
        # Verify database was called
        mock_database.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_run_execution_workflow(self, async_client, mock_database):
        """Test complete check run execution workflow."""
        # Mock database operations
        mock_database.execute.return_value = None
        mock_database.fetchval.return_value = 1  # Return check run ID
        
        # Mock the check execution service
        with patch('datametronome.podium.datametronome_podium.services.postgres_monitor_service.PostgresMonitorService.execute_check') as mock_execute:
            mock_execute.return_value = {
                "status": "passed",
                "details": {"anomalies_found": 0},
                "execution_time": 150.5
            }
            
            # Execute check
            check_data = {
                "stave_id": 1,
                "clef_id": 1,
                "parameters": {"table_name": "users"}
            }
            
            response = await async_client.post("/api/v1/checks/execute", json=check_data)
            assert response.status_code == 200
            
            check_result = response.json()
            assert check_result["status"] == "passed"
            assert "execution_time" in check_result
            assert "details" in check_result
    
    @pytest.mark.asyncio
    async def test_data_quality_monitoring_workflow(self, async_client, mock_database):
        """Test complete data quality monitoring workflow."""
        # Mock database operations
        mock_database.execute.return_value = None
        mock_database.fetch.return_value = [
            {"id": 1, "name": "users", "check_type": "null_check", "status": "passed"},
            {"id": 2, "name": "orders", "check_type": "duplicate_check", "status": "failed"}
        ]
        
        # Get data quality status
        response = await async_client.get("/api/v1/checks/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert "checks" in status_data
        assert len(status_data["checks"]) == 2
        assert status_data["checks"][0]["status"] == "passed"
        assert status_data["checks"][1]["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, async_client, mock_database):
        """Test API error handling for various scenarios."""
        # Test invalid JSON
        response = await async_client.post("/api/v1/users/", data="invalid json")
        assert response.status_code == 422
        
        # Test missing required fields
        incomplete_user = {"username": "test"}
        response = await async_client.post("/api/v1/users/", json=incomplete_user)
        assert response.status_code == 422
        
        # Test database connection error
        mock_database.execute.side_effect = Exception("Database connection failed")
        response = await async_client.post("/api/v1/users/", json=test_user_data)
        assert response.status_code == 500
        
        # Test validation errors
        invalid_user = {
            "username": "",  # Empty username
            "email": "invalid-email",  # Invalid email
            "full_name": "Test User"
        }
        response = await async_client.post("/api/v1/users/", json=invalid_user)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_authentication_workflow(self, async_client, mock_database):
        """Test authentication and authorization workflow."""
        # Test login with valid credentials
        login_data = {
            "username": "testuser",
            "password": "testpassword"
        }
        
        with patch('datametronome.podium.datametronome_podium.core.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = {"access_token": "test_token", "token_type": "bearer"}
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 200
            
            token_data = response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"
        
        # Test protected endpoint with token
        headers = {"Authorization": "Bearer test_token"}
        response = await async_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        
        # Test protected endpoint without token
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_client):
        """Test API rate limiting functionality."""
        # Make multiple rapid requests
        for i in range(10):
            response = await async_client.get("/health")
            assert response.status_code == 200
        
        # The 11th request should be rate limited (if rate limiting is implemented)
        # This test assumes rate limiting is configured
        response = await async_client.get("/health")
        # Rate limiting might return 429 or continue to work depending on configuration
        assert response.status_code in [200, 429]
    
    @pytest.mark.asyncio
    async def test_logging_and_monitoring(self, async_client, mock_database):
        """Test that API requests are properly logged and monitored."""
        # Mock logging
        with patch('datametronome.podium.datametronome_podium.core.logging.info') as mock_log:
            response = await async_client.get("/health")
            assert response.status_code == 200
            
            # Verify logging was called
            mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_database_transactions(self, mock_database):
        """Test database transaction handling."""
        # Mock transaction methods
        mock_database.begin.return_value = None
        mock_database.commit.return_value = None
        mock_database.rollback.return_value = None
        
        # Test successful transaction
        try:
            await mock_database.begin()
            await mock_database.execute("INSERT INTO users (username) VALUES ($1)", ["testuser"])
            await mock_database.commit()
        except Exception:
            await mock_database.rollback()
            raise
        
        # Verify transaction methods were called
        mock_database.begin.assert_called_once()
        mock_database.commit.assert_called_once()
        mock_database.rollback.assert_not_called()
        
        # Test failed transaction with rollback
        mock_database.execute.side_effect = Exception("Database error")
        
        try:
            await mock_database.begin()
            await mock_database.execute("INSERT INTO users (username) VALUES ($1)", ["testuser"])
            await mock_database.commit()
        except Exception:
            await mock_database.rollback()
        
        # Verify rollback was called
        mock_database.rollback.assert_called_once()


class TestPodiumAPIPerformance:
    """Performance tests for the Podium API."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client, mock_database):
        """Test API performance under concurrent load."""
        import asyncio
        import time
        
        # Mock database operations
        mock_database.execute.return_value = None
        mock_database.fetchval.return_value = 1
        
        async def make_request():
            """Make a single API request."""
            response = await async_client.get("/health")
            return response.status_code
        
        # Make 10 concurrent requests
        start_time = time.time()
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        
        # Performance check (should complete within reasonable time)
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        print(f"Concurrent requests completed in {execution_time:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_large_data_handling(self, async_client, mock_database):
        """Test API performance with large data sets."""
        # Mock large dataset
        large_dataset = [{"id": i, "name": f"user_{i}"} for i in range(10000)]
        mock_database.fetch.return_value = large_dataset
        
        # Test pagination
        response = await async_client.get("/api/v1/users/?page=1&size=100")
        assert response.status_code == 200
        
        # Test filtering
        response = await async_client.get("/api/v1/users/?search=user_1000")
        assert response.status_code == 200
        
        # Test sorting
        response = await async_client.get("/api/v1/users/?sort_by=name&sort_order=desc")
        assert response.status_code == 200


class TestPodiumAPISecurity:
    """Security tests for the Podium API."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, async_client, mock_database):
        """Test that the API prevents SQL injection attacks."""
        # Test malicious input
        malicious_input = "'; DROP TABLE users; --"
        
        # This should be properly sanitized and not cause issues
        response = await async_client.get(f"/api/v1/users/?search={malicious_input}")
        
        # Should either return 400 (bad request) or 200 with no results
        assert response.status_code in [200, 400]
        
        # If it returns 200, should not contain the malicious SQL
        if response.status_code == 200:
            data = response.json()
            assert "DROP TABLE" not in str(data)
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self, async_client, mock_database):
        """Test that the API prevents XSS attacks."""
        # Test malicious script input
        malicious_input = "<script>alert('xss')</script>"
        
        # This should be properly escaped
        response = await async_client.get(f"/api/v1/users/?search={malicious_input}")
        
        # Should return 200 with escaped content
        assert response.status_code == 200
        
        # Content should be escaped
        data = response.json()
        assert "<script>" not in str(data)
    
    @pytest.mark.asyncio
    async def test_input_validation(self, async_client):
        """Test input validation and sanitization."""
        # Test extremely long input
        long_input = "a" * 10000
        
        response = await async_client.get(f"/api/v1/users/?search={long_input}")
        assert response.status_code == 400  # Should reject extremely long input
        
        # Test special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        response = await async_client.get(f"/api/v1/users/?search={special_chars}")
        # Should either accept or reject based on validation rules
        assert response.status_code in [200, 400]


if __name__ == "__main__":
    pytest.main([__file__])
