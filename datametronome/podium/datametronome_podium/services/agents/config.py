"""ConfigAgent: helps users set up data sources (staves) and quality checks (clefs)."""
from datametronome_podium.services.agent_tools import ALL_TOOLS
from pydantic_ai import Agent
from pydantic_ai.models import Model

_SYSTEM_PROMPT = """You are the DataMetronome configuration specialist.

You help users set up data sources (staves), configure quality checks (clefs), and
suggest appropriate checks for their tables.

Key concepts:
- Staves: Data sources (PostgreSQL, BigQuery, etc.) — where data lives
- Clefs: Quality check definitions — what to monitor

CRITICAL: When a user asks to list, explore, or count anything — call the appropriate
tool directly. Never ask for IDs when you can discover them with a list tool.

CONVERSATION MEMORY: When users refer to "this stave", "it", "that", check conversation
history. Never ask them to repeat info already provided.

Be concise and action-oriented."""


def build_config_agent(model: Model, *, user_profile: str | None = None) -> Agent:
    """Build the config agent with the given model."""
    prompt = _SYSTEM_PROMPT
    if user_profile:
        prompt = f"{_SYSTEM_PROMPT}\n\n{user_profile}"
    return Agent(
        model=model,
        system_prompt=prompt,
        tools=ALL_TOOLS,
    )
