"""
Phase 3: Orchestrator - selects and coordinates multiple sub-agents.

Patterns: single-agent, chain (A→B), parallel (A+B).
"""

import logging
import re

from datametronome_podium.services.sub_agents import (
    AGENT_CONFIG,
    AGENT_INVESTIGATION,
    AGENT_REPORT,
    CONFIG_INSTRUCTION,
    CONFIG_TOOLS,
    INVESTIGATION_INSTRUCTION,
    INVESTIGATION_TOOLS,
    REPORT_INSTRUCTION,
    REPORT_TOOLS,
    resolve_agent_for_intent,
)

logger = logging.getLogger(__name__)

MODE_SINGLE = "single"
MODE_CHAIN = "chain"
MODE_PARALLEL = "parallel"

# Agent config by type: (tool_names, instruction)
AGENT_CONFIG_BY_TYPE = {
    AGENT_CONFIG: (CONFIG_TOOLS, CONFIG_INSTRUCTION),
    AGENT_INVESTIGATION: (INVESTIGATION_TOOLS, INVESTIGATION_INSTRUCTION),
    AGENT_REPORT: (REPORT_TOOLS, REPORT_INSTRUCTION),
}


def plan_orchestration(intent: str, message: str) -> tuple[str, list[str]]:
    """Determine orchestration mode and agent sequence.

    Returns:
        (mode, agent_types) e.g. ("single", ["report"]) or ("chain", ["investigation", "config"])
        or ("parallel", ["report", "config"])
    """
    text = (message or "").strip().lower()

    # Chain: investigation + "fix/suggest/how to" → Investigation then Config
    fix_patterns = [
        r"\b(?:how\s+to\s+)?fix\b",
        r"\bsuggest\s+(?:how\s+)?(?:to\s+)?\b",
        r"\bhow\s+do\s+i\s+(?:fix|remedy|resolve)\b",
        r"\b(?:what|which)\s+checks?\s+to\s+add\b",
        r"\brecommend\s+(?:quality\s+)?checks?\b",
    ]
    if intent == "investigation" and any(re.search(p, text) for p in fix_patterns):
        logger.info("Orchestrator: chain investigation→config (user asked for fixes/suggestions)")
        return MODE_CHAIN, [AGENT_INVESTIGATION, AGENT_CONFIG]

    # Parallel: user asks for overview + suggestions (Report + Config)
    parallel_patterns = [
        r"\b(?:overview|status|summary)\b.*\b(?:and\s+)?(?:suggest|recommend|what\s+to)\b",
        r"\b(?:suggest|recommend)\b.*\b(?:and\s+)?(?:overview|status|summary)\b",
        r"\b(?:both|everything)\b.*\b(?:report|overview|status)\b",
    ]
    if any(re.search(p, text) for p in parallel_patterns):
        logger.info("Orchestrator: parallel report+config (user asked for overview and suggestions)")
        return MODE_PARALLEL, [AGENT_REPORT, AGENT_CONFIG]

    # Default: single agent (resolve from intent)
    agent_type, _, _ = resolve_agent_for_intent(intent)
    return MODE_SINGLE, [agent_type]


def get_agent_config(agent_type: str) -> tuple[list[str], str]:
    """Return (tool_names, instruction) for an agent type."""
    return AGENT_CONFIG_BY_TYPE.get(
        agent_type, (INVESTIGATION_TOOLS, INVESTIGATION_INSTRUCTION)
    )
