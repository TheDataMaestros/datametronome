# Data Intelligence Layer — Design Spec

**Date:** 2026-03-15
**Status:** Draft
**Branch:** TBD

## Overview

A data intelligence layer that makes DataMetronome proactively explore connected data sources, understand the business domain, and surface actionable insights. Goes beyond data quality ("is the data clean?") into business intelligence ("what does this data mean for the business?").

## Goals

1. **Automatic exploration** — when a stave is created, AI agents discover schema, profile data, and classify the business domain
2. **Cumulative learning** — the system gets smarter over time, building a profile of what's "normal" for each data source
3. **Business insights** — surface trends, anomalies, and actionable suggestions (not just data quality metrics)
4. **Accelerated cold-start** — domain archetypes provide day-one intelligence based on known patterns for e-commerce, SaaS, IoT, etc.
5. **Suggest + auto-create** — AI creates quality checks based on discoveries, tagged and visible to the user

## Non-Goals

- Full autonomy (modifying schedules, alerting external systems without user approval)
- Cross-tenant data sharing or federated learning (future consideration)
- Real-time streaming analysis (batch/scheduled approach)

## Architecture

### Three-Tier Trigger Model

| Tier | Trigger | Pipeline Stages | Execution |
|------|---------|-----------------|-----------|
| **Auto-scan** | Stave creation (connection tested OK) | 1→2→3→5 (produces `initial` report with checks only, no business analysis) | Background Celery task |
| **On-demand** | User asks in chat | 3→4→5 | Async via orchestrator (dispatches Celery task, streams progress to chat) |
| **Scheduled daily** | Celery Beat cron (e.g., `0 6 * * *`) | 1→2→3→4→5 | Background Celery task |

### Five-Stage Pipeline

**Stage 1 — Discovery**
- List all tables, count rows, read column types
- Sample 100 rows per table
- Detect primary/foreign key relationships
- Output: raw schema map + sample data

**Stage 2 — Classification**
- Two-phase matching: (1) deterministic signature matching — count how many required/optional table names from each archetype exist in the schema, producing a ranked score; (2) LLM confirmation — the top-scoring archetype(s) are presented to the LLM alongside the actual schema for final classification and confidence scoring
- Classifies domain (e-commerce, SaaS, IoT, CRM, etc.)
- Identifies entity roles: fact tables, dimension tables, event logs
- Output: `DomainClassification` (domain_type, entity_roles, confidence, business_context)

**Stage 3 — Baseline Snapshot**
- Captures quantitative metrics per table/column: row counts, null rates, value distributions, freshness timestamps, min/max/distinct counts
- First run = initial baseline; subsequent runs = new snapshot for comparison
- Per-table query timeout: 30 seconds. Tables that exceed this are marked as `skipped` in the snapshot with the reason.
- Output: `BaselineSnapshot` (timestamped metrics)

**Stage 4 — Business Analysis**
- LLM receives: domain classification + current snapshot + historical deltas + existing check results
- Compares against previous snapshots (7/30/90-day windows)
- Produces business-level insights, anomaly detection, and suggestions
- Context is compressed (summaries + deltas, not raw data) to manage token costs
- Output: `InsightReport`

**Stage 5 — Suggest + Act**
- When Stage 4 was run: generates full InsightReport (health score, dimensions, anomalies, suggestions, natural language summary)
- When Stage 4 was skipped (auto-scan): generates an `initial` report with health_score based on data quality signals only, no business analysis dimensions, and auto-created checks based on archetype + schema patterns
- Auto-creates quality checks based on discovered patterns (tagged `source: ai-generated`)
- Check specs are validated against the existing check type schemas before creation; malformed specs are logged and skipped
- Stores report and updates data profile

### Concurrency Control

A Redis-based distributed lock prevents overlapping intelligence runs for the same stave:

- Lock key: `intelligence:lock:{stave_id}`, TTL: 30 minutes
- Before starting, each task attempts to acquire the lock. If locked, behavior depends on trigger:
  - **Daily scheduled**: skips silently (will run tomorrow)
  - **On-demand**: returns a message to the user: "An analysis is already in progress for this data source. Results will be available shortly."
  - **Auto-scan**: retries once after 5 minutes, then skips

### LLM Error Handling

Stages 2 and 4 depend on LLM calls. Failure handling:

| Failure | Stage 2 (Classification) | Stage 4 (Business Analysis) |
|---------|--------------------------|----------------------------|
| **Malformed output** (Pydantic validation fails) | Retry once with stricter prompt. On second failure, fall back to Generic archetype. | Retry once. On second failure, save the baseline snapshot (Stage 3 output is still valuable) but skip the InsightReport. Log the error. |
| **API down / rate limited** | Fall back to Generic archetype. Pipeline continues. | Save baseline snapshot, skip InsightReport. Log the error. |
| **Token limit exceeded** | Reduce context (fewer sample rows, summarize more aggressively), retry once. Then fall back to Generic. | Reduce context (fewer historical snapshots, top-5 tables only), retry once. Then save snapshot, skip report. |

The principle: **never lose the baseline snapshot** (Stage 3) due to an LLM failure in a later stage. Snapshots are pure data, always valuable.

### Domain Archetypes

Archetypes are curated knowledge bases that accelerate cold-start learning. They ship as YAML files with the package.

**Location:** `datametronome/podium/archetypes/`

**Archetype structure:**
```yaml
name: e-commerce
description: Online retail, orders, products

signatures:
  required: [orders, products, customers]
  optional: [carts, payments, categories, reviews, shipping]
  # Deterministic matching: score = (required matches / required count) * 0.7
  #                                + (optional matches / optional count) * 0.3
  # Threshold for LLM confirmation: score >= 0.4

metrics:
  - name: average_order_value
    query_hint: "AVG(total) FROM orders"
    typical_range: [20, 200]
  - name: cart_abandonment_rate
    typical_range: [0.60, 0.80]

patterns:
  - weekend_order_spike
  - holiday_seasonality
  - payment_failure_baseline

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
```

**Matching flow:** Schema discovered → deterministic signature scoring ranks archetypes → top candidates (score >= 0.4) sent to LLM for confirmation → LLM picks best match with confidence score → archetype informs first-day analysis → profile diverges as real data overrides assumptions.

If no archetype scores >= 0.4 in the deterministic phase, the LLM still sees the schema but without archetype hints, and may classify as Generic. If the LLM's confidence is < 50% for any non-generic archetype, the system uses Generic.

**Initial archetypes (v1):**
- E-Commerce (orders, products, customers)
- SaaS / Subscriptions (users, subscriptions, invoices, plans)
- IoT / Sensors (devices, readings, events)
- Marketing / CRM (contacts, campaigns, leads, deals)
- Generic (fallback — no domain assumptions)

**Expansion:** New archetypes added per release as user base reveals common domains. Users can also add custom archetype YAML files.

**Future consideration:** Archetypes could be loaded into the database at startup for runtime querying, while YAML remains the source-of-truth/shipping format.

## Data Model

### New Tables

#### `data_profiles`

One per stave. The AI's cumulative memory of a data source. Profile history is tracked via `profile_version` — each reclassification increments the version and stores the previous state in `previous_classification`.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| stave_id | FK → staves | One-to-one (unique constraint) |
| tenant_id | VARCHAR | Denormalized from stave for query performance (see Tenant Isolation) |
| domain_type | VARCHAR | Detected domain (e.g., `"e-commerce"`) |
| domain_confidence | FLOAT | Archetype match confidence (0-1) |
| domain_context | JSON | Business context description, entity roles |
| schema_map | JSON | Table/column structure with relationships |
| entity_roles | JSON | `{"fact": ["orders"], "dimension": ["products", "customers"]}` |
| learned_patterns | JSON | Patterns discovered over time (weekend spikes, seasonality, etc.) |
| profile_version | INTEGER | Incremented on each reclassification (default: 1) |
| previous_classification | JSON | `{domain_type, confidence, changed_at}` — last classification before current, null on first version |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

#### `baseline_snapshots`

Many per stave, one per run. Time-series of quantitative metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| stave_id | FK → staves | |
| tenant_id | VARCHAR | Denormalized from stave for query performance |
| snapshot_type | ENUM | `auto_scan`, `daily`, `on_demand` |
| table_metrics | JSON | `{table: {row_count, null_rates, distributions, freshness}}` |
| column_stats | JSON | Per-column statistics (min, max, distinct, nulls, distribution) |
| captured_at | TIMESTAMP | When the snapshot was taken |

**Retention policy:** Snapshots older than 90 days are aggregated into weekly summaries (average metrics per week) stored as `snapshot_type = "weekly_aggregate"`. Raw daily snapshots beyond 90 days are deleted. This keeps the table bounded at ~90 + (weeks_of_history * 1) rows per stave. A Celery Beat task `prune_old_snapshots` runs weekly to enforce this.

#### `insight_reports`

Many per stave, one per analysis. The actual output consumed by dashboard and chat.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| stave_id | FK → staves | |
| tenant_id | VARCHAR | Denormalized from stave for query performance |
| snapshot_id | FK → baseline_snapshots (nullable) | The snapshot this analysis is based on. Nullable because auto-scan `initial` reports may reference a snapshot but have no Stage 4 analysis. |
| report_type | ENUM | `initial`, `daily`, `on_demand` |
| health_score | INTEGER | 0-100 overall score |
| dimensions | JSON | `[{name, label, score, trend, delta, details}]` |
| anomalies | JSON | `[{severity, category, table, description, evidence, compared_to}]` |
| suggestions | JSON | `[{priority, category, action, reasoning, based_on}]` |
| summary | TEXT | Natural language summary for chat |
| key_findings | JSON | `[str]` — bullet-point findings |
| created_at | TIMESTAMP | |

#### `insight_suggestions`

Individual suggestions extracted from insight reports, with lifecycle tracking (pending → accepted/dismissed).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| stave_id | FK → staves | |
| tenant_id | VARCHAR | Denormalized from stave for query performance |
| report_id | FK → insight_reports | The report that generated this suggestion |
| priority | ENUM | `low`, `medium`, `high` |
| category | VARCHAR | `"growth"`, `"retention"`, `"operations"`, `"data_quality"` |
| action | TEXT | What to do |
| reasoning | TEXT | Why |
| based_on | TEXT | Evidence from the data |
| status | ENUM | `pending`, `accepted`, `dismissed` (default: `pending`) |
| resolved_at | TIMESTAMP | When accepted or dismissed (nullable) |
| created_at | TIMESTAMP | |

#### `insight_created_checks`

Join table linking insight reports to auto-created clefs. Enables reverse lookup: "which report created this check?"

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| report_id | FK → insight_reports | |
| clef_id | FK → clefs | |
| rationale | TEXT | Why this check was created |
| created_at | TIMESTAMP | |

### Tenant Isolation

All intelligence tables include `tenant_id`, denormalized from the parent stave. This is intentional for query performance — dashboard and overview queries filter by `tenant_id` without joining to staves.

**Consistency:** `tenant_id` is set once when the row is created (copied from the stave's tenant_id) and never updated independently. If stave tenant assignment changes (future multi-tenant migration), a data migration updates all child rows.

**Today (single-tenant):** `staves` does not yet have a `tenant_id` column. The intelligence layer uses `tenant_id = "default"` for all rows. When multi-tenancy is added, `tenant_id` will be added to staves and the intelligence tables' values will be migrated to match.

### Relationships

```
stave ──1:1──► data_profile (updated in place, versioned)
stave ──1:*──► baseline_snapshots (time-series, pruned after 90 days)
baseline_snapshot ──0..1:1──► insight_report (optional — auto-scan snapshots may not have a full report)
insight_report ──1:*──► insight_suggestions (extracted for lifecycle tracking)
insight_report ──*:*──► clefs (via insight_created_checks join table)
```

## Pydantic Models

### InsightReport (structured LLM output)

```python
class InsightReport(BaseModel):
    health_score: int  # 0-100
    report_type: Literal["initial", "daily", "on_demand"]
    dimensions: list[Dimension]
    anomalies: list[Anomaly]
    suggestions: list[Suggestion]
    summary: str  # natural language for chat
    key_findings: list[str]
    checks_to_create: list[CheckSpec]

class Dimension(BaseModel):
    name: str        # "data_freshness"
    label: str       # "Data Freshness"
    score: int       # 0-100
    trend: Literal["improving", "stable", "declining"]
    delta: float | None  # vs last run
    details: str     # explanation

class Anomaly(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    category: str    # "volume", "quality", "freshness", "business"
    table: str
    description: str
    evidence: str    # supporting data
    compared_to: str | None  # "7-day avg", "baseline"

class Suggestion(BaseModel):
    priority: Literal["low", "medium", "high"]
    category: str    # "growth", "retention", "operations", "data_quality"
    action: str      # what to do
    reasoning: str   # why
    based_on: str    # evidence from the data

class CheckSpec(BaseModel):
    table: str
    check_type: Literal[
        "row_count", "freshness", "column_values",  # Level 1
        "forecast", "data_profile_drift",            # Level 2
        "lookup_validation",                          # Level 3
    ]
    schedule: str    # cron expression
    config: dict     # validated against check_type schema before creation (see Stage 5)
    rationale: str   # why this check was suggested
```

### DomainClassification (stage 2 output)

```python
class DomainClassification(BaseModel):
    domain_type: str          # "e-commerce", "saas", "iot", etc.
    confidence: float         # 0-1
    business_context: str     # "Online retail store with ~50K orders/month"
    entity_roles: dict        # {"fact": [...], "dimension": [...], "event": [...]}
    matched_archetype: str | None  # archetype name if matched
```

### BaselineSnapshot (stage 3 output)

```python
class TableMetrics(BaseModel):
    row_count: int
    freshness: datetime | None  # most recent timestamp in table
    null_rates: dict[str, float]  # column_name → null percentage
    distributions: dict[str, dict]  # column_name → {min, max, distinct, top_values}
    status: Literal["ok", "skipped"]  # skipped if query timed out
    skip_reason: str | None

class BaselineSnapshot(BaseModel):
    stave_id: str
    snapshot_type: Literal["auto_scan", "daily", "on_demand", "weekly_aggregate"]
    table_metrics: dict[str, TableMetrics]  # table_name → metrics
    captured_at: datetime
```

## InsightAgent

A new Pydantic AI agent that joins the existing agent roster (Router, Config, Investigation, Report).

### System Prompt Strategy

The InsightAgent's system prompt is dynamically composed:
1. Base instructions (role: data analyst and business advisor)
2. Domain archetype context (if matched) — typical metrics, patterns, benchmarks
3. Current data profile (if exists) — what the AI already knows about this data source
4. Historical context — deltas from recent snapshots

This means the agent gets smarter per-stave: a stave analyzed for 90 days gets a much richer system prompt than a brand-new stave.

### Tools

**Reused from existing:**
- `list_stave_tables` — schema discovery
- `get_table_sample` — data sampling
- `suggest_quality_checks` — existing check suggestion logic
- `list_clefs` — current quality checks
- `list_checks` — check execution results

**New tools:**
- `get_data_profile(stave_id)` — load existing data profile
- `save_data_profile(stave_id, profile)` — persist updated profile
- `get_baseline_history(stave_id, days)` — load recent baseline snapshots for comparison
- `get_latest_insight(stave_id)` — load most recent insight report
- `create_insight_report(stave_id, report)` — persist new insight report + extract suggestions to `insight_suggestions` table
- `load_archetype(domain_type)` — load archetype YAML for domain context
- `create_checks_batch(checks)` — auto-create multiple quality checks (tagged `source: ai-generated`, linked via `insight_created_checks`)

## Router Integration

### New Intent

The RouterAgent gets a new `insight` intent added to its routing decisions:

```python
# Intent → Agent mapping
"configure"   → ConfigAgent
"investigate"  → InvestigationAgent
"report"       → ReportAgent
"insight"      → InsightAgent  # NEW

# Chain mode
"insight" + "configure" → InsightAgent → ConfigAgent
# "explore my data and set up monitoring"
```

**Trigger phrases:** "explore my data", "what's happening with sales?", "give me business insights", "analyze my database", "how's my data looking?"

### Orchestrator Changes

The orchestrator dispatches InsightAgent the same way it dispatches other agents — via the existing `RouterAgent → dispatch` flow. No architectural changes needed, just registration of the new agent.

## Celery Integration

### New Queue

A dedicated queue for intelligence tasks, separate from quality check execution:

```python
# Queue topology addition
"intelligence.default"  # Intelligence pipeline tasks (LLM-heavy, long-running)
```

Intelligence tasks are LLM-heavy and long-running (may take 1-5 minutes). Separating them from check queues prevents intelligence runs from starving time-sensitive check executions. Workers can be scaled independently.

### New Tasks

```python
@app.task(queue="intelligence.default")
def run_auto_scan(stave_id: str) -> None:
    """Triggered after stave creation + connection test.
    Runs pipeline stages 1→2→3→5.
    Acquires per-stave Redis lock before running."""

@app.task(queue="intelligence.default")
def run_daily_intelligence(stave_id: str) -> None:
    """Triggered by Celery Beat schedule.
    Runs full pipeline 1→2→3→4→5.
    Acquires per-stave Redis lock before running."""

@app.task(queue="intelligence.default")
def run_on_demand_analysis(stave_id: str, conversation_id: str | None = None) -> str:
    """Triggered by POST /insights/{stave_id}/analyze or chat.
    Runs pipeline stages 3→4→5.
    Returns the insight_report ID for the caller to fetch results."""

@app.task(queue="checks.default")
def prune_old_snapshots() -> None:
    """Weekly task. Aggregates snapshots older than 90 days into weekly
    summaries, then deletes the raw daily snapshots."""
```

### Celery Beat Schedule

```python
# Added to redbeat schedule for each active stave
{
    "name": f"intelligence-{stave_id}",
    "task": "run_daily_intelligence",
    "schedule": crontab(hour=6, minute=0),  # 6 AM daily
    "args": [stave_id],
}

# Global pruning task
{
    "name": "prune-old-snapshots",
    "task": "prune_old_snapshots",
    "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
}
```

The daily schedule is auto-created when a stave is created (alongside the auto-scan task) and removed when a stave is deleted or paused.

### Stave Lifecycle Hooks

- **Stave created + connection OK** → dispatch `run_auto_scan`, register daily Beat schedule
- **Stave paused (circuit breaker)** → remove daily Beat schedule
- **Stave unpaused** → re-register daily Beat schedule
- **Stave deleted** → remove daily Beat schedule, retain historical reports and profiles (soft delete pattern)

## API Endpoints

New feature slice: `features/insights/`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/insights/{stave_id}/profile` | Current data profile (domain, schema map) |
| GET | `/insights/{stave_id}/latest` | Most recent insight report |
| GET | `/insights/{stave_id}/history` | Historical reports (paginated) |
| GET | `/insights/{stave_id}/snapshots` | Baseline snapshot data (paginated, for detailed metric views) |
| GET | `/insights/{stave_id}/dashboard` | Aggregated dashboard view (scores, trends, active alerts) |
| POST | `/insights/{stave_id}/analyze` | Trigger on-demand analysis (async — returns task ID) |
| GET | `/insights/{stave_id}/analyze/{task_id}` | Poll on-demand analysis status |
| GET | `/insights/overview` | Cross-stave summary (all data sources at a glance) |
| GET | `/insights/{stave_id}/suggestions` | Pending AI suggestions (filterable by status) |
| POST | `/insights/{stave_id}/suggestions/{id}/accept` | Accept a suggestion |
| POST | `/insights/{stave_id}/suggestions/{id}/dismiss` | Dismiss a suggestion |

### Dashboard Endpoint Response

The `/dashboard` endpoint aggregates for frontend consumption:

```json
{
  "stave_id": "...",
  "health_score": 78,
  "health_trend": "improving",
  "dimensions": [
    {"name": "data_freshness", "label": "Data Freshness", "score": 92, "trend": "improving"},
    {"name": "completeness", "label": "Completeness", "score": 71, "trend": "stable"},
    {"name": "volume_health", "label": "Volume Health", "score": 85, "trend": "improving"},
    {"name": "business_kpis", "label": "Business KPIs", "score": 58, "trend": "declining"}
  ],
  "active_anomalies": [...],
  "pending_suggestions": [...],
  "ai_created_checks": [...],
  "last_analyzed_at": "2026-03-15T06:00:00Z"
}
```

## Cumulative Learning

The `data_profile` is the AI's long-term memory for a stave. It evolves:

| Timeframe | Knowledge Level |
|-----------|----------------|
| Day 1 | "E-commerce database, 12 tables, 3 fact tables" |
| Day 7 | "Orders peak on weekends, normal daily volume 150-200" |
| Day 30 | "Revenue correlates with marketing spend, churn rate 4.2%" |
| Day 90+ | "Q2 typically softer than Q1, holiday prep starts in October" |

The `learned_patterns` field in `data_profiles` accumulates observations over time. Each daily run can add new patterns or refine confidence in existing ones. The LLM sees this accumulated knowledge in its system prompt, so its analysis gets more contextual and specific over time.

Domain reclassification is versioned: if the LLM changes its classification (e.g., discovers the "e-commerce" DB also has significant IoT data), the `profile_version` increments and `previous_classification` preserves the old state. This enables detection and rollback of misclassifications.

## Output Rendering

One `InsightReport` serves two interfaces:

**Dashboard:** Renders structured fields — health_score as a big number, dimensions as score cards with trend arrows, anomalies as severity-coded cards, suggestions with accept/dismiss buttons, auto-created checks as a tag list.

**Chat:** Renders natural language fields — summary and key_findings woven into conversational responses. Can reference structured data when the user asks follow-up questions.

## Token Cost Management

- Schema sent as compressed summaries, not full DDL
- Sample data sent as statistical summaries (distributions, top values), not raw rows
- Historical comparison sent as deltas, not full snapshots
- Archetype context only included when matched with confidence > 50%
- Daily runs reuse the existing data_profile (no need to re-classify domain every day)

## File Structure

```
datametronome/podium/
├── archetypes/
│   ├── __init__.py           # Archetype loader + deterministic matcher
│   ├── ecommerce.yaml
│   ├── saas.yaml
│   ├── iot.yaml
│   ├── crm.yaml
│   └── generic.yaml
├── features/
│   └── insights/
│       ├── __init__.py
│       ├── router.py         # API endpoints
│       ├── schemas.py        # Request/response schemas
│       └── service.py        # Business logic
├── models/
│   ├── data_profile.py       # DataProfile model
│   ├── baseline_snapshot.py  # BaselineSnapshot model
│   ├── insight_report.py     # InsightReport model
│   ├── insight_suggestion.py # InsightSuggestion model
│   └── insight_created_check.py  # Join table model
├── services/
│   └── agents/
│       └── insight.py        # InsightAgent definition
└── worker/
    └── tasks/
        └── intelligence.py   # Celery tasks (auto_scan, daily_intelligence, on_demand, prune)
```

## Migration

One Alembic migration to create the five new tables: `data_profiles`, `baseline_snapshots`, `insight_reports`, `insight_suggestions`, `insight_created_checks`.

## Testing Strategy

- Unit tests for archetype loading, deterministic signature matching, and scoring
- Unit tests for InsightReport Pydantic model validation
- Unit tests for CheckSpec validation against check type schemas
- Unit tests for baseline snapshot comparison logic (delta calculation)
- Unit tests for snapshot pruning/aggregation logic
- Integration tests for the InsightAgent with mocked LLM responses
- Integration tests for LLM failure scenarios (malformed output, API down, token limits)
- Integration tests for Celery tasks (auto_scan, daily_intelligence, on_demand)
- Integration tests for concurrency lock (overlapping runs)
- API tests for all `/insights/` endpoints
- API tests for suggestion accept/dismiss lifecycle
- End-to-end test: create stave → auto-scan triggers → profile + report + suggestions created
