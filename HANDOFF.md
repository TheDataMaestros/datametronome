# Handoff: Migrate Multi-Agent System to Pydantic AI

## Goal

Migrate DataMetronome's multi-agent chat system from Google ADK to Pydantic AI, removing all regex-based routing in favour of a structured LLM router call.

## Current State

All 4 phases of the multi-agent plan are complete but the implementation has known weaknesses:

- **Intent routing** is regex-based (`intent_router.py`) — fragile, language-specific, breaks on non-English queries
- **Orchestration decisions** (single/chain/parallel) are also regex-based (`orchestrator.py`) — same problem
- **Sub-agents** (`sub_agents.py`) are not real agents — just prompt variations, all share the same tools
- **ADK agent** (`adk_agent.py`, 113KB) carries a lot of complexity for what it actually does

Files to delete entirely:
- `datametronome/podium/datametronome_podium/services/adk_agent.py`
- `datametronome/podium/datametronome_podium/services/intent_router.py`
- `datametronome/podium/datametronome_podium/services/sub_agents.py`
- `datametronome/podium/datametronome_podium/services/orchestrator.py`

## Agreed Design (Option B — Clean Redesign)

### Architecture

```
User message
    ↓
RouterAgent (small/fast model, last N messages for context)
    → returns RoutingDecision (structured Pydantic output)
    ↓
Orchestrator dispatches based on RoutingDecision
    ↓
Sub-agents run (single / chain / parallel)
    → full conversation history passed to sub-agents
    ↓
Response
```

### New File Structure

```
datametronome/podium/datametronome_podium/services/
  agents/
    router.py          # RouterAgent → RoutingDecision (structured output)
    config.py          # ConfigAgent (pydantic_ai.Agent + tools)
    investigation.py   # InvestigationAgent
    report.py          # ReportAgent
  orchestrator.py      # dispatches based on RoutingDecision, handles chain/parallel
  agent_factory.py     # builds agents from env config (model, api_key)
```

### RoutingDecision Schema

```python
class RoutingDecision(BaseModel):
    intent: Literal["quick", "config", "investigation", "report", "exploration"]
    mode: Literal["single", "chain", "parallel"]
    agents: list[Literal["config", "investigation", "report"]]
    reasoning: str  # for tracing/debugging
```

### Key Design Decisions (all confirmed)

| Decision | Choice | Reason |
|----------|--------|--------|
| Model provider | Multi via env var, easy to configure | Flexibility |
| Router | One structured LLM call → RoutingDecision | Clean, validated, no regex |
| Language support | Implicit — LLM mirrors user language naturally | No added complexity |
| Conversation history | Last N messages to router, full history to sub-agents | Balance context vs tokens |
| Quick intent fast-path | Dropped for now | YAGNI, adds complexity |

### Model Configuration (env vars to design)

Should support easy switching between Gemini, Anthropic, OpenAI, Ollama via env var.
Example pattern:
```
DATAMETRONOME_AI_PROVIDER=anthropic   # or gemini, openai, ollama
DATAMETRONOME_AI_MODEL=claude-sonnet-4-6
DATAMETRONOME_AI_API_KEY=sk-...
DATAMETRONOME_ROUTER_MODEL=claude-haiku-4-5  # optional cheaper model for routing
```

## What We Decided NOT To Do

- **Option A (thin wrapper)**: Keeps old mental model, sub-agents not first-class — rejected
- **Option C (single master agent with sub-agent tools)**: Unpredictable, harder to trace — rejected
- **Quick intent fast-path**: YAGNI — can add later when there's real cost data
- **Explicit language detection**: LLM mirrors language naturally, no need for `response_language` field

## Next Steps

1. **Write the implementation plan** — invoke `superpowers:writing-plans` skill (brainstorming was in progress, design approved, this is the next step per the brainstorming skill)
2. Install `pydantic-ai` in `requirements.txt`
3. Implement `agent_factory.py` — model builder from env config
4. Implement `agents/router.py` — RouterAgent with RoutingDecision structured output
5. Implement `agents/config.py`, `agents/investigation.py`, `agents/report.py` — proper Agent instances
6. Implement new `orchestrator.py` — dispatch logic, chain (pass result.data as context), parallel (asyncio.gather)
7. Update `chat.py` endpoint — replace ADK calls with `orchestrator.run(message, history)`
8. Update `requirements.txt` — add pydantic-ai, remove google-adk
9. Delete old files: `adk_agent.py`, `intent_router.py`, `sub_agents.py`, old `orchestrator.py`
10. Test multi-language routing works correctly
11. Update Docker / env.example

## Context Files

- Current chat endpoint: `datametronome/podium/datametronome_podium/api/v1/endpoints/chat.py`
- Config: `datametronome/podium/datametronome_podium/core/config.py`
- Multi-agent plan doc: `docs/MULTI_AGENT_PLAN.md`
- Memory: `memory/MEMORY.md`
- Tools available to agents: list_staves, get_stave, create_stave, list_stave_tables, get_table_sample, suggest_quality_checks, list_clefs, get_clef, list_checks, get_summary_report, get_quality_report
