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

_BASE_SYSTEM_PROMPT = """\
You are the DataMetronome Intelligence Analyst.

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
        metrics_json = json.dumps(archetype_context.get("metrics", []), indent=2)
        patterns = ", ".join(archetype_context.get("patterns", []))
        parts.append(
            f"DOMAIN ARCHETYPE: {archetype_context.get('name', 'unknown')}\n"
            f'This data source matches the "{archetype_context.get("name")}" archetype.\n'
            f"Typical metrics for this domain:\n{metrics_json}\n"
            f"Known patterns: {patterns}\n"
            "Use this domain knowledge to provide more specific insights from day one."
        )

    if profile_context:
        learned = json.dumps(profile_context.get("learned_patterns", {}), indent=2)
        parts.append(
            "ACCUMULATED KNOWLEDGE about this data source:\n"
            f"Domain: {profile_context.get('domain_type', 'unknown')}\n"
            f"Learned patterns: {learned}\n"
            "Use this accumulated knowledge to provide contextual, comparative insights."
        )

    if historical_context:
        parts.append(
            "HISTORICAL COMPARISON DATA:\n"
            f"{historical_context}\n"
            "Compare current metrics against these historical baselines."
        )

    return "\n\n".join(parts)


def build_insight_agent(
    model: Model,
    *,
    archetype_context: dict | None = None,
    profile_context: dict | None = None,
    historical_context: str | None = None,
) -> Agent:
    """Build the InsightAgent with dynamic context for chat interactions."""
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
