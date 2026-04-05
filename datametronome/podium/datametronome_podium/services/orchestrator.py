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

from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_executor

from datametronome_podium.services.agents.router import RoutingDecision, build_router_agent
from datametronome_podium.services.agents.config import build_config_agent
from datametronome_podium.services.agents.investigation import build_investigation_agent
from datametronome_podium.services.agents.report import build_report_agent
from datametronome_podium.services.agents.insight import build_insight_agent
from datametronome_podium.services.agent_factory import (
    build_model_from_settings,
    build_router_model_from_settings,
)
from datametronome_podium.services.workflow_state import (
    create_checkpoint,
    update_checkpoint,
    find_active_checkpoint,
    log_event,
)

logger = logging.getLogger(__name__)


def _fallback_route(message: str) -> RoutingDecision:
    """Keyword-based fallback when the LLM can't produce structured output.

    Works with any model — no structured output needed.
    """
    msg = message.lower()

    if any(w in msg for w in ["what do you know about me", "what did we find", "my memory", "show my profile"]):
        return RoutingDecision(
            intent="memory", mode="single", agents=["report"],
            reasoning="Fallback: detected memory keywords",
        )
    if any(w in msg for w in ["create", "add", "configure", "set up", "connect"]):
        return RoutingDecision(
            intent="config", mode="single", agents=["config"],
            reasoning="Fallback: detected config keywords",
        )
    if any(w in msg for w in ["why", "fail", "error", "broken", "diagnose", "wrong"]):
        return RoutingDecision(
            intent="investigation", mode="single", agents=["investigation"],
            reasoning="Fallback: detected investigation keywords",
        )
    if any(w in msg for w in ["report", "summary", "overview", "dashboard", "status"]):
        return RoutingDecision(
            intent="report", mode="single", agents=["report"],
            reasoning="Fallback: detected report keywords",
        )
    if any(w in msg for w in ["explore", "insight", "analyze", "what's happening", "how's my data", "business"]):
        return RoutingDecision(
            intent="insight", mode="single", agents=["insight"],
            reasoning="Fallback: detected insight keywords",
        )
    # Default: report agent handles general questions
    return RoutingDecision(
        intent="quick", mode="single", agents=["report"],
        reasoning="Fallback: defaulting to report agent",
    )


# --- Lazy agent factories (allow monkeypatching in tests) ---


def _get_router_agent():
    return build_router_agent(build_router_model_from_settings())


def _get_config_agent():
    return build_config_agent(build_model_from_settings())


def _get_investigation_agent():
    return build_investigation_agent(build_model_from_settings())


def _get_report_agent():
    return build_report_agent(build_model_from_settings())


def _get_insight_agent():
    from datametronome_podium.services.agent_factory import build_heavy_model_from_settings
    return build_insight_agent(build_heavy_model_from_settings())


def _get_agent_builder(agent_type: str, user_profile: str | None = None):
    """Resolve agent builder by name — indirects through module globals so patches work.

    When user_profile is None we delegate to the bare _get_*_agent helpers so that
    monkeypatching in tests remains effective. When a profile is provided we use
    closures that forward the profile kwarg to the underlying build functions.
    """
    if user_profile is None:
        builders = {
            "config": _get_config_agent,
            "investigation": _get_investigation_agent,
            "report": _get_report_agent,
            "insight": _get_insight_agent,
        }
        return builders.get(agent_type, _get_report_agent)

    # Profile-aware closures — bypasses the bare helpers intentionally because
    # the profile kwarg cannot be forwarded through the no-arg helper wrappers.
    def _config():
        return build_config_agent(build_model_from_settings(), user_profile=user_profile)

    def _investigation():
        return build_investigation_agent(build_model_from_settings(), user_profile=user_profile)

    def _report():
        return build_report_agent(build_model_from_settings(), user_profile=user_profile)

    def _insight():
        from datametronome_podium.services.agent_factory import build_heavy_model_from_settings
        return build_insight_agent(build_heavy_model_from_settings(), user_profile=user_profile)

    builders_with_profile = {
        "config": _config,
        "investigation": _investigation,
        "report": _report,
        "insight": _insight,
    }
    return builders_with_profile.get(agent_type, _report)


async def _load_user_profile(user_id: str | None) -> str | None:
    """Load and format the user's memory profile for system prompt injection."""
    if not user_id:
        return None
    try:
        from datametronome_podium.features.user_memory.repo import UserMemoryRepo
        from datametronome_podium.features.user_memory.service import UserMemoryService
        repo = UserMemoryRepo(get_executor())
        service = UserMemoryService(repo=repo)
        profile = await repo.get_profile(user_id)
        return service.format_profile_for_prompt(profile)
    except Exception as e:
        logger.warning("Failed to load user memory profile: %s", e)
        return None


async def _handle_memory_recall(user_id: str) -> str:
    """Handle a 'memory' intent — return formatted recall response as an early return."""
    try:
        from datametronome_podium.features.user_memory.repo import UserMemoryRepo
        from datametronome_podium.features.user_memory.service import UserMemoryService
        repo = UserMemoryRepo(get_executor())
        service = UserMemoryService(repo=repo)
        return await service.format_recall(user_id)
    except Exception as e:
        logger.warning("Failed to handle memory recall: %s", e)
        return "Sorry, I couldn't retrieve your memory profile right now."


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
    conversation_id: str | None = None,
    user_id: str | None = None,
    router_history_window: int = 6,
) -> dict[str, Any]:
    """Run the full chat pipeline: route -> dispatch -> respond.

    Args:
        message: Current user message
        history: Full conversation history as list of {role, content} dicts
        conversation_id: Optional conversation ID for checkpoint tracking
        user_id: Optional user ID for checkpoint tracking
        router_history_window: How many recent messages to send to the router for context

    Returns:
        dict with keys: message (str), intent (str), mode (str),
                        agents (list[str]), model (str)
    """
    all_history = convert_history_to_messages(history)
    router_history = all_history[-router_history_window:] if all_history else []

    user_profile_text = await _load_user_profile(user_id)

    # Skip LLM routing for Ollama — too slow and unreliable for structured output.
    # Use instant keyword-based routing instead, save the LLM call for the actual agent.
    if settings.ai_provider == "ollama":
        decision = _fallback_route(message)
        logger.info("Using keyword routing for Ollama (skipping LLM router)")
    else:
        router = _get_router_agent()
        try:
            routing_result = await router.run(message, message_history=router_history)
            decision = routing_result.output  # .output not .data in 1.67.0
        except Exception as e:
            logger.warning("Router structured output failed (%s), using fallback routing", e)
            decision = _fallback_route(message)

    logger.info(
        "Router decision: intent=%s mode=%s agents=%s reasoning=%r",
        decision.intent, decision.mode, decision.agents, decision.reasoning,
    )

    # Memory recall is a read-only operation — return early without agent dispatch
    # or checkpoint creation to keep it fast and side-effect-free.
    if decision.intent == "memory":
        response_message = await _handle_memory_recall(user_id or "")
        return {
            "message": response_message,
            "intent": decision.intent,
            "mode": "single",
            "agents": [],
            "model": "pydantic-ai",
        }

    # Check for paused checkpoint to resume, or create a new one
    checkpoint_id = None
    if conversation_id and user_id:
        existing = await find_active_checkpoint(conversation_id)
        if existing and existing["status"] == "paused":
            checkpoint_id = existing["id"]
            logger.info("Resuming paused checkpoint %s", checkpoint_id)
            await update_checkpoint(checkpoint_id, status="running")
            await log_event(checkpoint_id, "node_entered", "resume", {
                "resumed_from": existing.get("current_node"),
            })
        else:
            workflow_name = f"{decision.mode}:{'+'.join(decision.agents)}"
            checkpoint_id = await create_checkpoint(conversation_id, user_id, workflow_name)
        await log_event(checkpoint_id, "decision_made", "router", {
            "intent": decision.intent,
            "mode": decision.mode,
            "agents": decision.agents,
            "reasoning": decision.reasoning,
        })

    try:
        if decision.mode == "parallel" and len(decision.agents) >= 2:
            response_message = await _run_parallel(message, decision, all_history, checkpoint_id, user_profile_text)
        elif decision.mode == "chain" and len(decision.agents) >= 2:
            response_message = await _run_chain(message, decision, all_history, checkpoint_id, user_profile_text)
        else:
            response_message = await _run_single(message, decision, all_history, checkpoint_id, user_profile_text)

        if checkpoint_id:
            await update_checkpoint(checkpoint_id, status="completed")

    except Exception as e:
        if checkpoint_id:
            await log_event(checkpoint_id, "error", None, {"error": str(e)})
            await update_checkpoint(checkpoint_id, status="failed")
        raise

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
    checkpoint_id: str | None = None,
    user_profile: str | None = None,
) -> str:
    agent_type = decision.agents[0] if decision.agents else "report"

    if checkpoint_id:
        await log_event(checkpoint_id, "node_entered", agent_type)
        await update_checkpoint(checkpoint_id, current_node=agent_type)

    agent = _get_agent_builder(agent_type, user_profile=user_profile)()
    result = await agent.run(message, message_history=history)
    output = str(result.output)

    if checkpoint_id:
        await log_event(checkpoint_id, "node_completed", agent_type, {
            "output_preview": output[:200],
        })

    return output


async def _run_chain(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
    checkpoint_id: str | None = None,
    user_profile: str | None = None,
) -> str:
    """Run agents in sequence. Each agent after the first receives the previous output."""
    previous_output = ""
    last_result = ""

    for i, agent_type in enumerate(decision.agents):
        if checkpoint_id:
            await log_event(checkpoint_id, "node_entered", agent_type, {"step": i})
            await update_checkpoint(checkpoint_id, current_node=agent_type)

        agent = _get_agent_builder(agent_type, user_profile=user_profile)()

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

        if checkpoint_id:
            await log_event(checkpoint_id, "node_completed", agent_type, {
                "step": i,
                "output_preview": previous_output[:200],
            })
            await update_checkpoint(
                checkpoint_id,
                state_data={"step": i, "agent": agent_type, "output": previous_output[:500]},
            )

    return last_result


async def _run_parallel(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
    checkpoint_id: str | None = None,
    user_profile: str | None = None,
) -> str:
    """Run agents concurrently, combine their outputs."""
    if checkpoint_id:
        for agent_type in decision.agents:
            await log_event(checkpoint_id, "node_entered", agent_type)
        await update_checkpoint(checkpoint_id, current_node=",".join(decision.agents))

    async def run_agent(agent_type: str) -> tuple[str, str]:
        agent = _get_agent_builder(agent_type, user_profile=user_profile)()
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
            if checkpoint_id:
                await log_event(checkpoint_id, "error", None, {"error": str(r)})
        else:
            agent_type, text = r  # type: ignore[not-iterable]
            if text:
                parts.append(f"**{agent_type.title()}:**\n{text}")
            if checkpoint_id:
                await log_event(checkpoint_id, "node_completed", agent_type, {
                    "output_preview": text[:200],
                })

    return "\n\n---\n\n".join(parts) if parts else "No responses received."
