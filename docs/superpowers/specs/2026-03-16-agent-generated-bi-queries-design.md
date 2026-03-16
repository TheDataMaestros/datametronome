# Agent-Generated BI Query Plans

**Date:** 2026-03-16
**Branch:** feat/data-intelligence
**Status:** Draft

## Problem

The `ecommerce.yaml` archetype (and all future archetypes) currently embeds hardcoded SQL in `kpi_queries` and `performer_dimensions`. These SQL templates encode assumptions about specific column names (`order_purchase_timestamp`, `payment_value`, `product_id`) that are true for the olist dataset but false for any other ecommerce database with different naming conventions.

This breaks the fundamental promise of domain archetypes: that an archetype represents generic domain knowledge applicable to any database in that domain.

## Solution

Remove all SQL from archetypes. Replace with pure business semantics. Let the BusinessIntelligenceAgent discover the actual schema, reason about column roles, generate SQL tailored to that specific database, and cache the result for future runs.

---

## 1. Archetype YAML: Pure Business Semantics

### What Changes

`kpi_queries` (SQL templates) and the SQL inside `performer_dimensions` are removed entirely. The existing `metrics[].query_hint` fields (e.g., `"AVG(total) FROM orders"`) are also removed — they too contain schema-specific SQL fragments. The `metrics` list retains only `name` and `typical_range`.

Removed keys are replaced by:

- `kpi_definitions`: a list of KPIs with a name and plain-English description of what business question they answer
- `performer_dimensions`: entity name + plain-English description of what to measure, no SQL

### Example (ecommerce)

```yaml
metrics:
  - name: average_order_value
    typical_range: [20, 200]
  - name: cart_abandonment_rate
    typical_range: [0.60, 0.80]

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

### Principle

The archetype is now genuinely portable. Two ecommerce databases with entirely different column names — `total_amount` vs `price + freight_value`, `created_at` vs `order_purchase_timestamp` — both match the same archetype. The agent figures out the rest.

---

## 2. New Table: `stave_query_plans`

Stores the agent-generated SQL per stave, with a schema fingerprint used to detect when regeneration is needed. Multiple rows per stave are allowed (audit history); only one row per stave may be valid at a time (`invalidated_at IS NULL`), enforced by a partial unique index.

```
stave_query_plans
─────────────────
id                  UUID        PK
stave_id            UUID        FK → staves
tenant_id           UUID
schema_fingerprint  TEXT        SHA-256 of sorted table.column pairs from Stage 1
kpi_queries         JSONB       { kpi_name: sql_string, ... }
performer_queries   JSONB       { entity: { rank_query: sql, drill_query: sql }, ... }
generated_by_model  TEXT
generated_at        TIMESTAMPTZ
invalidated_at      TIMESTAMPTZ  NULL = currently valid
```

**Partial unique index:** `UNIQUE (stave_id) WHERE invalidated_at IS NULL` — ensures at most one valid plan per stave while allowing historical rows for audit.

### Lifecycle

- Created after the first successful BI agent run on a stave
- Each Stage 1 discovery computes a new fingerprint; if it differs from the valid plan's `schema_fingerprint`, `invalidated_at` is set on the current row
- After regeneration a new row is written; the invalidated row is retained for audit
- Rows with `invalidated_at` older than 90 days are pruned by the `prune_old_snapshots` Celery task, which is extended to also delete old `stave_query_plans` rows (in addition to its existing `baseline_snapshots` aggregation logic)

---

## 3. BI Agent: Three-Phase Loop

The BusinessIntelligenceAgent is restructured into three explicit phases.

### Phase 1 — Schema Overview *(skipped if valid plan exists)*

Stage 1 (discovery) already collects the full schema and samples. The BI agent receives the Stage 1 `discovery` dict directly — **no new database connection is opened in Phase 1**. The agent reasons over the already-collected schema data:

- What tables exist and their likely roles (fact, dimension, lookup)
- Which columns represent monetary values, timestamps, identifiers, status flags
- How tables relate to each other, inferred from column name patterns and sample values
- Which columns have useful cardinality (non-null, non-zero, meaningful distribution)

The agent produces a schema interpretation — a structured mapping of tables to their inferred roles and columns to their semantic roles (e.g., `order_purchase_timestamp → transaction_time`, `price → revenue_amount`). This interpretation is stored in `DataProfile.schema_interpretation` (new JSONB field) for observability: it lets operators understand why the agent generated a particular query and diagnose mistakes without re-running the pipeline.

### Phase 2 — Query Generation + Validation *(skipped if valid plan exists)*

Armed with its schema understanding, the agent generates SQL for each KPI and performer dimension defined in the archetype. A single read-only connection to the user's database is opened before Phase 2 begins and shared through Phase 3 if it runs. It is closed in a single `finally` block wrapping both phases — so the connection is always released whether Phase 2 aborts midway, Phase 3 is skipped, or both phases complete normally.

For each query:

1. Generate SQL using actual column names discovered in Phase 1
2. Execute via `run_raw_query` tool (see below)
3. Query returns without error → keep it, regardless of whether the value is 0 or NULL (0 is a valid business result; NULL may indicate an aggregation over an empty filter and is also accepted)
4. Query raises a database error → revise and retry (max 2 retries per query)
5. Store all valid queries in `stave_query_plans`

**`run_raw_query` tool:** New agent tool added to `business_intelligence.py`. Signature: `run_raw_query(ctx, sql: str) -> str`. Enforces a `LIMIT 1000` cap appended to SELECT statements before execution to prevent full-table scans. Returns results as JSON. Raises on any database error so the agent can retry with revised SQL.

**Abort threshold:** If fewer than half of all generated queries (KPI queries + performer rank queries + performer drill queries combined) succeed after retries, abort plan creation. No `stave_query_plans` row is written. Phase 3 is also skipped for this run. The BI track is retried at the next scheduled execution.

Individual query failures below that threshold are included in the business report as explicitly skipped KPIs/dimensions — surfaced to the user with the KPI name and the reason (e.g., "could not generate valid SQL after 2 retries"). They do not abort the plan.

### Phase 3 — Execution + Analysis *(skipped only if no valid plan exists)*

If a valid `stave_query_plans` row exists (either loaded from cache or just written by Phase 2):

1. Execute all KPI queries → collect raw values
2. Execute performer rank queries → identify top and bottom entities
3. Drill down on notable performers → collect weekly time-series
4. Reason over all results in business context: interpret numbers, identify anomalies, spot opportunities and risks, produce narrative
5. Output `LLMBusinessReport` — health score, executive summary, KPIs with commentary, performers, trends, opportunities, risks

If no valid plan exists (Phase 2 aborted), Phase 3 is skipped and no `BusinessReport` is created for this run.

Phase 3 is an LLM reasoning step, not just data retrieval. The agent sees all results together and draws conclusions ("revenue up 12% but AOV down; top category shifted from electronics to furniture this week").

---

## 4. Schema Fingerprinting + Invalidation

### Fingerprint Computation

Computed at the end of Stage 1 from `discovery["schema"]` — a dict of `table_name → {column_name → column_metadata}`. The fingerprint iterates column names (dict keys), not column metadata:

```python
fingerprint = sha256(
    "\n".join(
        sorted(
            f"{table}.{col}"
            for table, col_meta in discovery["schema"].items()
            for col in col_meta.keys()
        )
    ).encode()
).hexdigest()
```

This fingerprint is passed from `service.py` into the BI agent along with the full `discovery` dict.

### Invalidation Triggers

| Trigger | Mechanism |
|---|---|
| Schema change | Stage 1 fingerprint differs from valid plan's `schema_fingerprint` → `invalidated_at` set on current row |
| Domain reclassification | Stage 2 assigns a different `domain_type` than the stored profile → plan invalidated; regeneration uses the new archetype. Note: reclassification occurs in `persist_results` (Stage 5), so the invalidation takes effect on the **next** pipeline run, not the current one. The current run uses the archetype matched in Stage 2. |
| Manual | User requests regeneration via API → `invalidated_at` set on current row |

---

## 5. Error Handling

| Failure | Behaviour |
|---|---|
| Phase 1 fails (schema reasoning error) | Skip BI track entirely (Phases 2 and 3), log warning, Track 1 continues normally |
| Phase 2: single query unvalidatable after 2 retries | Skip that KPI/dimension, continue with remaining; note skipped in report |
| Phase 2: fewer than half of all queries succeed | Abort plan generation, no row written, Phase 3 skipped; retry next scheduled run |
| Phase 3 reasoning fails | Save raw query results as-is, skip narrative generation |
| Stored SQL fails on execution (schema drift not caught by fingerprint) | Immediately set `invalidated_at` on plan, Phase 3 skipped for this run; regeneration at next run |

---

## 6. Impact on Existing Code

| Component | Change |
|---|---|
| `archetypes/ecommerce.yaml` | Remove `kpi_queries`, remove SQL from `performer_dimensions`, remove `metrics[].query_hint`, add `kpi_definitions` |
| All other archetype YAMLs | Same transformation |
| `archetypes/__init__.py` | No change to loader; archetype dict just has different keys |
| `services/agents/business_intelligence.py` | Restructure into three phases; Phase 1 reads from `discovery` dict (no new connection); Phase 2+3 share one read-only connection (opened/closed by the agent runner); add `run_raw_query` tool; add plan load/store/invalidate logic |
| `features/insights/service.py` | Compute fingerprint from `discovery["schema"]` after Stage 1; pass `discovery` + fingerprint into BI agent; handle plan invalidation; persist `schema_interpretation` to `DataProfile` |
| `tasks/intelligence_tasks.py` | Extend `prune_old_snapshots` to also delete `stave_query_plans` rows with `invalidated_at` older than 90 days |
| DB migration | New `stave_query_plans` table with partial unique index; add `schema_interpretation` JSONB column to `data_profiles` |
| `features/insights/repo.py` | Add `StaveQueryPlan` model + CRUD (`get_valid_plan`, `create_plan`, `invalidate_plan`) |

### What Does NOT Change

- Stage 1–3 of the pipeline (discovery, classification, baseline) — unchanged
- Track 1 (InsightAgent, data quality analysis) — unchanged
- `LLMBusinessReport` output model — unchanged
- All API endpoints — unchanged
- Frontend — unchanged

---

## 7. Decisions

| Question | Decision |
|---|---|
| Skipped KPIs surfaced or silently omitted? | Surfaced — included in the business report with KPI name and reason for failure |
| Schema interpretation stored or internal? | Stored in `DataProfile.schema_interpretation` (JSONB) for observability |
