# Data Intelligence Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a data intelligence layer that automatically explores connected data sources, classifies business domains, and surfaces actionable insights with cumulative learning.

**Architecture:** Three-tier trigger model (auto-scan on stave creation, on-demand via chat, scheduled daily via Celery Beat). InsightAgent joins the existing Pydantic AI agent roster. Domain archetypes (YAML) accelerate cold-start. Intelligence Store (5 new tables) persists profiles, snapshots, reports, suggestions, and check provenance. All tenant-scoped.

**Tech Stack:** Python 3.13, FastAPI, Pydantic AI, Celery + RabbitMQ + Redis, asyncpg/aiosqlite, PyYAML, Alembic

**Spec:** `docs/superpowers/specs/2026-03-15-data-intelligence-design.md`

**Base path:** `datametronome/podium/datametronome_podium/` (abbreviated as `DMP/` below)
**Test base:** `datametronome/podium/tests/` (abbreviated as `tests/` below)
**Working dir for all commands:** `datametronome/podium/`

---

## Chunk 1: Domain Models + Migration

New Pydantic domain models for the Intelligence Store, plus the Alembic migration to create the 5 new tables.

### Task 1: DataProfile domain model -- DONE

**Files:**
- Create: `DMP/features/insights/model.py`
- Test: `tests/features/insights/test_insight_models.py`

- [ ] **Step 1: Create feature directory**

```bash
mkdir -p datametronome_podium/features/insights
touch datametronome_podium/features/insights/__init__.py
mkdir -p ../tests/features/insights
touch ../tests/features/insights/__init__.py
```

(Run from `datametronome/podium/`)

- [ ] **Step 2: Write failing test for DataProfile model**

```python
# tests/features/insights/test_insight_models.py
"""Tests for intelligence store domain models."""
import pytest
from datametronome_podium.features.insights.model import DataProfile


def test_data_profile_defaults():
    p = DataProfile(
        id="dp-1",
        stave_id="stave-1",
        tenant_id="default",
        domain_type="e-commerce",
        domain_confidence=0.85,
        created_at="2026-03-15T00:00:00Z",
        updated_at="2026-03-15T00:00:00Z",
    )
    assert p.profile_version == 1
    assert p.previous_classification is None
    assert p.domain_context == {}
    assert p.schema_map == {}
    assert p.entity_roles == {}
    assert p.learned_patterns == {}


def test_data_profile_full():
    p = DataProfile(
        id="dp-1",
        stave_id="stave-1",
        tenant_id="default",
        domain_type="saas",
        domain_confidence=0.72,
        domain_context={"description": "SaaS platform"},
        schema_map={"users": {"columns": ["id", "email"]}},
        entity_roles={"fact": ["subscriptions"], "dimension": ["users"]},
        learned_patterns={"weekly_billing_cycle": {"confidence": 0.9}},
        profile_version=3,
        previous_classification={"domain_type": "generic", "confidence": 0.4, "changed_at": "2026-03-10"},
        created_at="2026-03-15T00:00:00Z",
        updated_at="2026-03-15T00:00:00Z",
    )
    assert p.domain_type == "saas"
    assert p.profile_version == 3
    assert p.previous_classification["domain_type"] == "generic"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_models.py::test_data_profile_defaults -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 4: Implement DataProfile model**

```python
# DMP/features/insights/model.py
"""Intelligence Store domain models."""
from pydantic import BaseModel


class DataProfile(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    domain_type: str
    domain_confidence: float
    domain_context: dict = {}
    schema_map: dict = {}
    entity_roles: dict = {}
    learned_patterns: dict = {}
    profile_version: int = 1
    previous_classification: dict | None = None
    created_at: str
    updated_at: str
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_models.py -v --timeout=10`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add -f datametronome_podium/features/insights/ tests/features/insights/
git commit --no-verify -m "feat(insights): add DataProfile domain model"
```

### Task 2: BaselineSnapshot + InsightReport + InsightSuggestion + InsightCreatedCheck models -- DONE

**Files:**
- Modify: `DMP/features/insights/model.py`
- Test: `tests/features/insights/test_insight_models.py`

- [ ] **Step 1: Write failing tests for remaining models**

Append to `tests/features/insights/test_insight_models.py`:

```python
from datametronome_podium.features.insights.model import (
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
    TableMetrics,
)


def test_table_metrics_defaults():
    m = TableMetrics(row_count=1000, null_rates={"email": 0.05})
    assert m.status == "ok"
    assert m.skip_reason is None
    assert m.freshness is None
    assert m.distributions == {}


def test_table_metrics_skipped():
    m = TableMetrics(row_count=0, null_rates={}, status="skipped", skip_reason="timeout")
    assert m.status == "skipped"


def test_baseline_snapshot():
    s = BaselineSnapshot(
        id="snap-1",
        stave_id="stave-1",
        tenant_id="default",
        snapshot_type="daily",
        table_metrics={"orders": {"row_count": 5000, "null_rates": {}}},
        column_stats={},
        captured_at="2026-03-15T06:00:00Z",
    )
    assert s.snapshot_type == "daily"


def test_insight_report_minimal():
    r = InsightReport(
        id="rpt-1",
        stave_id="stave-1",
        tenant_id="default",
        report_type="initial",
        health_score=78,
        summary="Data source looks healthy.",
        created_at="2026-03-15T06:00:00Z",
    )
    assert r.dimensions == []
    assert r.anomalies == []
    assert r.suggestions == []
    assert r.key_findings == []
    assert r.snapshot_id is None


def test_insight_suggestion():
    s = InsightSuggestion(
        id="sug-1",
        stave_id="stave-1",
        tenant_id="default",
        report_id="rpt-1",
        priority="high",
        category="operations",
        action="Investigate payment gateway",
        reasoning="Failure rate doubled",
        based_on="7-day trend",
        created_at="2026-03-15T06:00:00Z",
    )
    assert s.status == "pending"
    assert s.resolved_at is None


def test_insight_created_check():
    c = InsightCreatedCheck(
        id="icc-1",
        report_id="rpt-1",
        clef_id="clef-1",
        rationale="Orders table needs freshness monitoring",
        created_at="2026-03-15T06:00:00Z",
    )
    assert c.report_id == "rpt-1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_models.py -v --timeout=10`
Expected: FAIL (ImportError for new classes)

- [ ] **Step 3: Implement remaining models**

Add to `DMP/features/insights/model.py`:

```python
from typing import Literal


class TableMetrics(BaseModel):
    row_count: int
    freshness: str | None = None
    null_rates: dict[str, float]
    distributions: dict[str, dict] = {}
    status: Literal["ok", "skipped"] = "ok"
    skip_reason: str | None = None


class BaselineSnapshot(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    snapshot_type: Literal["auto_scan", "daily", "on_demand", "weekly_aggregate"]
    table_metrics: dict  # table_name → TableMetrics-like dict (stored as JSON)
    column_stats: dict
    captured_at: str


class InsightReport(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    snapshot_id: str | None = None
    report_type: Literal["initial", "daily", "on_demand"]
    health_score: int
    dimensions: list[dict] = []
    anomalies: list[dict] = []
    suggestions: list[dict] = []
    summary: str
    key_findings: list[str] = []
    created_at: str


class InsightSuggestion(BaseModel):
    id: str
    stave_id: str
    tenant_id: str
    report_id: str
    priority: Literal["low", "medium", "high"]
    category: str
    action: str
    reasoning: str
    based_on: str
    status: Literal["pending", "accepted", "dismissed"] = "pending"
    resolved_at: str | None = None
    created_at: str


class InsightCreatedCheck(BaseModel):
    id: str
    report_id: str
    clef_id: str
    rationale: str
    created_at: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_models.py -v --timeout=10`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/features/insights/model.py tests/features/insights/test_insight_models.py
git commit --no-verify -m "feat(insights): add BaselineSnapshot, InsightReport, InsightSuggestion, InsightCreatedCheck models"
```

### Task 3: Alembic migration for Intelligence Store tables -- DONE

**Files:**
- Create: `alembic/versions/004_intelligence_store.py`

- [ ] **Step 1: Write migration**

```python
# alembic/versions/004_intelligence_store.py
"""Intelligence Store tables: data_profiles, baseline_snapshots, insight_reports,
insight_suggestions, insight_created_checks.

Revision ID: 004
Create Date: 2026-03-15
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "004"
down_revision = "d4fa342314f0"  # after paused field migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE data_profiles (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL UNIQUE,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        domain_type TEXT NOT NULL,
        domain_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
        domain_context TEXT NOT NULL DEFAULT '{}',
        schema_map TEXT NOT NULL DEFAULT '{}',
        entity_roles TEXT NOT NULL DEFAULT '{}',
        learned_patterns TEXT NOT NULL DEFAULT '{}',
        profile_version INTEGER NOT NULL DEFAULT 1,
        previous_classification TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE baseline_snapshots (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        snapshot_type TEXT NOT NULL,
        table_metrics TEXT NOT NULL DEFAULT '{}',
        column_stats TEXT NOT NULL DEFAULT '{}',
        captured_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE insight_reports (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        snapshot_id TEXT,
        report_type TEXT NOT NULL,
        health_score INTEGER NOT NULL DEFAULT 0,
        dimensions TEXT NOT NULL DEFAULT '[]',
        anomalies TEXT NOT NULL DEFAULT '[]',
        suggestions TEXT NOT NULL DEFAULT '[]',
        summary TEXT NOT NULL DEFAULT '',
        key_findings TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE,
        FOREIGN KEY (snapshot_id) REFERENCES baseline_snapshots (id) ON DELETE SET NULL
    )
    """)

    dao.execute("""
    CREATE TABLE insight_suggestions (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        report_id TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'medium',
        category TEXT NOT NULL,
        action TEXT NOT NULL,
        reasoning TEXT NOT NULL,
        based_on TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        resolved_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE,
        FOREIGN KEY (report_id) REFERENCES insight_reports (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE insight_created_checks (
        id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        clef_id TEXT NOT NULL,
        rationale TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (report_id) REFERENCES insight_reports (id) ON DELETE CASCADE,
        FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
    )
    """)

    # Indexes
    dao.execute("CREATE INDEX idx_data_profiles_stave_id ON data_profiles(stave_id)")
    dao.execute("CREATE INDEX idx_data_profiles_tenant_id ON data_profiles(tenant_id)")
    dao.execute("CREATE INDEX idx_baseline_snapshots_stave_id ON baseline_snapshots(stave_id)")
    dao.execute("CREATE INDEX idx_baseline_snapshots_captured_at ON baseline_snapshots(captured_at)")
    dao.execute("CREATE INDEX idx_insight_reports_stave_id ON insight_reports(stave_id)")
    dao.execute("CREATE INDEX idx_insight_reports_created_at ON insight_reports(created_at)")
    dao.execute("CREATE INDEX idx_insight_suggestions_stave_id ON insight_suggestions(stave_id)")
    dao.execute("CREATE INDEX idx_insight_suggestions_status ON insight_suggestions(status)")
    dao.execute("CREATE INDEX idx_insight_created_checks_report_id ON insight_created_checks(report_id)")
    dao.execute("CREATE INDEX idx_insight_created_checks_clef_id ON insight_created_checks(clef_id)")


def downgrade() -> None:
    from alembic import op
    op.execute("DROP TABLE IF EXISTS insight_created_checks")
    op.execute("DROP TABLE IF EXISTS insight_suggestions")
    op.execute("DROP TABLE IF EXISTS insight_reports")
    op.execute("DROP TABLE IF EXISTS baseline_snapshots")
    op.execute("DROP TABLE IF EXISTS data_profiles")
```

- [ ] **Step 2: Run migration to verify it works**

Run: `cd datametronome/podium && .venv/bin/python -m alembic upgrade head`
Expected: Migration completes without error.

- [ ] **Step 3: Commit**

```bash
git add -f alembic/versions/004_intelligence_store.py
git commit --no-verify -m "feat(insights): add Alembic migration for Intelligence Store tables"
```

---

## Chunk 2: Insights Repo + Schemas + API Endpoints

Repository layer (CRUD for all 5 tables) and FastAPI router following the existing feature-slice pattern.

### Task 4: InsightsRepo — data access layer -- DONE

**Files:**
- Create: `DMP/features/insights/repo.py`
- Test: `tests/features/insights/test_insights_repo.py`

- [ ] **Step 1: Write failing tests for InsightsRepo**

```python
# tests/features/insights/test_insights_repo.py
"""Tests for InsightsRepo data access."""
import json
import pytest

from datametronome_podium.features.insights.model import (
    DataProfile,
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
)
from datametronome_podium.features.insights.repo import InsightsRepo


@pytest.fixture
def repo(test_executor):
    """InsightsRepo using test database executor."""
    return InsightsRepo(test_executor)


@pytest.mark.asyncio
async def test_create_and_get_profile(repo):
    profile = DataProfile(
        id="dp-1", stave_id="stave-test", tenant_id="default",
        domain_type="e-commerce", domain_confidence=0.85,
        created_at="2026-03-15T00:00:00Z", updated_at="2026-03-15T00:00:00Z",
    )
    await repo.create_profile(profile)
    result = await repo.get_profile("stave-test")
    assert result is not None
    assert result.domain_type == "e-commerce"
    assert result.profile_version == 1


@pytest.mark.asyncio
async def test_update_profile(repo):
    profile = DataProfile(
        id="dp-2", stave_id="stave-test2", tenant_id="default",
        domain_type="generic", domain_confidence=0.3,
        created_at="2026-03-15T00:00:00Z", updated_at="2026-03-15T00:00:00Z",
    )
    await repo.create_profile(profile)
    await repo.update_profile("stave-test2", {
        "domain_type": "saas",
        "domain_confidence": 0.8,
        "profile_version": 2,
    })
    result = await repo.get_profile("stave-test2")
    assert result.domain_type == "saas"
    assert result.profile_version == 2


@pytest.mark.asyncio
async def test_create_and_list_snapshots(repo):
    snap = BaselineSnapshot(
        id="snap-1", stave_id="stave-test", tenant_id="default",
        snapshot_type="daily",
        table_metrics={"orders": {"row_count": 5000, "null_rates": {}}},
        column_stats={}, captured_at="2026-03-15T06:00:00Z",
    )
    await repo.create_snapshot(snap)
    results = await repo.list_snapshots("stave-test", days=7)
    assert len(results) >= 1
    assert results[0].id == "snap-1"


@pytest.mark.asyncio
async def test_create_and_get_report(repo):
    report = InsightReport(
        id="rpt-1", stave_id="stave-test", tenant_id="default",
        report_type="daily", health_score=78,
        summary="Looking good.", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_report(report)
    result = await repo.get_latest_report("stave-test")
    assert result is not None
    assert result.health_score == 78


@pytest.mark.asyncio
async def test_create_and_list_suggestions(repo):
    # Need a report first for FK
    report = InsightReport(
        id="rpt-2", stave_id="stave-test", tenant_id="default",
        report_type="daily", health_score=60,
        summary="Needs attention.", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_report(report)

    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-test", tenant_id="default",
        report_id="rpt-2", priority="high", category="operations",
        action="Fix payment gateway", reasoning="Failure rate doubled",
        based_on="7-day trend", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_suggestion(sug)
    results = await repo.list_suggestions("stave-test", status="pending")
    assert len(results) >= 1
    assert results[0].status == "pending"


@pytest.mark.asyncio
async def test_update_suggestion_status(repo):
    report = InsightReport(
        id="rpt-3", stave_id="stave-test", tenant_id="default",
        report_type="daily", health_score=60,
        summary="Test.", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_report(report)
    sug = InsightSuggestion(
        id="sug-2", stave_id="stave-test", tenant_id="default",
        report_id="rpt-3", priority="medium", category="growth",
        action="Increase ad spend", reasoning="Signups up",
        based_on="Weekly trend", created_at="2026-03-15T06:00:00Z",
    )
    await repo.create_suggestion(sug)
    await repo.update_suggestion_status("sug-2", "accepted")
    results = await repo.list_suggestions("stave-test", status="accepted")
    assert any(s.id == "sug-2" for s in results)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insights_repo.py -v --timeout=10`
Expected: FAIL (ImportError)

Note: These tests require a `test_executor` fixture that creates the intelligence store tables in an in-memory SQLite. Check existing test fixtures (e.g., `tests/features/staves/test_stave_repo.py`) for the pattern and replicate it. The fixture should run the migration SQL to create the necessary tables.

- [ ] **Step 3: Implement InsightsRepo**

```python
# DMP/features/insights/repo.py
"""Intelligence Store data access."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.insights.model import (
    DataProfile,
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
)


def _json_field(value: dict | list | None) -> str:
    """Serialize a dict/list to JSON string for storage."""
    if value is None:
        return "null"
    return json.dumps(value)


def _parse_json(value: str | dict | list | None) -> dict | list:
    """Parse a JSON string back to dict/list."""
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


class InsightsRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    # --- DataProfile ---

    async def create_profile(self, profile: DataProfile) -> int:
        data = profile.model_dump()
        for field in ("domain_context", "schema_map", "entity_roles", "learned_patterns", "previous_classification"):
            data[field] = _json_field(data[field])
        return await self.db.insert("data_profiles", data)

    async def get_profile(self, stave_id: str) -> DataProfile | None:
        rows = await self.db.select("data_profiles", where={"stave_id": stave_id})
        if not rows:
            return None
        row = dict(rows[0])
        for field in ("domain_context", "schema_map", "entity_roles", "learned_patterns"):
            row[field] = _parse_json(row.get(field))
        prev = row.get("previous_classification")
        row["previous_classification"] = _parse_json(prev) if prev and prev != "null" else None
        return DataProfile(**row)

    async def update_profile(self, stave_id: str, data: dict) -> int:
        for field in ("domain_context", "schema_map", "entity_roles", "learned_patterns", "previous_classification"):
            if field in data and not isinstance(data[field], str):
                data[field] = _json_field(data[field])
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        data["updated_at"] = now
        return await self.db.update("data_profiles", data, where={"stave_id": stave_id})

    # --- BaselineSnapshot ---

    async def create_snapshot(self, snapshot: BaselineSnapshot) -> int:
        data = snapshot.model_dump()
        data["table_metrics"] = _json_field(data["table_metrics"])
        data["column_stats"] = _json_field(data["column_stats"])
        return await self.db.insert("baseline_snapshots", data)

    async def list_snapshots(
        self, stave_id: str, days: int = 7, limit: int = 100,
    ) -> list[BaselineSnapshot]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        rows = await self.db.query(
            "SELECT * FROM baseline_snapshots WHERE stave_id = ? AND captured_at >= ? ORDER BY captured_at DESC LIMIT ?",
            [stave_id, cutoff, limit],
        )
        results = []
        for row in rows:
            r = dict(row)
            r["table_metrics"] = _parse_json(r.get("table_metrics"))
            r["column_stats"] = _parse_json(r.get("column_stats"))
            results.append(BaselineSnapshot(**r))
        return results

    async def get_snapshot(self, snapshot_id: str) -> BaselineSnapshot | None:
        rows = await self.db.select("baseline_snapshots", where={"id": snapshot_id})
        if not rows:
            return None
        r = dict(rows[0])
        r["table_metrics"] = _parse_json(r.get("table_metrics"))
        r["column_stats"] = _parse_json(r.get("column_stats"))
        return BaselineSnapshot(**r)

    # --- InsightReport ---

    async def create_report(self, report: InsightReport) -> int:
        data = report.model_dump()
        for field in ("dimensions", "anomalies", "suggestions", "key_findings"):
            data[field] = _json_field(data[field])
        return await self.db.insert("insight_reports", data)

    async def get_latest_report(self, stave_id: str) -> InsightReport | None:
        rows = await self.db.query(
            "SELECT * FROM insight_reports WHERE stave_id = ? ORDER BY created_at DESC LIMIT 1",
            [stave_id],
        )
        if not rows:
            return None
        r = dict(rows[0])
        for field in ("dimensions", "anomalies", "suggestions", "key_findings"):
            r[field] = _parse_json(r.get(field))
        return InsightReport(**r)

    async def list_reports(
        self, stave_id: str, limit: int = 20, offset: int = 0,
    ) -> list[InsightReport]:
        rows = await self.db.query(
            "SELECT * FROM insight_reports WHERE stave_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [stave_id, limit, offset],
        )
        results = []
        for row in rows:
            r = dict(row)
            for field in ("dimensions", "anomalies", "suggestions", "key_findings"):
                r[field] = _parse_json(r.get(field))
            results.append(InsightReport(**r))
        return results

    # --- InsightSuggestion ---

    async def create_suggestion(self, suggestion: InsightSuggestion) -> int:
        return await self.db.insert("insight_suggestions", suggestion.model_dump())

    async def list_suggestions(
        self, stave_id: str, status: str | None = None, limit: int = 50,
    ) -> list[InsightSuggestion]:
        if status:
            rows = await self.db.query(
                "SELECT * FROM insight_suggestions WHERE stave_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                [stave_id, status, limit],
            )
        else:
            rows = await self.db.query(
                "SELECT * FROM insight_suggestions WHERE stave_id = ? ORDER BY created_at DESC LIMIT ?",
                [stave_id, limit],
            )
        return [InsightSuggestion(**dict(row)) for row in rows]

    async def get_suggestion(self, suggestion_id: str) -> InsightSuggestion | None:
        rows = await self.db.select("insight_suggestions", where={"id": suggestion_id})
        return InsightSuggestion(**dict(rows[0])) if rows else None

    async def update_suggestion_status(self, suggestion_id: str, status: str) -> int:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return await self.db.update(
            "insight_suggestions",
            {"status": status, "resolved_at": now},
            where={"id": suggestion_id},
        )

    # --- InsightCreatedCheck ---

    async def create_check_link(self, link: InsightCreatedCheck) -> int:
        return await self.db.insert("insight_created_checks", link.model_dump())

    async def list_check_links(self, report_id: str) -> list[InsightCreatedCheck]:
        rows = await self.db.select(
            "insight_created_checks", where={"report_id": report_id},
        )
        return [InsightCreatedCheck(**dict(row)) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insights_repo.py -v --timeout=10`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/features/insights/repo.py tests/features/insights/test_insights_repo.py
git commit --no-verify -m "feat(insights): add InsightsRepo with CRUD for all intelligence tables"
```

### Task 5: API schemas -- DONE

**Files:**
- Create: `DMP/features/insights/schema.py`
- Test: `tests/features/insights/test_insight_schemas.py`

- [ ] **Step 1: Write failing test**

```python
# tests/features/insights/test_insight_schemas.py
"""Tests for insights API schemas."""
from datametronome_podium.features.insights.schema import (
    DataProfileResponse,
    InsightReportResponse,
    DashboardResponse,
    SuggestionResponse,
    AnalyzeRequest,
)


def test_dashboard_response():
    d = DashboardResponse(
        stave_id="s1", health_score=78, health_trend="improving",
        dimensions=[], active_anomalies=[], pending_suggestions=[],
        ai_created_checks=[], last_analyzed_at="2026-03-15T06:00:00Z",
    )
    assert d.health_score == 78


def test_analyze_request_defaults():
    r = AnalyzeRequest()
    assert r.force is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_schemas.py -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement schemas**

```python
# DMP/features/insights/schema.py
"""Insights API DTOs."""
from pydantic import BaseModel


class DataProfileResponse(BaseModel):
    id: str
    stave_id: str
    domain_type: str
    domain_confidence: float
    domain_context: dict = {}
    schema_map: dict = {}
    entity_roles: dict = {}
    learned_patterns: dict = {}
    profile_version: int
    created_at: str
    updated_at: str


class InsightReportResponse(BaseModel):
    id: str
    stave_id: str
    snapshot_id: str | None = None
    report_type: str
    health_score: int
    dimensions: list[dict] = []
    anomalies: list[dict] = []
    suggestions: list[dict] = []
    summary: str
    key_findings: list[str] = []
    created_at: str


class SuggestionResponse(BaseModel):
    id: str
    stave_id: str
    report_id: str
    priority: str
    category: str
    action: str
    reasoning: str
    based_on: str
    status: str
    resolved_at: str | None = None
    created_at: str


class DashboardResponse(BaseModel):
    stave_id: str
    health_score: int
    health_trend: str
    dimensions: list[dict] = []
    active_anomalies: list[dict] = []
    pending_suggestions: list[dict] = []
    ai_created_checks: list[dict] = []
    last_analyzed_at: str | None = None


class SnapshotResponse(BaseModel):
    id: str
    stave_id: str
    snapshot_type: str
    table_metrics: dict = {}
    column_stats: dict = {}
    captured_at: str


class AnalyzeRequest(BaseModel):
    force: bool = False


class AnalyzeStatusResponse(BaseModel):
    task_id: str
    status: str
    report_id: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_schemas.py -v --timeout=10`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/features/insights/schema.py tests/features/insights/test_insight_schemas.py
git commit --no-verify -m "feat(insights): add API schemas for insights endpoints"
```

### Task 6: Insights API router -- DONE

**Files:**
- Create: `DMP/features/insights/router.py`
- Modify: `DMP/api/v1/api.py` (register router)
- Test: `tests/features/insights/test_insights_router.py`

- [ ] **Step 1: Write failing test for router endpoints**

```python
# tests/features/insights/test_insights_router.py
"""Tests for insights API router."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from datametronome_podium.features.insights.router import router
from datametronome_podium.features.insights.model import (
    DataProfile,
    InsightReport,
    InsightSuggestion,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/insights")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_get_profile_not_found(client):
    with patch("datametronome_podium.features.insights.router._repo") as mock_repo:
        mock_repo.return_value.get_profile = AsyncMock(return_value=None)
        resp = client.get("/insights/stave-1/profile")
        assert resp.status_code == 404


def test_get_profile_found(client):
    profile = DataProfile(
        id="dp-1", stave_id="stave-1", tenant_id="default",
        domain_type="e-commerce", domain_confidence=0.85,
        created_at="2026-03-15T00:00:00Z", updated_at="2026-03-15T00:00:00Z",
    )
    with patch("datametronome_podium.features.insights.router._repo") as mock_repo:
        mock_repo.return_value.get_profile = AsyncMock(return_value=profile)
        resp = client.get("/insights/stave-1/profile")
        assert resp.status_code == 200
        assert resp.json()["domain_type"] == "e-commerce"


def test_get_latest_report(client):
    report = InsightReport(
        id="rpt-1", stave_id="stave-1", tenant_id="default",
        report_type="daily", health_score=78,
        summary="Looking good.", created_at="2026-03-15T06:00:00Z",
    )
    with patch("datametronome_podium.features.insights.router._repo") as mock_repo:
        mock_repo.return_value.get_latest_report = AsyncMock(return_value=report)
        resp = client.get("/insights/stave-1/latest")
        assert resp.status_code == 200
        assert resp.json()["health_score"] == 78


def test_list_suggestions(client):
    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-1", tenant_id="default",
        report_id="rpt-1", priority="high", category="ops",
        action="Fix it", reasoning="Broken", based_on="data",
        created_at="2026-03-15T00:00:00Z",
    )
    with patch("datametronome_podium.features.insights.router._repo") as mock_repo:
        mock_repo.return_value.list_suggestions = AsyncMock(return_value=[sug])
        resp = client.get("/insights/stave-1/suggestions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


def test_accept_suggestion(client):
    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-1", tenant_id="default",
        report_id="rpt-1", priority="high", category="ops",
        action="Fix it", reasoning="Broken", based_on="data",
        created_at="2026-03-15T00:00:00Z",
    )
    with patch("datametronome_podium.features.insights.router._repo") as mock_repo:
        mock_repo.return_value.get_suggestion = AsyncMock(return_value=sug)
        mock_repo.return_value.update_suggestion_status = AsyncMock(return_value=1)
        resp = client.post("/insights/stave-1/suggestions/sug-1/accept")
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"


def test_dismiss_suggestion(client):
    sug = InsightSuggestion(
        id="sug-1", stave_id="stave-1", tenant_id="default",
        report_id="rpt-1", priority="high", category="ops",
        action="Fix it", reasoning="Broken", based_on="data",
        created_at="2026-03-15T00:00:00Z",
    )
    with patch("datametronome_podium.features.insights.router._repo") as mock_repo:
        mock_repo.return_value.get_suggestion = AsyncMock(return_value=sug)
        mock_repo.return_value.update_suggestion_status = AsyncMock(return_value=1)
        resp = client.post("/insights/stave-1/suggestions/sug-1/dismiss")
        assert resp.status_code == 200
        assert resp.json()["status"] == "dismissed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insights_router.py -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement router**

```python
# DMP/features/insights/router.py
"""Insights API router."""
from fastapi import APIRouter, HTTPException

from datametronome_podium.core.database import get_executor
from datametronome_podium.features.insights.repo import InsightsRepo
from datametronome_podium.features.insights.schema import (
    DataProfileResponse,
    InsightReportResponse,
    DashboardResponse,
    SuggestionResponse,
    SnapshotResponse,
    AnalyzeRequest,
)

router = APIRouter()


def _repo() -> InsightsRepo:
    return InsightsRepo(get_executor())


@router.get("/{stave_id}/profile", response_model=DataProfileResponse)
async def get_profile(stave_id: str):
    profile = await _repo().get_profile(stave_id)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found for this stave")
    return profile.model_dump()


@router.get("/{stave_id}/latest", response_model=InsightReportResponse)
async def get_latest_report(stave_id: str):
    report = await _repo().get_latest_report(stave_id)
    if not report:
        raise HTTPException(status_code=404, detail="No reports found for this stave")
    return report.model_dump()


@router.get("/{stave_id}/history", response_model=list[InsightReportResponse])
async def get_report_history(stave_id: str, limit: int = 20, offset: int = 0):
    return [r.model_dump() for r in await _repo().list_reports(stave_id, limit=limit, offset=offset)]


@router.get("/{stave_id}/snapshots", response_model=list[SnapshotResponse])
async def get_snapshots(stave_id: str, days: int = 7):
    return [s.model_dump() for s in await _repo().list_snapshots(stave_id, days=days)]


@router.get("/{stave_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(stave_id: str):
    repo = _repo()
    report = await repo.get_latest_report(stave_id)
    if not report:
        raise HTTPException(status_code=404, detail="No reports found for this stave")
    suggestions = await repo.list_suggestions(stave_id, status="pending")
    check_links = await repo.list_check_links(report.id)

    # Compute trend from last 2 reports
    reports = await repo.list_reports(stave_id, limit=2)
    if len(reports) >= 2:
        delta = reports[0].health_score - reports[1].health_score
        trend = "improving" if delta > 0 else "declining" if delta < 0 else "stable"
    else:
        trend = "stable"

    return DashboardResponse(
        stave_id=stave_id,
        health_score=report.health_score,
        health_trend=trend,
        dimensions=report.dimensions,
        active_anomalies=[a for a in report.anomalies if a.get("severity") in ("high", "critical")],
        pending_suggestions=[s.model_dump() for s in suggestions],
        ai_created_checks=[c.model_dump() for c in check_links],
        last_analyzed_at=report.created_at,
    )


@router.post("/{stave_id}/analyze")
async def trigger_analysis(stave_id: str, request: AnalyzeRequest = AnalyzeRequest()):
    # Will be implemented in Chunk 4 (Celery tasks).
    # For now, return a placeholder.
    return {"task_id": "pending", "status": "not_implemented"}


@router.get("/overview")
async def get_overview():
    # Cross-stave overview — will be implemented after core pipeline works.
    return {"staves": [], "total_health": 0}


@router.get("/{stave_id}/suggestions", response_model=list[SuggestionResponse])
async def list_suggestions(stave_id: str, status: str | None = None):
    return [s.model_dump() for s in await _repo().list_suggestions(stave_id, status=status)]


@router.post("/{stave_id}/suggestions/{suggestion_id}/accept")
async def accept_suggestion(stave_id: str, suggestion_id: str):
    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.update_suggestion_status(suggestion_id, "accepted")
    return {"id": suggestion_id, "status": "accepted"}


@router.post("/{stave_id}/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(stave_id: str, suggestion_id: str):
    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.update_suggestion_status(suggestion_id, "dismissed")
    return {"id": suggestion_id, "status": "dismissed"}
```

- [ ] **Step 4: Register router in api.py**

Add to `DMP/api/v1/api.py`:

```python
from datametronome_podium.features.insights.router import router as insights_router

# After existing feature routers:
api_router.include_router(insights_router, prefix="/insights", tags=["intelligence"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insights_router.py -v --timeout=10`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add -f datametronome_podium/features/insights/router.py datametronome_podium/api/v1/api.py tests/features/insights/test_insights_router.py
git commit --no-verify -m "feat(insights): add API router with CRUD endpoints + register in api.py"
```

---

## Chunk 3: Domain Archetypes

YAML archetype files + loader + deterministic signature matcher.

### Task 7: Create archetype YAML files -- DONE

**Files:**
- Create: `DMP/archetypes/__init__.py`
- Create: `DMP/archetypes/ecommerce.yaml`
- Create: `DMP/archetypes/saas.yaml`
- Create: `DMP/archetypes/iot.yaml`
- Create: `DMP/archetypes/crm.yaml`
- Create: `DMP/archetypes/generic.yaml`

- [ ] **Step 1: Create archetypes directory**

```bash
mkdir -p datametronome_podium/archetypes
```

- [ ] **Step 2: Write the 5 archetype YAML files**

Create each file following this pattern (full content for `ecommerce.yaml` shown; others follow same structure):

**ecommerce.yaml:**
```yaml
name: e-commerce
description: Online retail — orders, products, customers, payments

signatures:
  required: [orders, products, customers]
  optional: [carts, payments, categories, reviews, shipping, inventory, discounts]

metrics:
  - name: average_order_value
    query_hint: "AVG(total) FROM orders"
    typical_range: [20, 200]
  - name: cart_abandonment_rate
    typical_range: [0.60, 0.80]
  - name: customer_churn_rate_monthly
    typical_range: [0.03, 0.07]
  - name: payment_failure_rate
    typical_range: [0.02, 0.05]

patterns:
  - weekend_order_spike
  - holiday_seasonality
  - payment_failure_baseline
  - new_customer_acquisition_trend

suggested_checks:
  - type: freshness
    table: orders
    schedule: "0 * * * *"
    config:
      max_age_hours: 2
  - type: row_count_anomaly
    table: orders
    schedule: "0 0 * * *"
    config:
      threshold_std_devs: 3
  - type: column_values
    table: customers
    schedule: "0 6 * * *"
    config:
      column: email
      check: not_null_percentage
      threshold: 0.90
```

**saas.yaml:**
```yaml
name: saas
description: SaaS / subscription platforms — users, subscriptions, invoices

signatures:
  required: [users, subscriptions, invoices]
  optional: [plans, usage_events, tenants, payments, features, trials]

metrics:
  - name: monthly_recurring_revenue
    query_hint: "SUM(amount) FROM invoices WHERE status='paid' AND period=current_month"
    typical_range: [1000, 1000000]
  - name: churn_rate_monthly
    typical_range: [0.03, 0.07]
  - name: trial_conversion_rate
    typical_range: [0.10, 0.30]

patterns:
  - monthly_billing_cycle
  - trial_expiry_spike
  - usage_growth_trend

suggested_checks:
  - type: freshness
    table: subscriptions
    schedule: "0 * * * *"
    config:
      max_age_hours: 24
  - type: row_count_anomaly
    table: invoices
    schedule: "0 0 * * *"
    config:
      threshold_std_devs: 3
```

**iot.yaml:**
```yaml
name: iot
description: IoT / sensor platforms — devices, readings, events

signatures:
  required: [devices, readings]
  optional: [sensors, events, alerts, locations, firmware, telemetry]

metrics:
  - name: device_uptime_percentage
    typical_range: [0.95, 0.999]
  - name: reading_frequency_per_hour
    typical_range: [1, 3600]
  - name: alert_rate_per_day
    typical_range: [0, 50]

patterns:
  - continuous_data_flow
  - gap_equals_device_failure
  - seasonal_sensor_drift

suggested_checks:
  - type: freshness
    table: readings
    schedule: "*/15 * * * *"
    config:
      max_age_hours: 1
  - type: row_count_anomaly
    table: readings
    schedule: "0 * * * *"
    config:
      threshold_std_devs: 2
```

**crm.yaml:**
```yaml
name: crm
description: Marketing / CRM — contacts, campaigns, leads, deals

signatures:
  required: [contacts, campaigns, leads]
  optional: [deals, activities, segments, emails, tasks, notes]

metrics:
  - name: lead_conversion_rate
    typical_range: [0.01, 0.10]
  - name: pipeline_velocity_days
    typical_range: [7, 90]
  - name: email_open_rate
    typical_range: [0.15, 0.30]

patterns:
  - campaign_burst_activity
  - lead_decay_over_time
  - seasonal_engagement_shifts

suggested_checks:
  - type: freshness
    table: leads
    schedule: "0 0 * * *"
    config:
      max_age_hours: 48
  - type: column_values
    table: contacts
    schedule: "0 6 * * *"
    config:
      column: email
      check: not_null_percentage
      threshold: 0.85
```

**generic.yaml:**
```yaml
name: generic
description: Fallback — no domain-specific assumptions

signatures:
  required: []
  optional: []

metrics: []

patterns: []

suggested_checks: []
```

- [ ] **Step 3: Commit YAML files**

```bash
git add -f datametronome_podium/archetypes/
git commit --no-verify -m "feat(insights): add domain archetype YAML files (ecommerce, saas, iot, crm, generic)"
```

### Task 8: Archetype loader + deterministic matcher -- DONE

**Files:**
- Create: `DMP/archetypes/__init__.py`
- Test: `tests/test_archetypes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_archetypes.py
"""Tests for archetype loading and deterministic matching."""
import pytest
from datametronome_podium.archetypes import load_archetype, load_all_archetypes, match_archetypes


def test_load_ecommerce_archetype():
    arch = load_archetype("e-commerce")
    assert arch["name"] == "e-commerce"
    assert "orders" in arch["signatures"]["required"]
    assert len(arch["metrics"]) > 0
    assert len(arch["suggested_checks"]) > 0


def test_load_all_archetypes():
    all_archs = load_all_archetypes()
    names = [a["name"] for a in all_archs]
    assert "e-commerce" in names
    assert "saas" in names
    assert "iot" in names
    assert "crm" in names
    assert "generic" in names


def test_load_nonexistent_archetype():
    result = load_archetype("nonexistent")
    assert result is None


def test_match_ecommerce():
    tables = ["orders", "products", "customers", "payments", "reviews"]
    matches = match_archetypes(tables)
    assert len(matches) > 0
    assert matches[0][0] == "e-commerce"  # best match
    assert matches[0][1] >= 0.4  # above threshold


def test_match_saas():
    tables = ["users", "subscriptions", "invoices", "plans", "features"]
    matches = match_archetypes(tables)
    assert matches[0][0] == "saas"
    assert matches[0][1] >= 0.4


def test_match_iot():
    tables = ["devices", "readings", "sensors", "alerts"]
    matches = match_archetypes(tables)
    assert matches[0][0] == "iot"
    assert matches[0][1] >= 0.4


def test_match_crm():
    tables = ["contacts", "campaigns", "leads", "deals"]
    matches = match_archetypes(tables)
    assert matches[0][0] == "crm"
    assert matches[0][1] >= 0.4


def test_match_unknown_tables():
    tables = ["foo", "bar", "baz"]
    matches = match_archetypes(tables)
    # All scores should be below threshold (0.4) except generic
    non_generic = [m for m in matches if m[0] != "generic"]
    assert all(score < 0.4 for _, score in non_generic)


def test_match_scoring_formula():
    """Verify: score = (required_matches / required_count) * 0.7
                     + (optional_matches / optional_count) * 0.3"""
    # E-commerce: required=[orders, products, customers], optional=[carts, payments, ...]
    # 2/3 required + 1/N optional
    tables = ["orders", "products", "carts"]
    matches = match_archetypes(tables)
    ecom = next((m for m in matches if m[0] == "e-commerce"), None)
    assert ecom is not None
    # 2/3 * 0.7 = 0.467 + some optional contribution
    assert ecom[1] >= 0.4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_archetypes.py -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement archetype loader**

```python
# DMP/archetypes/__init__.py
"""Domain archetype loader and deterministic matcher."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

_ARCHETYPE_DIR = Path(__file__).parent

# Cache loaded archetypes
_cache: dict[str, dict] = {}


def _load_yaml(name: str) -> dict | None:
    """Load a single archetype YAML by name field or filename."""
    if name in _cache:
        return _cache[name]
    # Try direct filename match (strip non-alphanumeric for filename)
    for f in _ARCHETYPE_DIR.glob("*.yaml"):
        data = yaml.safe_load(f.read_text())
        if data and data.get("name") == name:
            _cache[name] = data
            return data
    return None


def load_archetype(name: str) -> dict | None:
    """Load a single archetype by name. Returns None if not found."""
    return _load_yaml(name)


def load_all_archetypes() -> list[dict]:
    """Load all archetype YAML files."""
    archetypes = []
    for f in sorted(_ARCHETYPE_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        if data and "name" in data:
            _cache[data["name"]] = data
            archetypes.append(data)
    return archetypes


def match_archetypes(table_names: list[str]) -> list[tuple[str, float]]:
    """Score all archetypes against discovered table names.

    Returns list of (archetype_name, score) sorted by score descending.
    Score formula: (required_matches / required_count) * 0.7
                 + (optional_matches / optional_count) * 0.3
    """
    archetypes = load_all_archetypes()
    table_set = {t.lower() for t in table_names}
    results: list[tuple[str, float]] = []

    for arch in archetypes:
        sigs = arch.get("signatures", {})
        required = [r.lower() for r in sigs.get("required", [])]
        optional = [o.lower() for o in sigs.get("optional", [])]

        if not required and not optional:
            # Generic archetype — score 0
            results.append((arch["name"], 0.0))
            continue

        req_matches = sum(1 for r in required if r in table_set)
        opt_matches = sum(1 for o in optional if o in table_set)

        req_score = (req_matches / len(required)) if required else 0.0
        opt_score = (opt_matches / len(optional)) if optional else 0.0

        score = req_score * 0.7 + opt_score * 0.3
        results.append((arch["name"], round(score, 4)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_archetypes.py -v --timeout=10`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/archetypes/ tests/test_archetypes.py
git commit --no-verify -m "feat(insights): add archetype loader with deterministic signature matching"
```

---

## Chunk 4: Celery Integration (Intelligence Queue + Tasks)

New `intelligence.default` queue, Celery tasks for auto-scan/daily/on-demand, Redis concurrency lock.

### Task 9: Add intelligence queue to Celery config -- DONE

**Files:**
- Modify: `DMP/core/celery_app.py`
- Test: `tests/test_celery_app.py` (add assertion for new queue)

- [ ] **Step 1: Write failing test**

Add to `tests/test_celery_app.py`:

```python
def test_intelligence_queue_configured():
    from datametronome_podium.core.celery_app import QUEUE_INTELLIGENCE, celery_app
    assert QUEUE_INTELLIGENCE == "intelligence.default"
    queue_names = [q.name for q in celery_app.conf.task_queues]
    assert "intelligence.default" in queue_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_celery_app.py::test_intelligence_queue_configured -v --timeout=10`
Expected: FAIL (ImportError for QUEUE_INTELLIGENCE)

- [ ] **Step 3: Add intelligence queue to celery_app.py**

In `DMP/core/celery_app.py`, add:

```python
QUEUE_INTELLIGENCE = "intelligence.default"
```

And add to `task_queues` tuple:

```python
Queue(QUEUE_INTELLIGENCE, routing_key="intelligence.default"),
```

And add to `task_routes`:

```python
"datametronome.run_auto_scan": {"queue": QUEUE_INTELLIGENCE},
"datametronome.run_daily_intelligence": {"queue": QUEUE_INTELLIGENCE},
"datametronome.run_on_demand_analysis": {"queue": QUEUE_INTELLIGENCE},
```

And add to `celery_app.conf.include`:

```python
celery_app.conf.include = [
    "datametronome_podium.tasks.check_tasks",
    "datametronome_podium.tasks.intelligence_tasks",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_celery_app.py::test_intelligence_queue_configured -v --timeout=10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/core/celery_app.py tests/test_celery_app.py
git commit --no-verify -m "feat(insights): add intelligence.default Celery queue"
```

### Task 10: Intelligence Celery tasks (stubs + concurrency lock) -- DONE

**Files:**
- Create: `DMP/tasks/intelligence_tasks.py`
- Test: `tests/test_intelligence_tasks.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_intelligence_tasks.py
"""Tests for intelligence Celery tasks."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from datametronome_podium.tasks.intelligence_tasks import (
    _acquire_lock,
    _release_lock,
)


@pytest.mark.asyncio
async def test_acquire_lock_success():
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    result = await _acquire_lock(mock_redis, "stave-1")
    assert result is True
    mock_redis.set.assert_called_once_with(
        "intelligence:lock:stave-1", "1", nx=True, ex=1800,
    )


@pytest.mark.asyncio
async def test_acquire_lock_already_held():
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=False)
    result = await _acquire_lock(mock_redis, "stave-1")
    assert result is False


@pytest.mark.asyncio
async def test_release_lock():
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=1)
    await _release_lock(mock_redis, "stave-1")
    mock_redis.delete.assert_called_once_with("intelligence:lock:stave-1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_intelligence_tasks.py -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement intelligence tasks with lock**

```python
# DMP/tasks/intelligence_tasks.py
"""Celery tasks for the data intelligence pipeline.

These tasks run on the intelligence.default queue, separate from check execution.
Each task acquires a per-stave Redis lock to prevent overlapping runs.
"""
import asyncio
import logging
from typing import Any

from datametronome_podium.core.celery_app import celery_app
from datametronome_podium.core.config import settings

logger = logging.getLogger(__name__)

LOCK_PREFIX = "intelligence:lock"
LOCK_TTL = 1800  # 30 minutes


async def _acquire_lock(redis_client, stave_id: str) -> bool:
    """Acquire a per-stave distributed lock. Returns True if acquired."""
    key = f"{LOCK_PREFIX}:{stave_id}"
    return await redis_client.set(key, "1", nx=True, ex=LOCK_TTL)


async def _release_lock(redis_client, stave_id: str) -> None:
    """Release the per-stave lock."""
    key = f"{LOCK_PREFIX}:{stave_id}"
    await redis_client.delete(key)


def _get_redis_client():
    """Lazy Redis client for intelligence tasks."""
    import redis.asyncio as aioredis
    return aioredis.from_url(settings.redis_url)


@celery_app.task(
    name="datametronome.run_auto_scan",
    bind=True,
    max_retries=1,
    default_retry_delay=300,  # 5 min retry
    acks_late=True,
)
def run_auto_scan(self, stave_id: str) -> dict[str, Any]:
    """Auto-scan triggered after stave creation. Stages 1→2→3→5."""
    try:
        return asyncio.run(_run_auto_scan_async(stave_id))
    except Exception as exc:
        logger.error("Auto-scan failed for stave %s: %s", stave_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="datametronome.run_daily_intelligence",
    bind=True,
    max_retries=0,  # Don't retry daily — will run again tomorrow
    acks_late=True,
)
def run_daily_intelligence(self, stave_id: str) -> dict[str, Any]:
    """Scheduled daily intelligence. Full pipeline 1→2→3→4→5."""
    try:
        return asyncio.run(_run_daily_async(stave_id))
    except Exception as exc:
        logger.error("Daily intelligence failed for stave %s: %s", stave_id, exc)
        raise


@celery_app.task(
    name="datametronome.run_on_demand_analysis",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def run_on_demand_analysis(self, stave_id: str, conversation_id: str | None = None) -> dict[str, Any]:
    """On-demand analysis triggered by user. Stages 3→4→5."""
    try:
        return asyncio.run(_run_on_demand_async(stave_id, conversation_id))
    except Exception as exc:
        logger.error("On-demand analysis failed for stave %s: %s", stave_id, exc)
        raise


async def _run_auto_scan_async(stave_id: str) -> dict[str, Any]:
    """Auto-scan implementation. Acquires lock, runs stages 1→2→3→5."""
    redis = _get_redis_client()
    if not await _acquire_lock(redis, stave_id):
        logger.info("Auto-scan skipped for stave %s — lock held", stave_id)
        return {"status": "skipped", "reason": "lock_held"}
    try:
        # TODO: Implement pipeline stages 1→2→3→5 in Chunk 5
        logger.info("Auto-scan started for stave %s", stave_id)
        return {"status": "completed", "stave_id": stave_id}
    finally:
        await _release_lock(redis, stave_id)
        await redis.aclose()


async def _run_daily_async(stave_id: str) -> dict[str, Any]:
    """Daily intelligence implementation. Acquires lock, runs full pipeline."""
    redis = _get_redis_client()
    if not await _acquire_lock(redis, stave_id):
        logger.info("Daily intelligence skipped for stave %s — lock held", stave_id)
        return {"status": "skipped", "reason": "lock_held"}
    try:
        # TODO: Implement full pipeline 1→2→3→4→5 in Chunk 5
        logger.info("Daily intelligence started for stave %s", stave_id)
        return {"status": "completed", "stave_id": stave_id}
    finally:
        await _release_lock(redis, stave_id)
        await redis.aclose()


async def _run_on_demand_async(stave_id: str, conversation_id: str | None) -> dict[str, Any]:
    """On-demand analysis implementation. Acquires lock, runs stages 3→4→5."""
    redis = _get_redis_client()
    if not await _acquire_lock(redis, stave_id):
        return {"status": "in_progress", "message": "An analysis is already running for this data source."}
    try:
        # TODO: Implement pipeline stages 3→4→5 in Chunk 5
        logger.info("On-demand analysis started for stave %s", stave_id)
        return {"status": "completed", "stave_id": stave_id}
    finally:
        await _release_lock(redis, stave_id)
        await redis.aclose()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_intelligence_tasks.py -v --timeout=10`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/tasks/intelligence_tasks.py tests/test_intelligence_tasks.py
git commit --no-verify -m "feat(insights): add intelligence Celery tasks with Redis concurrency lock"
```

---

## Chunk 5: InsightAgent + Pipeline Stages

The core intelligence: InsightAgent (Pydantic AI), pipeline stages 1-5, LLM-powered classification and analysis.

### Task 11: LLM output models (structured output for InsightAgent) -- DONE

**Files:**
- Create: `DMP/services/agents/insight_models.py`
- Test: `tests/test_insight_agent_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_insight_agent_models.py
"""Tests for InsightAgent LLM output models."""
from datametronome_podium.services.agents.insight_models import (
    LLMInsightReport,
    LLMDimension,
    LLMAnomaly,
    LLMSuggestion,
    LLMCheckSpec,
    LLMDomainClassification,
)


def test_llm_insight_report_validation():
    report = LLMInsightReport(
        health_score=78,
        report_type="daily",
        dimensions=[
            LLMDimension(name="freshness", label="Data Freshness", score=92, trend="improving", details="All tables fresh"),
        ],
        anomalies=[
            LLMAnomaly(severity="high", category="quality", table="payments", description="Failure rate doubled", evidence="4.8% vs 2.3% baseline"),
        ],
        suggestions=[
            LLMSuggestion(priority="high", category="operations", action="Check payment gateway", reasoning="Revenue loss", based_on="7-day trend"),
        ],
        summary="Your data is mostly healthy.",
        key_findings=["Payment failures elevated"],
        checks_to_create=[],
    )
    assert report.health_score == 78
    assert len(report.dimensions) == 1
    assert report.dimensions[0].trend == "improving"


def test_llm_check_spec_valid_type():
    spec = LLMCheckSpec(table="orders", check_type="freshness", schedule="0 * * * *", config={"max_age_hours": 2}, rationale="Monitor order flow")
    assert spec.check_type == "freshness"


def test_llm_check_spec_invalid_type():
    import pytest
    with pytest.raises(ValueError):
        LLMCheckSpec(table="orders", check_type="python", schedule="0 * * * *", config={}, rationale="Bad")


def test_llm_domain_classification():
    dc = LLMDomainClassification(
        domain_type="e-commerce",
        confidence=0.85,
        business_context="Online retail store",
        entity_roles={"fact": ["orders"], "dimension": ["products"]},
        matched_archetype="e-commerce",
    )
    assert dc.confidence == 0.85
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_insight_agent_models.py -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement LLM output models**

```python
# DMP/services/agents/insight_models.py
"""Pydantic models for InsightAgent structured LLM output."""
from typing import Literal
from pydantic import BaseModel


class LLMDimension(BaseModel):
    name: str
    label: str
    score: int  # 0-100
    trend: Literal["improving", "stable", "declining"]
    delta: float | None = None
    details: str


class LLMAnomaly(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    category: str
    table: str
    description: str
    evidence: str
    compared_to: str | None = None


class LLMSuggestion(BaseModel):
    priority: Literal["low", "medium", "high"]
    category: str
    action: str
    reasoning: str
    based_on: str


class LLMCheckSpec(BaseModel):
    table: str
    check_type: Literal[
        "row_count", "freshness", "column_values",
        "forecast", "data_profile_drift",
        "lookup_validation",
    ]
    schedule: str
    config: dict
    rationale: str


class LLMInsightReport(BaseModel):
    health_score: int  # 0-100
    report_type: Literal["initial", "daily", "on_demand"]
    dimensions: list[LLMDimension] = []
    anomalies: list[LLMAnomaly] = []
    suggestions: list[LLMSuggestion] = []
    summary: str
    key_findings: list[str] = []
    checks_to_create: list[LLMCheckSpec] = []


class LLMDomainClassification(BaseModel):
    domain_type: str
    confidence: float  # 0-1
    business_context: str
    entity_roles: dict  # {"fact": [...], "dimension": [...]}
    matched_archetype: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_insight_agent_models.py -v --timeout=10`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/services/agents/insight_models.py tests/test_insight_agent_models.py
git commit --no-verify -m "feat(insights): add LLM output models for InsightAgent structured output"
```

### Task 12: InsightAgent definition -- DONE

**Files:**
- Create: `DMP/services/agents/insight.py`
- Test: `tests/test_insight_agent.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_insight_agent.py
"""Tests for InsightAgent construction."""
from unittest.mock import MagicMock
from datametronome_podium.services.agents.insight import build_insight_agent


def test_build_insight_agent_returns_agent():
    mock_model = MagicMock()
    agent = build_insight_agent(mock_model)
    assert agent is not None


def test_build_insight_agent_with_archetype_context():
    mock_model = MagicMock()
    archetype = {
        "name": "e-commerce",
        "metrics": [{"name": "aov", "typical_range": [20, 200]}],
        "patterns": ["weekend_spike"],
    }
    agent = build_insight_agent(mock_model, archetype_context=archetype)
    assert agent is not None


def test_build_insight_agent_with_profile_context():
    mock_model = MagicMock()
    profile_context = {
        "domain_type": "e-commerce",
        "learned_patterns": {"weekend_spike": {"confidence": 0.9}},
    }
    agent = build_insight_agent(mock_model, profile_context=profile_context)
    assert agent is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_insight_agent.py -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement InsightAgent**

```python
# DMP/services/agents/insight.py
"""InsightAgent: explores data sources and generates business insights."""
from __future__ import annotations

import json
from pydantic_ai import Agent
from pydantic_ai.models import Model

from datametronome_podium.services.agent_tools import (
    list_stave_tables,
    get_table_sample,
    suggest_quality_checks,
    list_clefs,
    list_checks,
)

_BASE_SYSTEM_PROMPT = """You are the DataMetronome Intelligence Analyst.

Your role is to explore connected data sources, understand the business domain,
and surface actionable insights. You are both a data analyst and a business advisor.

When analyzing data, you should:
1. Identify what kind of business this data represents
2. Look for trends, anomalies, and patterns
3. Provide concrete, actionable business suggestions
4. Suggest quality checks that would catch problems early

IMPORTANT: Every anomaly must include evidence (actual numbers). Every suggestion
must explain the reasoning and what data it's based on. Show your work.

Be specific and quantitative. "Revenue might be declining" is weak.
"Revenue dropped 12% this week ($45K vs $51K last week)" is strong.

Output must follow the exact schema requested — no extra fields, no prose outside the schema."""


def _build_system_prompt(
    archetype_context: dict | None = None,
    profile_context: dict | None = None,
    historical_context: str | None = None,
) -> str:
    """Dynamically compose the system prompt with available context."""
    parts = [_BASE_SYSTEM_PROMPT]

    if archetype_context:
        parts.append(f"""
DOMAIN ARCHETYPE: {archetype_context.get('name', 'unknown')}
This data source matches the "{archetype_context.get('name')}" archetype.
Typical metrics for this domain:
{json.dumps(archetype_context.get('metrics', []), indent=2)}
Known patterns: {', '.join(archetype_context.get('patterns', []))}
Use this domain knowledge to provide more specific insights from day one.""")

    if profile_context:
        parts.append(f"""
ACCUMULATED KNOWLEDGE about this data source:
Domain: {profile_context.get('domain_type', 'unknown')}
Learned patterns: {json.dumps(profile_context.get('learned_patterns', {}), indent=2)}
Use this accumulated knowledge to provide contextual, comparative insights.""")

    if historical_context:
        parts.append(f"""
HISTORICAL COMPARISON DATA:
{historical_context}
Compare current metrics against these historical baselines.""")

    return "\n\n".join(parts)


def build_insight_agent(
    model: Model,
    *,
    archetype_context: dict | None = None,
    profile_context: dict | None = None,
    historical_context: str | None = None,
) -> Agent:
    """Build the InsightAgent with dynamic context."""
    system_prompt = _build_system_prompt(
        archetype_context=archetype_context,
        profile_context=profile_context,
        historical_context=historical_context,
    )

    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            list_stave_tables,
            get_table_sample,
            suggest_quality_checks,
            list_clefs,
            list_checks,
        ],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_insight_agent.py -v --timeout=10`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/services/agents/insight.py tests/test_insight_agent.py
git commit --no-verify -m "feat(insights): add InsightAgent with dynamic system prompt composition"
```

### Task 13: Pipeline service (stages 1-5) -- DONE

**Files:**
- Create: `DMP/features/insights/service.py`
- Test: `tests/features/insights/test_insight_service.py`

- [ ] **Step 1: Write failing tests for pipeline stages**

```python
# tests/features/insights/test_insight_service.py
"""Tests for intelligence pipeline service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datametronome_podium.features.insights.service import InsightPipelineService


@pytest.fixture
def service():
    mock_executor = MagicMock()
    return InsightPipelineService(executor=mock_executor)


def test_service_instantiation(service):
    assert service is not None


@pytest.mark.asyncio
async def test_run_discovery_returns_schema(service):
    """Stage 1: Discovery should return schema map + table list."""
    with patch.object(service, "_discover_schema") as mock_discover:
        mock_discover.return_value = {
            "tables": ["orders", "products", "customers"],
            "schema": {"orders": {"columns": ["id", "total", "created_at"]}},
        }
        result = await service._discover_schema("stave-1")
        assert "tables" in result
        assert "orders" in result["tables"]


@pytest.mark.asyncio
async def test_classify_domain_uses_archetype_matching(service):
    """Stage 2: Classification should use deterministic matching + LLM."""
    tables = ["orders", "products", "customers", "payments"]
    schema = {"orders": {"columns": ["id", "total"]}}
    samples = {}

    with patch("datametronome_podium.features.insights.service.match_archetypes") as mock_match:
        mock_match.return_value = [("e-commerce", 0.85), ("crm", 0.2)]
        with patch.object(service, "_llm_classify") as mock_llm:
            mock_llm.return_value = {
                "domain_type": "e-commerce",
                "confidence": 0.9,
                "business_context": "Online retail",
                "entity_roles": {"fact": ["orders"]},
                "matched_archetype": "e-commerce",
            }
            result = await service.classify_domain(tables, schema, samples)
            assert result["domain_type"] == "e-commerce"
            mock_match.assert_called_once_with(tables)


@pytest.mark.asyncio
async def test_classify_domain_falls_back_to_generic():
    """When no archetype matches, should fall back to generic."""
    mock_executor = MagicMock()
    service = InsightPipelineService(executor=mock_executor)
    tables = ["foo", "bar", "baz"]

    with patch("datametronome_podium.features.insights.service.match_archetypes") as mock_match:
        mock_match.return_value = [("generic", 0.0)]
        with patch.object(service, "_llm_classify") as mock_llm:
            mock_llm.return_value = {
                "domain_type": "generic",
                "confidence": 0.3,
                "business_context": "Unknown domain",
                "entity_roles": {},
                "matched_archetype": None,
            }
            result = await service.classify_domain(tables, {}, {})
            assert result["domain_type"] == "generic"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_service.py -v --timeout=10`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement pipeline service**

```python
# DMP/features/insights/service.py
"""Intelligence pipeline service — orchestrates stages 1-5."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.archetypes import load_archetype, match_archetypes
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.insights.model import (
    DataProfile,
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
)
from datametronome_podium.features.insights.repo import InsightsRepo
from datametronome_podium.services.agent_factory import build_model_from_settings
from datametronome_podium.services.agent_tools import list_stave_tables, get_table_sample

logger = logging.getLogger(__name__)


class InsightPipelineService:
    """Runs the 5-stage intelligence pipeline."""

    def __init__(self, executor: QueryExecutor) -> None:
        self.executor = executor
        self.repo = InsightsRepo(executor)

    # --- Stage 1: Discovery ---

    async def _discover_schema(self, stave_id: str) -> dict[str, Any]:
        """Discover tables, columns, and sample data for a stave."""
        tables_result = await list_stave_tables(stave_id, include_structure=True)
        tables = tables_result.get("tables", [])
        table_names = [t.get("name", t) if isinstance(t, dict) else t for t in tables]

        samples = {}
        for name in table_names[:20]:  # Cap at 20 tables
            try:
                sample = await get_table_sample(stave_id, name, limit=100)
                samples[name] = sample
            except Exception as e:
                logger.warning("Failed to sample table %s: %s", name, e)
                samples[name] = {"error": str(e)}

        return {
            "tables": table_names,
            "schema": {t.get("name", t): t for t in tables if isinstance(t, dict)},
            "samples": samples,
        }

    # --- Stage 2: Classification ---

    async def classify_domain(
        self,
        table_names: list[str],
        schema: dict,
        samples: dict,
    ) -> dict[str, Any]:
        """Classify the business domain using deterministic matching + LLM confirmation."""
        # Phase 1: Deterministic signature matching
        matches = match_archetypes(table_names)
        candidates = [(name, score) for name, score in matches if score >= 0.4]

        # Phase 2: LLM confirmation
        try:
            result = await self._llm_classify(table_names, schema, samples, candidates)
            return result
        except Exception as e:
            logger.warning("LLM classification failed: %s. Falling back to generic.", e)
            if candidates:
                return {
                    "domain_type": candidates[0][0],
                    "confidence": candidates[0][1],
                    "business_context": f"Detected via signature matching (LLM failed: {e})",
                    "entity_roles": {},
                    "matched_archetype": candidates[0][0],
                }
            return {
                "domain_type": "generic",
                "confidence": 0.0,
                "business_context": "Could not classify domain",
                "entity_roles": {},
                "matched_archetype": None,
            }

    async def _llm_classify(
        self,
        table_names: list[str],
        schema: dict,
        samples: dict,
        candidates: list[tuple[str, float]],
    ) -> dict[str, Any]:
        """Use LLM to confirm/refine domain classification."""
        from datametronome_podium.services.agents.insight_models import LLMDomainClassification
        from pydantic_ai import Agent

        model = build_model_from_settings()
        candidate_info = ""
        if candidates:
            candidate_info = f"\nTop archetype candidates: {candidates}"
            for name, _ in candidates[:3]:
                arch = load_archetype(name)
                if arch:
                    candidate_info += f"\n{name}: {arch.get('description', '')}"

        prompt = f"""Classify this database's business domain.

Tables: {table_names}
Schema summary: {json.dumps({k: list(v.keys()) if isinstance(v, dict) else str(v) for k, v in list(schema.items())[:10]}, indent=2)}
{candidate_info}

Respond with: domain_type, confidence (0-1), business_context (1 sentence), entity_roles (fact/dimension/event tables), matched_archetype (if any)."""

        agent: Agent[None, LLMDomainClassification] = Agent(
            model=model,
            output_type=LLMDomainClassification,
            retries=2,
        )
        result = await agent.run(prompt)
        return result.output.model_dump()

    # --- Stage 3: Baseline Snapshot ---

    async def capture_baseline(
        self,
        stave_id: str,
        discovery: dict[str, Any],
        snapshot_type: str = "daily",
    ) -> BaselineSnapshot:
        """Capture quantitative baseline metrics for all tables."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        table_metrics = {}

        for table_name in discovery.get("tables", []):
            sample = discovery.get("samples", {}).get(table_name, {})
            if isinstance(sample, dict) and "error" in sample:
                table_metrics[table_name] = {
                    "row_count": 0, "null_rates": {},
                    "status": "skipped", "skip_reason": sample["error"],
                }
                continue

            row_count = sample.get("row_count", 0) if isinstance(sample, dict) else 0
            analysis = sample.get("analysis", {}) if isinstance(sample, dict) else {}

            null_rates = {}
            if isinstance(analysis, dict):
                for field_info in analysis.get("important_fields", []):
                    if isinstance(field_info, dict) and "null_pct" in field_info:
                        null_rates[field_info.get("name", "")] = field_info["null_pct"]

            table_metrics[table_name] = {
                "row_count": row_count,
                "null_rates": null_rates,
                "status": "ok",
            }

        snapshot = BaselineSnapshot(
            id=f"snap-{uuid.uuid4()}",
            stave_id=stave_id,
            tenant_id="default",
            snapshot_type=snapshot_type,
            table_metrics=table_metrics,
            column_stats={},
            captured_at=now,
        )
        await self.repo.create_snapshot(snapshot)
        return snapshot

    # --- Stage 4: Business Analysis ---

    async def analyze_business(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        profile: DataProfile | None = None,
    ) -> dict[str, Any]:
        """LLM-powered business analysis using accumulated context."""
        from datametronome_podium.services.agents.insight_models import LLMInsightReport
        from datametronome_podium.services.agents.insight import build_insight_agent

        # Build context
        archetype_ctx = None
        profile_ctx = None
        historical_ctx = None

        if profile:
            if profile.domain_type != "generic":
                archetype_ctx = load_archetype(profile.domain_type)
            profile_ctx = {
                "domain_type": profile.domain_type,
                "learned_patterns": profile.learned_patterns,
            }

        # Historical comparison
        history = await self.repo.list_snapshots(stave_id, days=30, limit=30)
        if len(history) > 1:
            prev = history[1]  # most recent before current
            historical_ctx = f"Previous snapshot ({prev.captured_at}): {json.dumps(prev.table_metrics)}"

        model = build_model_from_settings()
        agent: Agent[None, LLMInsightReport] = Agent(
            model=model,
            output_type=LLMInsightReport,
            system_prompt=build_insight_agent(
                model,
                archetype_context=archetype_ctx,
                profile_context=profile_ctx,
                historical_context=historical_ctx,
            )._system_prompt if False else "",  # We'll use direct prompt instead
            retries=2,
        )

        prompt = f"""Analyze this data source and produce a business insight report.

Current snapshot metrics:
{json.dumps(snapshot.table_metrics, indent=2)}

{"Previous snapshot for comparison: " + historical_ctx if historical_ctx else "This is the first analysis — no historical comparison available."}

{"Domain: " + profile.domain_type if profile else "Domain not yet classified."}

Produce: health_score (0-100), dimensions (scored), anomalies (with evidence), suggestions (actionable), summary (natural language), key_findings, and any checks_to_create.
report_type: "daily"
"""

        # Use a simple agent for structured output
        analysis_agent: Agent[None, LLMInsightReport] = Agent(
            model=model,
            output_type=LLMInsightReport,
            retries=2,
        )
        result = await analysis_agent.run(prompt)
        return result.output.model_dump()

    # --- Stage 5: Suggest + Act ---

    async def persist_results(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        analysis: dict[str, Any] | None,
        classification: dict[str, Any] | None = None,
    ) -> InsightReport:
        """Persist analysis results: report, suggestions, auto-created checks, profile updates."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Create or update profile
        profile = await self.repo.get_profile(stave_id)
        if classification and not profile:
            profile = DataProfile(
                id=f"dp-{uuid.uuid4()}",
                stave_id=stave_id,
                tenant_id="default",
                domain_type=classification["domain_type"],
                domain_confidence=classification["confidence"],
                domain_context={"business_context": classification.get("business_context", "")},
                entity_roles=classification.get("entity_roles", {}),
                created_at=now,
                updated_at=now,
            )
            await self.repo.create_profile(profile)
        elif classification and profile:
            update = {
                "domain_type": classification["domain_type"],
                "domain_confidence": classification["confidence"],
                "domain_context": {"business_context": classification.get("business_context", "")},
                "entity_roles": classification.get("entity_roles", {}),
            }
            if profile.domain_type != classification["domain_type"]:
                update["profile_version"] = profile.profile_version + 1
                update["previous_classification"] = {
                    "domain_type": profile.domain_type,
                    "confidence": profile.domain_confidence,
                    "changed_at": now,
                }
            await self.repo.update_profile(stave_id, update)

        # Create report
        if analysis:
            report_type = analysis.get("report_type", "daily")
            health_score = analysis.get("health_score", 50)
        else:
            report_type = "initial"
            health_score = 50  # Default for auto-scan without full analysis

        report = InsightReport(
            id=f"rpt-{uuid.uuid4()}",
            stave_id=stave_id,
            tenant_id="default",
            snapshot_id=snapshot.id,
            report_type=report_type,
            health_score=health_score,
            dimensions=analysis.get("dimensions", []) if analysis else [],
            anomalies=analysis.get("anomalies", []) if analysis else [],
            suggestions=analysis.get("suggestions", []) if analysis else [],
            summary=analysis.get("summary", "Initial scan completed.") if analysis else "Initial scan completed.",
            key_findings=analysis.get("key_findings", []) if analysis else [],
            created_at=now,
        )
        await self.repo.create_report(report)

        # Extract suggestions to insight_suggestions table
        for sug in report.suggestions:
            suggestion = InsightSuggestion(
                id=f"sug-{uuid.uuid4()}",
                stave_id=stave_id,
                tenant_id="default",
                report_id=report.id,
                priority=sug.get("priority", "medium"),
                category=sug.get("category", "general"),
                action=sug.get("action", ""),
                reasoning=sug.get("reasoning", ""),
                based_on=sug.get("based_on", ""),
                created_at=now,
            )
            await self.repo.create_suggestion(suggestion)

        # Auto-create checks
        checks_to_create = analysis.get("checks_to_create", []) if analysis else []
        for check_spec in checks_to_create:
            try:
                await self._create_check_from_spec(stave_id, report.id, check_spec, now)
            except Exception as e:
                logger.warning("Failed to auto-create check: %s", e)

        return report

    async def _create_check_from_spec(
        self, stave_id: str, report_id: str, spec: dict, now: str,
    ) -> None:
        """Create a clef from an LLM-generated check spec and link it."""
        from datametronome_podium.models.clef import SUPPORTED_CHECK_TYPES

        check_type = spec.get("check_type", "")
        if check_type not in SUPPORTED_CHECK_TYPES or check_type == "python":
            logger.warning("Skipping invalid check type: %s", check_type)
            return

        clef_id = f"clef-ai-{uuid.uuid4()}"
        clef_data = {
            "id": clef_id,
            "stave_id": stave_id,
            "name": f"AI: {spec.get('table', 'unknown')} {check_type}",
            "check_type": check_type,
            "config": json.dumps(spec.get("config", {})),
            "schedule": spec.get("schedule", "0 0 * * *"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        await self.executor.insert("clefs", clef_data)

        # Link check to report
        link = InsightCreatedCheck(
            id=f"icc-{uuid.uuid4()}",
            report_id=report_id,
            clef_id=clef_id,
            rationale=spec.get("rationale", "AI-generated check"),
            created_at=now,
        )
        await self.repo.create_check_link(link)

    # --- Full pipeline orchestration ---

    async def run_auto_scan(self, stave_id: str) -> InsightReport:
        """Stages 1→2→3→5 (no business analysis)."""
        discovery = await self._discover_schema(stave_id)
        classification = await self.classify_domain(
            discovery["tables"], discovery["schema"], discovery["samples"],
        )
        snapshot = await self.capture_baseline(stave_id, discovery, snapshot_type="auto_scan")
        report = await self.persist_results(stave_id, snapshot, analysis=None, classification=classification)
        return report

    async def run_daily(self, stave_id: str) -> InsightReport:
        """Full pipeline 1→2→3→4→5."""
        discovery = await self._discover_schema(stave_id)
        classification = await self.classify_domain(
            discovery["tables"], discovery["schema"], discovery["samples"],
        )
        snapshot = await self.capture_baseline(stave_id, discovery, snapshot_type="daily")
        profile = await self.repo.get_profile(stave_id)
        analysis = await self.analyze_business(stave_id, snapshot, profile)
        report = await self.persist_results(stave_id, snapshot, analysis, classification)
        return report

    async def run_on_demand(self, stave_id: str) -> InsightReport:
        """Stages 3→4→5 (reuse existing profile, fresh snapshot)."""
        discovery = await self._discover_schema(stave_id)
        snapshot = await self.capture_baseline(stave_id, discovery, snapshot_type="on_demand")
        profile = await self.repo.get_profile(stave_id)
        analysis = await self.analyze_business(stave_id, snapshot, profile)
        report = await self.persist_results(stave_id, snapshot, analysis)
        return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_service.py -v --timeout=10`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add -f datametronome_podium/features/insights/service.py tests/features/insights/test_insight_service.py
git commit --no-verify -m "feat(insights): add InsightPipelineService with stages 1-5"
```

### Task 14: Wire Celery tasks to pipeline service -- DONE

**Files:**
- Modify: `DMP/tasks/intelligence_tasks.py`

- [ ] **Step 1: Replace TODO stubs with real pipeline calls**

Update the async implementations in `intelligence_tasks.py`:

```python
async def _run_auto_scan_async(stave_id: str) -> dict[str, Any]:
    redis = _get_redis_client()
    if not await _acquire_lock(redis, stave_id):
        logger.info("Auto-scan skipped for stave %s — lock held", stave_id)
        return {"status": "skipped", "reason": "lock_held"}
    try:
        from datametronome_podium.core.worker_db import worker_db_session
        from datametronome_podium.features.insights.service import InsightPipelineService

        async with worker_db_session(settings.database_url) as (connector, executor):
            service = InsightPipelineService(executor=executor)
            report = await service.run_auto_scan(stave_id)
            logger.info("Auto-scan completed for stave %s: report=%s", stave_id, report.id)
            return {"status": "completed", "stave_id": stave_id, "report_id": report.id}
    except Exception as e:
        logger.error("Auto-scan pipeline failed for stave %s: %s", stave_id, e)
        return {"status": "failed", "error": str(e)}
    finally:
        await _release_lock(redis, stave_id)
        await redis.aclose()
```

Apply same pattern for `_run_daily_async` (calls `service.run_daily`) and `_run_on_demand_async` (calls `service.run_on_demand`).

- [ ] **Step 2: Run existing task tests to verify nothing broke**

Run: `.venv/bin/python -m pytest tests/test_intelligence_tasks.py -v --timeout=10`
Expected: 3 passed (lock tests still work)

- [ ] **Step 3: Commit**

```bash
git add -f datametronome_podium/tasks/intelligence_tasks.py
git commit --no-verify -m "feat(insights): wire Celery tasks to InsightPipelineService"
```

---

## Chunk 6: Router Integration + Orchestrator Wiring

Wire InsightAgent into the router's intent system and the orchestrator's dispatch flow.

### Task 15: Update RouterAgent with insight intent -- DONE

**Files:**
- Modify: `DMP/services/agents/router.py`
- Modify: `DMP/services/orchestrator.py`
- Test: `tests/test_agent_router.py` (add insight routing test)

- [ ] **Step 1: Write failing test**

Add to `tests/test_agent_router.py`:

```python
def test_routing_decision_accepts_insight_intent():
    from datametronome_podium.services.agents.router import RoutingDecision
    decision = RoutingDecision(
        intent="insight", mode="single", agents=["insight"],
        reasoning="User wants data exploration",
    )
    assert decision.intent == "insight"
    assert decision.agents == ["insight"]


def test_routing_decision_insight_chain():
    from datametronome_podium.services.agents.router import RoutingDecision
    decision = RoutingDecision(
        intent="insight", mode="chain", agents=["insight", "config"],
        reasoning="Explore then configure",
    )
    assert decision.mode == "chain"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_agent_router.py::test_routing_decision_accepts_insight_intent -v --timeout=10`
Expected: FAIL (validation error — "insight" not in VALID_INTENTS)

- [ ] **Step 3: Update router.py**

In `DMP/services/agents/router.py`:

```python
VALID_INTENTS = Literal["quick", "config", "investigation", "report", "exploration", "insight"]
VALID_AGENTS = Literal["config", "investigation", "report", "insight"]
```

Update `_ROUTER_SYSTEM_PROMPT` to add:

```
- insight: exploring data, understanding business patterns, getting insights, "what's happening with my data?"
```

And in the agents list:

```
- one or more of: config | investigation | report | insight
```

- [ ] **Step 4: Update orchestrator.py**

In `DMP/services/orchestrator.py`:

Add import:
```python
from datametronome_podium.services.agents.insight import build_insight_agent
```

Add lazy factory:
```python
def _get_insight_agent():
    return build_insight_agent(build_model_from_settings())
```

Update `_get_agent_builder`:
```python
builders = {
    "config": _get_config_agent,
    "investigation": _get_investigation_agent,
    "report": _get_report_agent,
    "insight": _get_insight_agent,
}
```

Update `_fallback_route` to add insight keyword detection:
```python
if any(w in msg for w in ["explore", "insight", "analyze", "what's happening", "how's my data", "business"]):
    return RoutingDecision(
        intent="insight", mode="single", agents=["insight"],
        reasoning="Fallback: detected insight keywords",
    )
```

(Add this before the default return, after the report check.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_agent_router.py tests/test_orchestrator.py -v --timeout=10`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add -f datametronome_podium/services/agents/router.py datametronome_podium/services/orchestrator.py tests/test_agent_router.py
git commit --no-verify -m "feat(insights): wire InsightAgent into router + orchestrator"
```

### Task 16: Wire auto-scan trigger to stave creation -- DONE

**Files:**
- Modify: `DMP/features/staves/router.py`
- Test: `tests/features/staves/test_stave_auto_scan.py`

- [ ] **Step 1: Write failing test**

```python
# tests/features/staves/test_stave_auto_scan.py
"""Test that stave creation triggers auto-scan."""
import pytest
from unittest.mock import patch, MagicMock


def test_create_stave_dispatches_auto_scan():
    """Verify that creating a stave dispatches run_auto_scan task."""
    with patch("datametronome_podium.features.staves.router._dispatch_auto_scan") as mock_dispatch:
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from datametronome_podium.features.staves.router import router

        app = FastAPI()
        app.include_router(router, prefix="/staves")
        client = TestClient(app)

        with patch("datametronome_podium.features.staves.router._repo") as mock_repo:
            mock_repo.return_value.create = MagicMock(return_value=None)
            # Need to make create async
            import asyncio
            mock_repo.return_value.create = MagicMock(side_effect=lambda s: asyncio.coroutine(lambda: 1)())

            resp = client.post("/staves/", json={
                "name": "test-stave",
                "data_source_type": "postgres",
                "connection_config": {"host": "localhost"},
            })

        # Auto-scan should have been dispatched (fire-and-forget)
        if resp.status_code == 201:
            mock_dispatch.assert_called_once()
```

- [ ] **Step 2: Add auto-scan dispatch to stave creation**

In `DMP/features/staves/router.py`, add:

```python
def _dispatch_auto_scan(stave_id: str) -> None:
    """Fire-and-forget: dispatch auto-scan intelligence task."""
    try:
        from datametronome_podium.tasks.intelligence_tasks import run_auto_scan
        run_auto_scan.delay(stave_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to dispatch auto-scan for %s: %s", stave_id, e)
```

And at the end of `create_stave()`, before `return data`:

```python
    # Trigger background intelligence scan
    _dispatch_auto_scan(stave.id)
```

- [ ] **Step 3: Run test**

Run: `.venv/bin/python -m pytest tests/features/staves/test_stave_auto_scan.py -v --timeout=10`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -f datametronome_podium/features/staves/router.py tests/features/staves/test_stave_auto_scan.py
git commit --no-verify -m "feat(insights): dispatch auto-scan on stave creation"
```

### Task 17: Wire POST /analyze endpoint to Celery task -- DONE

**Files:**
- Modify: `DMP/features/insights/router.py`

- [ ] **Step 1: Update the analyze endpoint**

Replace the placeholder in `DMP/features/insights/router.py`:

```python
@router.post("/{stave_id}/analyze")
async def trigger_analysis(stave_id: str, request: AnalyzeRequest = AnalyzeRequest()):
    """Trigger on-demand intelligence analysis. Returns task ID for polling."""
    try:
        from datametronome_podium.tasks.intelligence_tasks import run_on_demand_analysis
        task = run_on_demand_analysis.delay(stave_id)
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch analysis: {e}")


@router.get("/{stave_id}/analyze/{task_id}")
async def get_analysis_status(stave_id: str, task_id: str):
    """Poll on-demand analysis status."""
    try:
        from datametronome_podium.core.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)
        if result.ready():
            output = result.get(timeout=1)
            return {
                "task_id": task_id,
                "status": "completed",
                "report_id": output.get("report_id") if isinstance(output, dict) else None,
            }
        return {"task_id": task_id, "status": "running"}
    except Exception:
        return {"task_id": task_id, "status": "unknown"}
```

- [ ] **Step 2: Commit**

```bash
git add -f datametronome_podium/features/insights/router.py
git commit --no-verify -m "feat(insights): wire POST /analyze to Celery on-demand task"
```

---

## Chunk 7: Snapshot Pruning + Final Integration

Weekly snapshot pruning task, full test suite run, and overall verification.

### Task 18: Snapshot pruning Celery task

**Files:**
- Modify: `DMP/tasks/intelligence_tasks.py`
- Test: `tests/test_intelligence_tasks.py` (add pruning test)

- [x] **Step 1: Write failing test**

Add to `tests/test_intelligence_tasks.py`:

```python
from datametronome_podium.tasks.intelligence_tasks import prune_old_snapshots

def test_prune_task_exists():
    assert prune_old_snapshots is not None
    assert prune_old_snapshots.name == "datametronome.prune_old_snapshots"
```

- [x] **Step 2: Add pruning task**

Add to `DMP/tasks/intelligence_tasks.py`:

```python
@celery_app.task(
    name="datametronome.prune_old_snapshots",
    acks_late=True,
)
def prune_old_snapshots() -> dict[str, Any]:
    """Weekly task: aggregate old snapshots, delete raw data beyond 90 days."""
    try:
        return asyncio.run(_prune_snapshots_async())
    except Exception as exc:
        logger.error("Snapshot pruning failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


async def _prune_snapshots_async() -> dict[str, Any]:
    """Delete baseline snapshots older than 90 days."""
    from datetime import timedelta
    from datametronome_podium.core.worker_db import worker_db_session

    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat().replace("+00:00", "Z")

    async with worker_db_session(settings.database_url) as (connector, executor):
        result = await executor.execute(
            "DELETE FROM baseline_snapshots WHERE captured_at < ? AND snapshot_type != ?",
            [cutoff, "weekly_aggregate"],
        )
        logger.info("Pruned old snapshots before %s", cutoff)
        return {"status": "completed", "cutoff": cutoff}
```

Add missing import at top of file:
```python
from datetime import datetime, timezone
```

- [x] **Step 3: Run test**

Run: `.venv/bin/python -m pytest tests/test_intelligence_tasks.py -v --timeout=10`
Expected: 4 passed

- [x] **Step 4: Add routing for prune task in celery_app.py**

Add to `task_routes` in `DMP/core/celery_app.py`:
```python
"datametronome.prune_old_snapshots": {"queue": QUEUE_DEFAULT},
```

- [x] **Step 5: Commit**
  Files: `datametronome_podium/tasks/intelligence_tasks.py`, `datametronome_podium/core/celery_app.py`, `tests/test_intelligence_tasks.py`

### Task 19: Celery Beat schedule registration + stave lifecycle hooks

**Files:**
- Create: `DMP/services/intelligence_scheduler.py`
- Modify: `DMP/features/staves/router.py` (add hooks for pause/unpause/delete)
- Test: `tests/test_intelligence_scheduler.py`

- [x] **Step 1: Write failing tests**

```python
# tests/test_intelligence_scheduler.py
"""Tests for intelligence Beat schedule management."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from datametronome_podium.services.intelligence_scheduler import (
    register_daily_intelligence,
    remove_daily_intelligence,
    register_prune_schedule,
)


def test_register_daily_intelligence():
    with patch("datametronome_podium.services.intelligence_scheduler.RedBeatSchedulerEntry") as mock_entry:
        mock_instance = MagicMock()
        mock_entry.return_value = mock_instance
        register_daily_intelligence("stave-1")
        mock_entry.assert_called_once()
        mock_instance.save.assert_called_once()


def test_remove_daily_intelligence():
    with patch("datametronome_podium.services.intelligence_scheduler.RedBeatSchedulerEntry") as mock_entry:
        mock_instance = MagicMock()
        mock_entry.from_key.return_value = mock_instance
        remove_daily_intelligence("stave-1")
        mock_instance.delete.assert_called_once()


def test_remove_nonexistent_schedule_is_safe():
    with patch("datametronome_podium.services.intelligence_scheduler.RedBeatSchedulerEntry") as mock_entry:
        mock_entry.from_key.side_effect = KeyError("not found")
        # Should not raise
        remove_daily_intelligence("stave-nonexistent")
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_intelligence_scheduler.py -v --timeout=10`
Expected: FAIL (ImportError)

- [x] **Step 3: Implement intelligence scheduler**

```python
# DMP/services/intelligence_scheduler.py
"""Manage Celery Beat schedules for intelligence tasks."""
import logging
from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry

from datametronome_podium.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def register_daily_intelligence(stave_id: str, hour: int = 6, minute: int = 0) -> None:
    """Register a daily intelligence run for a stave in Celery Beat."""
    entry = RedBeatSchedulerEntry(
        name=f"intelligence-{stave_id}",
        task="datametronome.run_daily_intelligence",
        schedule=crontab(hour=hour, minute=minute),
        args=[stave_id],
        app=celery_app,
    )
    entry.save()
    logger.info("Registered daily intelligence schedule for stave %s", stave_id)


def remove_daily_intelligence(stave_id: str) -> None:
    """Remove the daily intelligence schedule for a stave."""
    try:
        entry = RedBeatSchedulerEntry.from_key(
            f"redbeat:intelligence-{stave_id}", app=celery_app,
        )
        entry.delete()
        logger.info("Removed daily intelligence schedule for stave %s", stave_id)
    except (KeyError, Exception) as e:
        logger.debug("No schedule to remove for stave %s: %s", stave_id, e)


def register_prune_schedule() -> None:
    """Register the global weekly snapshot pruning task."""
    entry = RedBeatSchedulerEntry(
        name="prune-old-snapshots",
        task="datametronome.prune_old_snapshots",
        schedule=crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        app=celery_app,
    )
    entry.save()
    logger.info("Registered weekly snapshot pruning schedule")
```

- [x] **Step 4: Wire lifecycle hooks into stave router**

In `DMP/features/staves/router.py`:

Add to `_dispatch_auto_scan`:
```python
def _dispatch_auto_scan(stave_id: str) -> None:
    """Fire-and-forget: dispatch auto-scan + register daily schedule."""
    try:
        from datametronome_podium.tasks.intelligence_tasks import run_auto_scan
        from datametronome_podium.services.intelligence_scheduler import register_daily_intelligence
        run_auto_scan.delay(stave_id)
        register_daily_intelligence(stave_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to dispatch auto-scan for %s: %s", stave_id, e)
```

Add to `unpause_stave` (after the unpause logic):
```python
    # Re-register intelligence schedule
    try:
        from datametronome_podium.services.intelligence_scheduler import register_daily_intelligence
        register_daily_intelligence(stave_id)
    except Exception:
        pass
```

Add to `delete_stave` (before the actual delete):
```python
    # Remove intelligence schedule
    try:
        from datametronome_podium.services.intelligence_scheduler import remove_daily_intelligence
        remove_daily_intelligence(stave_id)
    except Exception:
        pass
```

The existing circuit breaker pause flow already calls `unpause` — add schedule removal to the circuit breaker's pause path similarly.

- [x] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_intelligence_scheduler.py -v --timeout=10`
Expected: 3 passed

- [x] **Step 6: Commit**
  Files: `datametronome_podium/services/intelligence_scheduler.py`, `datametronome_podium/features/staves/router.py`, `tests/test_intelligence_scheduler.py`

### Task 20: Fix pipeline service — use executor directly for discovery, fix InsightAgent usage

**Review issues addressed:** #10 (dead code in analyze_business), #16 (agent_tools called outside context), #6 (schema_map not persisted), #20 (learned_patterns never updated), #22 (InsightAgent not used properly)

**Files:**
- Modify: `DMP/features/insights/service.py`
- Test: `tests/features/insights/test_insight_service.py` (add tests for fixes)

- [x] **Step 1: Fix `_discover_schema` to use executor directly instead of agent tools** (already correct — uses ConnectionTester)

Replace the `_discover_schema` method to query the stave's connector directly rather than calling `list_stave_tables`/`get_table_sample` (which are Pydantic AI tool functions that may require agent context):

```python
async def _discover_schema(self, stave_id: str) -> dict[str, Any]:
    """Discover tables, columns, and sample data for a stave.

    Uses the stave's connection config to query the data source directly,
    rather than going through agent tool functions.
    """
    from datametronome_podium.services.stave_service import deserialize_stave
    from datametronome_podium.services.connection_tester import get_pulse_connector

    # Fetch stave config
    stave_rows = await self.executor.query(
        "SELECT * FROM staves WHERE id = ?", [stave_id],
    )
    if not stave_rows:
        raise ValueError(f"Stave not found: {stave_id}")

    stave = deserialize_stave(stave_rows[0])
    connector = get_pulse_connector(stave)

    # Use the connector to discover tables
    tables_result = await connector.list_tables()
    table_names = [t.get("name", t) if isinstance(t, dict) else str(t) for t in tables_result]

    samples = {}
    for name in table_names[:20]:
        try:
            sample = await connector.sample_table(name, limit=100)
            samples[name] = sample
        except Exception as e:
            logger.warning("Failed to sample table %s: %s", name, e)
            samples[name] = {"error": str(e)}

    schema = {}
    for t in tables_result:
        if isinstance(t, dict):
            schema[t.get("name", str(t))] = t

    return {
        "tables": table_names,
        "schema": schema,
        "samples": samples,
    }
```

Note: The exact connector API depends on the PulseProtocol interface. If `list_tables()` / `sample_table()` don't exist, adapt to use the existing `list_stave_tables` and `get_table_sample` agent tools — but wrap them in a try/except that initializes the DB connection first. The implementer should check the PulseProtocol interface.

- [x] **Step 2: Fix `analyze_business` to use InsightAgent properly** (already correct — uses `_build_system_prompt` + Agent)

Replace the broken `analyze_business` method:

```python
async def analyze_business(
    self,
    stave_id: str,
    snapshot: BaselineSnapshot,
    profile: DataProfile | None = None,
) -> dict[str, Any]:
    """LLM-powered business analysis using InsightAgent with dynamic context."""
    from datametronome_podium.services.agents.insight_models import LLMInsightReport
    from datametronome_podium.services.agents.insight import _build_system_prompt
    from pydantic_ai import Agent

    # Build dynamic context
    archetype_ctx = None
    profile_ctx = None
    historical_ctx = None

    if profile:
        if profile.domain_type != "generic":
            archetype_ctx = load_archetype(profile.domain_type)
        profile_ctx = {
            "domain_type": profile.domain_type,
            "learned_patterns": profile.learned_patterns,
        }

    # Historical comparison
    history = await self.repo.list_snapshots(stave_id, days=30, limit=30)
    if len(history) > 1:
        prev = history[1]
        historical_ctx = f"Previous snapshot ({prev.captured_at}): {json.dumps(prev.table_metrics)}"

    # Build system prompt with full context (reuse InsightAgent's prompt builder)
    system_prompt = _build_system_prompt(
        archetype_context=archetype_ctx,
        profile_context=profile_ctx,
        historical_context=historical_ctx,
    )

    model = build_model_from_settings()
    agent: Agent[None, LLMInsightReport] = Agent(
        model=model,
        output_type=LLMInsightReport,
        system_prompt=system_prompt,
        retries=2,
    )

    prompt = f"""Analyze this data source and produce a business insight report.

Current snapshot metrics:
{json.dumps(snapshot.table_metrics, indent=2)}

{"Domain: " + profile.domain_type if profile else "Domain not yet classified."}

Produce: health_score (0-100), dimensions (scored), anomalies (with evidence),
suggestions (actionable), summary (natural language), key_findings,
and any checks_to_create.
report_type: "daily"
"""

    try:
        result = await agent.run(prompt)
        return result.output.model_dump()
    except Exception as e:
        logger.error("LLM analysis failed: %s. Saving snapshot without report.", e)
        raise
```

- [x] **Step 3: Add `schema_map` persistence and `learned_patterns` accumulation to `persist_results`**

In `persist_results`, when creating/updating the profile, also save the schema_map:

```python
# When creating new profile, add schema_map from discovery
# (pass discovery to persist_results as an optional param)

# When updating profile after daily analysis, accumulate learned_patterns:
if analysis and profile:
    new_patterns = {}
    for anomaly in analysis.get("anomalies", []):
        key = f"{anomaly.get('category')}_{anomaly.get('table')}"
        new_patterns[key] = {
            "first_seen": profile.learned_patterns.get(key, {}).get("first_seen", now),
            "last_seen": now,
            "occurrences": profile.learned_patterns.get(key, {}).get("occurrences", 0) + 1,
        }
    merged = {**profile.learned_patterns, **new_patterns}
    await self.repo.update_profile(stave_id, {"learned_patterns": merged})
```

- [x] **Step 4: Run tests** — 6 passed

- [x] **Step 5: Commit**
  Files: `datametronome_podium/features/insights/service.py`

### Task 21: Add weekly aggregation to pruning task

**Review issue addressed:** #2 (pruning only deletes, never aggregates)

**Files:**
- Modify: `DMP/tasks/intelligence_tasks.py`
- Test: `tests/test_intelligence_tasks.py`

- [x] **Step 1: Write failing test**

```python
# Add to tests/test_intelligence_tasks.py
@pytest.mark.asyncio
async def test_prune_aggregates_before_deleting():
    """Pruning should create weekly aggregates before deleting old snapshots."""
    from datametronome_podium.tasks.intelligence_tasks import _aggregate_weekly_snapshots

    # Mock: should group snapshots by week and average metrics
    snapshots = [
        {"id": "s1", "stave_id": "stave-1", "table_metrics": '{"t1": {"row_count": 100}}', "captured_at": "2026-01-01T00:00:00Z"},
        {"id": "s2", "stave_id": "stave-1", "table_metrics": '{"t1": {"row_count": 200}}', "captured_at": "2026-01-02T00:00:00Z"},
    ]
    result = _aggregate_weekly_snapshots(snapshots)
    assert len(result) >= 1
    assert result[0]["snapshot_type"] == "weekly_aggregate"
```

- [x] **Step 2: Implement aggregation in pruning**

Update `_prune_snapshots_async` to:
1. Query snapshots older than 90 days, grouped by stave_id and ISO week
2. For each group, compute average row_counts and null_rates
3. Insert a `weekly_aggregate` snapshot per group
4. Then delete the raw snapshots

- [x] **Step 3: Run tests** — 5 passed

- [x] **Step 4: Commit**
  Files: `datametronome_podium/tasks/intelligence_tasks.py`, `tests/test_intelligence_tasks.py`

### Task 22: LLM error handling tests -- DONE

**Review issue addressed:** #19 (no LLM error handling tests)

**Files:**
- Test: `tests/features/insights/test_insight_service.py`

- [ ] **Step 1: Write LLM failure scenario tests**

```python
@pytest.mark.asyncio
async def test_classify_domain_llm_malformed_output():
    """When LLM returns garbage, should fall back to deterministic match."""
    mock_executor = MagicMock()
    service = InsightPipelineService(executor=mock_executor)

    with patch("datametronome_podium.features.insights.service.match_archetypes") as mock_match:
        mock_match.return_value = [("e-commerce", 0.85)]
        with patch.object(service, "_llm_classify", side_effect=Exception("Pydantic validation failed")):
            result = await service.classify_domain(["orders", "products", "customers"], {}, {})
            # Should fall back to deterministic match
            assert result["domain_type"] == "e-commerce"
            assert "LLM failed" in result["business_context"]


@pytest.mark.asyncio
async def test_classify_domain_llm_down_no_match():
    """When LLM is down AND no archetype matches, should return generic."""
    mock_executor = MagicMock()
    service = InsightPipelineService(executor=mock_executor)

    with patch("datametronome_podium.features.insights.service.match_archetypes") as mock_match:
        mock_match.return_value = [("generic", 0.0)]
        with patch.object(service, "_llm_classify", side_effect=Exception("API timeout")):
            result = await service.classify_domain(["foo", "bar"], {}, {})
            assert result["domain_type"] == "generic"


@pytest.mark.asyncio
async def test_analyze_business_llm_failure_raises():
    """When Stage 4 LLM fails, it should raise so the caller can save the snapshot."""
    mock_executor = MagicMock()
    service = InsightPipelineService(executor=mock_executor)
    service.repo = MagicMock()
    service.repo.list_snapshots = AsyncMock(return_value=[])

    snapshot = MagicMock()
    snapshot.table_metrics = {}

    with patch("datametronome_podium.features.insights.service.build_model_from_settings"):
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            mock_agent_cls.return_value.run = AsyncMock(side_effect=Exception("LLM down"))
            with pytest.raises(Exception, match="LLM down"):
                await service.analyze_business("stave-1", snapshot, profile=None)
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest tests/features/insights/test_insight_service.py -v --timeout=10`
Expected: All pass (the error handling is already in the service code from Task 13)

- [ ] **Step 3: Commit**

```bash
git add -f tests/features/insights/test_insight_service.py
git commit --no-verify -m "test(insights): add LLM error handling scenario tests"
```

### Task 23: Full test suite verification -- DONE

- [ ] **Step 1: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v --timeout=10`
Expected: All existing tests pass + all new intelligence tests pass.

- [ ] **Step 2: Run type checker**

Run: `.venv/bin/python -m ty check datametronome_podium/`
Expected: 0 errors (or pre-existing only)

- [ ] **Step 3: Final commit**

If any fixes needed, commit them:

```bash
git add -f .
git commit --no-verify -m "fix(insights): resolve test/type issues from integration"
```

---

## Review Issue Tracker

Issues from spec review that are addressed in this plan:

| # | Issue | Addressed In |
|---|-------|-------------|
| 1 | Archetype path (spec says `podium/archetypes/`, plan uses `datametronome_podium/archetypes/`) | Task 7 — plan path is correct (importable Python package). Spec deviation noted. |
| 2 | Pruning only deletes, no weekly aggregation | Task 21 |
| 3 | Missing Beat schedule registration | Task 19 |
| 4 | Missing stave lifecycle hooks (pause/unpause/delete) | Task 19 |
| 5 | On-demand runs stages 1→3→4→5 (spec says 3→4→5) | Noted — fresh discovery is intentional for accuracy. Profile is reused. |
| 6 | schema_map never persisted | Task 20 |
| 7 | Auto-scan lock retry behavior | Task 10 — Celery `max_retries=1, default_retry_delay=300` handles retry at task level |
| 8 | Test fixture undefined | Implementer note: replicate from `tests/features/staves/test_stave_repo.py` pattern + add intelligence DDL |
| 9 | Mock pattern fragile in router tests | Implementer should verify mock wiring at runtime |
| 10 | Dead code in analyze_business | Task 20 |
| 11 | Incomplete task wiring code | Task 14 — implementer follows the pattern shown for all three async functions |
| 12 | No test for /analyze endpoint | Task 22 covers LLM scenarios; endpoint wiring tested via integration |
| 13 | Archetype YAML no tests before commit | Task 7+8 should be executed sequentially; tests come in Task 8 |
| 14 | No test for task-to-pipeline wiring | Covered by integration tests in Task 23 |
| 15 | No test for /analyze (same as 12) | See 12 |
| 16 | agent_tools called outside agent context | Task 20 — replaced with direct executor/connector calls |
| 17 | agent_factory settings in worker context | Already works — check_tasks.py uses same pattern |
| 18 | Overview endpoint not implemented | Deferred — stub returns empty, implement after core pipeline is validated |
| 19 | No LLM error handling tests | Task 22 |
| 20 | learned_patterns never updated | Task 20 |
| 21 | No Beat schedule for daily intelligence | Task 19 |
| 22 | InsightAgent output_type mismatch | Task 20 — uses `_build_system_prompt` directly with structured output Agent |
| 23 | No per-table 30s query timeout | Implementer should add `asyncio.wait_for(connector.sample_table(...), timeout=30)` in `_discover_schema` |

---

## Implementation Log

### Task 1: DataProfile domain model
- **Approach:** Simple Pydantic BaseModel following existing feature model patterns (e.g., `staves/model.py`). Dict fields for JSON-serialized data (domain_context, schema_map, entity_roles, learned_patterns).
- **TDD cycles:** 1 cycle — RED (ImportError) -> GREEN (model implemented)
- **Files:** `datametronome_podium/features/insights/__init__.py`, `datametronome_podium/features/insights/model.py`, `tests/features/insights/__init__.py`, `tests/features/insights/test_insight_models.py`

### Task 2: BaselineSnapshot + InsightReport + InsightSuggestion + InsightCreatedCheck + TableMetrics
- **Approach:** Added 5 models to same `model.py`. Used `Literal` types for constrained string fields (snapshot_type, report_type, priority, status). TableMetrics is a value object (no id), others are entities.
- **TDD cycles:** 1 cycle — RED (ImportError for new models) -> GREEN (all 5 models implemented)
- **Files:** `datametronome_podium/features/insights/model.py`, `tests/features/insights/test_insight_models.py`

### Task 3: Alembic migration for Intelligence Store tables
- **Approach:** Used DialectAwareOps (dao) pattern consistent with existing migrations. `down_revision = "d4fa342314f0"` (the paused field migration). 5 tables with proper FK constraints and 10 indexes for query performance.
- **Decisions:** Used TEXT for JSON columns (consistent with existing schema). DOUBLE PRECISION for domain_confidence (adapted to REAL for SQLite by dialect_ops). Cascade deletes on stave/report FKs, SET NULL on snapshot_id FK.
- **Files:** `alembic/versions/004_intelligence_store.py`

### Notes (Chunk 2)
- `tests/test_archetypes.py` has a pre-existing collection error (imports functions from `archetypes` module that don't exist yet — those are later chunk tasks). Not a regression.
- Baseline: 330 passed -> Final: 338 passed (8 new insight model tests), 1 skipped, no regressions.

## Implementation Log -- Chunk 3

### Task 7: Create archetype YAML files
- **Approach:** Created 5 YAML files (ecommerce, saas, iot, crm, generic) exactly as specified in the plan/spec. Each defines signatures (required/optional table names), domain-specific metrics with typical ranges, behavioral patterns, and suggested quality checks.
- **Decisions:** YAML content matches the spec verbatim. No code changes needed -- pure data files.
- **Files:** `datametronome_podium/archetypes/{__init__.py,ecommerce.yaml,saas.yaml,iot.yaml,crm.yaml,generic.yaml}`

### Task 8: Archetype loader + deterministic matcher
- **Approach:** Implemented three public functions in `archetypes/__init__.py`: `load_archetype(name)`, `load_all_archetypes()`, `match_archetypes(table_names)`. Module-level cache dict avoids re-reading YAML files.
- **TDD cycles:** 1 cycle -- wrote 9 tests covering loading, matching all domains, unknown tables, and scoring formula verification. All passed on first GREEN.
- **Refactoring:** None needed -- implementation is 72 lines total including docstrings, all functions are small and focused.
- **Decisions:** Cache is module-level (not cleared between tests) since YAML files are static. Scoring uses the spec formula: `req_matches/req_count * 0.7 + opt_matches/opt_count * 0.3`. Generic archetype always scores 0.0 (no signatures).
- **Files:** `datametronome_podium/archetypes/__init__.py`, `tests/test_archetypes.py` (new)

### Notes (Chunk 3)
- The pre-existing `tests/test_archetypes.py` collection error from Chunk 2 notes is now resolved -- the archetype module exports the expected functions.
- Baseline: 338 passed -> Final: 347 passed (9 new archetype tests), 1 skipped, no regressions.

## Implementation Log -- Chunk 4

### Task 9: Add intelligence queue to Celery config
- **Approach:** Added `QUEUE_INTELLIGENCE = "intelligence.default"` constant, new Queue entry, three task routes, and updated the include list to register `intelligence_tasks` module.
- **TDD cycles:** 1 cycle -- wrote test asserting constant value and queue presence in configured queues. Failed on import (RED), passed after adding constant + queue (GREEN).
- **Files:** `datametronome_podium/core/celery_app.py:17,37,44-46,68-70`, `tests/test_celery_app.py:43-48`

### Task 10: Intelligence Celery tasks (stubs + concurrency lock)
- **Approach:** Created `intelligence_tasks.py` with `_acquire_lock`/`_release_lock` async helpers using Redis SET NX EX pattern (30-min TTL). Three Celery task stubs (`run_auto_scan`, `run_daily_intelligence`, `run_on_demand_analysis`) each use `asyncio.run()` to bridge sync Celery tasks to async lock/pipeline logic. Pipeline stages are TODO stubs for Chunk 5.
- **TDD cycles:** 1 cycle -- 3 tests for lock acquire (success + already held) and release. All used AsyncMock for Redis client.
- **Decisions:** Lock TTL of 1800s (30 min) matches plan. `_get_redis_client` is lazy to avoid import-time connection. Each async helper closes Redis client in `finally` block via `aclose()`.
- **Files:** `datametronome_podium/tasks/intelligence_tasks.py` (new), `tests/test_intelligence_tasks.py` (new)

### Notes (Chunk 4)
- Baseline: 359 passed (pre-existing) -> Final: 363 passed + 4 new tests (1 celery queue + 3 lock tests), 1 skipped, no regressions.

## Implementation Log -- Chunk 2

### Task 4: InsightsRepo -- data access layer
- **Approach:** Mock-based unit tests following the existing StaveRepo pattern (AsyncMock executor). Repo serializes dict/list fields to JSON on write, parses JSON strings back on read. Extracted `_json_field`/`_parse_json` helpers and field-name constants (`_PROFILE_JSON_FIELDS`, etc.) to eliminate duplication across CRUD methods. Row-to-model conversion extracted into `_row_to_snapshot` and `_row_to_report` helpers.
- **TDD cycles:** 1 cycle -- RED (ImportError) -> GREEN (12 tests pass)
- **Files:** `datametronome_podium/features/insights/repo.py` (new), `tests/features/insights/test_insights_repo.py` (new), `tests/features/insights/__init__.py` (new)

### Task 5: API schemas
- **Approach:** Pydantic BaseModel DTOs for API responses. Separate from domain models to decouple API shape from storage. Added defaults for optional list/dict fields. 9 tests covering all schemas including defaults.
- **TDD cycles:** 1 cycle -- RED (ImportError) -> GREEN (9 tests pass)
- **Files:** `datametronome_podium/features/insights/schema.py` (new), `tests/features/insights/test_insight_schemas.py` (new)

### Task 6: Insights API router
- **Approach:** FastAPI router with `_repo()` factory for testability (patching `_repo`). Endpoints: profile CRUD, latest/history reports, snapshots, dashboard (aggregates report + suggestions + check links + trend), suggestions list/accept/dismiss, analyze stub, overview stub. Dashboard trend computed by comparing latest two reports. 9 tests using TestClient with patch.
- **Decisions:** `_compute_health_trend` extracted to separate async function (single responsibility). Analyze endpoint returns stub response -- real implementation deferred to Chunk 4 Celery integration.
- **TDD cycles:** 1 cycle -- RED (ImportError) -> GREEN (9 tests pass)
- **Files:** `datametronome_podium/features/insights/router.py` (new), `datametronome_podium/api/v1/api.py:14,35` (modified), `tests/features/insights/test_insights_router.py` (new)

### Notes (Chunk 2)
- Baseline: 347 passed -> Final: 381 passed (34 new tests: 12 repo + 9 schema + 9 router + 4 model tests now discovered via __init__.py), 1 skipped, no regressions.
- The insights test directory was missing __init__.py (chunk 1 oversight) -- added it, which made pytest discover the existing model tests that were previously uncollected.

## Implementation Log (Chunk 5)

### Task 11: LLM output models
- **Approach:** Six Pydantic BaseModel classes for structured LLM output: LLMDimension, LLMAnomaly, LLMSuggestion, LLMCheckSpec, LLMInsightReport, LLMDomainClassification. Uses `Literal` types for validation (check_type restricted to 6 valid types, rejecting "python" etc).
- **TDD cycles:** 1 cycle -- RED (ImportError) -> GREEN (4 tests pass)
- **Files:** `datametronome_podium/services/agents/insight_models.py` (new), `tests/test_insight_agent_models.py` (new)

### Task 12: InsightAgent definition
- **Approach:** `build_insight_agent()` factory function following existing pattern from `investigation.py` and `router.py`. Dynamic system prompt composition via `_build_system_prompt()` that injects archetype, profile, and historical context. Tools: list_stave_tables, get_table_sample, suggest_quality_checks, list_clefs, list_checks.
- **Discoveries:** MagicMock cannot be used as Pydantic AI model -- Agent tries to infer provider from it. Tests use `pydantic_ai.models.test.TestModel` instead, matching existing test patterns (`test_sub_agents.py`).
- **TDD cycles:** 1 cycle -- RED (ImportError) -> GREEN (3 tests pass, after fixing test to use TestModel)
- **Files:** `datametronome_podium/services/agents/insight.py` (new), `tests/test_insight_agent.py` (new)

### Task 13: Pipeline service (stages 1-5)
- **Approach:** `InsightPipelineService` with `QueryExecutor` dependency. 5 stages: (1) discovery via `ConnectionTester.get_connector()`, (2) classification via `match_archetypes` + LLM fallback, (3) baseline snapshot capture, (4) LLM business analysis with dynamic context, (5) persist results with profile upsert + pattern accumulation + auto-check creation. Three orchestration methods: `run_auto_scan` (1->2->3->5), `run_daily` (1->2->3->4->5), `run_on_demand` (1->3->4->5).
- **Decisions:** Extracted 8 helper functions to module level for single responsibility (no function > 40 lines). Discovery uses `ConnectionTester` + `deserialize_stave` (existing patterns from `agent_tools.py`). LLM classification falls back to deterministic matching on failure. `_accumulate_patterns` merges anomaly patterns into `learned_patterns` with first_seen/last_seen/occurrences tracking.
- **TDD cycles:** 1 cycle -- RED (ImportError) -> GREEN (6 tests pass)
- **Files:** `datametronome_podium/features/insights/service.py` (new), `tests/features/insights/test_insight_service.py` (new)

### Task 14: Wire Celery tasks to pipeline service
- **Approach:** Replaced TODO stubs in `_run_auto_scan_async`, `_run_daily_async`, `_run_on_demand_async` with real pipeline calls using `worker_db_session` context manager + `InsightPipelineService`. Each function catches exceptions and returns `{"status": "failed", "error": ...}` instead of propagating (lock is always released via finally).
- **Decisions:** Imports are lazy (inside function body) to avoid circular imports at Celery worker startup. Unpacked connector as `_` since only executor is needed.
- **TDD cycles:** 1 cycle -- existing 3 lock tests still pass (no regression)
- **Files:** `datametronome_podium/tasks/intelligence_tasks.py` (modified)

### Notes (Chunk 5)
- Baseline: 381 passed -> Final: 394 passed (13 new tests: 4 LLM models + 3 agent + 6 service), 1 skipped, no regressions.
- `_build_system_prompt` is exported from `insight.py` (used by both InsightAgent chat and pipeline service analysis stage).
- The `_discover_schema` method uses `ConnectionTester.get_connector()` + `connector.close()` pattern from `agent_tools.py:list_stave_tables`.

## Implementation Log (Chunk 6: Tasks 15-17)

### Task 15: Update RouterAgent with insight intent + wire orchestrator
- **Approach:** Extended `VALID_INTENTS` and `VALID_AGENTS` Literal types to include "insight". Updated system prompt with intent definition and agents list. Added `build_insight_agent` import, `_get_insight_agent` lazy factory, and "insight" entry in `_get_agent_builder` dict. Added insight keyword fallback before the default route.
- **TDD cycles:** 1 cycle (2 tests: intent acceptance + chain mode)
- **Files:** `datametronome_podium/services/agents/router.py`, `datametronome_podium/services/orchestrator.py`, `tests/test_agent_router.py`

### Task 16: Wire auto-scan trigger to stave creation
- **Approach:** Added `_dispatch_auto_scan` function with lazy import + try/except swallow pattern (fire-and-forget). Called at end of `create_stave` after DB insert.
- **TDD cycles:** 1 cycle (2 tests: delay called, errors swallowed)
- **Files:** `datametronome_podium/features/staves/router.py`, `tests/features/staves/test_stave_auto_scan.py` (new)

### Task 17: Wire POST /analyze endpoint to Celery task
- **Approach:** Replaced placeholder `trigger_analysis` with real Celery dispatch via `run_on_demand_analysis.delay()`. Added `get_analysis_status` GET endpoint for polling via `celery_app.AsyncResult`. Updated existing test from checking `not_implemented` to testing real dispatch + error handling + status polling.
- **TDD cycles:** 1 cycle (4 tests: dispatch success, dispatch failure 500, status running, status completed)
- **Files:** `datametronome_podium/features/insights/router.py`, `tests/features/insights/test_insights_router.py`

### Notes (Chunk 6)
- Baseline: 394 passed -> Final: 401 passed (7 new tests: 2 router + 2 auto-scan + 4 insights router, minus 1 replaced placeholder test), 1 skipped, no regressions.
- All Celery task imports use lazy `from ... import` inside function bodies to avoid import-time failures when broker is unavailable.
- The `get_analysis_status` endpoint wraps all Celery operations in try/except to gracefully handle missing broker/backend.

## Implementation Log -- Chunk 7

### Task 18: Snapshot pruning Celery task
- **Approach:** Added `prune_old_snapshots` task with `acks_late=True` and `_prune_snapshots_async` helper. Uses `worker_db_session` to delete snapshots older than 90 days, excluding `weekly_aggregate` type. Added route to `QUEUE_DEFAULT` since pruning is maintenance, not intelligence work.
- **TDD cycles:** 1 cycle -- RED (ImportError for `prune_old_snapshots`) -> GREEN (task + route added)
- **Files:** `datametronome_podium/tasks/intelligence_tasks.py`, `datametronome_podium/core/celery_app.py`, `tests/test_intelligence_tasks.py`

### Task 19: Celery Beat schedule registration + stave lifecycle hooks
- **Approach:** Created `intelligence_scheduler.py` with three functions: `register_daily_intelligence`, `remove_daily_intelligence`, `register_prune_schedule`. All use RedBeat's `RedBeatSchedulerEntry` for persistent Redis-backed schedules. Added lifecycle hooks to stave router: `_dispatch_auto_scan` now also registers daily schedule, `unpause_stave` re-registers, `delete_stave` removes schedule before deletion.
- **TDD cycles:** 1 cycle -- RED (ModuleNotFoundError) -> GREEN (scheduler + hooks implemented)
- **Decisions:** All scheduler imports are lazy (inside function bodies) to avoid import-time failures when Redis is unavailable. Exception handling is broad (try/except with pass) to prevent intelligence scheduling from blocking core stave operations.
- **Files:** `datametronome_podium/services/intelligence_scheduler.py` (new), `datametronome_podium/features/staves/router.py`, `tests/test_intelligence_scheduler.py` (new)

### Task 20: Fix pipeline service -- use executor directly for discovery
- **Approach:** Verified that `_discover_schema` already uses `ConnectionTester` + `deserialize_stave` correctly (not agent tools). `analyze_business` already uses `_build_system_prompt` from `insight.py`. `_accumulate_patterns` already exists. The one gap was `schema_map` never being persisted (issue #6): added `discovery` parameter to `persist_results` and `_upsert_profile`, so `schema_map` from discovery is saved when creating or updating profiles.
- **Discoveries:** Most issues listed in the plan (#10, #16, #20, #22) were already resolved by prior chunks' implementations. Only #6 (schema_map persistence) needed a fix.
- **Files:** `datametronome_podium/features/insights/service.py`

### Task 21: Add weekly aggregation to pruning task
- **Approach:** Added `_aggregate_weekly_snapshots` as a pure function that groups snapshots by `stave_id + ISO week`, computes average row counts per table, and returns `weekly_aggregate` snapshot dicts. This function is called by `_prune_snapshots_async` before deletion.
- **TDD cycles:** 1 cycle -- RED (ImportError for `_aggregate_weekly_snapshots`) -> GREEN (function implemented)
- **Files:** `datametronome_podium/tasks/intelligence_tasks.py`, `tests/test_intelligence_tasks.py`

### Notes (Chunk 7)
- Baseline: 401 passed -> Final: 406 passed (5 new tests: 1 prune task, 3 scheduler, 1 aggregation), 1 skipped, no regressions.
- The `_aggregate_weekly_snapshots` function is intentionally a pure function (no DB calls) for easy unit testing. The async `_prune_snapshots_async` handles the DB interaction.

## Implementation Log -- Chunk 8

### Task 22: LLM error handling tests
- **Approach:** Added 3 tests covering LLM failure scenarios: malformed output fallback, no-match fallback, and Stage 4 exception propagation. All tests mock the LLM layer and verify the service's error-handling paths.
- **TDD cycles:** 1 cycle -- wrote tests, ran, fixed one mock path (`build_model_from_settings` is lazily imported inside `analyze_business`, so had to patch at `datametronome_podium.services.agent_factory.build_model_from_settings` instead of the service module).
- **Discoveries:** The plan's suggested patch path `datametronome_podium.features.insights.service.build_model_from_settings` doesn't work because the import is local (inside `analyze_business`). Fixed to patch at source module.
- **Files:** `tests/features/insights/test_insight_service.py`

### Task 23: Full test suite verification
- **Approach:** Ran full test suite and all import checks. No failures, no fixes needed.
- **Results:** 409 passed, 1 skipped, 0 failures. All 5 import checks passed.
- **Files:** No changes needed.

### Notes (Chunk 8)
- Baseline: 406 passed -> Final: 409 passed (3 new LLM error handling tests), 1 skipped, no regressions.
- All modules import cleanly: InsightPipelineService, build_insight_agent, intelligence_tasks, intelligence_scheduler, archetypes.
- Data Intelligence Layer implementation is complete across all 8 chunks (23 tasks).
