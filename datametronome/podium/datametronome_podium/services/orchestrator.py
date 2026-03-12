"""
Orchestrator: routes user messages to the right sub-agents via structured LLM routing.

Flow:
    1. RouterAgent classifies message -> RoutingDecision
    2. Orchestrator dispatches based on decision.mode:
       - single: one agent, full conversation history
       - chain: agent A -> agent B (B receives A's output + original message)
       - parallel: agent A + agent B concurrently, results combined
"""
import asyncio
import logging
from typing import Any

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from datametronome_podium.services.agents.router import RoutingDecision, build_router_agent
from datametronome_podium.services.agents.config import build_config_agent
from datametronome_podium.services.agents.investigation import build_investigation_agent
from datametronome_podium.services.agents.report import build_report_agent
from datametronome_podium.services.agent_factory import (
    build_model_from_settings,
    build_router_model_from_settings,
)

logger = logging.getLogger(__name__)

# --- Lazy agent factories (allow monkeypatching in tests) ---


def _get_router_agent():
    return build_router_agent(build_router_model_from_settings())


def _get_config_agent():
    return build_config_agent(build_model_from_settings())


def _get_investigation_agent():
    return build_investigation_agent(build_model_from_settings())


def _get_report_agent():
    return build_report_agent(build_model_from_settings())


def _get_agent_builder(agent_type: str):
    """Resolve agent builder by name — indirects through module globals so patches work."""
    builders = {
        "config": _get_config_agent,
        "investigation": _get_investigation_agent,
        "report": _get_report_agent,
    }
    return builders.get(agent_type, _get_report_agent)


def convert_history_to_messages(history: list[dict]) -> list[ModelMessage]:
    """Convert DB message dicts (role/content) to Pydantic AI ModelMessage list.

    System messages are skipped — system prompts are handled by agent configuration.
    Only user and assistant messages are converted.
    """
    messages: list[ModelMessage] = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


async def run_chat(
    message: str,
    history: list[dict],
    *,
    router_history_window: int = 6,
) -> dict[str, Any]:
    """Run the full chat pipeline: route -> dispatch -> respond.

    Args:
        message: Current user message
        history: Full conversation history as list of {role, content} dicts
        router_history_window: How many recent messages to send to the router for context

    Returns:
        dict with keys: message (str), intent (str), mode (str),
                        agents (list[str]), model (str)
    """
    all_history = convert_history_to_messages(history)
    router_history = all_history[-router_history_window:] if all_history else []

    router = _get_router_agent()
    routing_result = await router.run(message, message_history=router_history)
    decision: RoutingDecision = routing_result.output  # .output not .data in 1.67.0

    logger.info(
        "Router decision: intent=%s mode=%s agents=%s reasoning=%r",
        decision.intent, decision.mode, decision.agents, decision.reasoning,
    )

    if decision.mode == "parallel" and len(decision.agents) >= 2:
        response_message = await _run_parallel(message, decision, all_history)
    elif decision.mode == "chain" and len(decision.agents) >= 2:
        response_message = await _run_chain(message, decision, all_history)
    else:
        response_message = await _run_single(message, decision, all_history)

    return {
        "message": response_message,
        "intent": decision.intent,
        "mode": decision.mode,
        "agents": decision.agents,
        "model": "pydantic-ai",
    }


async def _run_single(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
) -> str:
    agent_type = decision.agents[0] if decision.agents else "report"
    agent = _get_agent_builder(agent_type)()
    result = await agent.run(message, message_history=history)
    return str(result.output)


async def _run_chain(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
) -> str:
    """Run agents in sequence. Each agent after the first receives the previous output."""
    previous_output = ""
    last_result = ""

    for i, agent_type in enumerate(decision.agents):
        agent = _get_agent_builder(agent_type)()

        if i == 0:
            msg_to_send = message
        else:
            msg_to_send = (
                f"INVESTIGATION FINDINGS:\n{previous_output}\n\n"
                f"USER'S REQUEST: {message}\n\n"
                "Using the findings above, address the user's request "
                "(suggest fixes, recommend checks, or propose remedial actions)."
            )

        result = await agent.run(msg_to_send, message_history=history)
        previous_output = str(result.output)
        last_result = previous_output

    return last_result


async def _run_parallel(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
) -> str:
    """Run agents concurrently, combine their outputs."""
    async def run_agent(agent_type: str) -> tuple[str, str]:
        agent = _get_agent_builder(agent_type)()
        result = await agent.run(message, message_history=history)
        return agent_type, str(result.output)

    results = await asyncio.gather(
        *[run_agent(atype) for atype in decision.agents],
        return_exceptions=True,
    )

    parts = []
    for r in results:
        if isinstance(r, Exception):
            parts.append(f"[Error: {r}]")
        else:
            agent_type, text = r
            if text:
                parts.append(f"**{agent_type.title()}:**\n{text}")

    return "\n\n---\n\n".join(parts) if parts else "No responses received."
