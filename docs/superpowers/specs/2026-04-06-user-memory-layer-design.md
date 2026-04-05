# User Memory Layer — Design Spec

**Date:** 2026-04-06
**Status:** Approved
**Branch:** TBD (extends feat/data-intelligence)

## Overview

A per-user memory system that makes DataMetronome's chat agents smarter over time. Agents learn what each user works on, what they already know, and what they've investigated — so conversations get more relevant and less repetitive across sessions.

## Goals

1. **Domain focus** — agents know which tables, schemas, and domains the user works with
2. **Expertise calibration** — agents adjust explanation depth (e.g., skip SQL basics for experts, explain freshness checks for newcomers)
3. **Investigation history** — agents remember past conclusions (e.g., "NULL spike in customers.email was a migration issue, don't re-flag")
4. **User control** — users can view, edit, and deactivate memories

## Non-Goals

- Communication style adaptation (tone, verbosity, formatting)
- Cross-user memory or shared team knowledge
- Real-time memory (within a single conversation — existing `message_history` handles this)
- External knowledge ingestion (docs, Slack, wikis)

## Decision: Why Not SuperMemory

SuperMemory (https://github.com/supermemoryai/supermemory) was evaluated and rejected for the core pipeline:

- **SuperMemory is a general-purpose conversation memory layer** — extracts facts about users, builds profiles, does hybrid search (RAG + memory). Strong for thousands of users with unstructured, long-running conversations.
- **DataMetronome's needs are structured and domain-specific** — three specific memory categories (domain focus, expertise, investigation history), not general "facts about users."
- **We already have the building blocks** — Postgres, LLM providers, Celery, and a dynamic system prompt injection pattern in the Insight agent.
- **External dependency cost** — SuperMemory self-hosted still adds a complex Docker service (vector DB, processing pipeline) for one feature.
- **Better fit for in-house** — a targeted LLM extraction prompt understands data quality context better than generic extraction.

SuperMemory could be reconsidered if: (a) user base grows to hundreds+, (b) we add multi-session semantic search ("what did we discuss about orders last month?"), or (c) we add external knowledge ingestion.

## Data Model

### `user_memories`

Individual facts extracted from conversations. One row = one discrete piece of knowledge.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| user_id | VARCHAR | FK → users(id) ON DELETE CASCADE |
| category | ENUM | `domain_focus`, `expertise`, `investigation` |
| content | TEXT | The fact: "User frequently investigates the orders and payments tables" |
| source_conversation_id | VARCHAR | Which conversation this was extracted from |
| confidence | FLOAT | 0-1, how certain the extraction is |
| active | BOOLEAN | Default true. User can deactivate without deleting |
| superseded_by | FK → user_memories (nullable) | When contradicted, points to the replacement |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `user_memory_profiles`

Precomputed summary per user. This is what gets injected into agent system prompts — avoids querying N individual memories on every chat request.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| user_id | VARCHAR | FK → users(id) ON DELETE CASCADE, unique constraint |
| domain_summary | TEXT | "Focuses on orders, payments, customers tables. Primarily e-commerce domain." |
| expertise_summary | TEXT | "Strong SQL skills. Familiar with data modeling. New to data quality monitoring concepts." |
| investigation_summary | TEXT | "Investigated NULL spike in customers.email (2026-03-20, concluded: migration issue). Tracked order volume drop (2026-04-01, ongoing)." |
| memory_count | INTEGER | Total active memories |
| last_rebuilt_at | TIMESTAMP | |
| created_at | TIMESTAMP | |

### Design Choices

- **Granular memories** — one fact per row, individually supersedable, deactivatable, searchable
- **Denormalized profile** — cheap to inject into prompts, rebuilt after each extraction
- **`superseded_by` chain** — handles contradictions without deleting history (old fact stays for audit). Only active memories can be superseded — the service layer enforces this to prevent cycles.
- **No `tenant_id` yet** — `user_id` is the isolation boundary; tenant_id added when multi-tenancy lands

### Indexes

- `user_memories(user_id, active)` — primary query pattern: load active memories for a user
- `user_memories(source_conversation_id)` — extraction dedup: "already extracted this conversation?"
- `user_memory_profiles(user_id)` — unique, used on every chat request
- `chat_messages(conversation_id, created_at DESC)` — new composite index to support the poll task's correlated subquery efficiently (existing single-column indexes don't cover this)

### Memory Count Scaling

When a user accumulates > 100 active memories, the extraction prompt receives only the 50 most recent memories plus a category-count summary of the rest (e.g., "Additionally: 30 domain_focus, 25 expertise, 12 investigation memories not shown"). This keeps extraction within token limits.

Profile rebuild reads all active memories, but summarizes per-category in batches if the count exceeds 200 (summarize each category separately, then merge into the final profile). In practice, supersession and deactivation keep the active count well below this — most facts get refined rather than accumulated indefinitely.

### Relationships

```
user ──1:*──► user_memories (granular facts, grow over time)
user ──1:1──► user_memory_profiles (precomputed summary, rebuilt after extraction)
user_memory ──0..1──► user_memory (superseded_by self-reference)
```

## Extraction Pipeline

### Trigger: Celery Beat Polling (Option B)

A Celery Beat task runs every 10 minutes, finds conversations with new messages since last extraction, and processes them. No frontend changes needed, handles abandoned conversations, batches naturally.

Conversations with fewer than 3 user messages are skipped (not enough signal).

### Extraction Flow

```
Celery Beat (every 10 min)
  → Find conversations with new messages since last extraction
  → For each conversation:
    → Celery task: extract_user_memories(conversation_id, user_id)
      → Load conversation messages
      → Load existing active memories for this user
      → LLM call: structured extraction prompt
      → Returns: list[MemoryExtraction]
      → For each extraction:
          - NEW: insert into user_memories
          - UPDATE: insert new row, set old row's superseded_by
          - INVALIDATE: deactivate old row
      → Rebuild user_memory_profiles summary
```

### LLM Extraction Prompt

The prompt gives the LLM three jobs:

1. **Extract new facts** in three categories:
   - `domain_focus`: tables, schemas, domains the user works with or asks about
   - `expertise`: what the user knows well vs. needs explained (inferred from questions and language)
   - `investigation`: specific issues found, conclusions reached, ongoing problems

2. **Compare against existing memories** (passed as context) and flag:
   - `new` — fact not covered by any existing memory
   - `update` — refines or contradicts an existing memory (reference its ID)
   - `invalidate` — existing memory is now wrong (reference its ID)

3. **Output:** Pydantic-validated structured response

### Pydantic Models

```python
class MemoryExtraction(BaseModel):
    category: Literal["domain_focus", "expertise", "investigation"]
    content: str
    confidence: float  # 0-1
    action: Literal["new", "update", "invalidate"]
    existing_memory_id: str | None  # for update/invalidate
```

### Profile Rebuild

After extraction, a second (cheap, fast) LLM call summarizes all active memories into the three profile summary fields. This is the only thing agents see at runtime.

### Cost Control

- One extraction call per conversation, not per message
- Existing memories passed as compressed list, not full history
- Profile rebuild is a short summarization task — cheap tokens
- Skip conversations with < 3 user messages

## System Prompt Injection

### Integration Point

`orchestrator.run_chat()` — before dispatching to any agent, load the user's `user_memory_profiles` row (single DB query) and pass it to agent builders.

### Modified Flow

```
run_chat(message, history, user_id)
  → Load user_memory_profiles for user_id (single DB query)
  → Route message via RouterAgent (unchanged)
  → If decision.intent == "memory":
      → Early return: call recall logic directly (no agent dispatch)
      → Query user_memories, format response from template
  → Else: dispatch to agent, passing user_profile as new kwarg
      → Agent builder appends profile to system prompt
```

If no `user_memory_profiles` row exists (new user, first conversation), the USER CONTEXT block is omitted entirely from the system prompt — no placeholder text.

### What Agents See (appended to system prompt)

```
USER CONTEXT (learned from prior conversations):
- Domain focus: Focuses on orders, payments, customers tables. Primarily e-commerce domain.
- Expertise: Strong SQL skills. Familiar with data modeling. New to data quality monitoring — explain check types and thresholds.
- Investigation history: Investigated NULL spike in customers.email (2026-03-20, concluded: migration issue, don't re-flag). Tracked order volume drop (2026-04-01, ongoing).

Use this context to tailor your responses. Don't re-explain concepts the user already knows. Reference prior investigations when relevant.
```

### Which Agents Get It

All of them — config, investigation, report, insight. The profile is short (~3 paragraphs) so token cost is negligible. Each agent benefits differently:

- **Config agent:** knows which tables to suggest checks for first
- **Investigation agent:** knows not to re-flag the customers.email NULL spike
- **Report agent:** knows to lead with orders/payments metrics, skip verbose SQL explanations
- **Insight agent:** already has data-level context; now also gets user-level context

### Code Changes

- `orchestrator.run_chat()` — one DB call to load profile, pass to agent builders. Add early-return branch for `decision.intent == "memory"`.
- `router.py` — add `"memory"` to `VALID_INTENTS` Literal. No corresponding agent in `_get_agent_builder`.
- `_fallback_route()` — add memory trigger keywords: "what do you know about me", "what did we find", "my memory", "show my profile".
- Each `build_*_agent()` — accept optional `user_profile: str` kwarg, append to system prompt.
- The Insight agent already has `_build_system_prompt()` with dynamic context injection — same pattern extends to all agents.

Minimal blast radius — no changes to tools or conversation persistence.

## User Control API

Users can view, edit, and deactivate their memories. All endpoints scoped to `current_user`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/user/memory/profile` | Get precomputed profile (what agents see) |
| GET | `/user/memory` | List individual memories (filterable by `category`, `active`, `q` text search) |
| GET | `/user/memory/{id}` | Get a single memory with its supersession chain |
| PATCH | `/user/memory/{id}` | Edit content or deactivate (`active: false`) |
| DELETE | `/user/memory/{id}` | Hard delete a memory |
| POST | `/user/memory` | Manually add a memory (user tells the system something explicitly) |
| POST | `/user/memory/rebuild` | Force-rebuild the profile summary from current active memories |

### Key Behaviors

- **Deactivate vs delete:** Deactivating (`active: false`) keeps the memory for audit but removes it from the profile. Delete is permanent. Default UI action should be deactivate.
- **Manual add:** User can say "I'm a data engineer, I know SQL well" without waiting for extraction. Creates a memory with `confidence: 1.0` and `source_conversation_id: null`.
- **Edit propagation:** When a user edits or deactivates a memory, the profile is automatically rebuilt (lightweight Celery task).
- **Text search:** `GET /user/memory?category=investigation&q=orders` uses `ILIKE` on content. No semantic/vector search.

## Recall — Explicit Memory Search

### Two Recall Modes

**Direct recall** — user explicitly asks about memory:
> "What do you know about me?" / "What did we investigate last week?"

The Router agent classifies this as a `memory` intent. The orchestrator queries `user_memories` filtered by category and keyword, returns a formatted summary. No LLM needed — DB query + template.

**Scope for v1:** Direct recall supports category filtering and keyword search (`ILIKE`). Temporal queries like "last week" are not supported in v1 — the response shows all matching memories with their dates, and the user can scan visually. Temporal parsing (extracting date ranges from natural language) is a future enhancement that could use the router's structured output to extract a date range alongside the intent.

**Contextual recall** — user asks a question that benefits from memory but isn't explicitly about it:
> "Can you check the orders table again?"

Already handled by system prompt injection (Section: System Prompt Injection). The agent sees investigation history and knows "orders table" has prior context.

### Router Changes

The Router agent gets a new intent added:

```python
# Intent → Agent mapping (updated)
"quick"         → ReportAgent
"configure"     → ConfigAgent
"investigate"   → InvestigationAgent
"report"        → ReportAgent
"insight"       → InsightAgent
"memory"        → Direct recall (no agent, orchestrator handles)
```

**Trigger phrases (read-only in v1):** "what do you know about me", "what did we find", "what have we investigated", "my memory", "show my profile"

**Note:** Write operations ("forget that", "remember that") are handled through the User Control API endpoints, not through chat. The recall intent is read-only in v1. A future enhancement could route "forget X" and "remember X" through chat by having the orchestrator call the CRUD service directly.

### Direct Recall Response Format

```
Here's what I know about you:

**Domain Focus:**
- You frequently work with the orders, payments, and customers tables
- Your data sources are primarily e-commerce databases

**Expertise:**
- Strong SQL skills — you write complex joins and window functions
- New to data quality monitoring — you've asked about freshness checks and thresholds

**Past Investigations:**
- NULL spike in customers.email (2026-03-20) — concluded: migration issue
- Order volume drop (2026-04-01) — ongoing, monitoring

You can manage these memories at any time — ask me to forget something or tell me something new.
```

## Celery Integration

### New Tasks

```python
@app.task(queue="intelligence.default")
def extract_user_memories(conversation_id: str, user_id: str) -> None:
    """Extract memories from a completed conversation.
    Loads conversation + existing memories, runs LLM extraction,
    persists new/updated/invalidated memories, rebuilds profile."""

@app.task(queue="intelligence.default")
def rebuild_user_profile(user_id: str) -> None:
    """Rebuild the user_memory_profiles summary from active memories.
    Called after extraction or manual memory edits."""

@app.task(queue="intelligence.default")
def poll_conversations_for_extraction() -> None:
    """Celery Beat task (every 10 min). Finds conversations with new
    messages since last extraction, dispatches extract_user_memories
    for each. Skips conversations with < 3 user messages."""
```

### Celery Beat Schedule

```python
{
    "name": "poll-conversations-for-memory-extraction",
    "task": "poll_conversations_for_extraction",
    "schedule": crontab(minute="*/10"),  # Every 10 minutes
}
```

### Extraction Tracking

A lightweight `conversation_extraction_status` table tracks which conversations have been processed:

| Column | Type | Description |
|--------|------|-------------|
| conversation_id | VARCHAR | PK |
| user_id | VARCHAR | FK → users(id) |
| status | VARCHAR | `idle`, `processing`. Default: `idle` |
| last_extracted_at | TEXT (nullable) | ISO 8601 timestamp of last extraction. TEXT to match `chat_messages.created_at` format. |

**Population strategy: eager.** The chat message persistence code (in `chat.py` endpoint) upserts a row into `conversation_extraction_status` on every message save — just `INSERT ... ON CONFLICT (conversation_id) DO NOTHING`. This is cheap (one upsert per message) and ensures the poll task has a complete index of conversations without scanning `chat_messages`.

**Poll task query:**

```sql
SELECT ces.conversation_id, ces.user_id
FROM conversation_extraction_status ces
WHERE ces.status = 'idle'
  AND (
    ces.last_extracted_at IS NULL
    OR ces.last_extracted_at < (
        SELECT MAX(created_at) FROM chat_messages cm
        WHERE cm.conversation_id = ces.conversation_id
    )
  )
LIMIT 50
```

The `LIMIT 50` caps dispatch per poll cycle to prevent queue spikes. The `status = 'idle'` guard prevents double-dispatch if extraction takes > 10 minutes (the poll interval).

**Dispatch flow:**
1. Poll task sets `status = 'processing'` for selected rows (atomic UPDATE)
2. Dispatches `extract_user_memories.delay(conversation_id, user_id)` for each
3. Extraction task: on completion, sets `status = 'idle'` and `last_extracted_at = NOW()`; on failure, sets `status = 'idle'` (will be retried next poll)

Then for each result, check user message count >= 3 before dispatching extraction.

**Note on timestamps:** Both `last_extracted_at` and `chat_messages.created_at` use TEXT in ISO 8601 format. String comparison works correctly for ISO 8601 (`"2026-04-06T..." > "2026-04-05T..."`). Using the same type avoids implicit type coercion in the comparison. If format consistency becomes an issue, a future migration can add proper TIMESTAMP columns to both tables.

### Profile Rebuild Concurrency

Profile rebuilds are idempotent — they always read the current set of active memories and recompute summaries from scratch. If two rebuilds race (e.g., manual edit + poll extraction), there's a small window where one rebuild reads before the other's memory writes are committed, producing a slightly stale profile. This is an acceptable trade-off: the window is narrow (seconds), the impact is a temporarily stale summary, and the next extraction or manual edit triggers another rebuild that corrects it. No lock needed for v1; if this proves problematic, a `SELECT ... FOR UPDATE` on the profile row can serialize rebuilds.

## LLM Error Handling

| Failure | Behavior |
|---------|----------|
| Malformed extraction output | Retry once with stricter prompt. On second failure, skip this conversation (will retry next poll). |
| API down / rate limited | Skip, log warning. Will retry next poll cycle (10 min). |
| Token limit exceeded | Truncate conversation to last 20 messages, retry once. Then skip. |

The principle: **never lose existing memories due to an extraction failure.** Extraction is additive — failures just mean we don't learn from this conversation yet.

## File Structure

```
datametronome/podium/datametronome_podium/
├── features/
│   └── user_memory/
│       ├── __init__.py
│       ├── router.py         # API endpoints (user control + recall)
│       ├── schemas.py        # Request/response schemas
│       ├── service.py        # Extraction + profile rebuild + recall logic
│       └── repo.py           # Database operations
├── models/
│   ├── user_memory.py        # UserMemory SQLAlchemy model
│   └── user_memory_profile.py # UserMemoryProfile SQLAlchemy model
└── worker/
    └── tasks/
        └── user_memory.py    # Celery tasks (extract, rebuild, poll)
```

## Migration

One Alembic migration to create: `user_memories`, `user_memory_profiles`, `conversation_extraction_status`.

## Testing Strategy

### Unit Tests
- Memory extraction Pydantic model validation
- Supersession logic (new memory supersedes old, chain integrity)
- Profile rebuild from a set of active memories
- Conversation polling logic (skip < 3 messages, skip already extracted)
- Text search filtering (`ILIKE` on content with category filter)

### Integration Tests
- Full extraction pipeline: conversation → LLM call (mocked) → memories persisted → profile rebuilt
- LLM failure scenarios (malformed output, API down, token limit)
- Memory CRUD operations (create, deactivate, delete, manual add)
- Edit propagation (edit memory → profile auto-rebuilt)
- Supersession chain (old memory → superseded_by → new memory)

### API Tests
- All `/user/memory/*` endpoints with auth
- User isolation (user A cannot see user B's memories)
- Recall formatting (direct recall response structure)

### Orchestrator Tests
- Profile loaded and injected into agent system prompts
- Memory intent routed correctly (direct recall, not dispatched to agent)
- Graceful handling when no profile exists (new user, first conversation)
