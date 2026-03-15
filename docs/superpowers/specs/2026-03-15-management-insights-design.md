# Management Insights Layer — Design Spec

**Date:** 2026-03-15
**Status:** Approved
**Branch:** feat/data-intelligence

---

## Problem

The current Data Intelligence pipeline produces **data quality findings** — row counts, freshness, null rates, anomaly detection. These are valuable for engineers and data ops teams, but useless to a CEO, Head of Sales, or COO who needs to know: *Is the business growing? Who is performing? What should we act on today?*

The AI's analysis prompt asks for health scores and anomaly evidence. It says nothing about revenue trends, top-performing products, regional breakdowns, or executive summaries. This is the gap.

---

## Goal

Build a **Business Intelligence Track** that runs in parallel with the existing data quality track. The result is two clearly separated views on the Insights page:

- **Management View** — executive summary, KPIs, top/bottom performers with drill-down, trends, opportunities, risks
- **Technical View** — existing data quality findings, anomalies, suggestions (unchanged)

Accepting a suggestion auto-creates a monitoring check (clef) when the AI recommends one.

---

## Architecture Overview

Two parallel tracks inside the existing pipeline orchestrations:

```
Stage 1: Discovery (schema + samples)
Stage 2: Classification (domain type)
Stage 3: Baseline Snapshot
              ↓
  ┌───────────┴───────────┐
Track 1 (existing)    Track 2 (new)
Data Quality Agent    BusinessIntelligenceAgent
→ LLMInsightReport    → BusinessReport
  └───────────┬───────────┘
              ↓
Stage 5: persist_results — saves both, linked by stave_id + snapshot_id
```

Both tracks run concurrently via `asyncio.gather`. Total latency increase is bounded by whichever track is slower (typically both are similar).

---

## Data Models

### `BusinessReport` (new, `features/insights/model.py`)

```python
class BusinessReport(BaseModel):
    id: str
    stave_id: str
    snapshot_id: str
    tenant_id: str
    business_health_score: int           # 0-100, independent of data quality score
    executive_summary: str               # 3-5 sentences, plain English, CEO-readable
    kpis: list[KPIResult]
    top_performers: list[PerformerInsight]
    bottom_performers: list[PerformerInsight]
    trends: list[TrendInsight]
    opportunities: list[str]             # actionable for management
    risks: list[str]                     # business risks needing attention
    generated_at: str
```

### `KPIResult`

```python
class KPIResult(BaseModel):
    name: str                            # e.g. "average_order_value"
    label: str                           # e.g. "Average Order Value"
    value: float
    unit: str                            # e.g. "$", "%", "count"
    vs_benchmark: str | None             # e.g. "above typical range ($20-$200)"
    trend_direction: Literal["up", "down", "stable"]
```

### `PerformerInsight`

```python
class PerformerInsight(BaseModel):
    entity_type: str                     # "product", "region", "customer_segment", "category"
    entity_name: str
    metric: str
    value: float
    unit: str
    vs_average: float                    # % above/below average
    drill_down_explanation: str          # "Up 34% because X saw a spike on Y"
```

### `TrendInsight`

```python
class TrendInsight(BaseModel):
    metric: str
    direction: Literal["up", "down", "stable"]
    magnitude: float                     # percentage change
    timeframe: str                       # e.g. "last 7 days"
    explanation: str
```

### `LLMSuggestion` update (existing model)

Add optional field:
```python
check_spec: LLMCheckSpec | None = None
```

When the AI recommends monitoring a specific metric, it populates this field. Accepting the suggestion auto-creates the clef from this spec.

---

## BusinessIntelligenceAgent

**Location:** `services/agents/business_intelligence.py`

The agent is archetype-aware. Its system prompt is built dynamically from the matched archetype, injecting the domain name, KPI definitions, and performer dimensions. It uses a focused set of read-only query tools against the stave's data source.

**Tools:**

| Tool | Purpose |
|------|---------|
| `run_kpi_query(stave_id, kpi_name)` | Executes a named KPI query from the archetype YAML |
| `query_top_performers(stave_id, entity_type, metric, limit)` | Ranks entities by metric, returns top/bottom N |
| `drill_down(stave_id, entity_type, entity_name, metric)` | Follow-up query to explain a performer's result |
| `query_trend(stave_id, metric, days)` | Computes metric over time using snapshots + live data |

All tools are read-only. No writes, no cross-stave access.

**Output type:** `LLMBusinessReport` (Pydantic AI structured output), mapped to `BusinessReport` at persist time.

**System prompt structure:**
```
You are the DataMetronome Business Intelligence Analyst for a {domain_type} business.

DOMAIN: {archetype name and description}
AVAILABLE KPIs: {kpi list from archetype}
PERFORMER DIMENSIONS: {entity types and rank metrics}

Your job: compute real business metrics by calling the query tools, find top and bottom
performers, explain WHY they are performing that way by drilling down, identify trends,
and produce an executive summary a CEO can act on today.

Be specific and quantitative. "Revenue is up" is weak.
"Revenue grew 12% this week ($54K vs $48K last week), driven by Product X in Region Y" is strong.
```

---

## Archetype Enhancements

Each archetype YAML gains two new sections:

### `kpi_queries`
Named SQL templates, parameterized by `{schema}`:

```yaml
kpi_queries:
  average_order_value: |
    SELECT AVG(total_amount) as value
    FROM {schema}.orders
    WHERE status = 'completed'
  monthly_revenue: |
    SELECT SUM(total_amount) as value
    FROM {schema}.orders
    WHERE date_trunc('month', created_at) = date_trunc('month', NOW())
  conversion_rate: |
    SELECT COUNT(DISTINCT o.customer_id)::float / NULLIF(COUNT(DISTINCT c.id), 0) as value
    FROM {schema}.customers c
    LEFT JOIN {schema}.orders o ON o.customer_id = c.id
```

### `performer_dimensions`
What entities to rank and how to drill down:

```yaml
performer_dimensions:
  - entity: product
    table: order_items
    join_table: products
    join_key: product_id
    name_column: product_name
    rank_by: revenue
    rank_query: |
      SELECT p.product_name as name, SUM(oi.price * oi.quantity) as value
      FROM {schema}.order_items oi JOIN {schema}.products p ON oi.product_id = p.id
      GROUP BY p.product_name ORDER BY value DESC LIMIT {limit}
    drill_by: [week, category]
  - entity: region
    table: orders
    rank_by: order_count
    rank_query: |
      SELECT shipping_region as name, COUNT(*) as value
      FROM {schema}.orders GROUP BY shipping_region ORDER BY value DESC LIMIT {limit}
    drill_by: [product, customer_type]
```

Adding a new archetype (logistics, fintech, healthcare) requires only a new YAML file. No Python changes needed.

---

## Pipeline Integration

### Changes to `InsightPipelineService`

`analyze_business` is refactored. The existing data quality analysis is renamed `_analyze_data_quality`. A new `_analyze_business_intelligence` method runs the `BusinessIntelligenceAgent`. Both are called in `asyncio.gather`:

```python
async def _run_both_tracks(self, stave_id, snapshot, profile):
    quality_task = self._analyze_data_quality(stave_id, snapshot, profile)
    bi_task = self._analyze_business_intelligence(stave_id, snapshot, profile)
    quality_result, bi_result = await asyncio.gather(quality_task, bi_task, return_exceptions=True)
    return quality_result, bi_result
```

If Track 2 fails, Track 1 results are still persisted (graceful degradation).

### Changes to `persist_results`

- Saves `BusinessReport` to new `business_reports` table
- Links by `stave_id` and `snapshot_id`

### Changes to `accept_suggestion` endpoint

```python
@router.post("/{stave_id}/suggestions/{suggestion_id}/accept")
async def accept_suggestion(stave_id, suggestion_id):
    sug = await repo.get_suggestion(suggestion_id)
    await repo.update_suggestion_status(suggestion_id, "accepted")

    # Auto-create clef if AI provided a check spec
    if sug.check_spec:
        await service._create_check_from_spec(stave_id, sug.report_id, sug.check_spec, now)

    return {"id": suggestion_id, "status": "accepted", "check_created": bool(sug.check_spec)}
```

---

## Database Migration

New table:

```sql
CREATE TABLE business_reports (
    id TEXT PRIMARY KEY,
    stave_id TEXT NOT NULL REFERENCES staves(id),
    snapshot_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    business_health_score INTEGER NOT NULL DEFAULT 0,
    executive_summary TEXT NOT NULL DEFAULT '',
    kpis JSONB NOT NULL DEFAULT '[]',
    top_performers JSONB NOT NULL DEFAULT '[]',
    bottom_performers JSONB NOT NULL DEFAULT '[]',
    trends JSONB NOT NULL DEFAULT '[]',
    opportunities JSONB NOT NULL DEFAULT '[]',
    risks JSONB NOT NULL DEFAULT '[]',
    generated_at TEXT NOT NULL
);

CREATE INDEX idx_business_reports_stave_id ON business_reports(stave_id);
```

Existing `insight_suggestions` table gains a `check_spec` JSONB column (nullable).

---

## API Additions

```
GET  /api/v1/insights/{stave_id}/business          → BusinessReportResponse
GET  /api/v1/insights/{stave_id}/business/history  → list[BusinessReportResponse]
```

`DashboardResponse` gains `business_report: BusinessReportResponse | None` so the frontend can fetch everything in one call.

---

## Frontend Changes

### New `Management View` section (above Technical View)

Per stave, rendered when `item.businessReport !== null`:

```
Business Health Score  |  Executive Summary (prose)
─────────────────────────────────────────────────
KPI pills: AOV $124  |  MRR $48K  |  Conv. 3.2%
─────────────────────────────────────────────────
Top Performers (green)    Bottom Performers (red)
↑ Product X  +34%         ↓ Region Y  −18%
  drill-down explanation    drill-down explanation
─────────────────────────────────────────────────
Trends: Revenue ↑12% this week · Orders ↓3%
─────────────────────────────────────────────────
Opportunities (amber)  |  Risks (red)
```

Collapsed/skeleton state shown when `businessReport === null` with "Waiting for business analysis…" message.

### `insightsService` additions

```ts
getBusinessReport(staveId: string): Promise<BusinessReport>
getBusinessReportHistory(staveId: string): Promise<BusinessReport[]>
```

### Accept suggestion change

The Accept button response now includes `check_created: boolean`. When `true`, show a toast: "Suggestion accepted — monitoring check created."

---

## Graceful Degradation

- If Track 2 (BI) fails, Track 1 (data quality) results are saved normally. The Management View shows a "Business analysis unavailable" state.
- If a KPI query fails (e.g. table doesn't exist), that KPI is skipped and the agent continues with available data.
- If no archetype match exists (domain: `generic`), Track 2 still runs but with a generic prompt that attempts common business metrics (revenue, user counts, activity).

---

## What Makes This Different

No existing data monitoring product combines:
1. **Automated domain classification** (knows it's e-commerce vs SaaS vs CRM without configuration)
2. **Parallel quality + business intelligence tracks** from the same scan
3. **Drill-down explanations** — not just "Product X is top performer" but "because of a spike in Region Y on Tuesday"
4. **Accept-to-monitor** — one click turns an AI observation into a permanent automated check
5. **Archetype-driven KPIs** — business metrics are specific to the domain, not generic row counts

---

## Out of Scope (v1)

- Cross-stave comparisons (e.g. two data sources side by side)
- User-configurable KPI definitions via UI
- Weekly "board report" PDF export
- Separate executive vs. technical user roles/permissions
- Natural language Q&A on business report results (exists in chat already)
