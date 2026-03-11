"""
Phase 2: Specialized sub-agents with tailored tools and prompts.

Maps intent to agent config (tool subset + system prompt).

All agents share the full tool set — the LLM decides which tools to call.
Sub-agent specialization affects only the system prompt framing (tone, focus),
not tool access, so the agent works regardless of language or phrasing.
"""

AGENT_CONFIG = "config"
AGENT_INVESTIGATION = "investigation"
AGENT_REPORT = "report"

# All available tools — shared across every agent type.
# Restricting tools per agent was brittle (language-dependent intent routing
# could route to an agent missing a needed tool). The LLM is better at
# deciding which tool to call than a regex classifier.
ALL_TOOLS = [
    "list_staves",
    "get_stave",
    "create_stave",
    "list_stave_tables",
    "get_table_sample",
    "suggest_quality_checks",
    "list_clefs",
    "get_clef",
    "list_checks",
    "get_summary_report",
    "get_quality_report",
]

# Convenience aliases (used by orchestrator — keep names for compatibility)
CONFIG_TOOLS = ALL_TOOLS
INVESTIGATION_TOOLS = ALL_TOOLS
REPORT_TOOLS = ALL_TOOLS

_SHARED_CONTEXT = """CONVERSATION CONTEXT: When users refer to "this stave", "it", "that", check conversation history. Never ask them to repeat info already provided.\n\n"""

_TOOL_HINT = """
Available tools:
- list_staves(active_only=False): list data sources; pass active_only=True to filter active ones
- get_stave(stave_id): details for a specific stave
- create_stave(...): create a new data source
- list_stave_tables(stave_id): list tables in a stave
- get_table_sample(stave_id, table_name): sample rows from a table
- suggest_quality_checks(stave_id, table_name): suggest checks based on schema/data
- list_clefs(active_only=False, stave_id=None): list quality checks
- get_clef(clef_id): details for a specific clef
- list_checks(...): list check execution results
- get_summary_report(): system-wide status
- get_quality_report(): quality metrics over time

When a user asks to list, explore, or count anything — call the appropriate tool directly. Never ask for IDs when you can discover them with a list tool.\n"""

# System prompts per agent — framing only, tools are identical
CONFIG_INSTRUCTION = _SHARED_CONTEXT + """You are the DataMetronome configuration specialist. You help users set up data sources (staves), quality checks (clefs), and suggest appropriate checks for their tables.

Key concepts:
- Staves: Data sources (PostgreSQL, BigQuery, etc.) — where data lives
- Clefs: Quality check definitions — what to monitor
""" + _TOOL_HINT + """Be concise and action-oriented."""

INVESTIGATION_INSTRUCTION = _SHARED_CONTEXT + """You are the DataMetronome investigation specialist. You help users understand why checks failed, explore data, analyze anomalies, and diagnose issues.

Key concepts:
- Checks: Execution results of quality checks (passed/failed)
- get_quality_report: Overview of quality metrics
- get_table_sample: Inspect actual data for debugging
""" + _TOOL_HINT + """Be analytical and thorough."""

REPORT_INSTRUCTION = _SHARED_CONTEXT + """You are the DataMetronome reporting specialist. You provide overviews, status summaries, and quality reports.

Key concepts:
- get_summary_report: System-wide status
- get_quality_report: Quality metrics over time
- list_staves / list_clefs: Enumerate data sources and checks
""" + _TOOL_HINT + """Be clear and summarize key metrics."""


def resolve_agent_for_intent(intent: str) -> tuple[str, list[str], str]:
    """Return (agent_type, tool_names, instruction) for the given intent."""
    if intent == "config":
        return AGENT_CONFIG, ALL_TOOLS, CONFIG_INSTRUCTION
    if intent == "investigation":
        return AGENT_INVESTIGATION, ALL_TOOLS, INVESTIGATION_INSTRUCTION
    # report, quick, exploration — all get full tools
    return AGENT_REPORT, ALL_TOOLS, REPORT_INSTRUCTION
