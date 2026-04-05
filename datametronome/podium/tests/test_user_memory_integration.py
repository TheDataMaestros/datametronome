"""End-to-end integration test for the user memory pipeline.

These tests mock the LLM calls and the database repo, so they run fully
in-process without any network or DB dependencies.
"""
import pytest
from unittest.mock import AsyncMock, patch

from datametronome_podium.features.user_memory.schemas import MemoryExtraction
from datametronome_podium.features.user_memory.service import ProfileSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memories_after_extraction() -> list[dict]:
    """Return the three memories the service would create during the e2e test."""
    return [
        {"id": "mem-e2e-1", "category": "domain_focus", "content": "Works with orders and customers tables in e-commerce database"},
        {"id": "mem-e2e-2", "category": "expertise", "content": "Strong SQL skills — writes JOINs confidently"},
        {"id": "mem-e2e-3", "category": "investigation", "content": "NULL rate in customers.email (15%) attributed to recent migration"},
    ]


# ---------------------------------------------------------------------------
# Test 1: full extraction → profile rebuild → recall
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_memory_pipeline():
    """Simulates: conversation → extraction → profile → agent injection → recall."""
    from datametronome_podium.features.user_memory.service import UserMemoryService
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo

    repo = AsyncMock(spec=UserMemoryRepo)

    call_count = [0]
    created_memories: list[dict] = []

    async def mock_create_memory(
        *, id, user_id, category, content, source_conversation_id, confidence, created_at, updated_at
    ):
        call_count[0] += 1
        created_memories.append({"id": id, "category": category, "content": content})
        return id

    # First call (before extraction) returns empty; second call (inside
    # rebuild_profile) returns the memories just created so the LLM path fires.
    repo.list_active_memories.side_effect = [[], _make_memories_after_extraction()]
    repo.create_memory = mock_create_memory
    repo.supersede_memory = AsyncMock()
    repo.update_memory = AsyncMock()
    repo.get_profile.return_value = None
    repo.upsert_profile = AsyncMock()

    service = UserMemoryService(repo=repo)

    # extract_and_rebuild expects a plain string, not a list of dicts
    conversation = (
        "user: Show me the orders table in my e-commerce database\n"
        "assistant: Here's the orders table with 50K rows...\n"
        "user: I know SQL well, can you show me the JOIN between orders and customers?\n"
        "assistant: Here's the JOIN query...\n"
        "user: The NULL rate in customers.email looks high, I think it's from our migration last week\n"
        "assistant: Good catch, the NULL rate is 15%..."
    )

    mock_extractions = [
        MemoryExtraction(
            category="domain_focus",
            content="Works with orders and customers tables in e-commerce database",
            confidence=0.9,
            action="new",
            existing_memory_id=None,
        ),
        MemoryExtraction(
            category="expertise",
            content="Strong SQL skills — writes JOINs confidently",
            confidence=0.85,
            action="new",
            existing_memory_id=None,
        ),
        MemoryExtraction(
            category="investigation",
            content="NULL rate in customers.email (15%) attributed to recent migration",
            confidence=0.8,
            action="new",
            existing_memory_id=None,
        ),
    ]

    mock_profile_summary = ProfileSummary(
        domain_summary="Focuses on orders and customers tables in an e-commerce database.",
        expertise_summary="Strong SQL skills — writes JOINs confidently.",
        investigation_summary="Investigated NULL rate in customers.email (15%), concluded it's from a recent migration.",
    )

    with patch.object(service, "_call_extraction_llm", return_value=mock_extractions):
        with patch.object(service, "_call_rebuild_llm", return_value=mock_profile_summary):
            await service.extract_and_rebuild("conv-e2e", "user-e2e", conversation)

    # Three memories should have been created
    assert len(created_memories) == 3
    categories = {m["category"] for m in created_memories}
    assert categories == {"domain_focus", "expertise", "investigation"}

    # Profile should have been rebuilt exactly once
    repo.upsert_profile.assert_called_once()
    profile_call = repo.upsert_profile.call_args
    assert "orders" in profile_call.kwargs.get("domain_summary", "").lower()
    assert "sql" in profile_call.kwargs.get("expertise_summary", "").lower()

    # format_profile_for_prompt is a static method that builds the injection block
    mock_profile = {
        "domain_summary": "Focuses on orders and customers tables.",
        "expertise_summary": "Strong SQL skills.",
        "investigation_summary": "NULL rate in customers.email from migration.",
    }
    prompt_text = UserMemoryService.format_profile_for_prompt(mock_profile)
    assert prompt_text is not None
    assert "USER CONTEXT" in prompt_text
    # The static method renders "Domain focus:" (lowercase f)
    assert "Domain focus" in prompt_text

    # format_recall reads the profile and returns a structured string
    repo.get_profile.return_value = {
        "domain_summary": "Focuses on orders and customers tables.",
        "expertise_summary": "Strong SQL skills.",
        "investigation_summary": "NULL rate in customers.email from migration.",
        "memory_count": 3,
    }
    recall = await service.format_recall("user-e2e")
    # format_recall prefixes fields as "Domain:", "Expertise:", "Investigations:"
    assert "Domain:" in recall or "domain" in recall.lower()


# ---------------------------------------------------------------------------
# Test 2: "update" action triggers supersession
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_pipeline_with_supersession():
    """Test that update actions properly supersede existing memories."""
    from datametronome_podium.features.user_memory.service import UserMemoryService
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo

    repo = AsyncMock(spec=UserMemoryRepo)

    existing_memory = {
        "id": "mem-old",
        "category": "domain_focus",
        "content": "Works with orders only",
        "confidence": 0.9,
    }

    # First call: existing memory for extraction context.
    # Second call: updated memory list for rebuild_profile.
    updated_memory = {
        "id": "mem-new",
        "category": "domain_focus",
        "content": "Works with orders AND payments tables",
        "confidence": 0.95,
    }
    # Track the ID the service generates internally for the replacement memory.
    # We can't predict it (it's a uuid), so we capture it from the create call.
    created_ids: list[str] = []

    async def mock_create_memory(*, id, **_kwargs):
        created_ids.append(id)
        return id

    repo.list_active_memories.side_effect = [[existing_memory], [updated_memory]]
    repo.create_memory = mock_create_memory
    repo.supersede_memory = AsyncMock()
    repo.update_memory = AsyncMock()
    repo.get_profile.return_value = None
    repo.upsert_profile = AsyncMock()

    service = UserMemoryService(repo=repo)

    extractions = [
        MemoryExtraction(
            category="domain_focus",
            content="Works with orders AND payments tables",
            confidence=0.95,
            action="update",
            existing_memory_id="mem-old",
        ),
    ]

    mock_profile_summary = ProfileSummary(
        domain_summary="Orders and payments",
        expertise_summary="",
        investigation_summary="",
    )

    # Minimal conversation string (extract_and_rebuild expects str, not list)
    conversation = (
        "user: x\nassistant: y\n"
        "user: x\nassistant: y\n"
        "user: x\nassistant: y\n"
    )

    with patch.object(service, "_call_extraction_llm", return_value=extractions):
        with patch.object(service, "_call_rebuild_llm", return_value=mock_profile_summary):
            await service.extract_and_rebuild("conv-2", "user-1", conversation)

    # One new memory created — capture its service-generated ID
    assert len(created_ids) == 1
    new_id = created_ids[0]
    assert new_id.startswith("mem-")

    # Old memory must be superseded by the new one
    repo.supersede_memory.assert_called_once_with("mem-old", new_id)


# ---------------------------------------------------------------------------
# Test 3: format_profile_for_prompt edge cases
# ---------------------------------------------------------------------------


def test_format_profile_for_prompt_returns_none_for_empty_profile():
    """No injection when profile is None or all fields are blank."""
    from datametronome_podium.features.user_memory.service import UserMemoryService

    assert UserMemoryService.format_profile_for_prompt(None) is None
    assert UserMemoryService.format_profile_for_prompt({}) is None
    assert UserMemoryService.format_profile_for_prompt(
        {"domain_summary": "", "expertise_summary": "", "investigation_summary": ""}
    ) is None


def test_format_profile_for_prompt_includes_all_sections():
    """Injection block contains all three headings when all fields are populated."""
    from datametronome_podium.features.user_memory.service import UserMemoryService

    profile = {
        "domain_summary": "E-commerce",
        "expertise_summary": "SQL expert",
        "investigation_summary": "NULL rate in emails",
    }
    result = UserMemoryService.format_profile_for_prompt(profile)
    assert result is not None
    assert "Domain focus" in result
    assert "Expertise" in result
    assert "Investigation history" in result
    assert "USER CONTEXT" in result


# ---------------------------------------------------------------------------
# Test 4: format_recall with no profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_format_recall_with_no_profile():
    """format_recall returns an informative message when the user has no profile."""
    from datametronome_podium.features.user_memory.service import UserMemoryService
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo

    repo = AsyncMock(spec=UserMemoryRepo)
    repo.get_profile.return_value = None

    service = UserMemoryService(repo=repo)
    result = await service.format_recall("user-unknown")

    assert "don't have any saved context" in result.lower() or "no" in result.lower()
