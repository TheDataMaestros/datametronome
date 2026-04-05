"""Tests for UserMemoryRepo using a mocked QueryExecutor."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, call

from datametronome_podium.features.user_memory.repo import UserMemoryRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.execute = AsyncMock(return_value=1)
    executor.select = AsyncMock(return_value=[])
    executor.update = AsyncMock(return_value=1)
    return executor


# ---------------------------------------------------------------------------
# create_memory / get_memory
# ---------------------------------------------------------------------------

class TestCreateAndGetMemory:
    @pytest.mark.asyncio
    async def test_create_memory_returns_id(self, mock_executor):
        repo = UserMemoryRepo(mock_executor)
        returned_id = await repo.create_memory(
            id="mem-abc123",
            user_id="u1",
            category="expertise",
            content="Knows SQL well",
            source_conversation_id="conv-1",
            confidence=0.9,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert returned_id == "mem-abc123"
        mock_executor.insert.assert_called_once()
        inserted_table, inserted_data = mock_executor.insert.call_args.args
        assert inserted_table == "user_memories"
        assert inserted_data["id"] == "mem-abc123"
        assert inserted_data["active"] == 1

    @pytest.mark.asyncio
    async def test_get_memory_found(self, mock_executor):
        mock_executor.select.return_value = [
            {
                "id": "mem-abc123",
                "user_id": "u1",
                "category": "expertise",
                "content": "Knows SQL well",
                "source_conversation_id": "conv-1",
                "confidence": 0.9,
                "active": 1,
                "superseded_by": None,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ]
        repo = UserMemoryRepo(mock_executor)
        result = await repo.get_memory("mem-abc123")
        assert result is not None
        assert result["id"] == "mem-abc123"
        assert result["content"] == "Knows SQL well"

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, mock_executor):
        mock_executor.select.return_value = []
        repo = UserMemoryRepo(mock_executor)
        result = await repo.get_memory("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# list_active_memories
# ---------------------------------------------------------------------------

class TestListActiveMemories:
    @pytest.mark.asyncio
    async def test_list_active_returns_only_active(self, mock_executor):
        # Simulate DB returning only active rows (filtering is done by SQL)
        mock_executor.query.return_value = [
            {"id": "mem-1", "user_id": "u1", "active": 1, "content": "A"},
            {"id": "mem-2", "user_id": "u1", "active": 1, "content": "B"},
        ]
        repo = UserMemoryRepo(mock_executor)
        results = await repo.list_active_memories("u1")
        assert len(results) == 2
        # Confirm the SQL issued includes active = 1 filter
        sql_issued = mock_executor.query.call_args.args[0]
        assert "active = 1" in sql_issued

    @pytest.mark.asyncio
    async def test_list_active_with_category_filter(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "mem-1", "user_id": "u1", "active": 1, "category": "expertise"},
        ]
        repo = UserMemoryRepo(mock_executor)
        results = await repo.list_active_memories("u1", category="expertise")
        assert len(results) == 1
        sql_issued = mock_executor.query.call_args.args[0]
        assert "category = ?" in sql_issued

    @pytest.mark.asyncio
    async def test_list_active_empty(self, mock_executor):
        mock_executor.query.return_value = []
        repo = UserMemoryRepo(mock_executor)
        results = await repo.list_active_memories("u1")
        assert results == []


# ---------------------------------------------------------------------------
# deactivate / supersede memory
# ---------------------------------------------------------------------------

class TestDeactivateMemory:
    @pytest.mark.asyncio
    async def test_supersede_memory_deactivates_old(self, mock_executor):
        repo = UserMemoryRepo(mock_executor)
        await repo.supersede_memory("mem-old", "mem-new")
        mock_executor.update.assert_called_once()
        _table, update_data, kwargs = (
            mock_executor.update.call_args.args[0],
            mock_executor.update.call_args.args[1],
            mock_executor.update.call_args.kwargs,
        )
        assert _table == "user_memories"
        assert update_data["active"] == 0
        assert update_data["superseded_by"] == "mem-new"
        assert kwargs["where"] == {"id": "mem-old"}


# ---------------------------------------------------------------------------
# delete_memory
# ---------------------------------------------------------------------------

class TestDeleteMemory:
    @pytest.mark.asyncio
    async def test_delete_memory(self, mock_executor):
        mock_executor.execute.return_value = 1
        repo = UserMemoryRepo(mock_executor)
        rows = await repo.delete_memory("mem-abc")
        assert rows == 1
        sql = mock_executor.execute.call_args.args[0]
        assert "DELETE FROM user_memories" in sql


# ---------------------------------------------------------------------------
# search_memories
# ---------------------------------------------------------------------------

class TestSearchMemories:
    @pytest.mark.asyncio
    async def test_search_with_text_query(self, mock_executor):
        mock_executor.query.return_value = [
            {"id": "mem-1", "content": "knows SQL well", "active": 1},
        ]
        repo = UserMemoryRepo(mock_executor)
        results = await repo.search_memories("u1", q="SQL")
        assert len(results) == 1
        sql, params = mock_executor.query.call_args.args
        assert "LIKE ?" in sql
        assert any("SQL" in str(p) for p in params)

    @pytest.mark.asyncio
    async def test_search_active_only_default(self, mock_executor):
        mock_executor.query.return_value = []
        repo = UserMemoryRepo(mock_executor)
        await repo.search_memories("u1")
        sql, _ = mock_executor.query.call_args.args
        assert "active = 1" in sql

    @pytest.mark.asyncio
    async def test_search_include_inactive(self, mock_executor):
        mock_executor.query.return_value = []
        repo = UserMemoryRepo(mock_executor)
        await repo.search_memories("u1", active_only=False)
        sql, _ = mock_executor.query.call_args.args
        assert "active = 1" not in sql


# ---------------------------------------------------------------------------
# upsert_profile / get_profile
# ---------------------------------------------------------------------------

class TestCreateAndGetProfile:
    @pytest.mark.asyncio
    async def test_upsert_profile_inserts_when_missing(self, mock_executor):
        # get_profile (select) returns empty → triggers insert path
        mock_executor.select.return_value = []
        repo = UserMemoryRepo(mock_executor)
        await repo.upsert_profile(
            user_id="u1",
            domain_summary="e-commerce",
            expertise_summary="SQL advanced",
            investigation_summary="revenue trends",
            memory_count=5,
        )
        mock_executor.insert.assert_called_once()
        _table, data = mock_executor.insert.call_args.args
        assert _table == "user_memory_profiles"
        assert data["user_id"] == "u1"
        assert data["memory_count"] == 5
        assert data["id"].startswith("prof-")

    @pytest.mark.asyncio
    async def test_upsert_profile_updates_when_exists(self, mock_executor):
        existing = {
            "id": "prof-existingone",
            "user_id": "u1",
            "domain_summary": "old",
            "expertise_summary": "old",
            "investigation_summary": "old",
            "memory_count": 2,
            "last_rebuilt_at": "2026-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_executor.select.return_value = [existing]
        repo = UserMemoryRepo(mock_executor)
        await repo.upsert_profile(
            user_id="u1",
            domain_summary="new domain",
            expertise_summary="new expertise",
            investigation_summary="new investigation",
            memory_count=10,
        )
        mock_executor.update.assert_called_once()
        _table, update_data, kwargs = (
            mock_executor.update.call_args.args[0],
            mock_executor.update.call_args.args[1],
            mock_executor.update.call_args.kwargs,
        )
        assert _table == "user_memory_profiles"
        assert update_data["memory_count"] == 10
        assert kwargs["where"] == {"user_id": "u1"}

    @pytest.mark.asyncio
    async def test_get_profile_returns_none_when_missing(self, mock_executor):
        mock_executor.select.return_value = []
        repo = UserMemoryRepo(mock_executor)
        result = await repo.get_profile("u_nobody")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_profile_returns_dict(self, mock_executor):
        profile_row = {
            "id": "prof-abc",
            "user_id": "u1",
            "domain_summary": "e-commerce",
            "expertise_summary": "SQL",
            "investigation_summary": "trends",
            "memory_count": 3,
            "last_rebuilt_at": "2026-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_executor.select.return_value = [profile_row]
        repo = UserMemoryRepo(mock_executor)
        result = await repo.get_profile("u1")
        assert result is not None
        assert result["domain_summary"] == "e-commerce"


# ---------------------------------------------------------------------------
# upsert_extraction_status
# ---------------------------------------------------------------------------

class TestUpsertExtractionStatus:
    @pytest.mark.asyncio
    async def test_upsert_is_idempotent_via_on_conflict(self, mock_executor):
        """ON CONFLICT DO NOTHING means calling twice is safe."""
        repo = UserMemoryRepo(mock_executor)
        await repo.upsert_extraction_status("conv-1", "u1")
        await repo.upsert_extraction_status("conv-1", "u1")
        # execute called twice — second call also succeeds (mock doesn't raise)
        assert mock_executor.execute.call_count == 2
        sql = mock_executor.execute.call_args_list[0].args[0]
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql

    @pytest.mark.asyncio
    async def test_upsert_inserts_with_idle_status(self, mock_executor):
        repo = UserMemoryRepo(mock_executor)
        await repo.upsert_extraction_status("conv-2", "u2")
        sql, params = mock_executor.execute.call_args.args
        assert "idle" in sql
        assert "conv-2" in params
        assert "u2" in params


# ---------------------------------------------------------------------------
# find_conversations_needing_extraction
# ---------------------------------------------------------------------------

class TestFindConversationsNeedingExtraction:
    @pytest.mark.asyncio
    async def test_returns_idle_conversations(self, mock_executor):
        mock_executor.query.return_value = [
            {"conversation_id": "conv-1", "user_id": "u1", "last_extracted_at": None},
        ]
        repo = UserMemoryRepo(mock_executor)
        results = await repo.find_conversations_needing_extraction(limit=10)
        assert len(results) == 1
        assert results[0]["conversation_id"] == "conv-1"
        sql, params = mock_executor.query.call_args.args
        assert "status = 'idle'" in sql
        assert 10 in params


# ---------------------------------------------------------------------------
# mark_extraction_processing
# ---------------------------------------------------------------------------

class TestMarkExtractionProcessing:
    @pytest.mark.asyncio
    async def test_mark_processing_returns_rows_updated(self, mock_executor):
        mock_executor.execute.return_value = 1
        repo = UserMemoryRepo(mock_executor)
        result = await repo.mark_extraction_processing("conv-1")
        assert result == 1
        sql, params = mock_executor.execute.call_args.args
        assert "processing" in sql
        # Guard ensures atomicity: only update if still idle
        assert "status = 'idle'" in sql

    @pytest.mark.asyncio
    async def test_mark_processing_returns_zero_if_already_taken(self, mock_executor):
        mock_executor.execute.return_value = 0
        repo = UserMemoryRepo(mock_executor)
        result = await repo.mark_extraction_processing("conv-1")
        assert result == 0
