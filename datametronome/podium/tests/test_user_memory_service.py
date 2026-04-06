"""Tests for UserMemoryService.

All LLM calls (_call_extraction_llm, _call_rebuild_llm) are patched with
patch.object so tests remain fast and deterministic.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from datametronome_podium.features.user_memory.schemas import MemoryExtraction
from datametronome_podium.features.user_memory.service import (
    ProfileSummary,
    UserMemoryService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.list_active_memories = AsyncMock(return_value=[])
    repo.count_active_memories = AsyncMock(return_value=0)
    repo.create_memory = AsyncMock(return_value="mem-new000001")
    repo.supersede_memory = AsyncMock()
    repo.update_memory = AsyncMock(return_value=1)
    repo.get_profile = AsyncMock(return_value=None)
    repo.upsert_profile = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    return UserMemoryService(mock_repo)


def _make_extraction(**kwargs) -> MemoryExtraction:
    defaults = {
        "category": "expertise",
        "content": "Knows SQL well",
        "confidence": 0.9,
        "action": "new",
        "existing_memory_id": None,
    }
    return MemoryExtraction(**{**defaults, **kwargs})  # type: ignore[invalid-argument-type]


def _make_profile_summary(**kwargs) -> ProfileSummary:
    defaults = {
        "domain_summary": "e-commerce",
        "expertise_summary": "SQL, Python",
        "investigation_summary": "revenue trends",
    }
    return ProfileSummary(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# test_extract_memories_creates_new
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_memories_creates_new(service, mock_repo):
    """A 'new' extraction action should insert a memory and rebuild the profile."""
    extraction = _make_extraction(action="new", content="Expert in dbt")
    summary = _make_profile_summary(expertise_summary="Expert in dbt")

    with (
        patch.object(service, "_call_extraction_llm", return_value=[extraction]),
        patch.object(service, "_call_rebuild_llm", return_value=summary),
    ):
        await service.extract_and_rebuild("conv-1", "u1", "I use dbt every day")

    mock_repo.create_memory.assert_called_once()
    call_kwargs = mock_repo.create_memory.call_args.kwargs
    assert call_kwargs["content"] == "Expert in dbt"
    assert call_kwargs["category"] == "expertise"
    assert call_kwargs["user_id"] == "u1"
    assert call_kwargs["source_conversation_id"] == "conv-1"

    # Profile rebuild should have been triggered
    mock_repo.upsert_profile.assert_called_once()


# ---------------------------------------------------------------------------
# test_extract_memories_supersedes_existing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_memories_supersedes_existing(service, mock_repo):
    """An 'update' action should create a replacement memory and call supersede."""
    extraction = _make_extraction(
        action="update",
        content="Now an expert in dbt and Airflow",
        existing_memory_id="mem-oldone1234",
    )
    summary = _make_profile_summary()

    with (
        patch.object(service, "_call_extraction_llm", return_value=[extraction]),
        patch.object(service, "_call_rebuild_llm", return_value=summary),
    ):
        await service.extract_and_rebuild("conv-2", "u1", "I now use Airflow too")

    # New memory was created
    mock_repo.create_memory.assert_called_once()
    new_id = mock_repo.create_memory.call_args.kwargs["id"]

    # Old memory was superseded by the new one
    mock_repo.supersede_memory.assert_called_once_with("mem-oldone1234", new_id)


# ---------------------------------------------------------------------------
# test_extract_memories_invalidates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_memories_invalidates(service, mock_repo):
    """An 'invalidate' action should deactivate the existing memory without replacing it."""
    extraction = _make_extraction(
        action="invalidate",
        content="No longer uses MySQL",
        existing_memory_id="mem-mysql000",
    )
    summary = _make_profile_summary()

    with (
        patch.object(service, "_call_extraction_llm", return_value=[extraction]),
        patch.object(service, "_call_rebuild_llm", return_value=summary),
    ):
        await service.extract_and_rebuild("conv-3", "u1", "We migrated away from MySQL")

    # No new memory created — invalidate is a soft delete
    mock_repo.create_memory.assert_not_called()
    mock_repo.supersede_memory.assert_not_called()
    mock_repo.update_memory.assert_called_once_with("mem-mysql000", {"active": 0})


# ---------------------------------------------------------------------------
# test_format_recall_response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_format_recall_response(service, mock_repo):
    """format_recall returns a readable block when a profile exists."""
    mock_repo.get_profile.return_value = {
        "domain_summary": "e-commerce",
        "expertise_summary": "SQL expert",
        "investigation_summary": "cart abandonment anomalies",
    }

    result = await service.format_recall("u1")

    assert "e-commerce" in result
    assert "SQL expert" in result
    assert "cart abandonment" in result
    # Should start with a human-readable preamble
    assert result.startswith("Here's what I remember")


# ---------------------------------------------------------------------------
# test_format_recall_empty_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_format_recall_empty_profile(service, mock_repo):
    """format_recall returns a friendly message when no profile exists."""
    mock_repo.get_profile.return_value = None

    result = await service.format_recall("u_unknown")

    assert "don't have any saved context" in result.lower() or "don't" in result


# ---------------------------------------------------------------------------
# test_format_profile_for_prompt
# ---------------------------------------------------------------------------


def test_format_profile_for_prompt():
    """Returns a formatted system-prompt block when the profile has content."""
    profile = {
        "domain_summary": "logistics",
        "expertise_summary": "Python, SQL",
        "investigation_summary": "shipment delays",
    }

    result = UserMemoryService.format_profile_for_prompt(profile)

    assert result is not None
    assert "USER CONTEXT" in result
    assert "logistics" in result
    assert "Python, SQL" in result
    assert "shipment delays" in result
    assert "Don't re-explain" in result


# ---------------------------------------------------------------------------
# test_format_profile_for_prompt_none
# ---------------------------------------------------------------------------


def test_format_profile_for_prompt_none():
    """Returns None when profile is None or all summaries are empty."""
    assert UserMemoryService.format_profile_for_prompt(None) is None
    assert (
        UserMemoryService.format_profile_for_prompt(
            {"domain_summary": "", "expertise_summary": "", "investigation_summary": ""}
        )
        is None
    )


# ---------------------------------------------------------------------------
# test_format_profile_for_prompt_partial
# ---------------------------------------------------------------------------


def test_format_profile_for_prompt_partial():
    """Returns a block even when only one summary field is populated."""
    profile = {
        "domain_summary": "healthcare",
        "expertise_summary": "",
        "investigation_summary": "",
    }

    result = UserMemoryService.format_profile_for_prompt(profile)

    assert result is not None
    assert "healthcare" in result
