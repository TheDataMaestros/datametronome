"""UserMemoryService — extraction, profile rebuild, and recall formatting."""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic_ai import Agent

from datametronome_podium.core.timestamp_utils import now_utc_iso
from datametronome_podium.features.user_memory.schemas import MemoryExtraction

if TYPE_CHECKING:
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo

logger = logging.getLogger(__name__)

_MEMORY_SCALE_THRESHOLD = 100  # prompt only the 50 most recent when above this
_MEMORY_PROMPT_CAP = 50


# ---------------------------------------------------------------------------
# Internal LLM output types — not exposed as API DTOs
# ---------------------------------------------------------------------------


class ExtractionResult(BaseModel):
    """Pydantic AI structured output for memory extraction."""

    extractions: list[MemoryExtraction]


class ProfileSummary(BaseModel):
    """Pydantic AI structured output for profile rebuild."""

    domain_summary: str
    expertise_summary: str
    investigation_summary: str


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM = """\
You are a memory extractor for a data-quality platform. Read the conversation
and identify durable facts about the user: domain focus (what industry/domain
they work in), expertise (technical skills and knowledge level), and ongoing
investigations (data quality problems they are actively exploring).

For each fact, decide whether it is:
- "new": something not yet known
- "update": a refinement of an existing memory (provide existing_memory_id)
- "invalidate": an old fact that is now incorrect (provide existing_memory_id)

Return ONLY facts that are clearly stated or strongly implied. Confidence should
reflect how certain you are (0.0–1.0). Do not invent details."""

_REBUILD_SYSTEM = """\
You are summarising a user's memory profile for a data-quality assistant.
Given the list of active memories, write concise paragraph-length summaries for:
- domain_summary: industries, data domains, and business areas
- expertise_summary: technical skills, tools, and knowledge level
- investigation_summary: ongoing or recently completed data quality investigations

Be factual and concise. If a category has no memories, return an empty string."""


def _now_utc() -> str:
    return now_utc_iso()


def _gen_memory_id() -> str:
    return f"mem-{uuid.uuid4().hex[:12]}"


def _format_memories_for_prompt(memories: list[dict], overflow: int) -> str:
    """Render memory list as a numbered text block for LLM prompts."""
    lines = [f"{i + 1}. [{m['category']}] {m['content']} (id={m['id']})" for i, m in enumerate(memories)]
    if overflow:
        lines.append(f"... and {overflow} older memories not shown.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class UserMemoryService:
    """Orchestrates LLM-powered extraction and profile rebuild for user memories."""

    def __init__(self, repo: UserMemoryRepo) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Public pipeline entry-points
    # ------------------------------------------------------------------

    async def extract_and_rebuild(
        self,
        conversation_id: str,
        user_id: str,
        conversation: str,
    ) -> None:
        """Full pipeline: extract memories from a conversation, persist them, rebuild profile.

        Never raises — errors are logged so callers don't lose the conversation.
        """
        existing = await self._repo.list_active_memories(user_id)
        extractions = await self._call_extraction_llm(conversation, existing)
        await self._persist_extractions(conversation_id, user_id, extractions)
        await self.rebuild_profile(user_id)

    async def rebuild_profile(self, user_id: str) -> None:
        """Summarise all active memories into the three profile fields via LLM."""
        memories = await self._repo.list_active_memories(user_id)
        count = len(memories)

        if not memories:
            await self._repo.upsert_profile(
                user_id=user_id,
                domain_summary="",
                expertise_summary="",
                investigation_summary="",
                memory_count=0,
            )
            return

        summary = await self._call_rebuild_llm(memories)
        await self._repo.upsert_profile(
            user_id=user_id,
            domain_summary=summary.domain_summary,
            expertise_summary=summary.expertise_summary,
            investigation_summary=summary.investigation_summary,
            memory_count=count,
        )

    # ------------------------------------------------------------------
    # Formatting helpers (pure — no I/O)
    # ------------------------------------------------------------------

    async def format_recall(self, user_id: str) -> str:
        """Return a human-readable recall response from the user's current profile."""
        profile = await self._repo.get_profile(user_id)
        if not profile:
            return (
                "I don't have any saved context about you yet. "
                "As we chat, I'll learn about your domain and investigations."
            )
        parts = []
        if profile.get("domain_summary"):
            parts.append(f"Domain: {profile['domain_summary']}")
        if profile.get("expertise_summary"):
            parts.append(f"Expertise: {profile['expertise_summary']}")
        if profile.get("investigation_summary"):
            parts.append(f"Investigations: {profile['investigation_summary']}")

        if not parts:
            return (
                "I have a profile for you, but it doesn't contain any summaries yet. "
                "Keep chatting and I'll learn more about you."
            )

        return "Here's what I remember about you:\n" + "\n".join(f"- {p}" for p in parts)

    @staticmethod
    def format_profile_for_prompt(profile: dict | None) -> str | None:
        """Format a profile dict into a system-prompt injection block.

        Returns None when there is nothing useful to inject (no profile or all
        summaries are empty strings), so callers can skip the injection entirely.
        """
        if not profile:
            return None

        domain = profile.get("domain_summary", "")
        expertise = profile.get("expertise_summary", "")
        investigation = profile.get("investigation_summary", "")

        # Skip injection when every field is blank — no useful context to add
        if not any([domain, expertise, investigation]):
            return None

        return (
            "USER CONTEXT (learned from prior conversations):\n"
            f"- Domain focus: {domain}\n"
            f"- Expertise: {expertise}\n"
            f"- Investigation history: {investigation}\n"
            "\n"
            "Use this context to tailor your responses. "
            "Don't re-explain concepts the user already knows. "
            "Reference prior investigations when relevant."
        )

    # ------------------------------------------------------------------
    # Private LLM call wrappers — isolated for easy mocking in tests
    # ------------------------------------------------------------------

    async def _call_extraction_llm(
        self, conversation: str, existing_memories: list[dict]
    ) -> list[MemoryExtraction]:
        """Call the extraction agent. Returns [] on any LLM failure."""
        count = len(existing_memories)
        overflow = 0

        # Limit context sent to the LLM when the user has many memories
        if count > _MEMORY_SCALE_THRESHOLD:
            overflow = count - _MEMORY_PROMPT_CAP
            existing_memories = existing_memories[:_MEMORY_PROMPT_CAP]

        memories_text = _format_memories_for_prompt(existing_memories, overflow)
        prompt = (
            f"EXISTING MEMORIES:\n{memories_text}\n\n"
            f"CONVERSATION:\n{conversation}"
        )

        try:
            from datametronome_podium.services.agent_factory import build_model_from_settings

            agent: Agent[None, ExtractionResult] = Agent(  # ty: ignore[assignment]  # ty:ignore[ignore-comment-unknown-rule]
                model=build_model_from_settings(),
                system_prompt=_EXTRACTION_SYSTEM,
                output_type=ExtractionResult,
            )  # ty:ignore[invalid-assignment]
            result = await agent.run(prompt)
            return result.output.extractions
        except Exception:
            logger.warning("Memory extraction LLM call failed", exc_info=True)
            return []

    async def _call_rebuild_llm(self, memories: list[dict]) -> ProfileSummary:
        """Call the profile-rebuild agent. Falls back to raw concatenation on failure."""
        memories_text = "\n".join(
            f"[{m['category']}] {m['content']}" for m in memories
        )
        prompt = f"MEMORIES:\n{memories_text}"

        try:
            from datametronome_podium.services.agent_factory import build_model_from_settings

            agent: Agent[None, ProfileSummary] = Agent(  # ty: ignore[assignment]  # ty:ignore[ignore-comment-unknown-rule]
                model=build_model_from_settings(),
                system_prompt=_REBUILD_SYSTEM,
                output_type=ProfileSummary,
            )  # ty:ignore[invalid-assignment]
            result = await agent.run(prompt)
            return result.output
        except Exception:
            logger.warning("Profile rebuild LLM call failed — using raw facts", exc_info=True)
            # Degrade gracefully: concatenate raw facts per category
            return self._concat_fallback(memories)

    @staticmethod
    def _concat_fallback(memories: list[dict]) -> ProfileSummary:
        """Build a raw profile summary by concatenating facts when LLM is unavailable."""
        buckets: dict[str, list[str]] = {
            "domain_focus": [],
            "expertise": [],
            "investigation": [],
        }
        for m in memories:
            cat = m.get("category", "")
            if cat in buckets:
                buckets[cat].append(m["content"])

        return ProfileSummary(
            domain_summary="; ".join(buckets["domain_focus"]),
            expertise_summary="; ".join(buckets["expertise"]),
            investigation_summary="; ".join(buckets["investigation"]),
        )

    # ------------------------------------------------------------------
    # Persistence logic
    # ------------------------------------------------------------------

    async def _persist_extractions(
        self,
        conversation_id: str,
        user_id: str,
        extractions: list[MemoryExtraction],
    ) -> None:
        """Persist extracted memories: create new, supersede updated, deactivate invalidated."""
        now = _now_utc()

        for extraction in extractions:
            if extraction.action == "new":
                new_id = _gen_memory_id()
                await self._repo.create_memory(
                    id=new_id,
                    user_id=user_id,
                    category=extraction.category,
                    content=extraction.content,
                    source_conversation_id=conversation_id,
                    confidence=extraction.confidence,
                    created_at=now,
                    updated_at=now,
                )

            elif extraction.action == "update" and extraction.existing_memory_id:
                # Create the replacement first, then mark old as superseded
                new_id = _gen_memory_id()
                await self._repo.create_memory(
                    id=new_id,
                    user_id=user_id,
                    category=extraction.category,
                    content=extraction.content,
                    source_conversation_id=conversation_id,
                    confidence=extraction.confidence,
                    created_at=now,
                    updated_at=now,
                )
                await self._repo.supersede_memory(extraction.existing_memory_id, new_id)

            elif extraction.action == "invalidate" and extraction.existing_memory_id:
                # Deactivate without replacement — the fact is no longer true
                await self._repo.update_memory(
                    extraction.existing_memory_id, {"active": 0}
                )
