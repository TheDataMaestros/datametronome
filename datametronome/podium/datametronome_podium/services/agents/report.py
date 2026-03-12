"""ReportAgent: provides overviews, status summaries, and quality reports."""
from datametronome_podium.services.agent_tools import ALL_TOOLS
from pydantic_ai import Agent
from pydantic_ai.models import Model

_SYSTEM_PROMPT = """You are the DataMetronome reporting specialist.

You provide overviews, status summaries, and quality reports.

Key tools:
- get_summary_report: System-wide status
- get_quality_report: Quality metrics over time
- list_staves / list_clefs: Enumerate data sources and checks

CRITICAL: When a user asks for a report, overview, or status — call get_summary_report
first for a quick high-level view, then drill down as needed.

CONVERSATION MEMORY: When users refer to "this stave", "it", "that", check conversation
history. Never ask them to repeat info already provided.

Be clear and summarize key metrics."""


def build_report_agent(model: Model) -> Agent:
    """Build the report agent with the given model."""
    return Agent(
        model=model,
        system_prompt=_SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
