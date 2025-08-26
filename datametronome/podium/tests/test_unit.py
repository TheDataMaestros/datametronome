"""
Unit tests for DataMetronome Podium components.
These tests focus on individual components and logic without external dependencies.
Unit tests are the MOST IMPORTANT tests and should run quickly and reliably.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import the models and services for unit testing
from datametronome.podium.datametronome_podium.models.user import User
from datametronome.podium.datametronome_podium.models.stave import Stave
from datametronome.podium.datametronome_podium.models.clef import Clef
from datametronome.podium.datametronome_podium.models.check_run import CheckRun


class TestUserModelUnit:
    """Unit tests for User model validation and behavior."""
    
    def test_user_creation_valid_data(self):
        """Test user creation with valid data."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True
        }
        
        user = User(**user_data)
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.id is None  # Not set until saved
        assert user.created_at is not None
    
    def test_user_creation_minimal_data(self):
        """Test user creation with minimal required data."""
        user_data = {
            "username": "minimaluser",
            "email": "minimal@example.com"
        }
        
        user = User(**user_data)
        
        assert user.username == "minimaluser"
        assert user.email == "minimal@example.com"
        assert user.full_name is None
        assert user.is_active is True  # Default value
        assert user.created_at is not None
    
    def test_user_validation_invalid_email(self):
        """Test user validation with invalid email."""
        user_data = {
            "username": "testuser",
            "email": "invalid-email"  # Invalid email format
        }
        
        with pytest.raises(ValueError):
            User(**user_data)
    
    def test_user_validation_empty_username(self):
        """Test user validation with empty username."""
        user_data = {
            "username": "",  # Empty username
            "email": "test@example.com"
        }
        
        with pytest.raises(ValueError):
            User(**user_data)
    
    def test_user_validation_username_too_long(self):
        """Test user validation with username too long."""
        user_data = {
            "username": "a" * 51,  # 51 characters (max is 50)
            "email": "test@example.com"
        }
        
        with pytest.raises(ValueError):
            User(**user_data)
    
    def test_user_serialization(self):
        """Test user model serialization to JSON."""
        user = User(
            username="serializeuser",
            email="serialize@example.com",
            full_name="Serialize User"
        )
        
        user_dict = user.model_dump()
        
        assert user_dict["username"] == "serializeuser"
        assert user_dict["email"] == "serialize@example.com"
        assert user_dict["full_name"] == "Serialize User"
        assert "created_at" in user_dict
    
    def test_user_update(self):
        """Test user model field updates."""
        user = User(
            username="updateuser",
            email="update@example.com"
        )
        
        # Update fields
        user.full_name = "Updated User"
        user.is_active = False
        
        assert user.full_name == "Updated User"
        assert user.is_active is False


class TestStaveModelUnit:
    """Unit tests for Stave model validation and behavior."""
    
    def test_stave_creation_valid_data(self):
        """Test stave creation with valid data."""
        stave_data = {
            "name": "Test Stave",
            "description": "A test stave for unit testing",
            "stave_type": "postgres_monitor",
            "config": {
                "host": "localhost",
                "port": 5432,
                "database": "testdb"
            },
            "is_active": True
        }
        
        stave = Stave(**stave_data)
        
        assert stave.name == "Test Stave"
        assert stave.description == "A test stave for unit testing"
        assert stave.stave_type == "postgres_monitor"
        assert stave.config["host"] == "localhost"
        assert stave.is_active is True
    
    def test_stave_validation_invalid_type(self):
        """Test stave validation with invalid type."""
        stave_data = {
            "name": "Test Stave",
            "stave_type": "invalid_type",  # Invalid stave type
            "config": {}
        }
        
        with pytest.raises(ValueError):
            Stave(**stave_data)
    
    def test_stave_config_validation(self):
        """Test stave config validation."""
        stave_data = {
            "name": "Test Stave",
            "stave_type": "postgres_monitor",
            "config": {
                "host": "",  # Empty host
                "port": -1   # Invalid port
            }
        }
        
        with pytest.raises(ValueError):
            Stave(**stave_data)
    
    def test_stave_default_values(self):
        """Test stave default values."""
        stave_data = {
            "name": "Default Stave",
            "stave_type": "postgres_monitor"
        }
        
        stave = Stave(**stave_data)
        
        assert stave.description is None
        assert stave.is_active is True
        assert stave.config == {}
        assert stave.created_at is not None


class TestClefModelUnit:
    """Unit tests for Clef model validation and behavior."""
    
    def test_clef_creation_valid_data(self):
        """Test clef creation with valid data."""
        clef_data = {
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
        
        clef = Clef(**clef_data)
        
        assert clef.name == "Test Clef"
        assert clef.clef_type == "postgres_quality"
        assert clef.config["table_name"] == "users"
        assert len(clef.config["checks"]) == 1
        assert clef.is_active is True
    
    def test_clef_validation_invalid_type(self):
        """Test clef validation with invalid type."""
        clef_data = {
            "name": "Test Clef",
            "clef_type": "invalid_type",  # Invalid clef type
            "config": {}
        }
        
        with pytest.raises(ValueError):
            Clef(**clef_data)
    
    def test_clef_check_config_validation(self):
        """Test clef check configuration validation."""
        clef_data = {
            "name": "Test Clef",
            "clef_type": "postgres_quality",
            "config": {
                "table_name": "",
                "checks": [
                    {
                        "type": "invalid_check_type",
                        "column": "email"
                    }
                ]
            }
        }
        
        with pytest.raises(ValueError):
            Clef(**clef_data)
    
    def test_clef_serialization(self):
        """Test clef model serialization."""
        clef = Clef(
            name="Serialize Clef",
            clef_type="postgres_quality",
            config={"table_name": "test_table"}
        )
        
        clef_dict = clef.model_dump()
        
        assert clef_dict["name"] == "Serialize Clef"
        assert clef_dict["clef_type"] == "postgres_quality"
        assert clef_dict["config"]["table_name"] == "test_table"


class TestCheckRunModelUnit:
    """Unit tests for CheckRun model validation and behavior."""
    
    def test_check_run_creation_valid_data(self):
        """Test check run creation with valid data."""
        check_run_data = {
            "stave_id": 1,
            "clef_id": 1,
            "status": "running",
            "started_at": datetime.now(),
            "parameters": {"table_name": "users"}
        }
        
        check_run = CheckRun(**check_run_data)
        
        assert check_run.stave_id == 1
        assert check_run.clef_id == 1
        assert check_run.status == "running"
        assert check_run.parameters["table_name"] == "users"
    
    def test_check_run_status_validation(self):
        """Test check run status validation."""
        check_run_data = {
            "stave_id": 1,
            "clef_id": 1,
            "status": "invalid_status",  # Invalid status
            "parameters": {}
        }
        
        with pytest.raises(ValueError):
            CheckRun(**check_run_data)
    
    def test_check_run_status_transitions(self):
        """Test check run status transitions."""
        check_run = CheckRun(
            stave_id=1,
            clef_id=1,
            status="pending"
        )
        
        # Valid transitions
        check_run.status = "running"
        assert check_run.status == "running"
        
        check_run.status = "completed"
        assert check_run.status == "completed"
        
        check_run.status = "failed"
        assert check_run.status == "failed"
    
    def test_check_run_timing_calculation(self):
        """Test check run timing calculations."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        check_run = CheckRun(
            stave_id=1,
            clef_id=1,
            status="completed",
            started_at=start_time,
            completed_at=end_time
        )
        
        # Calculate duration
        duration = check_run.completed_at - check_run.started_at
        assert duration.total_seconds() == 30


class TestModelValidationUnit:
    """Unit tests for model validation logic."""
    
    def test_email_validation_patterns(self):
        """Test various email validation patterns."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com"
        ]
        
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user name@example.com"
        ]
        
        for email in valid_emails:
            user = User(username="testuser", email=email)
            assert user.email == email
        
        for email in invalid_emails:
            with pytest.raises(ValueError):
                User(username="testuser", email=email)
    
    def test_username_validation_patterns(self):
        """Test various username validation patterns."""
        valid_usernames = [
            "user123",
            "user_name",
            "user-name",
            "userName",
            "a" * 50  # Maximum length
        ]
        
        invalid_usernames = [
            "",  # Empty
            "a" * 51,  # Too long
            "user name",  # Contains space
            "user@name",  # Contains special character
            "123user"  # Starts with number
        ]
        
        for username in valid_usernames:
            user = User(username=username, email="test@example.com")
            assert user.username == username
        
        for username in invalid_usernames:
            with pytest.raises(ValueError):
                User(username=username, email="test@example.com")
    
    def test_config_validation_nested(self):
        """Test nested configuration validation."""
        valid_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "user",
                    "password": "pass"
                }
            }
        }
        
        stave = Stave(
            name="Test Stave",
            stave_type="postgres_monitor",
            config=valid_config
        )
        
        assert stave.config["database"]["host"] == "localhost"
        assert stave.config["database"]["credentials"]["username"] == "user"
    
    def test_parameter_validation_types(self):
        """Test parameter type validation."""
        valid_parameters = {
            "string_param": "value",
            "int_param": 42,
            "float_param": 3.14,
            "bool_param": True,
            "list_param": [1, 2, 3],
            "dict_param": {"key": "value"}
        }
        
        check_run = CheckRun(
            stave_id=1,
            clef_id=1,
            status="pending",
            parameters=valid_parameters
        )
        
        assert check_run.parameters["string_param"] == "value"
        assert check_run.parameters["int_param"] == 42
        assert check_run.parameters["bool_param"] is True


class TestModelSerializationUnit:
    """Unit tests for model serialization and deserialization."""
    
    def test_user_json_serialization(self):
        """Test user model JSON serialization."""
        user = User(
            username="jsonuser",
            email="json@example.com",
            full_name="JSON User"
        )
        
        # Convert to JSON string
        json_str = user.model_dump_json()
        user_dict = json.loads(json_str)
        
        assert user_dict["username"] == "jsonuser"
        assert user_dict["email"] == "json@example.com"
        assert user_dict["full_name"] == "JSON User"
    
    def test_stave_json_serialization(self):
        """Test stave model JSON serialization."""
        stave = Stave(
            name="JSON Stave",
            stave_type="postgres_monitor",
            config={"host": "localhost", "port": 5432}
        )
        
        json_str = stave.model_dump_json()
        stave_dict = json.loads(json_str)
        
        assert stave_dict["name"] == "JSON Stave"
        assert stave_dict["stave_type"] == "postgres_monitor"
        assert stave_dict["config"]["host"] == "localhost"
    
    def test_model_deserialization(self):
        """Test model deserialization from dictionaries."""
        user_dict = {
            "username": "deserializeuser",
            "email": "deserialize@example.com",
            "full_name": "Deserialize User",
            "is_active": False
        }
        
        user = User(**user_dict)
        
        assert user.username == "deserializeuser"
        assert user.email == "deserialize@example.com"
        assert user.full_name == "Deserialize User"
        assert user.is_active is False
    
    def test_model_partial_update(self):
        """Test partial model updates."""
        user = User(
            username="updateuser",
            email="update@example.com"
        )
        
        # Update with partial data
        update_data = {"full_name": "Updated Name", "is_active": False}
        for key, value in update_data.items():
            setattr(user, key, value)
        
        assert user.full_name == "Updated Name"
        assert user.is_active is False
        assert user.username == "updateuser"  # Unchanged


if __name__ == "__main__":
    pytest.main([__file__])
