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

`kpi_queries` (SQL templates) and the SQL inside `performer_dimensions` are removed entirely.

They are replaced by:

- `kpi_definitions`: a list of KPIs with a name and plain-English description of what business question they answer
- `performer_dimensions`: entity name + plain-English description of what to measure, no SQL

### Example (ecommerce)

```yaml
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

Stores the agent-generated SQL per stave, with a schema fingerprint used to detect when regeneration is needed.

```
stave_query_plans
─────────────────
id                  UUID        PK
stave_id            UUID        FK → staves (unique)
tenant_id           UUID
schema_fingerprint  TEXT        SHA-256 of sorted table.column pairs from Stage 1
kpi_queries         JSONB       { kpi_name: sql_string, ... }
performer_queries   JSONB       { entity: { rank_query: sql, drill_query: sql }, ... }
generated_by_model  TEXT
generated_at        TIMESTAMPTZ
invalidated_at      TIMESTAMPTZ  NULL = currently valid
```

### Lifecycle

- Created after the first successful BI agent run on a stave
- Each Stage 1 discovery computes a new fingerprint; if it differs from `schema_fingerprint`, `invalidated_at` is set
- After regeneration a new row is written; the old row is retained for audit
- Old rows beyond 90 days are pruned by the existing snapshot pruning task

---

## 3. BI Agent: Three-Phase Loop

The BusinessIntelligenceAgent is restructured into three explicit phases.

### Phase 1 — Schema Overview *(skipped if valid plan exists)*

The agent calls existing schema tools (`list_stave_tables`, `get_table_schema`, `get_table_sample`) in a deliberate first pass. The goal is understanding, not querying:

- What tables exist and their likely roles (fact, dimension, lookup)
- Which columns represent monetary values, timestamps, identifiers, status flags
- How tables relate to each other, inferred from column name patterns and sample values
- Which columns have useful cardinality (non-null, non-zero, meaningful distribution)

The agent produces an internal schema interpretation before generating any SQL.

### Phase 2 — Query Generation + Validation *(skipped if valid plan exists)*

Armed with its schema understanding, the agent generates SQL for each KPI and performer dimension defined in the archetype. For each query:

1. Generate SQL using actual column names discovered in Phase 1
2. Execute via `run_raw_query` tool
3. Result is sensible (non-null, non-error) → keep it
4. Result errors or returns null/zero → revise and retry (max 2 retries per query)
5. Store all valid queries in `stave_query_plans`

If fewer than half the queries succeed after retries, abort plan creation entirely. No `stave_query_plans` row is written. The BI track is skipped for this run and retried at the next scheduled execution.

### Phase 3 — Execution + Analysis *(always runs)*

Regardless of whether Phases 1 and 2 ran or were skipped:

1. Execute all KPI queries from `stave_query_plans` → collect raw values
2. Execute performer rank queries → identify top and bottom entities
3. Drill down on notable performers → collect weekly time-series
4. Reason over all results in business context: interpret numbers, identify anomalies, spot opportunities and risks, produce narrative
5. Output `LLMBusinessReport` — health score, executive summary, KPIs with commentary, performers, trends, opportunities, risks

Phase 3 is an LLM reasoning step, not just data retrieval. The agent sees all results together and draws conclusions ("revenue up 12% but AOV down; top category shifted from electronics to furniture this week").

---

## 4. Schema Fingerprinting + Invalidation

### Fingerprint Computation

Computed at the end of Stage 1 from the full schema map:

```python
fingerprint = sha256(
    "\n".join(sorted(f"{table}.{col}" for table, cols in schema_map.items() for col in cols))
)
```

### Invalidation Triggers

| Trigger | Mechanism |
|---|---|
| Schema change | Stage 1 fingerprint differs from stored → sets `invalidated_at` |
| Domain reclassification | Stage 2 assigns a different `domain_type` → always regenerates (different archetype = different KPI semantics) |
| Manual | User requests regeneration via API → sets `invalidated_at` |

---

## 5. Error Handling

| Failure | Behaviour |
|---|---|
| Phase 1 fails (schema tools error) | Skip BI track entirely, log warning, Track 1 continues normally |
| Phase 2: query unvalidatable after 2 retries | Skip that KPI/dimension, continue with remaining, note skipped in report |
| Phase 2: fewer than half queries succeed | Abort plan generation, no `stave_query_plans` row created, retry next scheduled run |
| Phase 3 reasoning fails | Save raw query results as-is, skip narrative generation |
| Stored SQL fails on execution (schema drift not caught by fingerprint) | Immediately invalidate plan, flag for regeneration at next run |

---

## 6. Impact on Existing Code

| Component | Change |
|---|---|
| `archetypes/ecommerce.yaml` | Remove `kpi_queries`, remove SQL from `performer_dimensions`, add `kpi_definitions` |
| All other archetype YAMLs | Same transformation |
| `archetypes/__init__.py` | No change to loader; archetype dict just has different keys |
| `services/agents/business_intelligence.py` | Restructure into three phases; add schema overview tools; add plan load/store logic |
| `features/insights/service.py` | Pass schema fingerprint to BI agent; handle plan invalidation |
| DB migration | New `stave_query_plans` table |
| `features/insights/repo.py` | Add `StaveQueryPlan` CRUD |

### What Does NOT Change

- Stage 1–3 of the pipeline (discovery, classification, baseline) — unchanged
- Track 1 (InsightAgent, data quality analysis) — unchanged
- `LLMBusinessReport` output model — unchanged
- All API endpoints — unchanged
- Frontend — unchanged

---

## 7. Open Questions

- Should skipped KPIs (failed validation) be surfaced to the user in the business report or silently omitted?
- Should the agent's schema interpretation from Phase 1 be stored (e.g., in `DataProfile`) for observability, or kept internal to the agent run?
