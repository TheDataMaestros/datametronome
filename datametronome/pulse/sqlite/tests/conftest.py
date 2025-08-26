"""
Pytest configuration and shared fixtures for DataPulse SQLite tests.

This file provides common test configuration and fixtures that can be
shared across all test modules.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return [
        {"name": "Alice", "email": "alice@example.com", "active": True},
        {"name": "Bob", "email": "bob@example.com", "active": False},
        {"name": "Charlie", "email": "charlie@example.com", "active": True},
        {"name": "Diana", "email": "diana@example.com", "active": True},
        {"name": "Eve", "email": "eve@example.com", "active": False}
    ]


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return [
        {"user_id": 1, "event_type": "login", "event_data": "web"},
        {"user_id": 1, "event_type": "logout", "event_data": "web"},
        {"user_id": 2, "event_type": "login", "event_data": "mobile"},
        {"user_id": 3, "event_type": "purchase", "event_data": "web"},
        {"user_id": 4, "event_type": "login", "event_data": "web"}
    ]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (benchmarks, etc.)"
    )
    config.addinivalue_line(
        "markers", "asyncio: Async tests"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark async tests with asyncio marker."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
