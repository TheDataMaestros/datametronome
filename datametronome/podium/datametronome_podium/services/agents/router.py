"""
RouterAgent: classifies user intent into a RoutingDecision.

Uses a small/fast model. Returns structured Pydantic output — no regex.
"""
import logging
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model

logger = logging.getLogger(__name__)

VALID_INTENTS = Literal["quick", "config", "investigation", "report", "exploration", "insight", "memory"]
VALID_MODES = Literal["single", "chain", "parallel"]
VALID_AGENTS = Literal["config", "investigation", "report", "insight"]


class RoutingDecision(BaseModel):
    """Structured routing output from the RouterAgent."""

    intent: VALID_INTENTS
    mode: VALID_MODES
    agents: list[VALID_AGENTS]
    reasoning: str  # short explanation for tracing/debugging


_ROUTER_SYSTEM_PROMPT = """You are a routing assistant for DataMetronome, a data quality monitoring platform.

Given a user message, output a routing decision with these fields:
- intent: one of quick | config | investigation | report | exploration | insight | memory
- mode: one of single | chain | parallel
- agents: list of agents to run — one or more of: config | investigation | report | insight
- reasoning: one sentence explaining your decision

Intent definitions:
- quick: greetings, status checks, simple counts, "how many staves do I have?"
- config: creating/configuring data sources (staves), setting up quality checks (clefs)
- investigation: diagnosing failures, root cause analysis, "why did this check fail?"
- report: summaries, dashboards, quality reports, "give me an overview"
- exploration: browsing tables, sampling data, "show me the tables in stave X"
- insight: exploring data, understanding business patterns, getting insights, "what's happening with my data?"
- memory: user asks about what you know about them, what was investigated, their profile, or past findings

Mode + agents rules:
- single: one agent handles the whole request → agents = [best_agent]
- chain: investigation followed by recommendations → agents = ["investigation", "config"]
  Use when: user asks to diagnose AND fix/suggest (e.g. "why did X fail and how to fix it")
- parallel: two agents run concurrently → agents = ["report", "config"]
  Use when: user asks for an overview AND suggestions at the same time

Default (when unsure): mode=single, agents=["report"]

Respond ONLY with the JSON object. No prose."""


def build_router_agent(model: Model) -> Agent[None, RoutingDecision]:
    """Build a RouterAgent with the given model."""
    agent: Agent[None, RoutingDecision] = Agent(  # ty: ignore[assignment]  # ty:ignore[ignore-comment-unknown-rule]
        model=model,
        output_type=RoutingDecision,
        system_prompt=_ROUTER_SYSTEM_PROMPT,
        retries=3,
    )  # ty:ignore[invalid-assignment]
    return agent
