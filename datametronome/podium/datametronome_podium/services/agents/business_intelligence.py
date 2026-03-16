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
    """Execute SQL and return rows as dicts. Propagates exceptions."""
    result = await connector.query({"sql": sql})
    if isinstance(result, list):
        return [dict(row) if not isinstance(row, dict) else row for row in result]
    return []


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
        f"Schema (table -> columns): {json.dumps(schema_summary, indent=2)}\n"
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
        system_prompt=_PHASE2_SYSTEM_PROMPT.format(
            schema_prefix=schema_prefix or "(no prefix)",
        ),
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
                "Phase 2 abort: only %d/%d queries succeeded",
                succeeded,
                total_expected,
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
            return json.dumps(
                {"error": f"Unknown KPI: {kpi_name}. Available: {available}"},
            )
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
        return json.dumps(
            {"dimensions": list(ctx.deps.performer_queries.keys())},
        )

    @agent.tool
    async def query_top_performers(
        ctx: RunContext[Phase3Deps], entity_type: str, limit: int = 5
    ) -> str:
        """Execute the rank query for an entity type. Returns top N performers."""
        dim = ctx.deps.performer_queries.get(entity_type, {})
        sql = dim.get("rank_query", "")
        if not sql:
            return json.dumps(
                {"error": f"No rank_query for entity: {entity_type}"},
            )
        # Fetch 2x the requested limit so the agent can see both top and bottom performers
        # without a second query (the agent slices the result itself).
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
                "vs_average_pct": round(
                    ((float(r.get("value", 0)) - avg) / avg * 100) if avg else 0,
                    1,
                ),
            }
            for r in rows[: limit * 2]
        ]
        return json.dumps(
            {
                "entity_type": entity_type,
                "average": round(avg, 2),
                "performers": performers,
            },
        )

    @agent.tool
    async def drill_down(
        ctx: RunContext[Phase3Deps], entity_type: str, entity_name: str
    ) -> str:
        """Execute the drill query for a specific entity to get time-series breakdown."""
        dim = ctx.deps.performer_queries.get(entity_type, {})
        sql = dim.get("drill_query", "")
        if not sql:
            return json.dumps(
                {"note": "No drill_query for this entity type"},
            )
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
