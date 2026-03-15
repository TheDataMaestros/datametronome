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


def _apply_schema(sql_template: str, schema_prefix: str, **kwargs: Any) -> str:
    """Replace {schema} and other placeholders in a SQL template."""
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
        for row in rows[: limit * 2]:
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
        safe_name = entity_name.replace("'", "''")
        sql = _apply_schema(sql_template, ctx.deps.schema_prefix, entity_name=safe_name)
        rows = await _execute_sql(ctx.deps.connector, sql)
        return json.dumps({"entity": entity_name, "breakdown": rows[:8]})

    return agent
