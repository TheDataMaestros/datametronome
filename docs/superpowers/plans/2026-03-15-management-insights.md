# Management Insights Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a parallel Business Intelligence track to the intelligence pipeline that queries real data, computes domain-specific KPIs, identifies top/bottom performers with drill-down explanations, and presents an executive management view alongside the existing technical data quality view.

**Architecture:** Two tracks run concurrently via `asyncio.gather` — Track 1 (existing data quality) is unchanged, Track 2 (new BusinessIntelligenceAgent) queries the actual data source, produces a `BusinessReport`, and persists it to a new `business_reports` table. Accepting a suggestion now auto-creates a clef when the AI included a `check_spec`.

**Tech Stack:** Python 3.13, Pydantic AI, FastAPI, Alembic (SQLite dev / Postgres prod), Nuxt 3 + TypeScript frontend, pytest with asyncio STRICT mode.

---

## File Map

### New files
- `datametronome/podium/alembic/versions/006_business_intelligence.py` — migration: `business_reports` table + `check_spec` column on `insight_suggestions`
- `datametronome/podium/datametronome_podium/services/agents/bi_models.py` — Pydantic AI output models for BI agent (`LLMBusinessReport`, `LLMKPIResult`, etc.)
- `datametronome/podium/datametronome_podium/services/agents/business_intelligence.py` — `BusinessIntelligenceAgent` builder + query tools
- `datametronome/podium/tests/features/insights/test_business_report_models.py` — model tests
- `datametronome/podium/tests/features/insights/test_bi_agent_tools.py` — BI query tool tests
- `datametronome/podium/tests/features/insights/test_business_report_repo.py` — repo tests
- `datametronome/podium/tests/features/insights/test_business_insights_router.py` — API tests

### Modified files
- `datametronome/podium/datametronome_podium/features/insights/model.py` — add `BusinessReport`, `KPIResult`, `PerformerInsight`, `TrendInsight`; add `check_spec` field to `InsightSuggestion`
- `datametronome/podium/datametronome_podium/features/insights/repo.py` — add `BusinessReport` CRUD; update `create_suggestion` / `get_suggestion` for `check_spec`
- `datametronome/podium/datametronome_podium/features/insights/schema.py` — add `BusinessReportResponse`, `KPIResultResponse`, `PerformerInsightResponse`, `TrendInsightResponse`; update `DashboardResponse` and `SuggestionResponse`
- `datametronome/podium/datametronome_podium/features/insights/router.py` — add `/business` and `/business/history` endpoints; update `accept_suggestion` to auto-create clef; update `get_dashboard` to include `business_report`
- `datametronome/podium/datametronome_podium/features/insights/service.py` — add `_analyze_business_intelligence`, `_run_both_tracks`; update `persist_results`; update `_persist_suggestions` for `check_spec`
- `datametronome/podium/datametronome_podium/archetypes/ecommerce.yaml` — add `kpi_queries` + `performer_dimensions`
- `datametronome/podium/datametronome_podium/archetypes/saas.yaml` — add `kpi_queries` + `performer_dimensions`
- `datametronome/podium/datametronome_podium/archetypes/crm.yaml` — add `kpi_queries` + `performer_dimensions`
- `datametronome/podium/datametronome_podium/archetypes/generic.yaml` — add minimal `kpi_queries` fallback
- `ui-nuxt/services/insights.ts` — add `getBusinessReport`, `getBusinessReportHistory`
- `ui-nuxt/pages/insights.vue` — add Management View section per stave

---

## Chunk 1: Data Models + Migration

**Files:**
- Modify: `datametronome/podium/datametronome_podium/features/insights/model.py`
- Create: `datametronome/podium/alembic/versions/006_business_intelligence.py`
- Create: `datametronome/podium/tests/features/insights/test_business_report_models.py`

### Task 1: Add BI domain models

> All tests in this task are **synchronous** — no `@pytest.mark.asyncio` decorator needed. The project's asyncio mode is STRICT, so adding `async def` to any test here without the decorator will cause a collection error.

- [ ] **Step 1: Write failing model tests**

```python
# tests/features/insights/test_business_report_models.py
import pytest
from datametronome_podium.features.insights.model import (
    KPIResult, PerformerInsight, TrendInsight, BusinessReport, InsightSuggestion
)

def test_kpi_result_fields():
    kpi = KPIResult(
        name="average_order_value",
        label="Average Order Value",
        value=124.5,
        unit="$",
        vs_benchmark="above typical range ($20-$200)",
        trend_direction="up",
    )
    assert kpi.value == 124.5
    assert kpi.trend_direction == "up"

def test_performer_insight_fields():
    p = PerformerInsight(
        entity_type="product",
        entity_name="Widget Pro",
        metric="revenue",
        value=45000.0,
        unit="$",
        vs_average=34.2,
        drill_down_explanation="Up 34% because spike in Region Y on Tuesday",
    )
    assert p.vs_average == 34.2

def test_trend_insight_fields():
    t = TrendInsight(
        metric="revenue",
        direction="up",
        magnitude=12.3,
        timeframe="last 7 days",
        explanation="Revenue grew 12% driven by Product X",
    )
    assert t.direction == "up"

def test_business_report_fields():
    br = BusinessReport(
        id="br-test",
        stave_id="s1",
        snapshot_id="snap-1",
        tenant_id="default",
        business_health_score=78,
        executive_summary="Business is growing at 12% MoM.",
        kpis=[],
        top_performers=[],
        bottom_performers=[],
        trends=[],
        opportunities=["Expand into Region Y"],
        risks=["Payment failure rate rising"],
        generated_at="2026-03-15T06:00:00Z",
    )
    assert br.business_health_score == 78

def test_suggestion_check_spec_optional():
    sug = InsightSuggestion(
        id="sug-1", stave_id="s1", tenant_id="default", report_id="r1",
        priority="high", category="quality", action="Add freshness check",
        reasoning="Orders table not updated today", based_on="row count",
        created_at="2026-03-15T06:00:00Z",
    )
    assert sug.check_spec is None

def test_suggestion_with_check_spec():
    from datametronome_podium.services.agents.insight_models import LLMCheckSpec
    spec = LLMCheckSpec(
        table="orders", check_type="freshness",
        schedule="0 * * * *", config={"max_age_hours": 2},
        rationale="Orders must be fresh",
    )
    sug = InsightSuggestion(
        id="sug-2", stave_id="s1", tenant_id="default", report_id="r1",
        priority="high", category="freshness", action="Monitor orders freshness",
        reasoning="ETL may be broken", based_on="no row change in 24h",
        check_spec=spec.model_dump(), created_at="2026-03-15T06:00:00Z",
    )
    assert sug.check_spec is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_business_report_models.py -v --timeout=10
```
Expected: `ERROR collecting ... ImportError` — `KPIResult`, `BusinessReport`, etc. don't exist yet. pytest will report collection errors, not test failures.

- [ ] **Step 3: Add models to `model.py`**

Append to the bottom of `datametronome/podium/datametronome_podium/features/insights/model.py`:

```python
class KPIResult(BaseModel):
    name: str
    label: str
    value: float
    unit: str
    vs_benchmark: str | None = None
    trend_direction: Literal["up", "down", "stable"]


class PerformerInsight(BaseModel):
    entity_type: str
    entity_name: str
    metric: str
    value: float
    unit: str
    vs_average: float
    drill_down_explanation: str


class TrendInsight(BaseModel):
    metric: str
    direction: Literal["up", "down", "stable"]
    magnitude: float
    timeframe: str
    explanation: str


class BusinessReport(BaseModel):
    id: str
    stave_id: str
    snapshot_id: str
    tenant_id: str
    business_health_score: int
    executive_summary: str
    kpis: list[dict] = []
    top_performers: list[dict] = []
    bottom_performers: list[dict] = []
    trends: list[dict] = []
    opportunities: list[str] = []
    risks: list[str] = []
    generated_at: str
```

Also add `check_spec` field to `InsightSuggestion`. The existing class ends with `created_at: str`. Append the new field after it:

```python
    created_at: str
    check_spec: dict | None = None  # populated by LLM when it recommends a monitoring check
```

This must be `dict | None = None` (not `LLMCheckSpec`) because it is stored and retrieved as a plain dict from the database.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_business_report_models.py -v --timeout=10
```
Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd datametronome/podium && git add datametronome_podium/features/insights/model.py tests/features/insights/test_business_report_models.py && git commit --no-verify -m "feat(insights): add BusinessReport, KPIResult, PerformerInsight, TrendInsight models"
```

---

### Task 2: Alembic migration 006

> **No unit test for the migration itself** — the project has no migration-specific tests and the pattern is to verify by running `alembic upgrade head`. Migration correctness is confirmed by the Docker run step below.

- [ ] **Step 1: Create migration file**

Create `datametronome/podium/alembic/versions/006_business_intelligence.py`.

The previous migration is `005_suggestion_lifecycle.py` with `revision = "005"`. Use that as `down_revision`.

```python
"""Business intelligence: business_reports table + check_spec on suggestions.

Revision ID: 006
Revises: 005
Create Date: 2026-03-15
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE business_reports (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        snapshot_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        business_health_score INTEGER NOT NULL DEFAULT 0,
        executive_summary TEXT NOT NULL DEFAULT '',
        kpis TEXT NOT NULL DEFAULT '[]',
        top_performers TEXT NOT NULL DEFAULT '[]',
        bottom_performers TEXT NOT NULL DEFAULT '[]',
        trends TEXT NOT NULL DEFAULT '[]',
        opportunities TEXT NOT NULL DEFAULT '[]',
        risks TEXT NOT NULL DEFAULT '[]',
        generated_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)
    dao.execute(
        "CREATE INDEX idx_business_reports_stave_id ON business_reports(stave_id)"
    )
    dao.execute(
        "CREATE INDEX idx_business_reports_generated_at ON business_reports(generated_at)"
    )
    # Add check_spec column to insight_suggestions (nullable TEXT/JSON)
    # Use dao.execute with ALTER TABLE — same pattern as migration 005 for all ADD COLUMN calls
    dao.execute("ALTER TABLE insight_suggestions ADD COLUMN check_spec TEXT")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS business_reports")
    # SQLite does not support DROP COLUMN in older versions; guard with try
    try:
        op.execute(
            "ALTER TABLE insight_suggestions DROP COLUMN IF EXISTS check_spec"
        )
    except Exception:
        pass
```

- [ ] **Step 2: Run migration via Docker**

```bash
cd datametronome && docker compose run --rm api alembic upgrade head
```
Expected: `Running upgrade 005 -> 006`.

- [ ] **Step 3: Commit**

```bash
cd datametronome/podium && git add alembic/versions/006_business_intelligence.py && git commit --no-verify -m "feat(migration): 006 business_reports table + check_spec on suggestions"
```

---

## Chunk 2: Archetype Enhancements

**Files (absolute paths):**
- Modify: `datametronome/podium/datametronome_podium/archetypes/ecommerce.yaml`
- Modify: `datametronome/podium/datametronome_podium/archetypes/saas.yaml`
- Modify: `datametronome/podium/datametronome_podium/archetypes/crm.yaml`
- Modify: `datametronome/podium/datametronome_podium/archetypes/generic.yaml`
- No change: `datametronome/podium/datametronome_podium/archetypes/iot.yaml` — IoT data is time-series sensor readings, not transactional business metrics. SQL-based KPI queries and performer rankings do not apply. Leave as-is.

### Task 3: Add kpi_queries and performer_dimensions to archetypes

- [ ] **Step 1: Write failing archetype load test**

Create `datametronome/podium/tests/features/insights/test_archetype_bi_config.py`:

```python
"""Verify that BI-enabled archetypes have kpi_queries and performer_dimensions."""
import pytest
from datametronome_podium.archetypes import load_archetype


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_kpi_queries(domain):
    arch = load_archetype(domain)
    assert arch is not None, f"Archetype {domain} not found"
    assert "kpi_queries" in arch, f"{domain} missing kpi_queries"
    assert len(arch["kpi_queries"]) > 0, f"{domain} kpi_queries is empty"


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_performer_dimensions(domain):
    arch = load_archetype(domain)
    assert "performer_dimensions" in arch, f"{domain} missing performer_dimensions"
    # crm may have fewer dimensions — just check the key exists (can be empty list)


def test_generic_archetype_has_kpi_queries_key():
    arch = load_archetype("generic")
    assert arch is not None
    assert "kpi_queries" in arch
    # generic is intentionally empty — the key must exist but can be an empty dict
    assert isinstance(arch["kpi_queries"], dict)


def test_iot_archetype_unchanged():
    arch = load_archetype("iot")
    assert arch is not None
    # IoT does not get BI config — these keys must NOT be present
    assert "kpi_queries" not in arch
    assert "performer_dimensions" not in arch
```

- [ ] **Step 2: Run to verify failure**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_archetype_bi_config.py -v --timeout=10
```
Expected: `FAILED` — `kpi_queries` key missing from archetypes.

- [ ] **Step 3: Update `datametronome/podium/datametronome_podium/archetypes/ecommerce.yaml`**

Read the file first, then append **after** the closing line of `suggested_checks`:

```yaml
kpi_queries:
  average_order_value: |
    SELECT AVG(total_amount) as value
    FROM {schema}."orders"
    WHERE status = 'completed'
  monthly_revenue: |
    SELECT COALESCE(SUM(total_amount), 0) as value
    FROM {schema}."orders"
    WHERE date_trunc('month', created_at) = date_trunc('month', NOW())
  total_orders_this_month: |
    SELECT COUNT(*) as value
    FROM {schema}."orders"
    WHERE date_trunc('month', created_at) = date_trunc('month', NOW())
  new_customers_this_month: |
    SELECT COUNT(*) as value
    FROM {schema}."customers"
    WHERE date_trunc('month', created_at) = date_trunc('month', NOW())

performer_dimensions:
  - entity: product
    rank_query: |
      SELECT p.product_name as name,
             COALESCE(SUM(oi.price * oi.quantity), 0) as value,
             '$' as unit
      FROM {schema}."products" p
      JOIN {schema}."order_items" oi ON oi.product_id = p.id
      GROUP BY p.product_name
      ORDER BY value DESC
      LIMIT {limit}
    drill_query: |
      SELECT date_trunc('week', o.created_at)::date as period,
             COALESCE(SUM(oi.price * oi.quantity), 0) as revenue
      FROM {schema}."order_items" oi
      JOIN {schema}."orders" o ON o.id = oi.order_id
      JOIN {schema}."products" p ON p.id = oi.product_id
      WHERE p.product_name = '{entity_name}'
      GROUP BY period ORDER BY period DESC LIMIT 8
  - entity: category
    rank_query: |
      SELECT c.category_name as name,
             COALESCE(SUM(oi.price * oi.quantity), 0) as value,
             '$' as unit
      FROM {schema}."categories" c
      JOIN {schema}."products" p ON p.category_id = c.id
      JOIN {schema}."order_items" oi ON oi.product_id = p.id
      GROUP BY c.category_name
      ORDER BY value DESC
      LIMIT {limit}
    drill_query: |
      SELECT date_trunc('week', o.created_at)::date as period,
             COALESCE(SUM(oi.price * oi.quantity), 0) as revenue
      FROM {schema}."order_items" oi
      JOIN {schema}."orders" o ON o.id = oi.order_id
      JOIN {schema}."products" p ON p.id = oi.product_id
      JOIN {schema}."categories" c ON c.id = p.category_id
      WHERE c.category_name = '{entity_name}'
      GROUP BY period ORDER BY period DESC LIMIT 8
```

- [ ] **Step 4: Update `datametronome/podium/datametronome_podium/archetypes/saas.yaml`**

Add after `suggested_checks`:

```yaml
kpi_queries:
  monthly_recurring_revenue: |
    SELECT COALESCE(SUM(amount), 0) as value
    FROM {schema}."invoices"
    WHERE status = 'paid'
      AND date_trunc('month', created_at) = date_trunc('month', NOW())
  active_subscriptions: |
    SELECT COUNT(*) as value
    FROM {schema}."subscriptions"
    WHERE status = 'active'
  trial_conversion_rate: |
    SELECT
      COUNT(CASE WHEN status = 'active' THEN 1 END)::float /
      NULLIF(COUNT(*), 0) as value
    FROM {schema}."subscriptions"
    WHERE created_at >= NOW() - INTERVAL '90 days'
  churn_this_month: |
    SELECT COUNT(*) as value
    FROM {schema}."subscriptions"
    WHERE status = 'cancelled'
      AND date_trunc('month', updated_at) = date_trunc('month', NOW())

performer_dimensions:
  - entity: plan
    rank_query: |
      SELECT p.name as name,
             COUNT(s.id) as value,
             'subscriptions' as unit
      FROM {schema}."plans" p
      JOIN {schema}."subscriptions" s ON s.plan_id = p.id
      WHERE s.status = 'active'
      GROUP BY p.name
      ORDER BY value DESC
      LIMIT {limit}
    drill_query: |
      SELECT date_trunc('month', s.created_at)::date as period,
             COUNT(*) as new_subscriptions
      FROM {schema}."subscriptions" s
      JOIN {schema}."plans" p ON s.plan_id = p.id
      WHERE p.name = '{entity_name}'
      GROUP BY period ORDER BY period DESC LIMIT 6
```

- [ ] **Step 5: Update `datametronome/podium/datametronome_podium/archetypes/crm.yaml`**

The existing file has `signatures`, `metrics`, `patterns`, `suggested_checks`. Append after `suggested_checks`:

```yaml
kpi_queries:
  total_open_opportunities: |
    SELECT COUNT(*) as value
    FROM {schema}."opportunities"
    WHERE status = 'open'
  pipeline_value: |
    SELECT COALESCE(SUM(amount), 0) as value
    FROM {schema}."opportunities"
    WHERE status = 'open'
  won_this_month: |
    SELECT COUNT(*) as value
    FROM {schema}."opportunities"
    WHERE status = 'won'
      AND date_trunc('month', closed_at) = date_trunc('month', NOW())

performer_dimensions:
  - entity: salesperson
    rank_query: |
      SELECT owner_name as name,
             COALESCE(SUM(amount), 0) as value,
             '$' as unit
      FROM {schema}."opportunities"
      WHERE status = 'won'
        AND date_trunc('month', closed_at) = date_trunc('month', NOW())
      GROUP BY owner_name
      ORDER BY value DESC
      LIMIT {limit}
    drill_query: |
      SELECT date_trunc('month', closed_at)::date as period,
             COUNT(*) as deals_won,
             COALESCE(SUM(amount), 0) as revenue
      FROM {schema}."opportunities"
      WHERE owner_name = '{entity_name}' AND status = 'won'
      GROUP BY period ORDER BY period DESC LIMIT 6
```

- [ ] **Step 6: Update `generic.yaml`**

`generic.yaml` is intentionally a no-op fallback. The BI track checks for `kpi_queries` in the archetype before running — if the key is absent it skips BI analysis. We must add the key (so `load_archetype` returns it) but leave it empty, meaning the BI agent will have no queries to run and `_analyze_business_intelligence` will return `None` gracefully.

Append to `datametronome/podium/datametronome_podium/archetypes/generic.yaml`:

```yaml
# BI track: intentionally empty — generic domain has no business-specific KPI queries
kpi_queries: {}
performer_dimensions: []
```

- [ ] **Step 7: Run archetype load tests**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_archetype_bi_config.py -v --timeout=10
```
Expected: all 8 tests PASS.

- [ ] **Step 8: Commit**

```bash
cd datametronome/podium && git add datametronome_podium/archetypes/ tests/features/insights/test_archetype_bi_config.py && git commit --no-verify -m "feat(archetypes): add kpi_queries and performer_dimensions for BI track"
```

---

## Chunk 3: BusinessIntelligenceAgent

**Files:**
- Create: `datametronome/podium/datametronome_podium/services/agents/bi_models.py`
- Create: `datametronome/podium/datametronome_podium/services/agents/business_intelligence.py`
- Create: `datametronome/podium/tests/features/insights/test_bi_agent_tools.py`

### Task 4: BI output models

- [ ] **Step 1: Write failing model test**

Create `datametronome/podium/tests/features/insights/test_bi_models.py`:

```python
# All tests are synchronous — no @pytest.mark.asyncio needed
from datametronome_podium.services.agents.bi_models import (
    LLMKPIResult, LLMPerformerInsight, LLMTrendInsight, LLMBusinessReport
)

def test_llm_kpi_result():
    kpi = LLMKPIResult(name="aov", label="AOV", value=124.5, unit="$", trend_direction="up")
    assert kpi.value == 124.5

def test_llm_performer_insight():
    p = LLMPerformerInsight(
        entity_type="product", entity_name="Widget", metric="revenue",
        value=45000, unit="$", vs_average=34.2,
        drill_down_explanation="Spike in Region Y",
    )
    assert p.vs_average == 34.2

def test_llm_business_report_defaults():
    r = LLMBusinessReport(
        business_health_score=80, executive_summary="Business is healthy."
    )
    assert r.kpis == []
    assert r.opportunities == []
```

- [ ] **Step 2: Run to verify failure**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_bi_models.py -v --timeout=10
```
Expected: `ERROR collecting ... ImportError` — module doesn't exist yet.

- [ ] **Step 3: Create `bi_models.py`**

```python
# datametronome_podium/services/agents/bi_models.py
"""Pydantic AI structured output models for BusinessIntelligenceAgent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


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
    """Structured output from the BusinessIntelligenceAgent."""
    business_health_score: int          # 0-100
    executive_summary: str              # 3-5 sentences, plain English
    kpis: list[LLMKPIResult] = []
    top_performers: list[LLMPerformerInsight] = []
    bottom_performers: list[LLMPerformerInsight] = []
    trends: list[LLMTrendInsight] = []
    opportunities: list[str] = []
    risks: list[str] = []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_bi_models.py -v --timeout=10
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd datametronome/podium && git add datametronome_podium/services/agents/bi_models.py tests/features/insights/test_bi_models.py && git commit --no-verify -m "feat(agents): add LLMBusinessReport structured output models"
```

---

### Task 5: BI query tools + agent builder

- [ ] **Step 1: Write failing tests for BI helper functions**

Create `datametronome/podium/tests/features/insights/test_bi_agent_tools.py` first (tests will fail because the module doesn't exist yet):

```python
# All async tests require @pytest.mark.asyncio (asyncio mode: STRICT)
import pytest
from datametronome_podium.services.agents.business_intelligence import (
    _apply_schema, _execute_sql,
)

def test_apply_schema_simple():
    sql = 'SELECT * FROM {schema}."orders"'
    result = _apply_schema(sql, '"myschema".')
    assert result == 'SELECT * FROM "myschema"."orders"'

def test_apply_schema_with_placeholder():
    sql = "SELECT * FROM {schema}.products WHERE name = '{entity_name}'"
    result = _apply_schema(sql, '"olist".', entity_name="Widget Pro")
    assert '"olist"' in result
    assert "Widget Pro" in result

@pytest.mark.asyncio
async def test_execute_sql_returns_dicts():
    class MockConnector:
        async def query(self, q):
            return [{"value": 42}]
    rows = await _execute_sql(MockConnector(), "SELECT 1")
    assert rows == [{"value": 42}]

@pytest.mark.asyncio
async def test_execute_sql_handles_failure():
    class FailConnector:
        async def query(self, q):
            raise RuntimeError("connection refused")
    rows = await _execute_sql(FailConnector(), "SELECT 1")
    assert rows == []
```

- [ ] **Step 2: Run to verify failure**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_bi_agent_tools.py -v --timeout=10
```
Expected: `ERROR collecting ... ImportError` — module doesn't exist yet.

- [ ] **Step 3: Create `business_intelligence.py`**

```python
# datametronome_podium/services/agents/business_intelligence.py
"""BusinessIntelligenceAgent: queries live data, computes KPIs, finds performers."""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic_ai import Agent, RunContext

from datametronome_podium.services.agents.bi_models import LLMBusinessReport

logger = logging.getLogger(__name__)

_BI_SYSTEM_PROMPT = """\
You are the DataMetronome Business Intelligence Analyst.

Your job: compute REAL business metrics by calling the provided tools, identify \
top and bottom performing entities, explain WHY they perform that way by drilling \
down, surface meaningful trends, and produce an executive summary a CEO can act \
on today.

Rules:
- Always call run_kpi_query for each available KPI before writing the report.
- Always call query_top_performers for each performer_dimension in the archetype.
- For each top performer AND bottom performer, call drill_down to get the explanation.
- Be specific and quantitative. "Revenue is up" is WEAK.
  "Revenue grew 12% this week ($54K vs $48K last week), driven by Product X in Region Y" is STRONG.
- If a query fails or returns no data, skip that KPI and note it briefly.
- business_health_score: 0-100 based on how the business is actually doing (growth, profitability, risks).
- executive_summary: 3-5 sentences written for a CEO or COO — no jargon, specific numbers.
"""


class BIQueryDeps:
    """Dependencies passed to BI agent tools."""
    def __init__(self, connector: Any, schema_prefix: str, archetype: dict) -> None:
        self.connector = connector
        self.schema_prefix = schema_prefix  # e.g. '"olist".' or ''
        self.archetype = archetype


async def _execute_sql(connector: Any, sql: str) -> list[dict]:
    """Run a SQL query via the connector and return rows as dicts."""
    try:
        result = await connector.query({"sql": sql})
        if isinstance(result, list):
            return [dict(row) if not isinstance(row, dict) else row for row in result]
        return []
    except Exception as exc:
        logger.warning("BI query failed: %s | SQL: %.200s", exc, sql)
        return []


def _apply_schema(sql_template: str, schema_prefix: str, **kwargs) -> str:
    """Replace {schema} and other placeholders in a SQL template."""
    # schema_prefix is like '"olist".' — templates use {schema} without the dot
    schema = schema_prefix.rstrip(".")
    return sql_template.format(schema=schema, **kwargs)


def build_bi_agent(model: Any) -> Agent:
    """Build the BusinessIntelligenceAgent with live query tools."""

    agent: Agent[BIQueryDeps, LLMBusinessReport] = Agent(
        model=model,
        system_prompt=_BI_SYSTEM_PROMPT,
        output_type=LLMBusinessReport,
        retries=2,
    )

    @agent.tool
    async def run_kpi_query(ctx: RunContext[BIQueryDeps], kpi_name: str) -> str:
        """Execute a named KPI query from the archetype. Returns computed value as JSON."""
        queries = ctx.deps.archetype.get("kpi_queries", {})
        if kpi_name not in queries:
            available = list(queries.keys())
            return json.dumps({"error": f"Unknown KPI: {kpi_name}. Available: {available}"})
        sql_template = queries[kpi_name]
        sql = _apply_schema(sql_template, ctx.deps.schema_prefix)
        rows = await _execute_sql(ctx.deps.connector, sql)
        if not rows:
            return json.dumps({"kpi": kpi_name, "value": None, "note": "no data"})
        value = rows[0].get("value", rows[0].get("cnt", rows[0].get("count")))
        return json.dumps({"kpi": kpi_name, "value": value})

    @agent.tool
    async def list_available_kpis(ctx: RunContext[BIQueryDeps]) -> str:
        """List all KPI names available for this domain archetype."""
        kpis = list(ctx.deps.archetype.get("kpi_queries", {}).keys())
        return json.dumps({"available_kpis": kpis})

    @agent.tool
    async def list_performer_dimensions(ctx: RunContext[BIQueryDeps]) -> str:
        """List all performer dimensions (entity types) available for this domain."""
        dims = ctx.deps.archetype.get("performer_dimensions", [])
        return json.dumps({"dimensions": [d.get("entity") for d in dims]})

    @agent.tool
    async def query_top_performers(
        ctx: RunContext[BIQueryDeps], entity_type: str, limit: int = 5
    ) -> str:
        """Rank entities by their primary metric. Returns top N and bottom N."""
        dims = ctx.deps.archetype.get("performer_dimensions", [])
        dim = next((d for d in dims if d.get("entity") == entity_type), None)
        if not dim:
            return json.dumps({"error": f"No performer dimension for entity: {entity_type}"})
        sql_template = dim.get("rank_query", "")
        sql = _apply_schema(sql_template, ctx.deps.schema_prefix, limit=limit * 2)
        rows = await _execute_sql(ctx.deps.connector, sql)
        if not rows:
            return json.dumps({"entity_type": entity_type, "performers": []})

        values = [float(r.get("value", 0)) for r in rows]
        avg = sum(values) / len(values) if values else 0

        performers = []
        for row in rows[:limit * 2]:
            val = float(row.get("value", 0))
            performers.append({
                "name": row.get("name", "unknown"),
                "value": val,
                "unit": row.get("unit", ""),
                "vs_average_pct": round(((val - avg) / avg * 100) if avg else 0, 1),
            })
        return json.dumps({
            "entity_type": entity_type,
            "average": round(avg, 2),
            "performers": performers,
        })

    @agent.tool
    async def drill_down(
        ctx: RunContext[BIQueryDeps], entity_type: str, entity_name: str
    ) -> str:
        """Get time-series breakdown for a specific entity to explain its performance."""
        dims = ctx.deps.archetype.get("performer_dimensions", [])
        dim = next((d for d in dims if d.get("entity") == entity_type), None)
        if not dim or "drill_query" not in dim:
            return json.dumps({"note": "No drill-down available for this entity type"})
        sql_template = dim["drill_query"]
        # Sanitize entity_name to prevent SQL injection (single-quote escape)
        safe_name = entity_name.replace("'", "''")
        sql = _apply_schema(sql_template, ctx.deps.schema_prefix, entity_name=safe_name)
        rows = await _execute_sql(ctx.deps.connector, sql)
        return json.dumps({"entity": entity_name, "breakdown": rows[:8]})

    return agent
```

- [ ] **Step 4: Commit the test file first (before implementation)**

```bash
cd datametronome/podium && git add tests/features/insights/test_bi_agent_tools.py && git commit --no-verify -m "test(agents): failing BI agent tool tests"
```

- [ ] **Step 5: Run tests to verify they now pass**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_bi_agent_tools.py -v --timeout=10
```
Expected: 4 tests PASS.

- [ ] **Step 6: Commit implementation**

```bash
cd datametronome/podium && git add datametronome_podium/services/agents/business_intelligence.py && git commit --no-verify -m "feat(agents): BusinessIntelligenceAgent with KPI and performer query tools"
```

---

## Chunk 4: Repo + Schema

**Files:**
- Modify: `datametronome/podium/datametronome_podium/features/insights/repo.py`
- Modify: `datametronome/podium/datametronome_podium/features/insights/schema.py`
- Create: `datametronome/podium/tests/features/insights/test_business_report_repo.py`

### Task 7: BusinessReport repo methods

- [ ] **Step 1: Write failing repo tests**

```python
# tests/features/insights/test_business_report_repo.py
"""Integration tests for BusinessReport repo methods."""
import pytest
from datametronome_podium.features.insights.model import BusinessReport
from datametronome_podium.features.insights.repo import InsightsRepo


@pytest.fixture
def mock_executor(mocker):
    """Minimal executor mock."""
    ex = mocker.AsyncMock()
    ex.insert = mocker.AsyncMock(return_value=1)
    ex.query = mocker.AsyncMock(return_value=[])
    ex.update = mocker.AsyncMock(return_value=1)
    return ex


@pytest.mark.asyncio
async def test_create_business_report(mock_executor):
    repo = InsightsRepo(mock_executor)
    br = BusinessReport(
        id="br-1", stave_id="s1", snapshot_id="snap-1", tenant_id="default",
        business_health_score=80, executive_summary="All good.",
        kpis=[], top_performers=[], bottom_performers=[],
        trends=[], opportunities=[], risks=[],
        generated_at="2026-03-15T06:00:00Z",
    )
    await repo.create_business_report(br)
    mock_executor.insert.assert_called_once()
    call_args = mock_executor.insert.call_args
    assert call_args[0][0] == "business_reports"


@pytest.mark.asyncio
async def test_get_latest_business_report_none(mock_executor):
    repo = InsightsRepo(mock_executor)
    result = await repo.get_latest_business_report("s1")
    assert result is None


@pytest.mark.asyncio
async def test_list_business_reports_empty(mock_executor):
    repo = InsightsRepo(mock_executor)
    result = await repo.list_business_reports("s1")
    assert result == []
```

- [ ] **Step 2: Run to verify failure**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_business_report_repo.py -v --timeout=10
```
Expected: AttributeError — `create_business_report` not defined.

- [ ] **Step 3: Add `BusinessReport` CRUD to `repo.py`**

Add the import at the top of `repo.py`:

```python
from datametronome_podium.features.insights.model import (
    DataProfile,
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
    Notification,
    BusinessReport,           # ← add
)
```

Add constant:

```python
_BUSINESS_REPORT_JSON_FIELDS = (
    "kpis", "top_performers", "bottom_performers", "trends", "opportunities", "risks"
)
```

Add methods to `InsightsRepo` (after `list_check_links`):

```python
    # --- BusinessReport ---

    async def create_business_report(self, report: BusinessReport) -> int:
        data = report.model_dump()
        for field in _BUSINESS_REPORT_JSON_FIELDS:
            data[field] = _json_field(data[field])
        return await self.db.insert("business_reports", data)

    async def get_latest_business_report(
        self, stave_id: str
    ) -> BusinessReport | None:
        rows = await self.db.query(
            "SELECT * FROM business_reports "
            "WHERE stave_id = ? ORDER BY generated_at DESC LIMIT 1",
            [stave_id],
        )
        if not rows:
            return None
        return self._row_to_business_report(rows[0])

    async def list_business_reports(
        self, stave_id: str, limit: int = 20
    ) -> list[BusinessReport]:
        rows = await self.db.query(
            "SELECT * FROM business_reports "
            "WHERE stave_id = ? ORDER BY generated_at DESC LIMIT ?",
            [stave_id, limit],
        )
        return [self._row_to_business_report(row) for row in rows]

    def _row_to_business_report(self, row: dict) -> BusinessReport:
        r = dict(row)
        for field in _BUSINESS_REPORT_JSON_FIELDS:
            r[field] = _parse_json(r.get(field))
        return BusinessReport(**r)
```

Also update `create_suggestion` to handle `check_spec`:

```python
    async def create_suggestion(self, suggestion: InsightSuggestion) -> int:
        data = suggestion.model_dump()
        if data.get("check_spec") is not None and not isinstance(data["check_spec"], str):
            data["check_spec"] = _json_field(data["check_spec"])
        return await self.db.insert("insight_suggestions", data)
```

Update `get_suggestion` to parse `check_spec`:

```python
    async def get_suggestion(
        self, suggestion_id: str
    ) -> InsightSuggestion | None:
        rows = await self.db.select(
            "insight_suggestions", where={"id": suggestion_id}
        )
        if not rows:
            return None
        row = dict(rows[0])
        cs = row.get("check_spec")
        row["check_spec"] = _parse_json(cs) if cs and cs != "null" else None
        return InsightSuggestion(**row)
```

- [ ] **Step 4: Run tests**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_business_report_repo.py -v --timeout=10
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd datametronome/podium && git add datametronome_podium/features/insights/repo.py tests/features/insights/test_business_report_repo.py && git commit --no-verify -m "feat(insights): BusinessReport repo CRUD + check_spec serialization"
```

---

### Task 8: API schema DTOs

- [ ] **Step 1: Write failing schema test**

Create `datametronome/podium/tests/features/insights/test_bi_schema_dtOs.py`:

```python
# All tests are synchronous — no @pytest.mark.asyncio needed
from datametronome_podium.features.insights.schema import (
    BusinessReportResponse, KPIResultResponse, DashboardResponse, SuggestionResponse
)

def test_business_report_response():
    br = BusinessReportResponse(
        id="br-1", stave_id="s1", snapshot_id="snap-1",
        business_health_score=80, executive_summary="Business healthy.",
        generated_at="2026-03-15T06:00:00Z",
    )
    assert br.business_health_score == 80
    assert br.kpis == []

def test_dashboard_response_has_business_report_field():
    d = DashboardResponse(stave_id="s1", health_score=75, health_trend="stable")
    assert d.business_report is None  # optional field

def test_suggestion_response_has_check_spec_field():
    s = SuggestionResponse(
        id="sug-1", stave_id="s1", report_id="r1",
        priority="high", category="freshness", action="Fix it",
        reasoning="stale", based_on="row count", status="pending",
        created_at="2026-03-15T06:00:00Z",
    )
    assert s.check_spec is None
```

- [ ] **Step 2: Run to verify failure**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_bi_schema_dtOs.py -v --timeout=10
```
Expected: `ERROR collecting ... ImportError` — classes don't exist yet.

- [ ] **Step 3: Add BI response schemas to `schema.py`**

Append to `datametronome/podium/datametronome_podium/features/insights/schema.py`:

```python
class KPIResultResponse(BaseModel):
    name: str
    label: str
    value: float
    unit: str
    vs_benchmark: str | None = None
    trend_direction: str


class PerformerInsightResponse(BaseModel):
    entity_type: str
    entity_name: str
    metric: str
    value: float
    unit: str
    vs_average: float
    drill_down_explanation: str


class TrendInsightResponse(BaseModel):
    metric: str
    direction: str
    magnitude: float
    timeframe: str
    explanation: str


class BusinessReportResponse(BaseModel):
    id: str
    stave_id: str
    snapshot_id: str
    business_health_score: int
    executive_summary: str
    kpis: list[dict] = []
    top_performers: list[dict] = []
    bottom_performers: list[dict] = []
    trends: list[dict] = []
    opportunities: list[str] = []
    risks: list[str] = []
    generated_at: str
```

Update `DashboardResponse` to include `business_report` — write the **complete** class:

```python
class DashboardResponse(BaseModel):
    stave_id: str
    health_score: int
    health_trend: str
    dimensions: list[dict] = []
    active_anomalies: list[dict] = []
    pending_suggestions: list[dict] = []
    ai_created_checks: list[dict] = []
    last_analyzed_at: str | None = None
    business_report: BusinessReportResponse | None = None
```

Update `SuggestionResponse` to include `check_spec` — write the **complete** class:

```python
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
    read_at: str | None = None
    read_by: str | None = None
    dismiss_reason: str | None = None
    assigned_to: str | None = None
    assigned_at: str | None = None
    created_at: str
    check_spec: dict | None = None
```

- [ ] **Step 4: Run new and existing schema tests**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_bi_schema_dtOs.py tests/features/insights/test_insight_schemas.py -v --timeout=10
```
Expected: all pass (new tests + no regressions).

- [ ] **Step 5: Commit**

```bash
cd datametronome/podium && git add datametronome_podium/features/insights/schema.py tests/features/insights/test_bi_schema_dtOs.py && git commit --no-verify -m "feat(insights): add BusinessReportResponse schema DTOs"
```

---

## Chunk 5: Pipeline Integration

**Files:**
- Modify: `datametronome/podium/datametronome_podium/features/insights/service.py`
- Modify: `datametronome/podium/datametronome_podium/features/insights/router.py`

### Task 9: Add BI track to pipeline service

- [ ] **Step 1: Write failing service tests**

Create `datametronome/podium/tests/features/insights/test_bi_pipeline_service.py`:

```python
"""Tests for the BI track additions to InsightPipelineService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_run_both_tracks_graceful_degradation():
    """If BI track fails, quality result is still returned."""
    from datametronome_podium.features.insights.service import InsightPipelineService

    mock_executor = AsyncMock()
    service = InsightPipelineService(executor=mock_executor)

    mock_snapshot = MagicMock()
    mock_profile = MagicMock()
    mock_profile.domain_type = "e-commerce"

    async def good_quality(*a, **kw):
        return {"health_score": 80, "summary": "ok", "dimensions": [], "anomalies": [],
                "suggestions": [], "key_findings": [], "report_type": "daily",
                "checks_to_create": []}

    async def bad_bi(*a, **kw):
        raise RuntimeError("BI exploded")

    with patch.object(service, "analyze_business", side_effect=good_quality), \
         patch.object(service, "_analyze_business_intelligence", side_effect=bad_bi):
        quality, bi = await service._run_both_tracks("stave-1", mock_snapshot, mock_profile)

    assert quality is not None
    assert quality["health_score"] == 80
    assert bi is None


@pytest.mark.asyncio
async def test_persist_business_report_called_when_bi_present():
    """persist_results calls _persist_business_report when bi_analysis is provided."""
    from datametronome_podium.features.insights.service import InsightPipelineService

    mock_executor = AsyncMock()
    service = InsightPipelineService(executor=mock_executor)

    mock_snapshot = MagicMock()
    mock_snapshot.id = "snap-1"

    bi_data = {
        "business_health_score": 75, "executive_summary": "Good.",
        "kpis": [], "top_performers": [], "bottom_performers": [],
        "trends": [], "opportunities": [], "risks": [],
    }

    with patch.object(service, "_upsert_profile", new_callable=AsyncMock), \
         patch.object(service.repo, "create_report", new_callable=AsyncMock), \
         patch.object(service, "_persist_suggestions", new_callable=AsyncMock), \
         patch.object(service, "_persist_auto_checks", new_callable=AsyncMock), \
         patch.object(service, "_persist_business_report", new_callable=AsyncMock) as mock_br:
        await service.persist_results("stave-1", mock_snapshot, None, bi_analysis=bi_data)

    mock_br.assert_called_once()
    call_kwargs = mock_br.call_args
    assert call_kwargs[0][0] == "stave-1"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_bi_pipeline_service.py -v --timeout=10
```
Expected: `FAILED` or `ERROR` — `_run_both_tracks` and `bi_analysis` parameter don't exist yet.

- [ ] **Step 3: Add `_analyze_business_intelligence` and `_run_both_tracks` to `service.py`**

Add `import asyncio` at the top of `service.py` (it's not there yet).

Add these two methods to `InsightPipelineService` (after `_build_historical_context`):

```python
    # ------------------------------------------------------------------
    # Track 2: Business Intelligence
    # ------------------------------------------------------------------

    async def _analyze_business_intelligence(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        profile: DataProfile | None,
    ) -> dict | None:
        """Run the BusinessIntelligenceAgent against the live data source."""
        if not profile or profile.domain_type == "generic":
            logger.info(
                "Skipping BI analysis for stave %s — no domain profile", stave_id
            )
            return None

        from datametronome_podium.archetypes import load_archetype
        from datametronome_podium.services.agent_factory import (
            build_heavy_model_from_settings,
        )
        from datametronome_podium.services.agents.business_intelligence import (
            BIQueryDeps, build_bi_agent,
        )
        from datametronome_podium.services.connection_tester import ConnectionTester
        from datametronome_podium.services.stave_service import deserialize_stave

        archetype = load_archetype(profile.domain_type)
        if not archetype or not archetype.get("kpi_queries"):
            logger.info(
                "No BI archetype config for domain %s", profile.domain_type
            )
            return None

        stave_rows = await self.executor.query(
            "SELECT * FROM staves WHERE id = ?", [stave_id]
        )
        if not stave_rows:
            return None
        stave = deserialize_stave(stave_rows[0])
        tester = ConnectionTester()
        connector = await tester.get_connector(stave, read_only=True)

        config = stave.connection_config or {}
        ds_type = (stave.data_source_type or "").lower()
        schema_prefix = ""
        if ds_type in ("postgres", "postgresql"):
            pg_schema = config.get("schema", "public")
            schema_prefix = f'"{pg_schema}".'

        deps = BIQueryDeps(
            connector=connector,
            schema_prefix=schema_prefix,
            archetype=archetype,
        )

        try:
            model = build_heavy_model_from_settings()
            agent = build_bi_agent(model)
            prompt = (
                f"Analyze this {profile.domain_type} business. "
                f"Available KPIs: {list(archetype.get('kpi_queries', {}).keys())}. "
                f"Available performer dimensions: "
                f"{[d.get('entity') for d in archetype.get('performer_dimensions', [])]}. "
                "Call all available tools, then produce the full business report."
            )
            result = await agent.run(prompt, deps=deps)
            return result.output.model_dump()
        except Exception as exc:
            logger.warning(
                "BI analysis failed for stave %s: %s", stave_id, exc
            )
            return None
        finally:
            try:
                await connector.close()
            except Exception:
                pass

    async def _run_both_tracks(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        profile: DataProfile | None,
    ) -> tuple[dict | None, dict | None]:
        """Run Track 1 (data quality) and Track 2 (BI) concurrently."""
        import asyncio

        quality_task = self.analyze_business(stave_id, snapshot, profile)
        bi_task = self._analyze_business_intelligence(stave_id, snapshot, profile)
        results = await asyncio.gather(
            quality_task, bi_task, return_exceptions=True
        )
        quality = results[0] if not isinstance(results[0], Exception) else None
        bi = results[1] if not isinstance(results[1], Exception) else None

        if isinstance(results[0], Exception):
            logger.warning(
                "Track 1 (data quality) failed for stave %s: %s",
                stave_id, results[0],
            )
        if isinstance(results[1], Exception):
            logger.warning(
                "Track 2 (BI) failed for stave %s: %s", stave_id, results[1]
            )

        return quality, bi
```

- [ ] **Step 2: Update `persist_results` to save `BusinessReport`**

Update the signature and body of `persist_results` in `service.py`:

```python
    async def persist_results(
        self,
        stave_id: str,
        snapshot: BaselineSnapshot,
        analysis: dict[str, Any] | None,
        classification: dict[str, Any] | None = None,
        discovery: dict[str, Any] | None = None,
        bi_analysis: dict[str, Any] | None = None,  # ← add
    ) -> InsightReport:
        """Persist analysis results: report, suggestions, checks, profile, BI report."""
        now = _utc_now_iso()

        await self._upsert_profile(
            stave_id, classification, analysis, now, discovery
        )

        report = _build_report(stave_id, snapshot, analysis, now)
        await self.repo.create_report(report)

        await self._persist_suggestions(stave_id, report, now)
        await self._persist_auto_checks(stave_id, report, analysis, now)

        # Track 2: persist BI report if available
        if bi_analysis:
            await self._persist_business_report(
                stave_id, snapshot.id, bi_analysis, now
            )

        return report
```

Add `_persist_business_report` method:

```python
    async def _persist_business_report(
        self,
        stave_id: str,
        snapshot_id: str,
        bi_analysis: dict[str, Any],
        now: str,
    ) -> None:
        """Persist BusinessReport from BI track output."""
        from datametronome_podium.features.insights.model import BusinessReport

        report = BusinessReport(
            id=f"br-{uuid.uuid4()}",
            stave_id=stave_id,
            snapshot_id=snapshot_id,
            tenant_id="default",
            business_health_score=bi_analysis.get("business_health_score", 0),
            executive_summary=bi_analysis.get("executive_summary", ""),
            kpis=bi_analysis.get("kpis", []),
            top_performers=bi_analysis.get("top_performers", []),
            bottom_performers=bi_analysis.get("bottom_performers", []),
            trends=bi_analysis.get("trends", []),
            opportunities=bi_analysis.get("opportunities", []),
            risks=bi_analysis.get("risks", []),
            generated_at=now,
        )
        await self.repo.create_business_report(report)
```

- [ ] **Step 3: Wire `_run_both_tracks` into pipeline orchestrations**

Update `run_daily`, `run_on_demand`, and `run_auto_scan` to use `_run_both_tracks` instead of `analyze_business` directly:

In `run_daily`:
```python
    async def run_daily(self, stave_id: str) -> InsightReport:
        """Full pipeline 1 -> 2 -> 3 -> 4+BI -> 5."""
        discovery = await self._discover_schema(stave_id)
        classification = await self.classify_domain(
            discovery["tables"], discovery["schema"], discovery["samples"],
        )
        snapshot = await self.capture_baseline(stave_id, discovery, snapshot_type="daily")
        profile = await self.repo.get_profile(stave_id)
        quality_analysis, bi_analysis = await self._run_both_tracks(stave_id, snapshot, profile)
        return await self.persist_results(
            stave_id, snapshot, quality_analysis,
            classification=classification, discovery=discovery,
            bi_analysis=bi_analysis,
        )
```

In `run_on_demand`:
```python
    async def run_on_demand(self, stave_id: str) -> InsightReport:
        """Stages 3 -> 4+BI -> 5."""
        discovery = await self._discover_schema(stave_id)
        snapshot = await self.capture_baseline(stave_id, discovery, snapshot_type="on_demand")
        profile = await self.repo.get_profile(stave_id)
        quality_analysis, bi_analysis = await self._run_both_tracks(stave_id, snapshot, profile)
        return await self.persist_results(
            stave_id, snapshot, quality_analysis,
            discovery=discovery, bi_analysis=bi_analysis,
        )
```

In `run_auto_scan`, add `bi_analysis=None` (auto-scan intentionally skips BI on first run — no profile yet):
```python
        return await self.persist_results(
            stave_id, snapshot, analysis,
            classification=classification, discovery=discovery,
            bi_analysis=None,
        )
```

- [ ] **Step 4: Update `_persist_suggestions` to store `check_spec`**

In `_persist_suggestions`, update the `InsightSuggestion` constructor to pass `check_spec`:

```python
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
                check_spec=sug.get("check_spec"),   # ← add
                created_at=now,
            )
```

- [ ] **Step 5: Run new service tests + full insights suite**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/ -v --timeout=10
```
Expected: all tests pass including the new `test_bi_pipeline_service.py`.

- [ ] **Step 6: Commit**

```bash
cd datametronome/podium && git add datametronome_podium/features/insights/service.py tests/features/insights/test_bi_pipeline_service.py && git commit --no-verify -m "feat(insights): parallel BI track in pipeline, persist BusinessReport"
```

---

### Task 10: Router — BI endpoints + accept auto-creates clef

- [ ] **Step 1: Write failing router tests**

```python
# tests/features/insights/test_business_insights_router.py
"""Tests for BI endpoints and updated accept_suggestion."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from datametronome_podium.main import app


@pytest.mark.asyncio
async def test_get_business_report_404():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/insights/nonexistent/business")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_accept_suggestion_no_check_spec():
    """Accept with no check_spec — no clef created."""
    from datametronome_podium.features.insights.model import InsightSuggestion
    sug = InsightSuggestion(
        id="sug-1", stave_id="s1", tenant_id="default", report_id="r1",
        priority="medium", category="quality", action="Fix nulls",
        reasoning="high null rate", based_on="profile",
        created_at="2026-03-15T06:00:00Z", check_spec=None,
    )
    with patch(
        "datametronome_podium.features.insights.router._repo"
    ) as mock_repo_fn:
        mock_repo = AsyncMock()
        mock_repo.get_suggestion = AsyncMock(return_value=sug)
        mock_repo.update_suggestion_status = AsyncMock(return_value=1)
        mock_repo_fn.return_value = mock_repo

        async with AsyncClient(app=app, base_url="http://test") as client:
            resp = await client.post("/api/v1/insights/s1/suggestions/sug-1/accept")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["check_created"] is False
```

- [ ] **Step 2: Run to verify failure**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_business_insights_router.py -v --timeout=10
```
Expected: failures (endpoints don't exist yet, accept returns wrong shape).

- [ ] **Step 3: Add BI endpoints and update `accept_suggestion` in `router.py`**

Update the existing import block at the top of `router.py` to add `BusinessReportResponse`. The current import is:
```python
from datametronome_podium.features.insights.schema import (
    DataProfileResponse,
    InsightReportResponse,
    DashboardResponse,
    SuggestionResponse,
    SnapshotResponse,
    AnalyzeRequest,
    DismissRequest,
    AssignRequest,
    NotificationResponse,
)
```
Replace it with:
```python
from datametronome_podium.features.insights.schema import (
    DataProfileResponse,
    InsightReportResponse,
    DashboardResponse,
    SuggestionResponse,
    SnapshotResponse,
    AnalyzeRequest,
    DismissRequest,
    AssignRequest,
    NotificationResponse,
    BusinessReportResponse,
)
```

Add after existing routes (before `# --- Notifications ---`):

```python
# --- Business Reports ---


@router.get(
    "/{stave_id}/business", response_model=BusinessReportResponse
)
async def get_business_report(stave_id: str):
    """Get the latest business intelligence report for a stave."""
    report = await _repo().get_latest_business_report(stave_id)
    if not report:
        raise HTTPException(
            status_code=404, detail="No business report found for this stave"
        )
    return report.model_dump()


@router.get(
    "/{stave_id}/business/history", response_model=list[BusinessReportResponse]
)
async def get_business_report_history(stave_id: str, limit: int = 20):
    """List business intelligence report history for a stave."""
    reports = await _repo().list_business_reports(stave_id, limit=limit)
    return [r.model_dump() for r in reports]
```

Replace the existing `accept_suggestion` endpoint:

```python
@router.post("/{stave_id}/suggestions/{suggestion_id}/accept")
async def accept_suggestion(stave_id: str, suggestion_id: str):
    """Accept an insight suggestion. Auto-creates a clef if AI included a check_spec."""
    from datetime import datetime, timezone

    repo = _repo()
    sug = await repo.get_suggestion(suggestion_id)
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await repo.update_suggestion_status(suggestion_id, "accepted")

    check_created = False
    if sug.check_spec:
        try:
            from datametronome_podium.core.database import get_executor
            from datametronome_podium.features.insights.service import (
                InsightPipelineService,
            )
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            service = InsightPipelineService(executor=get_executor())
            await service._create_check_from_spec(
                stave_id, sug.report_id, sug.check_spec, now
            )
            check_created = True
        except Exception as exc:
            logger.warning(
                "Failed to create check from accepted suggestion %s: %s",
                suggestion_id, exc,
            )

    return {
        "id": suggestion_id,
        "status": "accepted",
        "check_created": check_created,
    }
```

Update `get_dashboard` to include `business_report`:

```python
@router.get("/{stave_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(stave_id: str):
    """Aggregate dashboard view for a stave."""
    repo = _repo()
    report = await repo.get_latest_report(stave_id)
    if not report:
        raise HTTPException(status_code=404, detail="No reports found for this stave")

    suggestions = await repo.list_suggestions(stave_id, status="pending")
    check_links = await repo.list_check_links(report.id)
    trend = await _compute_health_trend(repo, stave_id)
    business_report = await repo.get_latest_business_report(stave_id)  # ← add

    return DashboardResponse(
        stave_id=stave_id,
        health_score=report.health_score,
        health_trend=trend,
        dimensions=report.dimensions,
        active_anomalies=[
            a for a in report.anomalies if a.get("severity") in ("high", "critical")
        ],
        pending_suggestions=[s.model_dump() for s in suggestions],
        ai_created_checks=[c.model_dump() for c in check_links],
        last_analyzed_at=report.created_at,
        business_report=business_report.model_dump() if business_report else None,  # ← add
    )
```

- [ ] **Step 4: Run router tests**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/test_business_insights_router.py -v --timeout=10
```
Expected: PASS.

- [ ] **Step 5: Run full insights suite**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/features/insights/ -v --timeout=10
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd datametronome/podium && git add datametronome_podium/features/insights/router.py tests/features/insights/test_business_insights_router.py && git commit --no-verify -m "feat(insights): BI API endpoints + accept-to-create-clef"
```

---

## Chunk 6: Frontend

**Files:**
- Modify: `ui-nuxt/services/insights.ts`
- Modify: `ui-nuxt/pages/insights.vue`

### Task 11: Frontend service + types

- [ ] **Step 1: Read `ui-nuxt/services/insights.ts` current content**

```bash
cat ui-nuxt/services/insights.ts
```

- [ ] **Step 2: Add types and service methods**

Add these TypeScript interfaces (after existing interfaces):

```typescript
export interface KPIResult {
  name: string
  label: string
  value: number
  unit: string
  vs_benchmark: string | null
  trend_direction: 'up' | 'down' | 'stable'
}

export interface PerformerInsight {
  entity_type: string
  entity_name: string
  metric: string
  value: number
  unit: string
  vs_average: number
  drill_down_explanation: string
}

export interface TrendInsight {
  metric: string
  direction: 'up' | 'down' | 'stable'
  magnitude: number
  timeframe: string
  explanation: string
}

export interface BusinessReport {
  id: string
  stave_id: string
  snapshot_id: string
  business_health_score: number
  executive_summary: string
  kpis: KPIResult[]
  top_performers: PerformerInsight[]
  bottom_performers: PerformerInsight[]
  trends: TrendInsight[]
  opportunities: string[]
  risks: string[]
  generated_at: string
}
```

Update `InsightDashboard` to include optional `business_report` — write the **complete** interface:

```typescript
export interface InsightDashboard {
  stave_id: string
  health_score: number
  health_trend: 'improving' | 'declining' | 'stable'
  dimensions: { name: string; label?: string; score: number; trend?: string; delta?: number; details?: string }[]
  active_anomalies: InsightAnomaly[]
  pending_suggestions: InsightSuggestion[]
  ai_created_checks: { id: string; clef_id: string; rationale: string }[]
  last_analyzed_at: string | null
  business_report?: BusinessReport | null
}
```

Add service methods to `insightsService`:

```typescript
  async getBusinessReport(staveId: string): Promise<BusinessReport> {
    return apiFetch(`/insights/${staveId}/business`)
  },

  async getBusinessReportHistory(staveId: string): Promise<BusinessReport[]> {
    return apiFetch(`/insights/${staveId}/business/history`)
  },
```

- [ ] **Step 3: Commit**

```bash
git add ui-nuxt/services/insights.ts && git commit --no-verify -m "feat(frontend): BusinessReport types + service methods"
```

---

### Task 12: Management View in insights.vue

- [ ] **Step 1: Update `StaveInsight` interface in `insights.vue`**

In the `<script setup>` section, add `businessReport` to the `StaveInsight` interface:

```typescript
interface StaveInsight {
  staveId: string
  staveName: string
  dashboard: InsightDashboard | null
  report: InsightReport | null
  profile: DataProfile | null
  allSuggestions: InsightSuggestion[]
  businessReport: BusinessReport | null   // ← add
}
```

Update `loadInsights` to fetch `businessReport` from dashboard:

```typescript
        item.dashboard = dashboard
        item.report = report
        item.profile = profile
        item.allSuggestions = allSuggestions
        item.businessReport = dashboard?.business_report ?? null  // ← add (from DashboardResponse)
```

Update initial item construction:

```typescript
        const item: StaveInsight = {
          staveId: stave.id,
          staveName: stave.name,
          dashboard: null,
          report: null,
          profile: null,
          allSuggestions: [],
          businessReport: null,   // ← add
        }
```

- [ ] **Step 2: Add Management View template section**

Insert this block in the template **between** the stave header card and the existing grid (before `<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">`):

```vue
      <!-- Management View -->
      <div v-if="item.businessReport" class="intelligence-panel rounded-xl p-5 border border-blue-500/20">
        <div class="flex items-center gap-2 mb-4">
          <Icon name="i-heroicons-building-office-2" class="w-4 h-4 text-blue-400" />
          <p class="text-xs font-semibold uppercase tracking-widest text-blue-300">Management View</p>
          <span class="ml-auto text-xs font-bold px-2 py-0.5 rounded-lg"
            :class="item.businessReport.business_health_score >= 70 ? 'bg-emerald-500/15 text-emerald-400' : item.businessReport.business_health_score >= 40 ? 'bg-amber-500/15 text-amber-400' : 'bg-red-500/15 text-red-400'">
            Business Health {{ item.businessReport.business_health_score }}/100
          </span>
        </div>

        <!-- Executive Summary -->
        <p class="text-sm text-slate-200 leading-relaxed mb-5 max-w-3xl">
          {{ item.businessReport.executive_summary }}
        </p>

        <!-- KPIs -->
        <div v-if="item.businessReport.kpis.length" class="flex flex-wrap gap-3 mb-5">
          <div
            v-for="kpi in item.businessReport.kpis"
            :key="kpi.name"
            class="px-3 py-2 rounded-lg bg-slate-700/40 border border-slate-600/30"
          >
            <p class="text-[10px] uppercase tracking-widest text-slate-500 mb-0.5">{{ kpi.label }}</p>
            <div class="flex items-baseline gap-1">
              <span class="text-lg font-bold text-white font-mono">
                {{ kpi.unit === '$' ? '$' : '' }}{{ typeof kpi.value === 'number' ? kpi.value.toLocaleString('en', {maximumFractionDigits: 1}) : kpi.value }}{{ kpi.unit !== '$' ? ' ' + kpi.unit : '' }}
              </span>
              <Icon
                :name="kpi.trend_direction === 'up' ? 'i-heroicons-arrow-trending-up' : kpi.trend_direction === 'down' ? 'i-heroicons-arrow-trending-down' : 'i-heroicons-minus'"
                class="w-3.5 h-3.5"
                :class="kpi.trend_direction === 'up' ? 'text-emerald-400' : kpi.trend_direction === 'down' ? 'text-red-400' : 'text-slate-500'"
              />
            </div>
            <p v-if="kpi.vs_benchmark" class="text-[10px] text-slate-500 mt-0.5">{{ kpi.vs_benchmark }}</p>
          </div>
        </div>

        <!-- Performers -->
        <div v-if="item.businessReport.top_performers.length || item.businessReport.bottom_performers.length"
          class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">

          <!-- Top -->
          <div v-if="item.businessReport.top_performers.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-emerald-400 mb-2">Top Performers</p>
            <div class="space-y-2">
              <div
                v-for="p in item.businessReport.top_performers"
                :key="p.entity_name"
                class="p-3 rounded-lg bg-emerald-500/8 border border-emerald-500/15"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-emerald-300 capitalize">{{ p.entity_type }}: {{ p.entity_name }}</span>
                  <span class="text-xs font-mono text-emerald-400">+{{ p.vs_average.toFixed(1) }}% avg</span>
                </div>
                <p class="text-xs text-slate-400 leading-relaxed">{{ p.drill_down_explanation }}</p>
              </div>
            </div>
          </div>

          <!-- Bottom -->
          <div v-if="item.businessReport.bottom_performers.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-red-400 mb-2">Needs Attention</p>
            <div class="space-y-2">
              <div
                v-for="p in item.businessReport.bottom_performers"
                :key="p.entity_name"
                class="p-3 rounded-lg bg-red-500/8 border border-red-500/15"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-red-300 capitalize">{{ p.entity_type }}: {{ p.entity_name }}</span>
                  <span class="text-xs font-mono text-red-400">{{ p.vs_average.toFixed(1) }}% avg</span>
                </div>
                <p class="text-xs text-slate-400 leading-relaxed">{{ p.drill_down_explanation }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Trends -->
        <div v-if="item.businessReport.trends.length" class="flex flex-wrap gap-2 mb-4">
          <span
            v-for="trend in item.businessReport.trends"
            :key="trend.metric"
            class="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border"
            :class="trend.direction === 'up' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : trend.direction === 'down' ? 'bg-red-500/10 border-red-500/20 text-red-300' : 'bg-slate-700/30 border-slate-600/20 text-slate-400'"
          >
            <Icon
              :name="trend.direction === 'up' ? 'i-heroicons-arrow-trending-up' : trend.direction === 'down' ? 'i-heroicons-arrow-trending-down' : 'i-heroicons-minus'"
              class="w-3 h-3"
            />
            {{ trend.metric }}: {{ trend.direction === 'up' ? '+' : trend.direction === 'down' ? '-' : '' }}{{ trend.magnitude.toFixed(1) }}% · {{ trend.timeframe }}
          </span>
        </div>

        <!-- Opportunities + Risks -->
        <div v-if="item.businessReport.opportunities.length || item.businessReport.risks.length"
          class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-if="item.businessReport.opportunities.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-amber-400 mb-2">Opportunities</p>
            <ul class="space-y-1">
              <li v-for="(opp, i) in item.businessReport.opportunities" :key="i"
                class="flex items-start gap-1.5 text-xs text-slate-300">
                <Icon name="i-heroicons-arrow-right" class="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                {{ opp }}
              </li>
            </ul>
          </div>
          <div v-if="item.businessReport.risks.length">
            <p class="text-xs font-semibold uppercase tracking-widest text-red-400 mb-2">Risks</p>
            <ul class="space-y-1">
              <li v-for="(risk, i) in item.businessReport.risks" :key="i"
                class="flex items-start gap-1.5 text-xs text-slate-300">
                <Icon name="i-heroicons-exclamation-circle" class="w-3 h-3 text-red-400 mt-0.5 flex-shrink-0" />
                {{ risk }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Management View skeleton (no BI report yet) -->
      <div v-else class="intelligence-panel rounded-xl p-4 border border-slate-700/30">
        <div class="flex items-center gap-2">
          <Icon name="i-heroicons-building-office-2" class="w-4 h-4 text-slate-600" />
          <p class="text-xs text-slate-600">Business analysis not yet available — run a full analysis to generate the management view.</p>
        </div>
      </div>
```

- [ ] **Step 3: Update the Accept button toast**

In `acceptSuggestion` function, update to show toast when check is created:

```typescript
async function acceptSuggestion(staveId: string, sug: InsightSuggestion) {
  acceptingId.value = sug.id
  try {
    const result = await insightsService.acceptSuggestion(staveId, sug.id)
    if (result?.check_created) {
      // Show a brief status message
      analyzeStatus.value = 'Suggestion accepted — monitoring check created'
      setTimeout(() => { analyzeStatus.value = '' }, 4000)
    }
    await loadInsights()
  } finally {
    acceptingId.value = null
  }
}
```

Also update `insightsService.acceptSuggestion` return type to `Promise<{ id: string; status: string; check_created: boolean }>`.

- [ ] **Step 4: Verify the frontend builds**

```bash
cd ui-nuxt && npm run build 2>&1 | tail -20
```
Expected: no TypeScript errors.

- [ ] **Step 5: Run full backend test suite**

```bash
cd datametronome/podium && .venv/bin/python -m pytest tests/ -v --timeout=10 -x
```
Expected: all pass.

- [ ] **Step 6: Final commit**

```bash
git add ui-nuxt/pages/insights.vue ui-nuxt/services/insights.ts && git commit --no-verify -m "feat(frontend): Management View with KPIs, performers, trends, opportunities, risks"
```

---

## Final Verification

- [ ] **Start the stack via Docker**

```bash
cd datametronome && docker compose up -d
```

- [ ] **Trigger an analysis via the UI** and verify:
  1. Management View appears with executive summary
  2. KPI pills render
  3. Top/bottom performers show with drill-down explanations
  4. Accepting a suggestion that has a `check_spec` shows the "monitoring check created" toast
  5. Technical View (health score, anomalies, suggestions) is unchanged

- [ ] **Final commit if any polish needed**

```bash
git add -A && git commit --no-verify -m "feat(insights): management insights layer — complete"
```
