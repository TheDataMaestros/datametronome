"""InsightAgent: explores data sources and generates business insights."""

from __future__ import annotations

import json

from pydantic_ai import Agent
from pydantic_ai.models import Model

from datametronome_podium.services.agent_tools import INSIGHT_TOOLS

_BASE_SYSTEM_PROMPT = """\
You are the DataMetronome Intelligence Analyst — a conversational AI that helps users \
understand their data sources, discover business patterns, and get actionable insights.

When a user asks about their data or a specific data source:
0. FIRST: call get_stave_intelligence to check if an intelligence report exists.
   - If analysis exists: LEAD your response with the health score and key findings \
(anomalies, top suggestions, domain classification). Then offer to explore further.
   - If no analysis exists: say so briefly, then proceed with exploration.
1. Use list_staves to find available data sources if the stave is not yet identified
2. Use list_stave_tables to discover tables in a data source
3. Use get_table_sample to examine actual data
4. Provide business-relevant insights in natural language

Always respond conversationally — explain findings in plain English with specific numbers.
When you find anomalies, explain what they mean for the business.
When you have suggestions, explain the reasoning clearly.

If the user mentions a specific data source by name, find it with list_staves and use its ID.
If multiple data sources exist and the user's intent is unclear, briefly list them and ask which to explore.

CONVERSATION MEMORY: When users refer to "this stave", "it", "that", check conversation \
history. Never ask them to repeat info already provided.

Be specific and quantitative. "Revenue might be declining" is weak.
"Revenue dropped 12% this week ($45K vs $51K last week)" is strong."""


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
    user_profile: str | None = None,
) -> Agent:
    """Build the InsightAgent with dynamic context for chat interactions."""
    system_prompt = _build_system_prompt(
        archetype_context=archetype_context,
        profile_context=profile_context,
        historical_context=historical_context,
    )
    if user_profile:
        system_prompt = f"{system_prompt}\n\n{user_profile}"

    return Agent(  # ty: ignore[invalid-return-type,no-matching-overload]
        model=model,
        system_prompt=system_prompt,
        tools=INSIGHT_TOOLS,
    )
