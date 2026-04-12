"""Tests for AppSettingsRepo — encrypted key-value store."""

import pytest
from unittest.mock import AsyncMock

from datametronome_podium.features.settings.repo import AppSettingsRepo, SENSITIVE_KEYS


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.execute = AsyncMock()
    return executor


class TestAppSettingsRepo:
    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, mock_executor):
        repo = AppSettingsRepo(mock_executor)
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_existing_key(self, mock_executor):
        mock_executor.query.return_value = [
            {"key": "ai_provider", "value": "anthropic", "is_encrypted": False,
             "updated_at": "2026-04-09T00:00:00Z"}
        ]
        repo = AppSettingsRepo(mock_executor)
        result = await repo.get("ai_provider")
        assert result is not None
        assert result.key == "ai_provider"
        assert result.value == "anthropic"

    @pytest.mark.asyncio
    async def test_get_all_empty(self, mock_executor):
        repo = AppSettingsRepo(mock_executor)
        result = await repo.get_all()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_returns_rows(self, mock_executor):
        mock_executor.query.return_value = [
            {"key": "ai_provider", "value": "anthropic", "is_encrypted": False,
             "updated_at": "2026-04-09T00:00:00Z"},
            {"key": "ai_model", "value": "claude-sonnet-4-6", "is_encrypted": False,
             "updated_at": "2026-04-09T00:00:00Z"},
        ]
        repo = AppSettingsRepo(mock_executor)
        result = await repo.get_all()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_set_inserts_when_new(self, mock_executor):
        # get returns None -> insert path
        mock_executor.query.return_value = []
        repo = AppSettingsRepo(mock_executor)
        row = await repo.set("ai_provider", "openai")
        assert row.key == "ai_provider"
        assert row.value == "openai"
        assert not row.is_encrypted
        # execute called for INSERT
        mock_executor.execute.assert_called_once()
        call_sql = mock_executor.execute.call_args[0][0]
        assert "INSERT" in call_sql

    @pytest.mark.asyncio
    async def test_set_updates_when_existing(self, mock_executor):
        # First call (get) returns existing row, second call (get_all) doesn't matter
        mock_executor.query.return_value = [
            {"key": "ai_provider", "value": "ollama", "is_encrypted": False,
             "updated_at": "2026-04-09T00:00:00Z"},
        ]
        repo = AppSettingsRepo(mock_executor)
        await repo.set("ai_provider", "anthropic")
        call_sql = mock_executor.execute.call_args[0][0]
        assert "UPDATE" in call_sql

    @pytest.mark.asyncio
    async def test_set_sensitive_key_encrypts(self, mock_executor):
        mock_executor.query.return_value = []
        repo = AppSettingsRepo(mock_executor)
        row = await repo.set("ai_api_key", "sk-secret-123")
        assert row.is_encrypted is True
        assert row.value.startswith("enc::")

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_missing(self, mock_executor):
        repo = AppSettingsRepo(mock_executor)
        result = await repo.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_found(self, mock_executor):
        mock_executor.query.return_value = [
            {"key": "ai_provider", "value": "anthropic", "is_encrypted": False,
             "updated_at": "2026-04-09T00:00:00Z"},
        ]
        repo = AppSettingsRepo(mock_executor)
        result = await repo.delete("ai_provider")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_decrypted_sensitive_key(self, mock_executor):
        from datametronome_podium.core.encryption import encrypt_value
        encrypted = encrypt_value("sk-secret-123")
        mock_executor.query.return_value = [
            {"key": "ai_api_key", "value": encrypted, "is_encrypted": True,
             "updated_at": "2026-04-09T00:00:00Z"},
        ]
        repo = AppSettingsRepo(mock_executor)
        result = await repo.get_decrypted("ai_api_key")
        assert result == "sk-secret-123"

    @pytest.mark.asyncio
    async def test_get_decrypted_plain_key(self, mock_executor):
        mock_executor.query.return_value = [
            {"key": "ai_model", "value": "claude-sonnet-4-6", "is_encrypted": False,
             "updated_at": "2026-04-09T00:00:00Z"},
        ]
        repo = AppSettingsRepo(mock_executor)
        result = await repo.get_decrypted("ai_model")
        assert result == "claude-sonnet-4-6"

    def test_sensitive_keys_includes_api_key(self):
        assert "ai_api_key" in SENSITIVE_KEYS
