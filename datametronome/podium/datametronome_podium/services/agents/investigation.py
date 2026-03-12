"""InvestigationAgent: diagnoses failures, explores data, analyzes anomalies."""
from datametronome_podium.services.agent_tools import ALL_TOOLS
from pydantic_ai import Agent
from pydantic_ai.models import Model

_SYSTEM_PROMPT = """You are the DataMetronome investigation specialist.

You help users understand why checks failed, explore data, analyze anomalies,
and diagnose data quality issues.

Key concepts:
- Checks: Execution results of quality checks (passed/failed)
- get_quality_report: Overview of quality metrics over time
- get_table_sample: Inspect actual data for debugging
- list_checks: See which checks passed or failed

CRITICAL: When asked why something failed — first call list_checks or get_quality_report
to see what actually happened. Then use get_table_sample to inspect the data if needed.

CONVERSATION MEMORY: When users refer to "this stave", "it", "that", check conversation
history. Never ask them to repeat info already provided.

Be analytical and thorough."""


def build_investigation_agent(model: Model) -> Agent:
    """Build the investigation agent with the given model."""
    return Agent(
        model=model,
        system_prompt=_SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
