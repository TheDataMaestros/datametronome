import pytest
from unittest.mock import AsyncMock
from datametronome_podium.features.users.repo import UserRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    return executor


class TestUserRepo:
    @pytest.mark.asyncio
    async def test_find_by_username_returns_none(self, mock_executor):
        repo = UserRepo(mock_executor)
        result = await repo.find_by_username("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_username_returns_user(self, mock_executor):
        mock_executor.select.return_value = [{
            "id": "1", "username": "admin", "email": "a@b.com",
            "hashed_password": "hash", "is_active": True,
            "is_superuser": False, "created_at": "2025-01-01", "updated_at": "2025-01-01"
        }]
        repo = UserRepo(mock_executor)
        result = await repo.find_by_username("admin")
        assert result is not None
        assert result.username == "admin"

    @pytest.mark.asyncio
    async def test_create_user(self, mock_executor):
        repo = UserRepo(mock_executor)
        from datametronome_podium.features.users.model import User
        user = User(
            id="1", username="test", email="t@t.com",
            hashed_password="hash", is_active=True, is_superuser=False,
            created_at="2025-01-01", updated_at="2025-01-01"
        )
        result = await repo.create(user)
        assert result == 1
        mock_executor.insert.assert_called_once()
