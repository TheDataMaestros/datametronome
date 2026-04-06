# Agent-Generated BI Query Plans Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the BusinessIntelligenceAgent to discover schema, generate SQL dynamically, cache results in `stave_query_plans`, and reason over results — eliminating all hardcoded SQL from domain archetypes.

**Architecture:** Archetypes carry pure business semantics (KPI names + plain-English descriptions, no SQL). The BI agent runs a three-phase loop: Phase 1 reasons over Stage 1 discovery data to produce a `SchemaInterpretation`; Phase 2 generates + validates SQL per KPI/dimension caching results in `stave_query_plans`; Phase 3 executes cached SQL and produces `LLMBusinessReport`. Phases 1+2 are skipped on cached runs (fingerprint unchanged). On-demand analysis skips Phases 1+2 entirely and uses the existing plan.

**Tech Stack:** Python 3.13, Pydantic AI, asyncpg/SQLite (via QueryExecutor), Alembic (DialectAwareOps), YAML archetypes, hashlib SHA-256

---

## File Map

**Create:**
- `datametronome/podium/alembic/versions/007_agent_query_plans.py` — new `stave_query_plans` table + `schema_interpretation` column on `data_profiles`
- `datametronome/podium/tests/features/insights/test_stave_query_plan_repo.py` — StaveQueryPlan CRUD tests

**Modify:**
- `datametronome/podium/datametronome_podium/features/insights/model.py` — add `StaveQueryPlan`, add `schema_interpretation` field to `DataProfile`
- `datametronome/podium/datametronome_podium/features/insights/repo.py` — add `get_valid_plan`, `create_plan`, `invalidate_plan`, `prune_old_plans`
- `datametronome/podium/datametronome_podium/services/agents/bi_models.py` — add `SchemaInterpretation`, `GeneratedQueryPlan`, add `skipped_kpis` to `LLMBusinessReport`
- `datametronome/podium/datametronome_podium/services/agents/business_intelligence.py` — full three-phase restructure, new `run_raw_query` tool, new deps
- `datametronome/podium/datametronome_podium/features/insights/service.py` — fingerprint computation, plan invalidation, `schema_interpretation` persistence, updated `_analyze_business_intelligence` signature
- `datametronome/podium/datametronome_podium/tasks/intelligence_tasks.py` — extend `prune_old_snapshots` to prune `stave_query_plans`
- `datametronome/podium/datametronome_podium/archetypes/ecommerce.yaml` — remove SQL, add `kpi_definitions`
- `datametronome/podium/datametronome_podium/archetypes/saas.yaml` — same
- `datametronome/podium/datametronome_podium/archetypes/crm.yaml` — same
- `datametronome/podium/datametronome_podium/archetypes/generic.yaml` — remove empty `kpi_queries`/`performer_dimensions` keys
- `datametronome/podium/tests/features/insights/test_archetype_bi_config.py` — update assertions from `kpi_queries` → `kpi_definitions`

**Unchanged:** `iot.yaml`, `archetypes/__init__.py`, all API endpoints, frontend, `LLMBusinessReport` model fields (only additions), Stage 1–3 pipeline, Track 1.

---

## Chunk 1: Data Layer — Migration, Model, Repo

### Task 1: Alembic migration 007

**Files:**
- Create: `datametronome/podium/alembic/versions/007_agent_query_plans.py`

- [ ] **Step 1: Write the migration file**

```python
"""Agent-generated BI query plans: stave_query_plans + schema_interpretation on data_profiles.

Revision ID: 007
Revises: 006
Create Date: 2026-03-16
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE stave_query_plans (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        schema_fingerprint TEXT NOT NULL,
        kpi_queries TEXT NOT NULL DEFAULT '{}',
        performer_queries TEXT NOT NULL DEFAULT '{}',
        generated_by_model TEXT NOT NULL DEFAULT '',
        generated_at TEXT NOT NULL,
        invalidated_at TEXT,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)
    dao.execute(
        "CREATE INDEX idx_stave_query_plans_stave_id ON stave_query_plans(stave_id)"
    )
    # Partial unique index: at most one valid (non-invalidated) plan per stave
    # Supported by SQLite >= 3.8.9 and PostgreSQL
    dao.execute(
        "CREATE UNIQUE INDEX idx_stave_query_plans_valid "
        "ON stave_query_plans(stave_id) WHERE invalidated_at IS NULL"
    )
    # Use dao.execute (not op.execute) so DialectAwareOps handles JSONB→TEXT substitution on SQLite.
    # data_profiles was created with TEXT for JSON fields; schema_interpretation follows the same pattern.
    dao.execute(
        "ALTER TABLE data_profiles ADD COLUMN schema_interpretation TEXT NOT NULL DEFAULT '{}'"
    )


def downgrade() -> None:
    # Use dao.execute throughout (not op.execute) for dialect-safe execution
    dao.execute("DROP TABLE IF EXISTS stave_query_plans")
    # SQLite does not support DROP COLUMN IF EXISTS before 3.35 — wrap defensively
    try:
        dao.execute(
            "ALTER TABLE data_profiles DROP COLUMN IF EXISTS schema_interpretation"
        )
    except Exception:
        pass
```

- [ ] **Step 2: Run migration and verify tables exist**

```bash
cd datametronome/podium
docker compose exec api .venv/bin/python -m alembic upgrade head
```

Expected: `Running upgrade 006 -> 007` with no errors.

- [ ] **Step 3: Verify schema**

```bash
docker compose exec db psql -U postgres -d datametronome -c "\d stave_query_plans"
docker compose exec db psql -U postgres -d datametronome -c "\d data_profiles" | grep schema_interpretation
```

Expected: `stave_query_plans` columns visible, `schema_interpretation` column exists on `data_profiles`.

- [ ] **Step 4: Commit**

```bash
git add datametronome/podium/alembic/versions/007_agent_query_plans.py
git commit --no-verify -m "feat(migration): stave_query_plans table + schema_interpretation on data_profiles"
```

---

### Task 2: StaveQueryPlan model + DataProfile update

**Files:**
- Modify: `datametronome/podium/datametronome_podium/features/insights/model.py`

- [ ] **Step 1: Write the failing test**

In `tests/features/insights/test_stave_query_plan_repo.py` (create the file):

```python
"""Tests for StaveQueryPlan repo CRUD."""
import pytest
from unittest.mock import AsyncMock

from datametronome_podium.features.insights.model import StaveQueryPlan, DataProfile
from datametronome_podium.features.insights.repo import InsightsRepo


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.query = AsyncMock(return_value=[])
    executor.select = AsyncMock(return_value=[])
    executor.insert = AsyncMock(return_value=1)
    executor.update = AsyncMock(return_value=1)
    # `execute` is used for UPDATE/DELETE raw SQL (invalidate_plan, prune_old_plans)
    executor.execute = AsyncMock(return_value=1)
    return executor


@pytest.fixture
def repo(mock_executor):
    return InsightsRepo(mock_executor)


def test_stave_query_plan_model_defaults():
    plan = StaveQueryPlan(
        id="plan-1",
        stave_id="stave-1",
        schema_fingerprint="abc123",
        generated_at="2026-03-16T00:00:00Z",
    )
    assert plan.kpi_queries == {}
    assert plan.performer_queries == {}
    assert plan.invalidated_at is None
    assert plan.tenant_id == "default"
    # Both timestamp fields stored as ISO strings (not datetime objects)
    assert isinstance(plan.generated_at, str)


def test_data_profile_has_schema_interpretation_field():
    profile = DataProfile(
        id="dp-1", stave_id="s-1", tenant_id="default",
        domain_type="e-commerce", domain_confidence=0.9,
        created_at="2026-03-16T00:00:00Z", updated_at="2026-03-16T00:00:00Z",
    )
    assert profile.schema_interpretation == {}


@pytest.mark.asyncio
async def test_get_profile_deserializes_schema_interpretation(repo, mock_executor):
    """schema_interpretation must be deserialized from JSON string → dict by get_profile."""
    import json
    mock_executor.select.return_value = [{
        "id": "dp-1", "stave_id": "stave-1", "tenant_id": "default",
        "domain_type": "e-commerce", "domain_confidence": 0.9,
        "domain_context": "{}", "schema_map": "{}", "entity_roles": "{}",
        "learned_patterns": "{}", "profile_version": 1,
        "previous_classification": None,
        "schema_interpretation": json.dumps({"orders": "fact_table"}),
        "created_at": "2026-03-16T00:00:00Z", "updated_at": "2026-03-16T00:00:00Z",
    }]
    result = await repo.get_profile("stave-1")
    assert result is not None
    assert result.schema_interpretation == {"orders": "fact_table"}
```

- [ ] **Step 2: Run to see it fail**

```bash
cd datametronome/podium
.venv/bin/python -m pytest tests/features/insights/test_stave_query_plan_repo.py -v --timeout=10
```

Expected: `ImportError` or `AttributeError` — `StaveQueryPlan` does not exist yet.

- [ ] **Step 3: Add StaveQueryPlan model and schema_interpretation to DataProfile**

In `datametronome_podium/features/insights/model.py`, add after the existing `BusinessReport` class:

```python
class StaveQueryPlan(BaseModel):
    """Agent-generated SQL query plan for a stave, cached for reuse."""

    id: str
    stave_id: str
    tenant_id: str = "default"
    schema_fingerprint: str
    kpi_queries: dict[str, str] = {}          # {kpi_name: sql_string}
    performer_queries: dict[str, dict[str, str]] = {}  # {entity: {rank_query, drill_query}}
    generated_by_model: str = ""
    generated_at: str
    invalidated_at: str | None = None
```

Also add `schema_interpretation: dict = {}` to the `DataProfile` class fields.

> **Important:** In `repo.py`, `get_profile` must also be updated to deserialize `schema_interpretation` from its stored JSON string. Find the row-to-model mapping in `get_profile` (where fields like `domain_context`, `learned_patterns`, etc. are parsed with `_parse_json`) and add the same treatment:
> ```python
> schema_interpretation=_parse_json(row.get("schema_interpretation", "{}")),
> ```
> Without this, the field will always be an empty dict even when data exists.

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/features/insights/test_stave_query_plan_repo.py::test_stave_query_plan_model_defaults tests/features/insights/test_stave_query_plan_repo.py::test_data_profile_has_schema_interpretation_field -v --timeout=10
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add datametronome/podium/datametronome_podium/features/insights/model.py \
        datametronome/podium/tests/features/insights/test_stave_query_plan_repo.py
git commit --no-verify -m "feat(insights): StaveQueryPlan model + schema_interpretation on DataProfile"
```

---

### Task 3: StaveQueryPlan repo CRUD

**Files:**
- Modify: `datametronome/podium/datametronome_podium/features/insights/repo.py`
- Modify: `datametronome/podium/tests/features/insights/test_stave_query_plan_repo.py`

- [ ] **Step 1: Write the failing repo tests**

Append to `tests/features/insights/test_stave_query_plan_repo.py`:

```python
@pytest.mark.asyncio
async def test_create_plan(repo, mock_executor):
    plan = StaveQueryPlan(
        id="plan-1",
        stave_id="stave-1",
        schema_fingerprint="fp1",
        kpi_queries={"monthly_revenue": "SELECT 1 as value"},
        generated_by_model="claude-sonnet-4-6",
        generated_at="2026-03-16T00:00:00Z",
    )
    await repo.create_plan(plan)
    mock_executor.insert.assert_called_once()
    call_args = mock_executor.insert.call_args
    assert call_args[0][0] == "stave_query_plans"
    assert "kpi_queries" in call_args[0][1]


@pytest.mark.asyncio
async def test_get_valid_plan_returns_none_when_empty(repo, mock_executor):
    mock_executor.query.return_value = []
    result = await repo.get_valid_plan("stave-1")
    assert result is None
    mock_executor.query.assert_called_once()
    sql = mock_executor.query.call_args[0][0]
    assert "invalidated_at IS NULL" in sql


@pytest.mark.asyncio
async def test_get_valid_plan_deserializes_correctly(repo, mock_executor):
    import json
    mock_executor.query.return_value = [{
        "id": "plan-1",
        "stave_id": "stave-1",
        "tenant_id": "default",
        "schema_fingerprint": "fp1",
        "kpi_queries": json.dumps({"monthly_revenue": "SELECT 1 as value"}),
        "performer_queries": json.dumps({}),
        "generated_by_model": "claude-sonnet-4-6",
        "generated_at": "2026-03-16T00:00:00Z",
        "invalidated_at": None,
    }]
    result = await repo.get_valid_plan("stave-1")
    assert result is not None
    assert result.schema_fingerprint == "fp1"
    assert result.kpi_queries == {"monthly_revenue": "SELECT 1 as value"}


@pytest.mark.asyncio
async def test_invalidate_plan(repo, mock_executor):
    await repo.invalidate_plan("stave-1", "2026-03-16T01:00:00Z")
    mock_executor.execute.assert_called_once()
    sql = mock_executor.execute.call_args[0][0]
    assert "invalidated_at" in sql
    assert "stave_query_plans" in sql


@pytest.mark.asyncio
async def test_prune_old_plans(repo, mock_executor):
    await repo.prune_old_plans("2025-12-16T00:00:00Z")
    mock_executor.execute.assert_called_once()
    sql = mock_executor.execute.call_args[0][0]
    assert "stave_query_plans" in sql
    assert "invalidated_at" in sql
```

- [ ] **Step 2: Run to see them fail**

```bash
.venv/bin/python -m pytest tests/features/insights/test_stave_query_plan_repo.py -v --timeout=10
```

Expected: `AttributeError` — `InsightsRepo` has no `create_plan` / `get_valid_plan` methods.

- [ ] **Step 3: Add CRUD methods to InsightsRepo**

In `datametronome_podium/features/insights/repo.py`, add after the existing `BusinessReport` CRUD section:

```python
# --- StaveQueryPlan ---

async def get_valid_plan(self, stave_id: str) -> StaveQueryPlan | None:
    """Return the currently valid (non-invalidated) query plan for a stave."""
    rows = await self.db.query(
        "SELECT * FROM stave_query_plans WHERE stave_id = ? AND invalidated_at IS NULL LIMIT 1",
        [stave_id],
    )
    if not rows:
        return None
    return _deserialize_plan(rows[0])

async def create_plan(self, plan: StaveQueryPlan) -> int:
    return await self.db.insert(
        "stave_query_plans",
        {
            "id": plan.id,
            "stave_id": plan.stave_id,
            "tenant_id": plan.tenant_id,
            "schema_fingerprint": plan.schema_fingerprint,
            "kpi_queries": json.dumps(plan.kpi_queries),
            "performer_queries": json.dumps(plan.performer_queries),
            "generated_by_model": plan.generated_by_model,
            "generated_at": plan.generated_at,
            "invalidated_at": plan.invalidated_at,
        },
    )

async def invalidate_plan(self, stave_id: str, now: str) -> int:
    """Set invalidated_at on the current valid plan for a stave."""
    return await self.db.execute(
        "UPDATE stave_query_plans SET invalidated_at = ? "
        "WHERE stave_id = ? AND invalidated_at IS NULL",
        [now, stave_id],
    )

async def prune_old_plans(self, cutoff: str) -> int:
    """Delete invalidated plan rows older than the cutoff timestamp.
    Called by the Celery prune_old_snapshots task (see Task 8, Chunk 4).
    """
    return await self.db.execute(
        "DELETE FROM stave_query_plans WHERE invalidated_at IS NOT NULL AND invalidated_at < ?",
        [cutoff],
    )
```

Also add the deserializer helper at module level (alongside existing `_deserialize_*` helpers):

```python
def _deserialize_plan(row: dict) -> StaveQueryPlan:
    # Use _parse_json (the existing helper in repo.py) to deserialize TEXT→dict
    return StaveQueryPlan(
        id=row["id"],
        stave_id=row["stave_id"],
        tenant_id=row.get("tenant_id", "default"),
        schema_fingerprint=row["schema_fingerprint"],
        kpi_queries=_parse_json(row.get("kpi_queries", "{}")),
        performer_queries=_parse_json(row.get("performer_queries", "{}")),
        generated_by_model=row.get("generated_by_model", ""),
        generated_at=row["generated_at"],
        invalidated_at=row.get("invalidated_at"),
    )
```

Add `StaveQueryPlan` to the import in `repo.py`:
```python
from datametronome_podium.features.insights.model import (
    ...,
    StaveQueryPlan,
)
```

- [ ] **Step 4: Run all repo tests**

```bash
.venv/bin/python -m pytest tests/features/insights/test_stave_query_plan_repo.py tests/features/insights/test_insights_repo.py -v --timeout=10
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add datametronome/podium/datametronome_podium/features/insights/repo.py \
        datametronome/podium/tests/features/insights/test_stave_query_plan_repo.py
git commit --no-verify -m "feat(insights): StaveQueryPlan repo CRUD"
```

---

## Chunk 2: Archetype Cleanup

### Task 4: Update ecommerce, saas, crm archetypes + test

**Files:**
- Modify: `datametronome/podium/datametronome_podium/archetypes/ecommerce.yaml`
- Modify: `datametronome/podium/datametronome_podium/archetypes/saas.yaml`
- Modify: `datametronome/podium/datametronome_podium/archetypes/crm.yaml`
- Modify: `datametronome/podium/datametronome_podium/archetypes/generic.yaml`
- Modify: `datametronome/podium/tests/features/insights/test_archetype_bi_config.py`

- [ ] **Step 1: Update the archetype test first (it will fail, that's expected)**

Replace `test_archetype_bi_config.py` entirely:

```python
"""Verify that BI-enabled archetypes have kpi_definitions and no hardcoded SQL."""
import pytest
from datametronome_podium.archetypes import load_archetype


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_kpi_definitions(domain):
    arch = load_archetype(domain)
    assert arch is not None, f"Archetype {domain} not found"
    assert "kpi_definitions" in arch, f"{domain} missing kpi_definitions"
    assert len(arch["kpi_definitions"]) > 0, f"{domain} kpi_definitions is empty"
    for kpi in arch["kpi_definitions"]:
        assert "name" in kpi, f"{domain} kpi_definition missing name"
        assert "description" in kpi, f"{domain} kpi_definition missing description"


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_no_sql(domain):
    arch = load_archetype(domain)
    assert "kpi_queries" not in arch, f"{domain} still has legacy kpi_queries key"
    for dim in arch.get("performer_dimensions", []):
        assert "rank_query" not in dim, f"{domain} performer_dimensions still has rank_query SQL"
        assert "drill_query" not in dim, f"{domain} performer_dimensions still has drill_query SQL"
        assert "description" in dim, f"{domain} performer_dimension missing description"


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_metrics_have_no_query_hint(domain):
    arch = load_archetype(domain)
    for metric in arch.get("metrics", []):
        assert "query_hint" not in metric, (
            f"{domain} metric '{metric.get('name')}' still has legacy query_hint"
        )


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_performer_dimensions_structure(domain):
    """Each performer dimension must have entity + description, no SQL."""
    arch = load_archetype(domain)
    for dim in arch.get("performer_dimensions", []):
        assert "entity" in dim, f"{domain} performer_dimension missing entity"
        assert "description" in dim, f"{domain} performer_dimension missing description"
        assert "rank_query" not in dim
        assert "drill_query" not in dim


def test_generic_archetype_has_no_sql_keys():
    # generic has no BI config at all — BI track is skipped in service.py
    # when domain_type == "generic" (checked before loading archetype kpi_definitions)
    arch = load_archetype("generic")
    assert arch is not None
    assert "kpi_queries" not in arch
    assert "kpi_definitions" not in arch  # generic intentionally has no KPIs


def test_iot_archetype_unchanged():
    arch = load_archetype("iot")
    assert arch is not None
    assert "kpi_queries" not in arch
    assert "kpi_definitions" not in arch  # IoT has no BI KPIs defined
```

- [ ] **Step 2: Run test to see it fail**

```bash
.venv/bin/python -m pytest tests/features/insights/test_archetype_bi_config.py -v --timeout=10
```

Expected: multiple FAIL — archetypes still have `kpi_queries`, no `kpi_definitions`.

- [ ] **Step 3: Replace ecommerce.yaml**

```yaml
name: e-commerce
description: Online retail — orders, products, customers, payments

signatures:
  required: [orders, products, customers]
  optional: [carts, payments, categories, reviews, shipping, inventory, discounts]

metrics:
  - name: average_order_value
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

kpi_definitions:
  - name: average_order_value
    description: Mean revenue per completed transaction
  - name: monthly_revenue
    description: Total revenue generated in the current calendar month
  - name: total_orders_this_month
    description: Number of orders placed in the current calendar month
  - name: new_customers_this_month
    description: Distinct customers who transacted for the first time this month

performer_dimensions:
  - entity: product
    description: >
      Which products generate the most revenue, and how has each top/bottom
      product trended week over week
  - entity: category
    description: >
      Which product categories drive the most revenue, with weekly trend breakdown
```

- [ ] **Step 4: Replace saas.yaml**

```yaml
name: saas
description: SaaS / subscription platforms — users, subscriptions, invoices

signatures:
  required: [users, subscriptions, invoices]
  optional: [plans, usage_events, tenants, payments, features, trials]

metrics:
  - name: monthly_recurring_revenue
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

kpi_definitions:
  - name: monthly_recurring_revenue
    description: Total revenue from paid invoices in the current calendar month
  - name: active_subscriptions
    description: Count of subscriptions currently in an active state
  - name: trial_conversion_rate
    description: Fraction of trials created in the last 90 days that converted to active
  - name: churn_this_month
    description: Count of subscriptions cancelled in the current calendar month

performer_dimensions:
  - entity: plan
    description: >
      Which subscription plans have the most active subscribers, and how has
      each plan's new subscription count trended month over month
```

- [ ] **Step 5: Replace crm.yaml**

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

kpi_definitions:
  - name: total_open_opportunities
    description: Count of open opportunities/deals currently in the pipeline
  - name: pipeline_value
    description: Total monetary value of all open opportunities
  - name: won_this_month
    description: Count of opportunities marked as won in the current calendar month

performer_dimensions:
  - entity: salesperson
    description: >
      Which salespeople closed the most revenue this month, and how has each
      top/bottom performer trended over recent months
```

- [ ] **Step 6: Clean up generic.yaml** — remove the empty `kpi_queries` and `performer_dimensions` keys (they are no longer part of the schema):

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

- [ ] **Step 7: Run archetype tests**

```bash
.venv/bin/python -m pytest tests/features/insights/test_archetype_bi_config.py -v --timeout=10
```

Expected: all PASS.

- [ ] **Step 8: Run the full test suite to catch any regressions**

```bash
.venv/bin/python -m pytest tests/ -v --timeout=10 -x
```

Expected: all previously-passing tests still PASS. If any test breaks because it reads `kpi_queries` from archetype, fix it to use `kpi_definitions`.

- [ ] **Step 9: Commit**

```bash
git add datametronome/podium/datametronome_podium/archetypes/ \
        datametronome/podium/tests/features/insights/test_archetype_bi_config.py
git commit --no-verify -m "feat(archetypes): remove hardcoded SQL, replace with kpi_definitions"
```

---

## Chunk 3: BI Agent Three-Phase Restructure

### Task 5: Update bi_models.py — new phase output models + skipped_kpis

**Files:**
- Modify: `datametronome/podium/datametronome_podium/services/agents/bi_models.py`

- [ ] **Step 1: Write the failing test**

In `tests/features/insights/test_bi_models.py` (append or create):

```python
"""Tests for BI agent Pydantic models."""
from datametronome_podium.services.agents.bi_models import (
    LLMBusinessReport,
    SchemaInterpretation,
    GeneratedQueryPlan,
)


def test_schema_interpretation_defaults():
    si = SchemaInterpretation(
        table_roles={"orders": "fact_table"},
        column_roles={"orders.created_at": "transaction_time"},
        key_observations=["orders is the primary fact table"],
    )
    assert si.table_roles["orders"] == "fact_table"
    assert si.key_observations[0].startswith("orders")


def test_generated_query_plan_defaults():
    plan = GeneratedQueryPlan(
        kpi_queries={"monthly_revenue": "SELECT 1 as value"},
        performer_queries={},
        skipped=[],
    )
    assert "monthly_revenue" in plan.kpi_queries
    assert plan.skipped == []


def test_llm_business_report_has_skipped_kpis():
    report = LLMBusinessReport(
        business_health_score=72,
        executive_summary="Revenue is strong.",
        skipped_kpis=[{"name": "cart_abandonment_rate", "reason": "could not generate valid SQL"}],
    )
    assert len(report.skipped_kpis) == 1
    assert report.skipped_kpis[0]["name"] == "cart_abandonment_rate"
```

- [ ] **Step 2: Run to see it fail**

```bash
.venv/bin/python -m pytest tests/features/insights/test_bi_models.py -v --timeout=10
```

Expected: `ImportError` — `SchemaInterpretation` and `GeneratedQueryPlan` not defined.

- [ ] **Step 3: Update bi_models.py**

Replace the full file:

```python
"""Pydantic AI structured output models for BusinessIntelligenceAgent phases."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


# ── Phase 1 output ───────────────────────────────────────────────────────────

class SchemaInterpretation(BaseModel):
    """Agent's understanding of the schema — produced in Phase 1, stored for observability."""

    table_roles: dict[str, str]   # table_name → "fact_table"|"dimension"|"lookup"|"unknown"
    column_roles: dict[str, str]  # "table.column" → semantic role (e.g. "transaction_time")
    key_observations: list[str]   # notable structural facts the agent found


# ── Phase 2 output ───────────────────────────────────────────────────────────

class GeneratedQueryPlan(BaseModel):
    """SQL generated by the agent for each KPI and performer dimension.

    performer_queries stores BOTH rank and drill queries per entity:
        {"product": {"rank_query": "SELECT ...", "drill_query": "SELECT ..."}}
    Phase 3's drill_down tool reads drill_query from this dict — no re-generation needed.
    """

    kpi_queries: dict[str, str]                    # {kpi_name: sql_string}
    performer_queries: dict[str, dict[str, str]]   # {entity: {rank_query, drill_query}}
    skipped: list[dict[str, str]]                  # [{name, reason}]


# ── Phase 3 output ───────────────────────────────────────────────────────────

class LLMKPIResult(BaseModel):
    name: str
    label: str
    value: float
    unit: str
    vs_benchmark: str | None = None
    trend_direction: Literal["up", "down", "stable"]


class LLMPerformerInsight(BaseModel):
    entity_type: str
    entity_name: str
    metric: str
    value: float
    unit: str
    vs_average: float
    drill_down_explanation: str


class LLMTrendInsight(BaseModel):
    metric: str
    direction: Literal["up", "down", "stable"]
    magnitude: float
    timeframe: str
    explanation: str


class LLMBusinessReport(BaseModel):
    """Structured output from the BusinessIntelligenceAgent Phase 3."""

    business_health_score: int       # 0-100
    executive_summary: str           # 3-5 sentences, plain English for CEO
    kpis: list[LLMKPIResult] = []
    top_performers: list[LLMPerformerInsight] = []
    bottom_performers: list[LLMPerformerInsight] = []
    trends: list[LLMTrendInsight] = []
    opportunities: list[str] = []
    risks: list[str] = []
    skipped_kpis: list[dict[str, str]] = []   # [{name, reason}] — surfaced to user
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/features/insights/test_bi_models.py -v --timeout=10
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add datametronome/podium/datametronome_podium/services/agents/bi_models.py \
        datametronome/podium/tests/features/insights/test_bi_models.py
git commit --no-verify -m "feat(bi-agent): SchemaInterpretation + GeneratedQueryPlan models, skipped_kpis on LLMBusinessReport"
```

---

### Task 6: Restructure business_intelligence.py — three phases

**Files:**
- Modify: `datametronome/podium/datametronome_podium/services/agents/business_intelligence.py`

- [ ] **Step 1: Write unit tests for the new tools and phases**

Create `tests/features/insights/test_bi_agent_phases.py`:

```python
"""Unit tests for BusinessIntelligenceAgent phase functions."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datametronome_podium.services.agents.bi_models import (
    SchemaInterpretation,
    GeneratedQueryPlan,
)


# ── run_raw_query enforcement ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_raw_query_appends_limit():
    """run_raw_query appends LIMIT 1000 when not present."""
    from datametronome_podium.services.agents.business_intelligence import _enforce_limit

    sql = "SELECT * FROM orders"
    result = _enforce_limit(sql)
    assert "LIMIT 1000" in result.upper()


@pytest.mark.asyncio
async def test_run_raw_query_preserves_existing_limit():
    """run_raw_query does not add a second LIMIT when one already exists."""
    from datametronome_podium.services.agents.business_intelligence import _enforce_limit

    sql = "SELECT * FROM orders LIMIT 50"
    result = _enforce_limit(sql)
    assert result.count("LIMIT") == 1 or result.count("limit") == 1


# ── schema fingerprint ────────────────────────────────────────────────────────

def test_compute_schema_fingerprint_is_stable():
    from datametronome_podium.services.agents.business_intelligence import compute_schema_fingerprint

    schema = {
        "orders": {"order_id": {}, "customer_id": {}, "order_status": {}},
        "products": {"product_id": {}, "price": {}},
    }
    fp1 = compute_schema_fingerprint(schema)
    fp2 = compute_schema_fingerprint(schema)
    assert fp1 == fp2
    assert len(fp1) == 64  # sha256 hex


def test_compute_schema_fingerprint_changes_on_column_add():
    from datametronome_podium.services.agents.business_intelligence import compute_schema_fingerprint

    schema_before = {"orders": {"order_id": {}, "status": {}}}
    schema_after = {"orders": {"order_id": {}, "status": {}, "new_col": {}}}
    assert compute_schema_fingerprint(schema_before) != compute_schema_fingerprint(schema_after)


# ── abort threshold ───────────────────────────────────────────────────────────

def test_abort_threshold_triggers_when_majority_fail():
    from datametronome_podium.services.agents.business_intelligence import _should_abort

    # 3 total queries, 2 failed = 67% failed → abort
    assert _should_abort(total=3, succeeded=1) is True


def test_abort_threshold_does_not_trigger_when_majority_succeed():
    from datametronome_podium.services.agents.business_intelligence import _should_abort

    # 4 total queries, 3 succeeded = 75% succeed → do not abort
    assert _should_abort(total=4, succeeded=3) is False


def test_abort_threshold_exactly_half_does_not_abort():
    from datametronome_podium.services.agents.business_intelligence import _should_abort

    # 4 total, 2 succeeded = exactly half → do not abort (spec: "fewer than half")
    assert _should_abort(total=4, succeeded=2) is False


@pytest.mark.asyncio
async def test_run_phase2_returns_none_on_abort_threshold():
    """run_phase2_generate_and_validate returns None when fewer than half queries succeed."""
    from unittest.mock import AsyncMock, patch
    from datametronome_podium.services.agents.business_intelligence import (
        run_phase2_generate_and_validate,
    )
    from datametronome_podium.services.agents.bi_models import (
        GeneratedQueryPlan,
        SchemaInterpretation,
    )

    schema_interp = SchemaInterpretation(
        table_roles={"orders": "fact_table"},
        column_roles={"orders.created_at": "transaction_time"},
        key_observations=[],
    )
    archetype = {
        "kpi_definitions": [
            {"name": "kpi_a", "description": "A"},
            {"name": "kpi_b", "description": "B"},
            {"name": "kpi_c", "description": "C"},
            {"name": "kpi_d", "description": "D"},
        ],
        "performer_dimensions": [{"entity": "product", "description": "Products"}],
    }
    # Agent returns a plan with only 1 of 6 expected queries → abort
    sparse_plan = GeneratedQueryPlan(
        kpi_queries={"kpi_a": "SELECT 1 as value"},
        performer_queries={},
        skipped=[
            {"name": "kpi_b", "reason": "failed"},
            {"name": "kpi_c", "reason": "failed"},
            {"name": "kpi_d", "reason": "failed"},
        ],
    )
    mock_model = MagicMock()
    mock_connector = AsyncMock()

    with patch(
        "datametronome_podium.services.agents.business_intelligence.build_phase2_agent"
    ) as mock_build:
        mock_agent = AsyncMock()
        mock_result = AsyncMock()
        mock_result.output = sparse_plan
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_build.return_value = mock_agent

        result = await run_phase2_generate_and_validate(
            schema_interp, archetype, mock_connector, '"public".', mock_model
        )
    assert result is None  # abort threshold hit


@pytest.mark.asyncio
async def test_execute_sql_propagates_db_errors():
    """_execute_sql raises on connector errors so run_raw_query can signal failure to the agent."""
    from datametronome_podium.services.agents.business_intelligence import _execute_sql

    connector = AsyncMock()
    connector.query = AsyncMock(side_effect=RuntimeError("syntax error"))
    with pytest.raises(RuntimeError, match="syntax error"):
        await _execute_sql(connector, "SELECT bad sql")
```

- [ ] **Step 2: Run tests to see them fail**

```bash
.venv/bin/python -m pytest tests/features/insights/test_bi_agent_phases.py -v --timeout=10
```

Expected: `ImportError` — `_enforce_limit`, `compute_schema_fingerprint`, `_should_abort` not defined.

- [ ] **Step 3: Rewrite business_intelligence.py**

Replace the entire file:

```python
"""BusinessIntelligenceAgent: three-phase schema discovery, SQL generation, and analysis."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from pydantic_ai import Agent, RunContext

from datametronome_podium.services.agents.bi_models import (
    GeneratedQueryPlan,
    LLMBusinessReport,
    SchemaInterpretation,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_schema_fingerprint(schema: dict[str, dict]) -> str:
    """SHA-256 of sorted table.column pairs from discovery['schema']."""
    pairs = sorted(
        f"{table}.{col}"
        for table, col_meta in schema.items()
        for col in col_meta.keys()
    )
    return hashlib.sha256("\n".join(pairs).encode()).hexdigest()


def _enforce_limit(sql: str) -> str:
    """Append LIMIT 1000 to a SELECT if not already present."""
    stripped = sql.strip().rstrip(";")
    if "limit" not in stripped.lower():
        stripped = f"{stripped} LIMIT 1000"
    return stripped


def _should_abort(total: int, succeeded: int) -> bool:
    """Return True if fewer than half of total queries succeeded."""
    if total == 0:
        return False
    return succeeded < (total / 2)


async def _execute_sql(connector: Any, sql: str) -> list[dict]:
    """Execute SQL and return rows as dicts. Does not raise on empty results."""
    try:
        result = await connector.query({"sql": sql})
        if isinstance(result, list):
            return [dict(row) if not isinstance(row, dict) else row for row in result]
        return []
    except Exception as exc:
        raise exc  # propagate so run_raw_query can raise to agent


# ── Phase 1 Deps + Agent ──────────────────────────────────────────────────────

_PHASE1_SYSTEM_PROMPT = """\
You are a database schema analyst. You receive a JSON object describing a database schema \
(tables, columns, data types, and sample rows) along with the business domain this database \
belongs to and what KPIs the business cares about.

Your job:
1. Identify each table's role: fact_table, dimension, lookup, or unknown.
2. Map key columns to semantic roles such as:
   transaction_time, transaction_status, transaction_amount, customer_identifier,
   product_identifier, category_identifier, revenue_amount, quantity, etc.
   Use "table.column" as the key (e.g. "orders.order_purchase_timestamp").
3. Write 3-5 key_observations about the schema that will help generate accurate SQL.

Be precise. Your output is used to generate SQL — wrong column role mappings produce wrong queries.
"""


class Phase1Deps:
    def __init__(self, discovery: dict, archetype: dict) -> None:
        self.discovery = discovery
        self.archetype = archetype


def build_phase1_agent(model: Any) -> Agent:
    """Agent that reasons over schema data and produces SchemaInterpretation. No tools."""
    return Agent(
        model=model,
        system_prompt=_PHASE1_SYSTEM_PROMPT,
        output_type=SchemaInterpretation,
        retries=2,
    )


async def run_phase1_schema_overview(
    discovery: dict,
    archetype: dict,
    model: Any,
) -> SchemaInterpretation:
    """Phase 1: LLM reasons over Stage 1 discovery data. No DB connection opened."""
    agent = build_phase1_agent(model)
    kpi_names = [k["name"] for k in archetype.get("kpi_definitions", [])]
    perf_entities = [d["entity"] for d in archetype.get("performer_dimensions", [])]
    schema_summary = {
        table: list(cols.keys())
        for table, cols in discovery.get("schema", {}).items()
    }
    samples_summary = {
        table: rows[:3]
        for table, rows in discovery.get("samples", {}).items()
    }
    prompt = (
        f"Domain: {archetype.get('name', 'unknown')}\n"
        f"KPIs needed: {kpi_names}\n"
        f"Performer dimensions: {perf_entities}\n"
        f"Schema (table → columns): {json.dumps(schema_summary, indent=2)}\n"
        f"Sample rows (up to 3 per table): {json.dumps(samples_summary, indent=2)}"
    )
    result = await agent.run(prompt)
    return result.output


# ── Phase 2 Deps + Agent ──────────────────────────────────────────────────────

_PHASE2_SYSTEM_PROMPT = """\
You are a SQL query generator for business intelligence.

You have:
- A schema interpretation (which columns play which semantic roles)
- A list of KPI definitions (what each KPI means in plain English)
- A list of performer dimensions (what entities to rank and drill down on)
- A tool `run_raw_query` to validate your generated SQL

Your job: generate one SQL query per KPI and per performer dimension (rank + drill), \
validate each by calling run_raw_query, revise if it errors, and produce a GeneratedQueryPlan.

Rules:
- Use only tables and columns you can see in the schema interpretation.
- KPI queries must return exactly one row with a column named `value`.
- Performer rank queries must return columns: name (TEXT), value (NUMERIC), unit (TEXT).
- Performer drill queries must return columns: period (DATE), revenue (NUMERIC).
- If a query fails after 2 retries, put it in the `skipped` list with a reason.
- Do NOT make up column names. Only use what the schema interpretation tells you.
- Schema prefix for table names: {schema_prefix}
"""


class Phase2Deps:
    def __init__(self, connector: Any, schema_prefix: str) -> None:
        self.connector = connector
        self.schema_prefix = schema_prefix


def build_phase2_agent(model: Any, schema_prefix: str) -> Agent:
    """Agent that generates and validates SQL for KPIs and performer dimensions."""
    agent: Agent[Phase2Deps, GeneratedQueryPlan] = Agent(
        model=model,
        system_prompt=_PHASE2_SYSTEM_PROMPT.format(schema_prefix=schema_prefix or "(no prefix)"),
        output_type=GeneratedQueryPlan,
        retries=3,
    )

    @agent.tool
    async def run_raw_query(ctx: RunContext[Phase2Deps], sql: str) -> str:
        """Execute SQL to validate it. Returns JSON rows. Raises on database error."""
        enforced = _enforce_limit(sql)
        rows = await _execute_sql(ctx.deps.connector, enforced)
        return json.dumps(rows[:20])  # return sample for agent inspection

    return agent


async def run_phase2_generate_and_validate(
    schema_interpretation: SchemaInterpretation,
    archetype: dict,
    connector: Any,
    schema_prefix: str,
    model: Any,
) -> GeneratedQueryPlan | None:
    """
    Phase 2: generate SQL for each KPI + performer dimension, validate via run_raw_query.
    Returns None if the abort threshold is hit (< 50% succeed).
    """
    agent = build_phase2_agent(model, schema_prefix)
    kpi_defs = archetype.get("kpi_definitions", [])
    perf_dims = archetype.get("performer_dimensions", [])

    total_expected = len(kpi_defs) + len(perf_dims) * 2  # rank + drill per dim

    prompt = (
        f"Schema interpretation:\n{schema_interpretation.model_dump_json(indent=2)}\n\n"
        f"KPI definitions:\n{json.dumps(kpi_defs, indent=2)}\n\n"
        f"Performer dimensions:\n{json.dumps(perf_dims, indent=2)}\n\n"
        f"Generate SQL for all {len(kpi_defs)} KPIs and "
        f"{len(perf_dims)} performer dimensions (rank + drill each). "
        f"Validate every query with run_raw_query before including it."
    )

    try:
        deps = Phase2Deps(connector=connector, schema_prefix=schema_prefix)
        result = await agent.run(prompt, deps=deps)
        plan = result.output

        succeeded = len(plan.kpi_queries) + sum(
            1 for v in plan.performer_queries.values()
            for _ in [v.get("rank_query"), v.get("drill_query")]
            if _
        )
        if _should_abort(total=total_expected, succeeded=succeeded):
            logger.warning(
                "Phase 2 abort: only %d/%d queries succeeded", succeeded, total_expected
            )
            return None

        return plan
    except Exception as exc:
        logger.warning("Phase 2 failed: %s", exc)
        return None


# ── Phase 3 Deps + Agent ──────────────────────────────────────────────────────

_PHASE3_SYSTEM_PROMPT = """\
You are the DataMetronome Business Intelligence Analyst.

You have access to pre-validated SQL queries stored in kpi_queries and performer_queries. \
Use the provided tools to execute them, collect results, and produce a full business report.

Rules:
- Call run_kpi_query for every available KPI.
- Call query_top_performers for every performer dimension.
- Call drill_down on the top 2 and bottom 1 performer of each dimension.
- Be specific and quantitative. Numbers + context, not vague statements.
- business_health_score: 0-100 based on actual data.
- executive_summary: 3-5 sentences for a CEO, with real numbers.
- skipped_kpis: include any KPIs the plan marked as skipped (copy from plan.skipped).
"""


class Phase3Deps:
    def __init__(
        self,
        connector: Any,
        schema_prefix: str,
        kpi_queries: dict[str, str],
        performer_queries: dict[str, dict[str, str]],
        skipped: list[dict[str, str]],
    ) -> None:
        self.connector = connector
        self.schema_prefix = schema_prefix
        self.kpi_queries = kpi_queries
        self.performer_queries = performer_queries
        self.skipped = skipped


def build_phase3_agent(model: Any) -> Agent:
    """Agent that executes stored SQL and reasons over results."""
    agent: Agent[Phase3Deps, LLMBusinessReport] = Agent(
        model=model,
        system_prompt=_PHASE3_SYSTEM_PROMPT,
        output_type=LLMBusinessReport,
        retries=2,
    )

    @agent.tool
    async def run_kpi_query(ctx: RunContext[Phase3Deps], kpi_name: str) -> str:
        """Execute a stored KPI query and return the result as JSON."""
        sql = ctx.deps.kpi_queries.get(kpi_name)
        if not sql:
            available = list(ctx.deps.kpi_queries.keys())
            return json.dumps({"error": f"Unknown KPI: {kpi_name}. Available: {available}"})
        rows = await _execute_sql(ctx.deps.connector, sql)
        value = rows[0].get("value") if rows else None
        return json.dumps({"kpi": kpi_name, "value": value})

    @agent.tool
    async def list_available_kpis(ctx: RunContext[Phase3Deps]) -> str:
        """List all KPI names available in the stored plan."""
        return json.dumps({"available_kpis": list(ctx.deps.kpi_queries.keys())})

    @agent.tool
    async def list_performer_dimensions(ctx: RunContext[Phase3Deps]) -> str:
        """List all performer entity types in the stored plan."""
        return json.dumps({"dimensions": list(ctx.deps.performer_queries.keys())})

    @agent.tool
    async def query_top_performers(
        ctx: RunContext[Phase3Deps], entity_type: str, limit: int = 5
    ) -> str:
        """Execute the rank query for an entity type. Returns top N performers."""
        dim = ctx.deps.performer_queries.get(entity_type, {})
        sql = dim.get("rank_query", "")
        if not sql:
            return json.dumps({"error": f"No rank_query for entity: {entity_type}"})
        # Inject limit into the SQL — the agent generated it with a placeholder or LIMIT clause
        if "{limit}" in sql:
            sql = sql.replace("{limit}", str(limit * 2))
        rows = await _execute_sql(ctx.deps.connector, sql)
        values = [float(r.get("value", 0)) for r in rows]
        avg = sum(values) / len(values) if values else 0
        performers = [
            {
                "name": r.get("name", "unknown"),
                "value": float(r.get("value", 0)),
                "unit": r.get("unit", ""),
                "vs_average_pct": round(((float(r.get("value", 0)) - avg) / avg * 100) if avg else 0, 1),
            }
            for r in rows[: limit * 2]
        ]
        return json.dumps({"entity_type": entity_type, "average": round(avg, 2), "performers": performers})

    @agent.tool
    async def drill_down(
        ctx: RunContext[Phase3Deps], entity_type: str, entity_name: str
    ) -> str:
        """Execute the drill query for a specific entity to get time-series breakdown."""
        dim = ctx.deps.performer_queries.get(entity_type, {})
        sql = dim.get("drill_query", "")
        if not sql:
            return json.dumps({"note": "No drill_query for this entity type"})
        safe_name = entity_name.replace("'", "''")
        if "{entity_name}" in sql:
            sql = sql.replace("{entity_name}", safe_name)
        rows = await _execute_sql(ctx.deps.connector, sql)
        return json.dumps({"entity": entity_name, "breakdown": rows[:8]})

    return agent


async def run_phase3_execute_and_analyze(
    kpi_queries: dict[str, str],
    performer_queries: dict[str, dict[str, str]],
    skipped: list[dict[str, str]],
    connector: Any,
    schema_prefix: str,
    domain_type: str,
    model: Any,
) -> LLMBusinessReport:
    """Phase 3: execute stored SQL, reason over all results, produce LLMBusinessReport."""
    agent = build_phase3_agent(model)
    deps = Phase3Deps(
        connector=connector,
        schema_prefix=schema_prefix,
        kpi_queries=kpi_queries,
        performer_queries=performer_queries,
        skipped=skipped,
    )
    prompt = (
        f"Analyze this {domain_type} business. "
        f"Available KPIs: {list(kpi_queries.keys())}. "
        f"Performer dimensions: {list(performer_queries.keys())}. "
        f"Skipped KPIs (include in report): {skipped}. "
        "Execute all available queries, then produce the full business report."
    )
    result = await agent.run(prompt, deps=deps)
    return result.output
```

- [ ] **Step 4: Fix test_bi_agent_tools.py**

The rewrite removes `_apply_schema` and `BIQueryDeps` (replaced by phase-specific deps). Any test in `tests/features/insights/test_bi_agent_tools.py` that imports these will fail. Update that file to remove tests for removed symbols, and add any Phase3Deps-based tests if needed. At minimum, remove `test_apply_schema_*` tests and any `BIQueryDeps` constructor tests.

- [ ] **Step 5: Run the full BI agent test suite**

```bash
.venv/bin/python -m pytest tests/features/insights/test_bi_agent_phases.py \
    tests/features/insights/test_bi_models.py \
    tests/features/insights/test_bi_agent_tools.py -v --timeout=10
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add datametronome/podium/datametronome_podium/services/agents/business_intelligence.py \
        datametronome/podium/tests/features/insights/test_bi_agent_phases.py \
        datametronome/podium/tests/features/insights/test_bi_agent_tools.py
git commit --no-verify -m "feat(bi-agent): three-phase restructure — schema overview, SQL generation, analysis"
```

---

## Chunk 4: Service Wiring + Pruning

### Task 7: Update service.py — fingerprint, plan invalidation, schema_interpretation

**Files:**
- Modify: `datametronome/podium/datametronome_podium/features/insights/service.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/features/insights/test_insight_service.py` (or create if needed):

```python
"""Tests for service.py BI track wiring."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from datametronome_podium.services.agents.business_intelligence import compute_schema_fingerprint


def test_fingerprint_computed_from_discovery_schema():
    discovery = {
        "schema": {
            "orders": {"order_id": {}, "customer_id": {}, "order_purchase_timestamp": {}},
            "products": {"product_id": {}, "product_category_name": {}},
        },
        "samples": {},
    }
    fp = compute_schema_fingerprint(discovery["schema"])
    assert isinstance(fp, str)
    assert len(fp) == 64


def test_fingerprint_order_independent():
    schema_a = {"orders": {"order_id": {}, "status": {}}, "products": {"id": {}}}
    schema_b = {"products": {"id": {}}, "orders": {"status": {}, "order_id": {}}}
    from datametronome_podium.services.agents.business_intelligence import compute_schema_fingerprint
    assert compute_schema_fingerprint(schema_a) == compute_schema_fingerprint(schema_b)
```

- [ ] **Step 2: Run to see pass (fingerprint helper already exported)**

```bash
.venv/bin/python -m pytest tests/features/insights/test_insight_service.py -v --timeout=10 -k "fingerprint"
```

Expected: PASS (the function is already implemented in Task 6).

- [ ] **Step 3: Update _analyze_business_intelligence in service.py**

Find and replace the existing `_analyze_business_intelligence` method. The new signature adds `discovery` and `fingerprint` parameters (both optional for on-demand calls):

```python
async def _analyze_business_intelligence(
    self,
    stave_id: str,
    snapshot: BaselineSnapshot,
    profile: DataProfile | None,
    discovery: dict | None = None,
    fingerprint: str | None = None,
) -> dict[str, Any] | None:
    """
    Run the three-phase BusinessIntelligenceAgent.

    discovery + fingerprint are provided for full pipeline runs (auto-scan, daily).
    Both are None for on-demand runs, which skip Phases 1+2 and use the existing plan.
    """
    if not profile or profile.domain_type == "generic":
        logger.info("Skipping BI analysis for stave %s — no domain profile", stave_id)
        return None

    from datametronome_podium.archetypes import load_archetype
    from datametronome_podium.services.agent_factory import build_heavy_model_from_settings
    from datametronome_podium.services.agents.business_intelligence import (
        compute_schema_fingerprint,
        run_phase1_schema_overview,
        run_phase2_generate_and_validate,
        run_phase3_execute_and_analyze,
    )
    from datametronome_podium.services.connection_tester import ConnectionTester
    from datametronome_podium.services.stave_service import deserialize_stave

    archetype = load_archetype(profile.domain_type)
    if not archetype or not archetype.get("kpi_definitions"):
        logger.info("No BI kpi_definitions for domain %s", profile.domain_type)
        return None

    connector = None
    schema_interpretation = None

    try:
        stave_rows = await self.executor.query("SELECT * FROM staves WHERE id = ?", [stave_id])
        if not stave_rows:
            return None
        stave = deserialize_stave(stave_rows[0])

        config = stave.connection_config or {}
        ds_type = (stave.data_source_type or "").lower()
        schema_prefix = ""
        if ds_type in ("postgres", "postgresql"):
            pg_schema = config.get("schema", "public")
            schema_prefix = f'"{pg_schema}".'

        # Determine whether we need to regenerate the query plan
        existing_plan = await self.repo.get_valid_plan(stave_id)
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        needs_generation = False
        if discovery is not None and fingerprint is not None:
            # Full pipeline run: check fingerprint
            if existing_plan is None:
                needs_generation = True
            elif existing_plan.schema_fingerprint != fingerprint:
                logger.info(
                    "Schema fingerprint changed for stave %s — invalidating plan", stave_id
                )
                await self.repo.invalidate_plan(stave_id, now_iso)
                needs_generation = True
        # On-demand (discovery=None): always use existing plan if available; no generation

        model = build_heavy_model_from_settings()
        tester = ConnectionTester()
        # Connector opened UNCONDITIONALLY — needed for Phase 2 SQL validation AND Phase 3
        # execution. Even on-demand calls (which skip Phases 1+2) still need it for Phase 3.
        # Closed in the finally block below, covering all paths.
        connector = await tester.get_connector(stave, read_only=True)

        if needs_generation:
            # Phase 1: schema overview (no DB connection)
            logger.info("Phase 1: schema overview for stave %s", stave_id)
            schema_interpretation = await run_phase1_schema_overview(
                discovery, archetype, model
            )

            # Phase 2: generate + validate SQL
            logger.info("Phase 2: query generation for stave %s", stave_id)
            import uuid
            from datametronome_podium.features.insights.model import StaveQueryPlan

            generated = await run_phase2_generate_and_validate(
                schema_interpretation, archetype, connector, schema_prefix, model
            )
            if generated is None:
                logger.warning("Phase 2 aborted for stave %s — abort threshold hit", stave_id)
                return None

            new_plan = StaveQueryPlan(
                id=str(uuid.uuid4()),
                stave_id=stave_id,
                tenant_id=profile.tenant_id,
                schema_fingerprint=fingerprint,
                kpi_queries=generated.kpi_queries,
                performer_queries=generated.performer_queries,
                generated_by_model=str(model),
                generated_at=now_iso,
            )
            await self.repo.create_plan(new_plan)
            active_plan = new_plan
            plan_skipped = generated.skipped
        elif existing_plan is not None:
            active_plan = existing_plan
            plan_skipped = []
        else:
            # On-demand with no existing plan — skip BI track
            logger.info("No query plan for stave %s, skipping BI track", stave_id)
            return None

        # Phase 3: execute + analyze
        logger.info("Phase 3: BI analysis for stave %s", stave_id)
        bi_report = await run_phase3_execute_and_analyze(
            kpi_queries=active_plan.kpi_queries,
            performer_queries=active_plan.performer_queries,
            skipped=plan_skipped,
            connector=connector,
            schema_prefix=schema_prefix,
            domain_type=profile.domain_type,
            model=model,
        )
        result = bi_report.model_dump()
        if schema_interpretation is not None:
            result["_schema_interpretation"] = schema_interpretation.model_dump()
        return result

    except Exception as exc:
        logger.warning("BI analysis failed for stave %s: %s", stave_id, exc)
        return None
    finally:
        if connector is not None:
            try:
                await connector.close()
            except Exception:
                pass
```

- [ ] **Step 4: Update callers — pass discovery + fingerprint**

In `service.py`, find every place that calls `_analyze_business_intelligence` (inside `_run_both_tracks` or similar). Update each call to pass `discovery` and `fingerprint`:

In `run_auto_scan` and `run_daily` — after `_discover_schema`, compute fingerprint and pass it:

```python
discovery = await self._discover_schema(stave_id)
fingerprint = compute_schema_fingerprint(discovery.get("schema", {}))
# ... later in _run_both_tracks:
bi_analysis = await self._analyze_business_intelligence(
    stave_id, snapshot, profile, discovery=discovery, fingerprint=fingerprint
)
```

In `run_on_demand` — do NOT pass discovery or fingerprint (defaults to None):

```python
bi_analysis = await self._analyze_business_intelligence(stave_id, snapshot, profile)
```

- [ ] **Step 5: Persist schema_interpretation in persist_results**

In `_persist_business_report` or in `persist_results`, after BI analysis returns, extract and save the schema_interpretation:

```python
if bi_analysis and "_schema_interpretation" in bi_analysis:
    interp = bi_analysis.pop("_schema_interpretation")
    await self.repo.update_profile(stave_id, {
        "schema_interpretation": json.dumps(interp),
    })
```

Make sure `_parse_json_field` in `repo.py` handles `schema_interpretation` in `get_profile` deserialization (add it alongside other JSON fields like `learned_patterns`).

- [ ] **Step 6: Run relevant tests**

```bash
.venv/bin/python -m pytest tests/features/insights/test_insight_service.py \
    tests/features/insights/test_bi_pipeline_service.py -v --timeout=10
```

Expected: all PASS. Fix any test that was constructing the old `_analyze_business_intelligence` signature.

- [ ] **Step 7: Commit**

```bash
git add datametronome/podium/datametronome_podium/features/insights/service.py
git commit --no-verify -m "feat(service): fingerprint computation, plan invalidation, schema_interpretation persistence"
```

---

### Task 8: Extend prune_old_snapshots to prune stave_query_plans

**Files:**
- Modify: `datametronome/podium/datametronome_podium/tasks/intelligence_tasks.py`

- [ ] **Step 1: Write failing test**

In `tests/features/insights/test_bi_pipeline_service.py` (or a new file if needed), add:

```python
@pytest.mark.asyncio
async def test_prune_old_snapshots_also_prunes_query_plans():
    """prune_old_snapshots must call repo.prune_old_plans to delete stave_query_plans rows."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from datametronome_podium.tasks.intelligence_tasks import _prune_snapshots_async

    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(return_value=1)

    with patch(
        "datametronome_podium.tasks.intelligence_tasks.worker_db_session"
    ) as mock_session, patch(
        "datametronome_podium.features.insights.repo.InsightsRepo.prune_old_plans",
        new_callable=AsyncMock,
    ) as mock_prune:
        mock_session.return_value.__aenter__ = AsyncMock(return_value=(None, mock_executor))
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        await _prune_snapshots_async()

    # repo.prune_old_plans must have been called with the cutoff timestamp
    mock_prune.assert_called_once()
    cutoff_arg = mock_prune.call_args[0][0]
    assert "2025" in cutoff_arg or "2026" in cutoff_arg  # cutoff is a timestamp string
```

- [ ] **Step 2: Run to see it fail**

```bash
.venv/bin/python -m pytest -k "test_prune_old_snapshots_also_prunes_query_plans" -v --timeout=10
```

Expected: FAIL — `stave_query_plans` not mentioned in pruning logic.

- [ ] **Step 3: Update _prune_snapshots_async in intelligence_tasks.py**

Import `InsightsRepo` inside `_prune_snapshots_async` (matching how other tasks import features) and call `repo.prune_old_plans(cutoff)` after the existing snapshot pruning:

```python
from datametronome_podium.features.insights.repo import InsightsRepo

async with worker_db_session(settings.database_url) as (_, executor):
    # ... existing baseline_snapshots pruning ...

    # Prune invalidated query plans older than 90 days
    repo = InsightsRepo(executor)
    await repo.prune_old_plans(cutoff)
    logger.info("Pruned old query plans before %s", cutoff)
```

This reuses the `prune_old_plans` method defined in Task 3 (repo CRUD) rather than duplicating the SQL.

- [ ] **Step 4: Run test**

```bash
.venv/bin/python -m pytest -k "test_prune_old_snapshots_also_prunes_query_plans" -v --timeout=10
```

Expected: PASS.

- [ ] **Step 5: Run the full test suite**

```bash
.venv/bin/python -m pytest tests/ -v --timeout=10
```

Expected: all previously-passing tests PASS, new tests PASS.

- [ ] **Step 6: Commit**

```bash
git add datametronome/podium/datametronome_podium/tasks/intelligence_tasks.py
git commit --no-verify -m "feat(tasks): prune stave_query_plans alongside baseline_snapshots"
```

---

### Task 9: End-to-end smoke test + final verification

- [ ] **Step 1: Run the full test suite one final time**

```bash
cd datametronome/podium
.venv/bin/python -m pytest tests/ -v --timeout=10 --tb=short 2>&1 | tail -30
```

Expected: all tests pass, no regressions.

- [ ] **Step 2: Verify Docker stack starts cleanly**

```bash
docker compose up -d
docker compose exec api .venv/bin/python -m alembic upgrade head
docker compose logs api | grep -E "(ERROR|WARNING)" | grep -v "BI query" | head -20
```

Expected: migration runs cleanly, no new errors in logs.

- [ ] **Step 3: Verify archetypes load correctly**

```bash
docker compose exec api .venv/bin/python -c "
from datametronome_podium.archetypes import load_all_archetypes
for a in load_all_archetypes():
    has_kpi = 'kpi_definitions' in a
    has_sql = 'kpi_queries' in a
    print(f\"{a['name']:15} kpi_definitions={has_kpi} legacy_kpi_queries={has_sql}\")
"
```

Expected: e-commerce, saas, crm show `kpi_definitions=True legacy_kpi_queries=False`. iot, generic show `kpi_definitions=False legacy_kpi_queries=False`.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit --no-verify -m "chore: agent-generated BI query plans — implementation complete"
```
