"""Tests for user memory Pydantic schemas."""
import pytest
from datametronome_podium.features.user_memory.schemas import (
    UserMemoryResponse,
    UserMemoryProfileResponse,
    UserMemoryCreate,
    UserMemoryUpdate,
    MemoryExtraction,
)


def test_memory_response_from_db_row():
    row = {
        "id": "mem-abc",
        "user_id": "user-1",
        "category": "domain_focus",
        "content": "Works with orders table",
        "source_conversation_id": "conv-1",
        "confidence": 0.9,
        "active": True,
        "superseded_by": None,
        "created_at": "2026-04-06T00:00:00Z",
        "updated_at": "2026-04-06T00:00:00Z",
    }
    mem = UserMemoryResponse(**row)  # ty:ignore[invalid-argument-type]
    assert mem.category == "domain_focus"
    assert mem.active is True


def test_memory_create_defaults():
    mc = UserMemoryCreate(category="expertise", content="Knows SQL well")
    assert mc.confidence == 1.0


def test_memory_extraction_model():
    ext = MemoryExtraction(
        category="investigation",
        content="NULL spike in customers",
        confidence=0.85,
        action="new",
        existing_memory_id=None,
    )
    assert ext.action == "new"


def test_memory_extraction_update_requires_id():
    ext = MemoryExtraction(
        category="domain_focus",
        content="Updated focus",
        confidence=0.9,
        action="update",
        existing_memory_id="mem-old",
    )
    assert ext.existing_memory_id == "mem-old"


def test_profile_response():
    profile = UserMemoryProfileResponse(
        id="prof-1",
        user_id="user-1",
        domain_summary="E-commerce",
        expertise_summary="SQL expert",
        investigation_summary="NULL spike",
        memory_count=5,
        last_rebuilt_at="2026-04-06T00:00:00Z",
        created_at="2026-04-06T00:00:00Z",
    )
    assert profile.memory_count == 5
