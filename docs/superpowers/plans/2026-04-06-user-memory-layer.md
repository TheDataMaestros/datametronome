# User Memory Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-user memory system that makes chat agents smarter over time by extracting domain focus, expertise level, and investigation history from conversations.

**Architecture:** Two new tables (`user_memories`, `user_memory_profiles`) plus an extraction tracking table. A Celery Beat task polls for new conversations every 10 minutes, dispatches LLM extraction, and rebuilds a precomputed profile. The profile is injected into all agent system prompts via the orchestrator. Users can view/edit/delete memories via REST API.

**Tech Stack:** FastAPI, Pydantic AI, Celery + Redis, PostgreSQL (via QueryExecutor), existing LLM provider infrastructure.

**Spec:** `docs/superpowers/specs/2026-04-06-user-memory-layer-design.md`

---

## File Structure

### New Files
```
datametronome/podium/datametronome_podium/
├── features/user_memory/
│   ├── __init__.py
│   ├── router.py          # API endpoints (CRUD + recall)
│   ├── schemas.py         # Request/response DTOs
│   ├── service.py         # Extraction + profile rebuild logic
│   └── repo.py            # Database operations
├── tasks/
│   └── user_memory_tasks.py  # Celery tasks (extract, rebuild, poll)
└── tests/
    ├── test_user_memory_repo.py
    ├── test_user_memory_service.py
    ├── test_user_memory_router.py
    ├── test_user_memory_tasks.py
    └── test_user_memory_orchestrator.py
```

### Modified Files
```
alembic/versions/009_user_memory.py           # New migration
core/celery_app.py                             # Task include + beat schedule
api/v1/api.py                                  # Wire user_memory router
api/v1/endpoints/chat.py:268-281               # Eager upsert to extraction tracking
services/orchestrator.py:124-212               # Load profile, memory intent branch
services/agents/router.py:15,29-54             # Add "memory" intent
services/agents/config.py:24-30                # Accept user_profile kwarg
services/agents/investigation.py:26-32         # Accept user_profile kwarg
services/agents/report.py:24-30                # Accept user_profile kwarg
services/agents/insight.py:78-96               # Accept user_profile kwarg
```

---

## Chunk 1: Data Model + Migration

### Task 1: Alembic Migration

**Files:**
- Create: `datametronome/podium/alembic/versions/009_user_memory.py`

- [ ] **Step 1: Write the migration**

```python
"""009 — user memory tables.

Revision ID: 009_user_memory
Revises: 008_dashboard_prefs
"""
from alembic import op
from datametronome_podium.alembic.dialect_ops import DialectAwareOps as dao

revision = "009_user_memory"
down_revision = "008_dashboard_prefs"


def upgrade():
    dao.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category TEXT NOT NULL CHECK (category IN ('domain_focus', 'expertise', 'investigation')),
            content TEXT NOT NULL,
            source_conversation_id TEXT,
            confidence REAL NOT NULL DEFAULT 1.0,
            active INTEGER NOT NULL DEFAULT 1,
            superseded_by TEXT REFERENCES user_memories(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    dao.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_user_active ON user_memories(user_id, active)")
    dao.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_conversation ON user_memories(source_conversation_id)")

    dao.execute("""
        CREATE TABLE IF NOT EXISTS user_memory_profiles (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            domain_summary TEXT NOT NULL DEFAULT '',
            expertise_summary TEXT NOT NULL DEFAULT '',
            investigation_summary TEXT NOT NULL DEFAULT '',
            memory_count INTEGER NOT NULL DEFAULT 0,
            last_rebuilt_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    dao.execute("""
        CREATE TABLE IF NOT EXISTS conversation_extraction_status (
            conversation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'processing')),
            last_extracted_at TEXT
        )
    """)

    dao.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_messages_conv_created
        ON chat_messages(conversation_id, created_at DESC)
    """)


def downgrade():
    dao.execute("DROP TABLE IF EXISTS conversation_extraction_status")
    dao.execute("DROP TABLE IF EXISTS user_memory_profiles")
    dao.execute("DROP TABLE IF EXISTS user_memories")
    dao.execute("DROP INDEX IF EXISTS idx_chat_messages_conv_created")
```

- [ ] **Step 2: Run migration and verify**

Run: `.venv/bin/python -m alembic upgrade head` from `datametronome/podium/`
Expected: Tables created, no errors.

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/009_user_memory.py
git commit -m "feat(memory): add user_memories, user_memory_profiles, extraction_status tables"
```

---

### Task 2: Pydantic Models (feature slice)

**Files:**
- Create: `datametronome/podium/datametronome_podium/features/user_memory/__init__.py`
- Create: `datametronome/podium/datametronome_podium/features/user_memory/schemas.py`

- [ ] **Step 1: Write the test for schemas**

Create: `datametronome/podium/tests/test_user_memory_schemas.py`

```python
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
    mem = UserMemoryResponse(**row)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_user_memory_schemas.py -v --timeout=10`
Expected: ImportError — module doesn't exist yet.

- [ ] **Step 3: Write the schemas**

Create `features/user_memory/__init__.py` (empty).

Create `features/user_memory/schemas.py`:

```python
"""User memory API DTOs and extraction models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UserMemoryResponse(BaseModel):
    id: str
    user_id: str
    category: str
    content: str
    source_conversation_id: str | None = None
    confidence: float
    active: bool
    superseded_by: str | None = None
    created_at: str
    updated_at: str


class UserMemoryProfileResponse(BaseModel):
    id: str
    user_id: str
    domain_summary: str
    expertise_summary: str
    investigation_summary: str
    memory_count: int
    last_rebuilt_at: str
    created_at: str


class UserMemoryCreate(BaseModel):
    category: Literal["domain_focus", "expertise", "investigation"]
    content: str
    confidence: float = 1.0


class UserMemoryUpdate(BaseModel):
    content: str | None = None
    active: bool | None = None


class MemoryExtraction(BaseModel):
    category: Literal["domain_focus", "expertise", "investigation"]
    content: str
    confidence: float
    action: Literal["new", "update", "invalidate"]
    existing_memory_id: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_user_memory_schemas.py -v --timeout=10`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add features/user_memory/__init__.py features/user_memory/schemas.py tests/test_user_memory_schemas.py
git commit -m "feat(memory): add user memory Pydantic schemas"
```

---

### Task 3: Repository (CRUD)

**Files:**
- Create: `datametronome/podium/datametronome_podium/features/user_memory/repo.py`
- Create: `datametronome/podium/tests/test_user_memory_repo.py`

- [ ] **Step 1: Write the repo tests**

```python
"""Tests for UserMemoryRepo — uses real DB via QueryExecutor."""
import pytest
from datetime import datetime, timezone

from datametronome_podium.core.database import get_executor
from datametronome_podium.features.user_memory.repo import UserMemoryRepo


@pytest.fixture
def repo():
    return UserMemoryRepo(get_executor())


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_create_and_get_memory(repo):
    now = _now()
    mem_id = "mem-test-1"
    await repo.create_memory(
        id=mem_id, user_id="user-1", category="domain_focus",
        content="Works with orders table", source_conversation_id="conv-1",
        confidence=0.9, created_at=now, updated_at=now,
    )
    mem = await repo.get_memory(mem_id)
    assert mem is not None
    assert mem["content"] == "Works with orders table"
    assert mem["active"] == 1


@pytest.mark.asyncio
async def test_list_active_memories(repo):
    now = _now()
    for i in range(3):
        await repo.create_memory(
            id=f"mem-list-{i}", user_id="user-list", category="expertise",
            content=f"Fact {i}", source_conversation_id=None,
            confidence=1.0, created_at=now, updated_at=now,
        )
    # Deactivate one
    await repo.update_memory(f"mem-list-1", {"active": 0, "updated_at": now})
    active = await repo.list_active_memories("user-list")
    assert len(active) == 2


@pytest.mark.asyncio
async def test_deactivate_memory(repo):
    now = _now()
    await repo.create_memory(
        id="mem-deact", user_id="user-deact", category="investigation",
        content="NULL spike", source_conversation_id="conv-2",
        confidence=0.8, created_at=now, updated_at=now,
    )
    await repo.update_memory("mem-deact", {"active": 0, "updated_at": now})
    mem = await repo.get_memory("mem-deact")
    assert mem["active"] == 0


@pytest.mark.asyncio
async def test_delete_memory(repo):
    now = _now()
    await repo.create_memory(
        id="mem-del", user_id="user-del", category="domain_focus",
        content="To delete", source_conversation_id=None,
        confidence=1.0, created_at=now, updated_at=now,
    )
    await repo.delete_memory("mem-del")
    mem = await repo.get_memory("mem-del")
    assert mem is None


@pytest.mark.asyncio
async def test_search_memories(repo):
    now = _now()
    await repo.create_memory(
        id="mem-search-1", user_id="user-search", category="investigation",
        content="NULL spike in customers.email", source_conversation_id="conv-3",
        confidence=0.85, created_at=now, updated_at=now,
    )
    await repo.create_memory(
        id="mem-search-2", user_id="user-search", category="domain_focus",
        content="Works with products table", source_conversation_id="conv-3",
        confidence=0.9, created_at=now, updated_at=now,
    )
    results = await repo.search_memories("user-search", q="customers")
    assert len(results) == 1
    assert "customers" in results[0]["content"]


@pytest.mark.asyncio
async def test_create_and_get_profile(repo):
    now = _now()
    await repo.upsert_profile(
        user_id="user-prof",
        domain_summary="E-commerce focus",
        expertise_summary="SQL expert",
        investigation_summary="Tracked NULL spike",
        memory_count=3,
        now=now,
    )
    profile = await repo.get_profile("user-prof")
    assert profile is not None
    assert profile["domain_summary"] == "E-commerce focus"
    assert profile["memory_count"] == 3


@pytest.mark.asyncio
async def test_upsert_extraction_status(repo):
    await repo.upsert_extraction_status("conv-track", "user-track")
    # Should not fail on duplicate
    await repo.upsert_extraction_status("conv-track", "user-track")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_user_memory_repo.py -v --timeout=10`
Expected: ImportError.

- [ ] **Step 3: Write the repo**

```python
"""User memory data access via QueryExecutor."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from datametronome_podium.core.query import QueryExecutor


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str = "mem") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class UserMemoryRepo:
    """CRUD for user_memories, user_memory_profiles, conversation_extraction_status."""

    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    # --- user_memories ---

    async def create_memory(
        self,
        *,
        id: str | None = None,
        user_id: str,
        category: str,
        content: str,
        source_conversation_id: str | None = None,
        confidence: float = 1.0,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> str:
        mem_id = id or _new_id("mem")
        now = created_at or _now()
        await self.db.insert("user_memories", {
            "id": mem_id,
            "user_id": user_id,
            "category": category,
            "content": content,
            "source_conversation_id": source_conversation_id,
            "confidence": confidence,
            "active": 1,
            "superseded_by": None,
            "created_at": now,
            "updated_at": updated_at or now,
        })
        return mem_id

    async def get_memory(self, memory_id: str) -> dict | None:
        rows = await self.db.select("user_memories", where={"id": memory_id})
        return dict(rows[0]) if rows else None

    async def list_active_memories(
        self, user_id: str, category: str | None = None, limit: int = 200,
    ) -> list[dict]:
        if category:
            rows = await self.db.query(
                "SELECT * FROM user_memories WHERE user_id = ? AND active = 1 AND category = ? "
                "ORDER BY created_at DESC LIMIT ?",
                [user_id, category, limit],
            )
        else:
            rows = await self.db.query(
                "SELECT * FROM user_memories WHERE user_id = ? AND active = 1 "
                "ORDER BY created_at DESC LIMIT ?",
                [user_id, limit],
            )
        return [dict(r) for r in rows]

    async def search_memories(
        self, user_id: str, q: str | None = None,
        category: str | None = None, active_only: bool = True,
    ) -> list[dict]:
        conditions = ["user_id = ?"]
        params: list = [user_id]
        if active_only:
            conditions.append("active = 1")
        if category:
            conditions.append("category = ?")
            params.append(category)
        if q:
            conditions.append("content LIKE ?")
            params.append(f"%{q}%")
        where = " AND ".join(conditions)
        rows = await self.db.query(
            f"SELECT * FROM user_memories WHERE {where} ORDER BY created_at DESC",
            params,
        )
        return [dict(r) for r in rows]

    async def update_memory(self, memory_id: str, data: dict) -> int:
        return await self.db.update("user_memories", data, where={"id": memory_id})

    async def supersede_memory(self, old_id: str, new_id: str) -> None:
        now = _now()
        await self.db.update(
            "user_memories",
            {"active": 0, "superseded_by": new_id, "updated_at": now},
            where={"id": old_id},
        )

    async def delete_memory(self, memory_id: str) -> int:
        return await self.db.execute(
            "DELETE FROM user_memories WHERE id = ?", [memory_id]
        )

    async def count_active_memories(self, user_id: str) -> int:
        rows = await self.db.query(
            "SELECT COUNT(*) as cnt FROM user_memories WHERE user_id = ? AND active = 1",
            [user_id],
        )
        return rows[0]["cnt"] if rows else 0

    # --- user_memory_profiles ---

    async def get_profile(self, user_id: str) -> dict | None:
        rows = await self.db.select("user_memory_profiles", where={"user_id": user_id})
        return dict(rows[0]) if rows else None

    async def upsert_profile(
        self,
        *,
        user_id: str,
        domain_summary: str,
        expertise_summary: str,
        investigation_summary: str,
        memory_count: int,
        now: str | None = None,
    ) -> None:
        ts = now or _now()
        existing = await self.get_profile(user_id)
        if existing:
            await self.db.update(
                "user_memory_profiles",
                {
                    "domain_summary": domain_summary,
                    "expertise_summary": expertise_summary,
                    "investigation_summary": investigation_summary,
                    "memory_count": memory_count,
                    "last_rebuilt_at": ts,
                },
                where={"user_id": user_id},
            )
        else:
            await self.db.insert("user_memory_profiles", {
                "id": _new_id("prof"),
                "user_id": user_id,
                "domain_summary": domain_summary,
                "expertise_summary": expertise_summary,
                "investigation_summary": investigation_summary,
                "memory_count": memory_count,
                "last_rebuilt_at": ts,
                "created_at": ts,
            })

    # --- conversation_extraction_status ---

    async def upsert_extraction_status(self, conversation_id: str, user_id: str) -> None:
        await self.db.execute(
            "INSERT INTO conversation_extraction_status (conversation_id, user_id, status) "
            "VALUES (?, ?, 'idle') ON CONFLICT (conversation_id) DO NOTHING",
            [conversation_id, user_id],
        )

    async def find_conversations_needing_extraction(self, limit: int = 50) -> list[dict]:
        rows = await self.db.query(
            "SELECT ces.conversation_id, ces.user_id "
            "FROM conversation_extraction_status ces "
            "WHERE ces.status = 'idle' AND ("
            "  ces.last_extracted_at IS NULL "
            "  OR ces.last_extracted_at < ("
            "    SELECT MAX(created_at) FROM chat_messages cm "
            "    WHERE cm.conversation_id = ces.conversation_id"
            "  )"
            ") LIMIT ?",
            [limit],
        )
        return [dict(r) for r in rows]

    async def mark_extraction_processing(self, conversation_id: str) -> int:
        return await self.db.execute(
            "UPDATE conversation_extraction_status SET status = 'processing' "
            "WHERE conversation_id = ? AND status = 'idle'",
            [conversation_id],
        )

    async def mark_extraction_done(self, conversation_id: str) -> None:
        now = _now()
        await self.db.execute(
            "UPDATE conversation_extraction_status SET status = 'idle', last_extracted_at = ? "
            "WHERE conversation_id = ?",
            [now, conversation_id],
        )

    async def mark_extraction_failed(self, conversation_id: str) -> None:
        await self.db.execute(
            "UPDATE conversation_extraction_status SET status = 'idle' "
            "WHERE conversation_id = ?",
            [conversation_id],
        )

    async def count_user_messages(self, conversation_id: str) -> int:
        rows = await self.db.query(
            "SELECT COUNT(*) as cnt FROM chat_messages "
            "WHERE conversation_id = ? AND role = 'user'",
            [conversation_id],
        )
        return rows[0]["cnt"] if rows else 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_user_memory_repo.py -v --timeout=10`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add features/user_memory/repo.py tests/test_user_memory_repo.py
git commit -m "feat(memory): add UserMemoryRepo with CRUD + extraction tracking"
```

---

## Chunk 2: Extraction Service + Celery Tasks

### Task 4: Extraction Service

**Files:**
- Create: `datametronome/podium/datametronome_podium/features/user_memory/service.py`
- Create: `datametronome/podium/tests/test_user_memory_service.py`

- [ ] **Step 1: Write the service tests**

```python
"""Tests for UserMemoryService — extraction and profile rebuild."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from datametronome_podium.features.user_memory.service import UserMemoryService
from datametronome_podium.features.user_memory.schemas import MemoryExtraction


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.list_active_memories.return_value = []
    repo.count_active_memories.return_value = 0
    repo.create_memory.return_value = "mem-new-1"
    repo.get_profile.return_value = None
    return repo


@pytest.fixture
def service(mock_repo):
    return UserMemoryService(repo=mock_repo)


@pytest.mark.asyncio
async def test_extract_memories_creates_new(service, mock_repo):
    """New extraction inserts memories and rebuilds profile."""
    conversation = [
        {"role": "user", "content": "Show me the orders table"},
        {"role": "assistant", "content": "Here's the orders table..."},
        {"role": "user", "content": "What about the payments table?"},
        {"role": "assistant", "content": "The payments table has..."},
        {"role": "user", "content": "I think the NULL rate is from a migration"},
        {"role": "assistant", "content": "That's a good observation..."},
    ]

    extractions = [
        MemoryExtraction(
            category="domain_focus",
            content="Works with orders and payments tables",
            confidence=0.9,
            action="new",
            existing_memory_id=None,
        ),
        MemoryExtraction(
            category="investigation",
            content="NULL rate attributed to migration",
            confidence=0.8,
            action="new",
            existing_memory_id=None,
        ),
    ]

    with patch.object(service, "_call_extraction_llm", return_value=extractions):
        with patch.object(service, "_call_rebuild_llm", return_value={
            "domain_summary": "Orders and payments",
            "expertise_summary": "",
            "investigation_summary": "NULL rate from migration",
        }):
            await service.extract_and_rebuild("conv-1", "user-1", conversation)

    assert mock_repo.create_memory.call_count == 2
    mock_repo.upsert_profile.assert_called_once()


@pytest.mark.asyncio
async def test_extract_memories_supersedes_existing(service, mock_repo):
    """Update action supersedes the old memory."""
    mock_repo.list_active_memories.return_value = [
        {"id": "mem-old", "category": "domain_focus", "content": "Works with orders"},
    ]

    extractions = [
        MemoryExtraction(
            category="domain_focus",
            content="Works with orders AND payments",
            confidence=0.95,
            action="update",
            existing_memory_id="mem-old",
        ),
    ]

    with patch.object(service, "_call_extraction_llm", return_value=extractions):
        with patch.object(service, "_call_rebuild_llm", return_value={
            "domain_summary": "Orders and payments",
            "expertise_summary": "",
            "investigation_summary": "",
        }):
            await service.extract_and_rebuild("conv-2", "user-1", [
                {"role": "user", "content": "x"}, {"role": "assistant", "content": "y"},
                {"role": "user", "content": "x"}, {"role": "assistant", "content": "y"},
                {"role": "user", "content": "x"}, {"role": "assistant", "content": "y"},
            ])

    mock_repo.supersede_memory.assert_called_once_with("mem-old", mock_repo.create_memory.return_value)


@pytest.mark.asyncio
async def test_extract_memories_invalidates(service, mock_repo):
    """Invalidate action deactivates the old memory."""
    mock_repo.list_active_memories.return_value = [
        {"id": "mem-wrong", "category": "investigation", "content": "Migration issue"},
    ]

    extractions = [
        MemoryExtraction(
            category="investigation",
            content="",
            confidence=1.0,
            action="invalidate",
            existing_memory_id="mem-wrong",
        ),
    ]

    with patch.object(service, "_call_extraction_llm", return_value=extractions):
        with patch.object(service, "_call_rebuild_llm", return_value={
            "domain_summary": "",
            "expertise_summary": "",
            "investigation_summary": "",
        }):
            await service.extract_and_rebuild("conv-3", "user-1", [
                {"role": "user", "content": "x"}, {"role": "assistant", "content": "y"},
                {"role": "user", "content": "x"}, {"role": "assistant", "content": "y"},
                {"role": "user", "content": "x"}, {"role": "assistant", "content": "y"},
            ])

    mock_repo.update_memory.assert_called_once()
    call_args = mock_repo.update_memory.call_args
    assert call_args[0][0] == "mem-wrong"
    assert call_args[0][1]["active"] == 0


@pytest.mark.asyncio
async def test_format_recall_response(service, mock_repo):
    """Direct recall formats profile into structured text."""
    mock_repo.get_profile.return_value = {
        "domain_summary": "Orders and payments tables",
        "expertise_summary": "Strong SQL skills",
        "investigation_summary": "NULL spike in customers",
        "memory_count": 5,
    }
    response = await service.format_recall("user-1")
    assert "Orders and payments" in response
    assert "Strong SQL" in response
    assert "NULL spike" in response


@pytest.mark.asyncio
async def test_format_recall_empty_profile(service, mock_repo):
    """Recall with no profile returns a friendly message."""
    mock_repo.get_profile.return_value = None
    response = await service.format_recall("user-new")
    assert "haven't learned" in response.lower() or "no memories" in response.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_user_memory_service.py -v --timeout=10`
Expected: ImportError.

- [ ] **Step 3: Write the service**

```python
"""User memory extraction and profile rebuild service."""
from __future__ import annotations

import logging
from typing import Any

from datametronome_podium.features.user_memory.repo import UserMemoryRepo
from datametronome_podium.features.user_memory.schemas import MemoryExtraction

logger = logging.getLogger(__name__)

# Maximum memories to include in extraction prompt context
_MAX_CONTEXT_MEMORIES = 50
_OVERFLOW_THRESHOLD = 100


class UserMemoryService:
    """Extracts user memories from conversations and manages profiles."""

    def __init__(self, repo: UserMemoryRepo) -> None:
        self.repo = repo

    async def extract_and_rebuild(
        self,
        conversation_id: str,
        user_id: str,
        conversation: list[dict],
    ) -> None:
        """Full extraction pipeline: extract facts → persist → rebuild profile."""
        existing = await self.repo.list_active_memories(user_id)

        # Scale context for extraction prompt
        if len(existing) > _OVERFLOW_THRESHOLD:
            context_memories = existing[:_MAX_CONTEXT_MEMORIES]
            overflow_count = len(existing) - _MAX_CONTEXT_MEMORIES
        else:
            context_memories = existing
            overflow_count = 0

        extractions = await self._call_extraction_llm(
            conversation, context_memories, overflow_count
        )

        for ext in extractions:
            if ext.action == "new":
                await self.repo.create_memory(
                    user_id=user_id,
                    category=ext.category,
                    content=ext.content,
                    source_conversation_id=conversation_id,
                    confidence=ext.confidence,
                )
            elif ext.action == "update" and ext.existing_memory_id:
                new_id = await self.repo.create_memory(
                    user_id=user_id,
                    category=ext.category,
                    content=ext.content,
                    source_conversation_id=conversation_id,
                    confidence=ext.confidence,
                )
                await self.repo.supersede_memory(ext.existing_memory_id, new_id)
            elif ext.action == "invalidate" and ext.existing_memory_id:
                await self.repo.update_memory(
                    ext.existing_memory_id,
                    {"active": 0, "updated_at": self.repo._now()},
                )

        await self._rebuild_profile(user_id)

    async def _rebuild_profile(self, user_id: str) -> None:
        """Rebuild the precomputed profile from all active memories."""
        all_memories = await self.repo.list_active_memories(user_id)
        count = len(all_memories)

        if count == 0:
            await self.repo.upsert_profile(
                user_id=user_id,
                domain_summary="",
                expertise_summary="",
                investigation_summary="",
                memory_count=0,
            )
            return

        summaries = await self._call_rebuild_llm(all_memories)
        await self.repo.upsert_profile(
            user_id=user_id,
            domain_summary=summaries.get("domain_summary", ""),
            expertise_summary=summaries.get("expertise_summary", ""),
            investigation_summary=summaries.get("investigation_summary", ""),
            memory_count=count,
        )

    async def rebuild_profile(self, user_id: str) -> None:
        """Public interface for profile rebuild (called after manual edits)."""
        await self._rebuild_profile(user_id)

    async def _call_extraction_llm(
        self,
        conversation: list[dict],
        existing_memories: list[dict],
        overflow_count: int = 0,
    ) -> list[MemoryExtraction]:
        """Call LLM to extract memories from a conversation.

        Uses the project's existing model infrastructure (build_model_from_settings).
        """
        from pydantic import BaseModel
        from pydantic_ai import Agent
        from datametronome_podium.services.agent_factory import build_model_from_settings

        class ExtractionResult(BaseModel):
            extractions: list[MemoryExtraction]

        existing_text = "\n".join(
            f"- [{m['id']}] ({m['category']}) {m['content']}"
            for m in existing_memories
        )
        if overflow_count > 0:
            existing_text += f"\n(+ {overflow_count} older memories not shown)"

        conv_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" for msg in conversation
        )

        prompt = f"""Analyze this conversation and extract facts about the USER into three categories:

CATEGORIES:
- domain_focus: tables, schemas, databases, domains the user works with or asks about
- expertise: what the user knows well vs. needs explained (infer from their questions and language)
- investigation: specific data issues found, conclusions reached, ongoing problems

EXISTING MEMORIES (compare against these):
{existing_text or "(none)"}

For each fact, specify:
- action: "new" (not covered by existing), "update" (refines/contradicts existing — include existing_memory_id), "invalidate" (existing memory is wrong — include existing_memory_id)
- Only extract facts that are clearly supported by the conversation
- confidence: 0-1 based on how certain the inference is

CONVERSATION:
{conv_text}"""

        model = build_model_from_settings()
        agent: Agent[None, ExtractionResult] = Agent(
            model=model,
            output_type=ExtractionResult,
            system_prompt="You extract structured facts about users from data quality monitoring conversations. Be precise and conservative — only extract facts clearly supported by the conversation.",
            retries=2,
        )

        try:
            result = await agent.run(prompt)
            return result.output.extractions
        except Exception as e:
            logger.warning("Memory extraction LLM call failed: %s", e)
            return []

    async def _call_rebuild_llm(
        self, memories: list[dict]
    ) -> dict[str, str]:
        """Call LLM to summarize memories into three profile fields."""
        from pydantic import BaseModel
        from pydantic_ai import Agent
        from datametronome_podium.services.agent_factory import build_model_from_settings

        class ProfileSummary(BaseModel):
            domain_summary: str
            expertise_summary: str
            investigation_summary: str

        by_category: dict[str, list[str]] = {
            "domain_focus": [], "expertise": [], "investigation": [],
        }
        for m in memories:
            cat = m.get("category", "domain_focus")
            by_category.setdefault(cat, []).append(m["content"])

        prompt = f"""Summarize these user facts into three concise profile summaries (1-3 sentences each):

DOMAIN FOCUS facts:
{chr(10).join(f'- {c}' for c in by_category.get('domain_focus', [])) or '(none)'}

EXPERTISE facts:
{chr(10).join(f'- {c}' for c in by_category.get('expertise', [])) or '(none)'}

INVESTIGATION HISTORY facts:
{chr(10).join(f'- {c}' for c in by_category.get('investigation', [])) or '(none)'}

Write each summary as if briefing a colleague: specific, quantitative where possible, no filler."""

        model = build_model_from_settings()
        agent: Agent[None, ProfileSummary] = Agent(
            model=model,
            output_type=ProfileSummary,
            system_prompt="You summarize user facts into concise profile descriptions for a data quality monitoring platform.",
            retries=2,
        )

        try:
            result = await agent.run(prompt)
            return result.output.model_dump()
        except Exception as e:
            logger.warning("Profile rebuild LLM call failed: %s", e)
            # Fallback: concatenate raw facts
            return {
                "domain_summary": "; ".join(by_category.get("domain_focus", [])),
                "expertise_summary": "; ".join(by_category.get("expertise", [])),
                "investigation_summary": "; ".join(by_category.get("investigation", [])),
            }

    async def format_recall(self, user_id: str) -> str:
        """Format a direct recall response for the user."""
        profile = await self.repo.get_profile(user_id)
        if not profile:
            return "I haven't learned anything about you yet. As we chat, I'll pick up on what data you work with, your expertise level, and what you've investigated."

        parts = ["Here's what I know about you:\n"]

        if profile.get("domain_summary"):
            parts.append(f"**Domain Focus:**\n{profile['domain_summary']}\n")
        if profile.get("expertise_summary"):
            parts.append(f"**Expertise:**\n{profile['expertise_summary']}\n")
        if profile.get("investigation_summary"):
            parts.append(f"**Past Investigations:**\n{profile['investigation_summary']}\n")

        parts.append(
            "You can manage these memories at any time through your profile settings, "
            "or ask me to show specific memories."
        )
        return "\n".join(parts)

    def format_profile_for_prompt(self, profile: dict | None) -> str | None:
        """Format a profile dict into the system prompt injection block."""
        if not profile:
            return None

        has_content = any(
            profile.get(f) for f in ("domain_summary", "expertise_summary", "investigation_summary")
        )
        if not has_content:
            return None

        parts = ["USER CONTEXT (learned from prior conversations):"]
        if profile.get("domain_summary"):
            parts.append(f"- Domain focus: {profile['domain_summary']}")
        if profile.get("expertise_summary"):
            parts.append(f"- Expertise: {profile['expertise_summary']}")
        if profile.get("investigation_summary"):
            parts.append(f"- Investigation history: {profile['investigation_summary']}")
        parts.append(
            "\nUse this context to tailor your responses. "
            "Don't re-explain concepts the user already knows. "
            "Reference prior investigations when relevant."
        )
        return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_user_memory_service.py -v --timeout=10`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add features/user_memory/service.py tests/test_user_memory_service.py
git commit -m "feat(memory): add UserMemoryService with extraction + profile rebuild"
```

---

### Task 5: Celery Tasks

**Files:**
- Create: `datametronome/podium/datametronome_podium/tasks/user_memory_tasks.py`
- Modify: `datametronome/podium/datametronome_podium/core/celery_app.py`
- Create: `datametronome/podium/tests/test_user_memory_tasks.py`

- [ ] **Step 1: Write task tests**

```python
"""Tests for user memory Celery tasks."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from datametronome_podium.tasks.user_memory_tasks import (
    poll_conversations_for_extraction,
    extract_user_memories,
    rebuild_user_profile,
)


def test_tasks_are_registered():
    """All user memory tasks should be registered with celery."""
    assert poll_conversations_for_extraction.name == "datametronome.poll_conversations_for_extraction"
    assert extract_user_memories.name == "datametronome.extract_user_memories"
    assert rebuild_user_profile.name == "datametronome.rebuild_user_profile"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_user_memory_tasks.py -v --timeout=10`
Expected: ImportError.

- [ ] **Step 3: Write the tasks**

```python
"""Celery tasks for user memory extraction and profile rebuilds.

Queue: intelligence.default (shared with data intelligence tasks).
"""
import asyncio
import logging
from typing import Any

from datametronome_podium.core.celery_app import celery_app
from datametronome_podium.core.config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine in a fresh event loop (safe for Celery prefork workers)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="datametronome.poll_conversations_for_extraction",
    acks_late=True,
)
def poll_conversations_for_extraction() -> dict[str, Any]:
    """Celery Beat task (every 10 min). Finds conversations needing extraction."""
    try:
        return _run_async(_poll_async())
    except Exception as exc:
        logger.error("Memory extraction poll failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


@celery_app.task(
    name="datametronome.extract_user_memories",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    acks_late=True,
)
def extract_user_memories(self, conversation_id: str, user_id: str) -> dict[str, Any]:
    """Extract memories from a single conversation."""
    try:
        return _run_async(_extract_async(conversation_id, user_id))
    except Exception as exc:
        logger.error(
            "Memory extraction failed for conversation %s: %s",
            conversation_id, exc,
        )
        # Mark as failed so it can be retried next poll
        _run_async(_mark_failed(conversation_id))
        raise self.retry(exc=exc)


@celery_app.task(
    name="datametronome.rebuild_user_profile",
    acks_late=True,
)
def rebuild_user_profile(user_id: str) -> dict[str, Any]:
    """Rebuild a user's memory profile (triggered after manual edits)."""
    try:
        return _run_async(_rebuild_async(user_id))
    except Exception as exc:
        logger.error("Profile rebuild failed for user %s: %s", user_id, exc)
        return {"status": "failed", "error": str(exc)}


async def _poll_async() -> dict[str, Any]:
    """Find conversations with new messages and dispatch extraction tasks."""
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo

    async with worker_db_session(settings.database_url) as (_, executor):
        repo = UserMemoryRepo(executor)
        candidates = await repo.find_conversations_needing_extraction(limit=50)

        dispatched = 0
        for row in candidates:
            conv_id = row["conversation_id"]
            uid = row["user_id"]

            # Skip conversations with < 3 user messages
            msg_count = await repo.count_user_messages(conv_id)
            if msg_count < 3:
                continue

            # Atomically mark as processing
            updated = await repo.mark_extraction_processing(conv_id)
            if updated > 0:
                extract_user_memories.delay(conv_id, uid)
                dispatched += 1

        logger.info("Memory extraction poll: %d dispatched from %d candidates", dispatched, len(candidates))
        return {"status": "completed", "dispatched": dispatched}


async def _extract_async(conversation_id: str, user_id: str) -> dict[str, Any]:
    """Load conversation, run extraction, update tracking."""
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo
    from datametronome_podium.features.user_memory.service import UserMemoryService
    from datametronome_podium.features.chat.repo import ChatRepo

    async with worker_db_session(settings.database_url) as (_, executor):
        chat_repo = ChatRepo(executor)
        memory_repo = UserMemoryRepo(executor)
        service = UserMemoryService(repo=memory_repo)

        # Load conversation messages
        messages = await chat_repo.get_history(conversation_id, user_id, limit=50)
        conversation = [{"role": m.role, "content": m.content} for m in messages]

        await service.extract_and_rebuild(conversation_id, user_id, conversation)
        await memory_repo.mark_extraction_done(conversation_id)

        logger.info("Memory extraction completed for conversation %s", conversation_id)
        return {"status": "completed", "conversation_id": conversation_id}


async def _rebuild_async(user_id: str) -> dict[str, Any]:
    """Rebuild profile for a single user."""
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo
    from datametronome_podium.features.user_memory.service import UserMemoryService

    async with worker_db_session(settings.database_url) as (_, executor):
        repo = UserMemoryRepo(executor)
        service = UserMemoryService(repo=repo)
        await service.rebuild_profile(user_id)

        logger.info("Profile rebuild completed for user %s", user_id)
        return {"status": "completed", "user_id": user_id}


async def _mark_failed(conversation_id: str) -> None:
    """Mark extraction as failed (reset to idle for retry)."""
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo

    async with worker_db_session(settings.database_url) as (_, executor):
        repo = UserMemoryRepo(executor)
        await repo.mark_extraction_failed(conversation_id)
```

- [ ] **Step 4: Wire into Celery config**

Modify `core/celery_app.py`:

Add to `celery_app.conf.include` (line 75-79):
```python
"datametronome_podium.tasks.user_memory_tasks",
```

Add to `task_routes` (line 44-52):
```python
"datametronome.poll_conversations_for_extraction": {"queue": QUEUE_INTELLIGENCE},
"datametronome.extract_user_memories": {"queue": QUEUE_INTELLIGENCE},
"datametronome.rebuild_user_profile": {"queue": QUEUE_INTELLIGENCE},
```

Add to `beat_schedule` (line 82-101):
```python
"poll-conversations-for-memory-extraction": {
    "task": "datametronome.poll_conversations_for_extraction",
    "schedule": crontab(minute="*/10"),
    "options": {"queue": "intelligence.default"},
},
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_user_memory_tasks.py -v --timeout=10`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tasks/user_memory_tasks.py core/celery_app.py tests/test_user_memory_tasks.py
git commit -m "feat(memory): add Celery tasks for extraction polling + profile rebuild"
```

---

## Chunk 3: API Router + Wiring

### Task 6: API Router

**Files:**
- Create: `datametronome/podium/datametronome_podium/features/user_memory/router.py`
- Modify: `datametronome/podium/datametronome_podium/api/v1/api.py`
- Create: `datametronome/podium/tests/test_user_memory_router.py`

- [ ] **Step 1: Write API tests**

```python
"""Tests for user memory API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_profile.return_value = {
        "id": "prof-1", "user_id": "user-1",
        "domain_summary": "E-commerce", "expertise_summary": "SQL",
        "investigation_summary": "NULL spike",
        "memory_count": 3, "last_rebuilt_at": "2026-04-06T00:00:00Z",
        "created_at": "2026-04-06T00:00:00Z",
    }
    repo.search_memories.return_value = [
        {
            "id": "mem-1", "user_id": "user-1", "category": "domain_focus",
            "content": "Works with orders", "source_conversation_id": "conv-1",
            "confidence": 0.9, "active": 1, "superseded_by": None,
            "created_at": "2026-04-06T00:00:00Z", "updated_at": "2026-04-06T00:00:00Z",
        },
    ]
    repo.get_memory.return_value = {
        "id": "mem-1", "user_id": "user-1", "category": "domain_focus",
        "content": "Works with orders", "source_conversation_id": "conv-1",
        "confidence": 0.9, "active": 1, "superseded_by": None,
        "created_at": "2026-04-06T00:00:00Z", "updated_at": "2026-04-06T00:00:00Z",
    }
    repo.create_memory.return_value = "mem-new"
    repo.update_memory.return_value = 1
    repo.delete_memory.return_value = 1
    return repo


def test_get_profile(mock_repo):
    """GET /user/memory/profile returns the precomputed profile."""
    with patch(
        "datametronome_podium.features.user_memory.router._repo",
        return_value=mock_repo,
    ):
        from datametronome_podium.features.user_memory.router import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/user/memory")

        # Patch auth dependency
        with patch(
            "datametronome_podium.features.user_memory.router._get_user_id",
            return_value="user-1",
        ):
            client = TestClient(app)
            resp = client.get("/user/memory/profile")
            assert resp.status_code == 200
            assert resp.json()["domain_summary"] == "E-commerce"


def test_list_memories(mock_repo):
    """GET /user/memory returns filtered memories."""
    with patch(
        "datametronome_podium.features.user_memory.router._repo",
        return_value=mock_repo,
    ):
        from datametronome_podium.features.user_memory.router import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/user/memory")

        with patch(
            "datametronome_podium.features.user_memory.router._get_user_id",
            return_value="user-1",
        ):
            client = TestClient(app)
            resp = client.get("/user/memory?category=domain_focus")
            assert resp.status_code == 200
            assert len(resp.json()) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_user_memory_router.py -v --timeout=10`
Expected: ImportError.

- [ ] **Step 3: Write the router**

```python
"""User memory API router."""
import logging
from fastapi import APIRouter, HTTPException, Request

from datametronome_podium.core.database import get_executor
from datametronome_podium.features.user_memory.repo import UserMemoryRepo
from datametronome_podium.features.user_memory.schemas import (
    UserMemoryResponse,
    UserMemoryProfileResponse,
    UserMemoryCreate,
    UserMemoryUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _repo() -> UserMemoryRepo:
    return UserMemoryRepo(get_executor())


def _get_user_id(request: Request) -> str:
    """Extract user_id from request state (set by auth middleware)."""
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        return user.get("id") or user.get("username") or "anonymous"
    return "anonymous"


# --- Profile ---


@router.get("/profile", response_model=UserMemoryProfileResponse)
async def get_profile(request: Request):
    """Get the precomputed memory profile (what agents see)."""
    user_id = _get_user_id(request)
    profile = await _repo().get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="No memory profile found")
    return profile


# --- List / Search ---


@router.get("", response_model=list[UserMemoryResponse])
async def list_memories(
    request: Request,
    category: str | None = None,
    active: bool | None = None,
    q: str | None = None,
):
    """List memories, optionally filtered."""
    user_id = _get_user_id(request)
    active_only = active if active is not None else True
    return await _repo().search_memories(
        user_id, q=q, category=category, active_only=active_only
    )


# --- Single memory ---


@router.get("/{memory_id}", response_model=UserMemoryResponse)
async def get_memory(memory_id: str, request: Request):
    """Get a single memory."""
    user_id = _get_user_id(request)
    mem = await _repo().get_memory(memory_id)
    if not mem or mem["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    return mem


# --- Create (manual) ---


@router.post("", response_model=UserMemoryResponse, status_code=201)
async def create_memory(body: UserMemoryCreate, request: Request):
    """Manually add a memory."""
    user_id = _get_user_id(request)
    repo = _repo()
    mem_id = await repo.create_memory(
        user_id=user_id,
        category=body.category,
        content=body.content,
        confidence=body.confidence,
    )
    mem = await repo.get_memory(mem_id)

    # Trigger async profile rebuild
    try:
        from datametronome_podium.tasks.user_memory_tasks import rebuild_user_profile
        rebuild_user_profile.delay(user_id)
    except Exception:
        logger.warning("Failed to dispatch profile rebuild for user %s", user_id)

    return mem


# --- Update ---


@router.patch("/{memory_id}", response_model=UserMemoryResponse)
async def update_memory(memory_id: str, body: UserMemoryUpdate, request: Request):
    """Edit a memory's content or deactivate it."""
    user_id = _get_user_id(request)
    repo = _repo()
    mem = await repo.get_memory(memory_id)
    if not mem or mem["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")

    update_data = body.model_dump(exclude_unset=True)
    if "active" in update_data:
        update_data["active"] = 1 if update_data["active"] else 0

    from datetime import datetime, timezone
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    await repo.update_memory(memory_id, update_data)

    # Trigger async profile rebuild
    try:
        from datametronome_podium.tasks.user_memory_tasks import rebuild_user_profile
        rebuild_user_profile.delay(user_id)
    except Exception:
        logger.warning("Failed to dispatch profile rebuild for user %s", user_id)

    return await repo.get_memory(memory_id)


# --- Delete ---


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, request: Request):
    """Hard delete a memory."""
    user_id = _get_user_id(request)
    repo = _repo()
    mem = await repo.get_memory(memory_id)
    if not mem or mem["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    await repo.delete_memory(memory_id)

    # Trigger async profile rebuild
    try:
        from datametronome_podium.tasks.user_memory_tasks import rebuild_user_profile
        rebuild_user_profile.delay(user_id)
    except Exception:
        logger.warning("Failed to dispatch profile rebuild for user %s", user_id)


# --- Rebuild ---


@router.post("/rebuild", status_code=202)
async def rebuild_profile(request: Request):
    """Force-rebuild the profile from current active memories."""
    user_id = _get_user_id(request)
    try:
        from datametronome_podium.tasks.user_memory_tasks import rebuild_user_profile
        rebuild_user_profile.delay(user_id)
        return {"status": "queued", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch rebuild: {e}")
```

- [ ] **Step 4: Wire router in api.py**

Add to `api/v1/api.py`:

Import (after line 14):
```python
from datametronome_podium.features.user_memory.router import router as user_memory_router
```

Include (after line 35):
```python
api_router.include_router(user_memory_router, prefix="/user/memory", tags=["user memory"])
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_user_memory_router.py -v --timeout=10`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add features/user_memory/router.py api/v1/api.py tests/test_user_memory_router.py
git commit -m "feat(memory): add user memory API endpoints + wire router"
```

---

## Chunk 4: Orchestrator + Agent Integration

### Task 7: Router Agent — Add Memory Intent

**Files:**
- Modify: `datametronome/podium/datametronome_podium/services/agents/router.py`

- [ ] **Step 1: Add "memory" to VALID_INTENTS**

At line 15, change:
```python
VALID_INTENTS = Literal["quick", "config", "investigation", "report", "exploration", "insight"]
```
to:
```python
VALID_INTENTS = Literal["quick", "config", "investigation", "report", "exploration", "insight", "memory"]
```

- [ ] **Step 2: Update router system prompt**

Add to `_ROUTER_SYSTEM_PROMPT` intent definitions (after line 43):
```
- memory: user asks about what you know about them, what was investigated, their profile, or past findings
```

- [ ] **Step 3: Commit**

```bash
git add services/agents/router.py
git commit -m "feat(memory): add 'memory' intent to router agent"
```

---

### Task 8: Agent Builders — Accept user_profile kwarg

**Files:**
- Modify: `datametronome/podium/datametronome_podium/services/agents/config.py`
- Modify: `datametronome/podium/datametronome_podium/services/agents/investigation.py`
- Modify: `datametronome/podium/datametronome_podium/services/agents/report.py`
- Modify: `datametronome/podium/datametronome_podium/services/agents/insight.py`

- [ ] **Step 1: Update config.py**

Change `build_config_agent` (line 24-30):
```python
def build_config_agent(model: Model, *, user_profile: str | None = None) -> Agent:
    """Build the config agent with the given model."""
    prompt = _SYSTEM_PROMPT
    if user_profile:
        prompt = f"{_SYSTEM_PROMPT}\n\n{user_profile}"
    return Agent(
        model=model,
        system_prompt=prompt,
        tools=ALL_TOOLS,
    )
```

- [ ] **Step 2: Update investigation.py**

Same pattern — add `user_profile: str | None = None` kwarg, append to system prompt if provided.

- [ ] **Step 3: Update report.py**

Same pattern.

- [ ] **Step 4: Update insight.py**

Change `build_insight_agent` (line 78-96) — add `user_profile` to the `_build_system_prompt` call:

```python
def build_insight_agent(
    model: Model,
    *,
    archetype_context: dict | None = None,
    profile_context: dict | None = None,
    historical_context: str | None = None,
    user_profile: str | None = None,
) -> Agent:
    """Build the InsightAgent with dynamic context for chat interactions."""
    system_prompt = _build_system_prompt(
        archetype_context=archetype_context,
        profile_context=profile_context,
        historical_context=historical_context,
    )
    if user_profile:
        system_prompt = f"{system_prompt}\n\n{user_profile}"

    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=INSIGHT_TOOLS,
    )
```

- [ ] **Step 5: Commit**

```bash
git add services/agents/config.py services/agents/investigation.py services/agents/report.py services/agents/insight.py
git commit -m "feat(memory): add user_profile kwarg to all agent builders"
```

---

### Task 9: Orchestrator — Load Profile + Memory Intent

**Files:**
- Modify: `datametronome/podium/datametronome_podium/services/orchestrator.py`
- Create: `datametronome/podium/tests/test_user_memory_orchestrator.py`

- [ ] **Step 1: Write orchestrator integration tests**

```python
"""Tests for user memory integration in the orchestrator."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_memory_intent_returns_recall():
    """When router classifies as 'memory', orchestrator returns recall directly."""
    from datametronome_podium.services.orchestrator import run_chat
    from datametronome_podium.services.agents.router import RoutingDecision

    decision = RoutingDecision(
        intent="memory", mode="single", agents=["report"],
        reasoning="User asks about their profile",
    )

    mock_router_result = MagicMock()
    mock_router_result.output = decision

    with patch("datametronome_podium.services.orchestrator._get_router_agent") as mock_router:
        mock_router.return_value.run = AsyncMock(return_value=mock_router_result)
        with patch("datametronome_podium.services.orchestrator._load_user_profile", return_value=None):
            with patch("datametronome_podium.services.orchestrator._handle_memory_recall", return_value="Here's what I know..."):
                result = await run_chat(
                    "What do you know about me?",
                    [],
                    user_id="user-1",
                )
    assert result["intent"] == "memory"
    assert "what I know" in result["message"]


@pytest.mark.asyncio
async def test_profile_injected_into_agent():
    """Profile text is passed to agent builder when available."""
    from datametronome_podium.services.orchestrator import run_chat
    from datametronome_podium.services.agents.router import RoutingDecision

    decision = RoutingDecision(
        intent="report", mode="single", agents=["report"],
        reasoning="Status request",
    )

    mock_router_result = MagicMock()
    mock_router_result.output = decision

    mock_agent_result = MagicMock()
    mock_agent_result.output = "Here is your report."

    profile_text = "USER CONTEXT: Focuses on orders table."

    with patch("datametronome_podium.services.orchestrator._get_router_agent") as mock_router:
        mock_router.return_value.run = AsyncMock(return_value=mock_router_result)
        with patch("datametronome_podium.services.orchestrator._load_user_profile", return_value=profile_text):
            with patch("datametronome_podium.services.orchestrator._get_report_agent") as mock_builder:
                mock_agent = AsyncMock()
                mock_agent.run = AsyncMock(return_value=mock_agent_result)
                mock_builder.return_value = mock_agent
                result = await run_chat(
                    "Give me a status report",
                    [],
                    user_id="user-1",
                )

    # Verify the agent builder was called with user_profile
    mock_builder.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_user_memory_orchestrator.py -v --timeout=10`
Expected: ImportError or AttributeError (functions don't exist yet).

- [ ] **Step 3: Modify orchestrator.py**

Add imports at top:
```python
from datametronome_podium.features.user_memory.repo import UserMemoryRepo
from datametronome_podium.features.user_memory.service import UserMemoryService
from datametronome_podium.core.database import get_executor
```

Add helper functions (before `run_chat`):
```python
async def _load_user_profile(user_id: str | None) -> str | None:
    """Load and format the user's memory profile for system prompt injection."""
    if not user_id:
        return None
    try:
        repo = UserMemoryRepo(get_executor())
        service = UserMemoryService(repo=repo)
        profile = await repo.get_profile(user_id)
        return service.format_profile_for_prompt(profile)
    except Exception as e:
        logger.warning("Failed to load user memory profile: %s", e)
        return None


async def _handle_memory_recall(user_id: str) -> str:
    """Handle a 'memory' intent — return formatted recall response."""
    try:
        repo = UserMemoryRepo(get_executor())
        service = UserMemoryService(repo=repo)
        return await service.format_recall(user_id)
    except Exception as e:
        logger.warning("Failed to handle memory recall: %s", e)
        return "Sorry, I couldn't retrieve your memory profile right now."
```

Modify `run_chat` — add profile loading after line 145 (before routing):
```python
user_profile_text = await _load_user_profile(user_id)
```

Add memory intent early return after the routing decision (before the dispatch switch at line 188):
```python
if decision.intent == "memory":
    response_message = await _handle_memory_recall(user_id)
    if checkpoint_id:
        await update_checkpoint(checkpoint_id, status="completed")
    return {
        "message": response_message,
        "intent": decision.intent,
        "mode": "single",
        "agents": [],
        "model": "pydantic-ai",
    }
```

Update `_fallback_route` — add memory keywords (after line 60):
```python
if any(w in msg for w in ["what do you know about me", "what did we find", "my memory", "show my profile"]):
    return RoutingDecision(
        intent="memory", mode="single", agents=["report"],
        reasoning="Fallback: detected memory keywords",
    )
```

Update agent builder calls in `_get_config_agent`, `_get_investigation_agent`, `_get_report_agent`, `_get_insight_agent` to accept and forward `user_profile`. The simplest approach: modify `_get_agent_builder` to return a factory that accepts `user_profile`:

```python
def _get_agent_builder(agent_type: str, user_profile: str | None = None):
    """Resolve agent builder by name, injecting user profile."""
    def _build_config():
        return build_config_agent(build_model_from_settings(), user_profile=user_profile)

    def _build_investigation():
        return build_investigation_agent(build_model_from_settings(), user_profile=user_profile)

    def _build_report():
        return build_report_agent(build_model_from_settings(), user_profile=user_profile)

    def _build_insight():
        from datametronome_podium.services.agent_factory import build_heavy_model_from_settings
        return build_insight_agent(build_heavy_model_from_settings(), user_profile=user_profile)

    builders = {
        "config": _build_config,
        "investigation": _build_investigation,
        "report": _build_report,
        "insight": _build_insight,
    }
    return builders.get(agent_type, _build_report)
```

Pass `user_profile_text` to `_get_agent_builder` in `_run_single`, `_run_chain`, and `_run_parallel`. Add `user_profile` parameter to each runner function signature.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_user_memory_orchestrator.py tests/test_orchestrator.py -v --timeout=10`
Expected: All PASS (including existing orchestrator tests — no regressions).

- [ ] **Step 5: Commit**

```bash
git add services/orchestrator.py tests/test_user_memory_orchestrator.py
git commit -m "feat(memory): integrate user profile into orchestrator + memory intent"
```

---

### Task 10: Chat Endpoint — Eager Upsert

**Files:**
- Modify: `datametronome/podium/datametronome_podium/api/v1/endpoints/chat.py`

- [ ] **Step 1: Add upsert after user message save**

After line 281 (after user message saved successfully), add:

```python
# Track conversation for memory extraction
try:
    await db.execute(
        "INSERT INTO conversation_extraction_status (conversation_id, user_id, status) "
        "VALUES (?, ?, 'idle') ON CONFLICT (conversation_id) DO NOTHING",
        [conversation_id, user_id],
    )
except Exception:
    pass  # Non-critical — extraction will still work, just with a delayed first discovery
```

- [ ] **Step 2: Run existing chat tests to verify no regressions**

Run: `.venv/bin/python -m pytest tests/ -k "chat" -v --timeout=10`
Expected: All existing chat tests PASS.

- [ ] **Step 3: Commit**

```bash
git add api/v1/endpoints/chat.py
git commit -m "feat(memory): add eager upsert to conversation_extraction_status in chat endpoint"
```

---

## Chunk 5: Full Integration Test + Existing Test Suite

### Task 11: Full Integration Test

**Files:**
- Create: `datametronome/podium/tests/test_user_memory_integration.py`

- [ ] **Step 1: Write end-to-end test**

```python
"""End-to-end integration test for the user memory pipeline."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from datametronome_podium.features.user_memory.schemas import MemoryExtraction


@pytest.mark.asyncio
async def test_full_memory_pipeline():
    """Simulates: conversation → extraction → profile → agent injection."""
    from datametronome_podium.features.user_memory.service import UserMemoryService
    from datametronome_podium.features.user_memory.repo import UserMemoryRepo
    from datametronome_podium.core.database import get_executor

    repo = UserMemoryRepo(get_executor())
    service = UserMemoryService(repo=repo)

    # Simulate a conversation
    conversation = [
        {"role": "user", "content": "Show me the orders table in my e-commerce database"},
        {"role": "assistant", "content": "Here's the orders table with 50K rows..."},
        {"role": "user", "content": "I know SQL well, can you show me the JOIN between orders and customers?"},
        {"role": "assistant", "content": "Here's the JOIN query..."},
        {"role": "user", "content": "The NULL rate in customers.email looks high, I think it's from our migration last week"},
        {"role": "assistant", "content": "Good catch, the NULL rate is 15%..."},
    ]

    mock_extractions = [
        MemoryExtraction(category="domain_focus", content="Works with orders and customers tables in e-commerce database", confidence=0.9, action="new", existing_memory_id=None),
        MemoryExtraction(category="expertise", content="Strong SQL skills — writes JOINs confidently", confidence=0.85, action="new", existing_memory_id=None),
        MemoryExtraction(category="investigation", content="NULL rate in customers.email (15%) attributed to recent migration", confidence=0.8, action="new", existing_memory_id=None),
    ]

    with patch.object(service, "_call_extraction_llm", return_value=mock_extractions):
        with patch.object(service, "_call_rebuild_llm", return_value={
            "domain_summary": "Focuses on orders and customers tables in an e-commerce database.",
            "expertise_summary": "Strong SQL skills — writes JOINs confidently.",
            "investigation_summary": "Investigated NULL rate in customers.email (15%), concluded it's from a recent migration.",
        }):
            await service.extract_and_rebuild("conv-e2e", "user-e2e", conversation)

    # Verify memories were created
    memories = await repo.list_active_memories("user-e2e")
    assert len(memories) == 3
    categories = {m["category"] for m in memories}
    assert categories == {"domain_focus", "expertise", "investigation"}

    # Verify profile was built
    profile = await repo.get_profile("user-e2e")
    assert profile is not None
    assert "orders" in profile["domain_summary"].lower()
    assert "sql" in profile["expertise_summary"].lower()

    # Verify profile formats correctly for prompt injection
    prompt_text = service.format_profile_for_prompt(profile)
    assert prompt_text is not None
    assert "USER CONTEXT" in prompt_text
    assert "Domain focus" in prompt_text

    # Verify recall formatting
    recall = await service.format_recall("user-e2e")
    assert "Domain Focus" in recall
    assert "orders" in recall.lower()
```

- [ ] **Step 2: Run integration test**

Run: `.venv/bin/python -m pytest tests/test_user_memory_integration.py -v --timeout=30`
Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v --timeout=30`
Expected: All existing tests PASS + all new memory tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_user_memory_integration.py
git commit -m "test(memory): add end-to-end integration test for memory pipeline"
```

---

### Task 12: Final Verification

- [ ] **Step 1: Run full test suite with timeout**

Run: `.venv/bin/python -m pytest tests/ --timeout=10 -v`
Expected: All PASS, no hangs.

- [ ] **Step 2: Verify migration runs clean in Docker**

Run: `docker-compose exec podium alembic upgrade head`
Expected: Migration applies cleanly.

- [ ] **Step 3: Verify app starts**

Run: `docker-compose up -d && docker-compose logs podium | tail -20`
Expected: App starts without import errors.

- [ ] **Step 4: Final commit with any fixes**

If any fixes were needed, commit them now.
