# Multi-Agent Architecture Plan

**Status**: Phase 3 complete
**Phase**: —
**Last Updated**: March 2025

---

## Overview

This document describes the plan to evolve DataMetronome's single-agent chat assistant into a multi-agent system with routing, specialized sub-agents, and orchestration. The goal is to improve response quality, reduce cost through smarter model routing, and build experience with production multi-agent patterns.

---

## Rationale

- **Domain is already semi-specialized**: Current agent handles configuration, exploration, troubleshooting, reporting — natural candidates for sub-agents.
- **Routing use case**: Simple queries ("status?", "how many staves?") → fast/cheap model; complex analysis ("why did check X fail?") → more capable model.
- **Product value**: Better answers, potential cost reduction, differentiation vs generic assistants.
- **Learning value**: Hands-on experience for Aptus-style multi-agent roles.

---

## Phases

### Phase 0: Foundations (1–2 weeks) — COMPLETE

Prerequisite before introducing multi-agent logic.

- [x] **Tracing / observability**: Structured logging for each chat request: user message, inferred intent, tool calls, model used, latency. Stored in `agent_traces` table.
- [x] **Intent dataset**: JSON file with sample queries and expected intent labels for evaluation and router training.
- [x] **Prometheus metrics**: `chat_requests_total`, `chat_request_duration_seconds`, `chat_tool_calls_total`.

**Output**: Trace infrastructure + intent dataset for Phase 1.

---

### Phase 1: Simple Router (2–3 weeks) — COMPLETE

Single router, still one agent — prove the pattern.

- [x] **Intent classifier**: Classify query as `quick` | `config` | `investigation` | `report` | `exploration`.
- [x] **Router**: Quick → fast model (e.g. Ollama local); others → current ADK agent.
- [x] **Dual-path in chat endpoint**: `POST /chat` calls router first, then dispatches.

**Output**: Working routing with potential cost savings on simple queries.

---

### Phase 2: Specialized Sub-Agents (3–4 weeks) — COMPLETE

One agent → three, each with a subset of tools.

- [x] **Agent Config**: Staves, clefs, creating checks.
  Tools: `list_staves`, `get_stave`, `create_stave`, `list_clefs`, `get_clef`, `list_stave_tables`, `suggest_quality_checks`.
- [x] **Agent Investigation**: Anomalies, failures, root cause.
  Tools: `list_checks`, `get_quality_report`, `get_summary_report`, `get_stave`, `get_clef`, `get_table_sample`, `list_stave_tables`.
- [x] **Agent Report**: Overview, status, reports.
  Tools: `get_summary_report`, `get_quality_report`, `list_staves`, `list_clefs`, `list_checks`.

**Output**: Three specialized agents with tailored system prompts and tool sets.

---

### Phase 3: Orchestrator (2–3 weeks) — COMPLETE

Coordinator that orchestrates sub-agents.

- [x] **Orchestrator**: Receives intent from router, selects one or more sub-agents.
- [x] **Multi-agent patterns**: single-agent, chain (A→B). Parallel deferred.
- [x] **Synthesis**: Chain uses last agent's output as final response (previous output passed as context).
- [x] **Shared state**: `orchestrator` context dict with `previous_output` between chain agents.

**Output**: Full multi-agent pipeline with routing and orchestration.

---

## Timeline Estimate

| Phase   | Time     | Dependencies |
|---------|----------|--------------|
| 0 Foundations | 1–2 weeks | None         |
| 1 Router       | 2–3 weeks | Phase 0      |
| 2 Sub-agents   | 3–4 weeks | Phase 1      |
| 3 Orchestrator | 2–3 weeks | Phase 2      |
| **Total**      | **8–12 weeks** | |

---

## Risk Mitigation

- **Complexity**: Start with 2 sub-agents (Config + Investigation), add Report later.
- **Regression**: A/B test router on/off; compare quality before/after.
- **Operational overhead**: Clear config for model-per-intent; fallback "all same model" for MVP.

---

## Testing & Docker

### Local
```bash
make setup-db      # Initialize DB (creates agent_traces via init_db)
make migrate       # Run migrations (for existing DBs)
make start-podium  # Start backend
# In another terminal: make start-ui
# Open http://localhost:3000, login admin/admin, try Chat
```

### Docker
```bash
make docker-build
make docker-up           # Podium + Postgres
# Optional full stack:
make docker-up-full      # + UI on :3000
make docker-migrate      # Run migrations (if DB exists in ./data)
```

---

## Files

- **Intent dataset**: `datametronome/podium/agent_intent_dataset.json`
- **Intent router**: `datametronome_podium/services/intent_router.py`
- **Sub-agents config**: `datametronome_podium/services/sub_agents.py`
- **Orchestrator**: `datametronome_podium/services/orchestrator.py`
- **Tracing service**: `datametronome_podium/services/agent_tracing.py`
- **Traces table**: `agent_traces` (migration 003)
- **Migration script**: `datametronome/podium/scripts/migrate_agent_traces.py`
- **Config**: `DATAMETRONOME_ADK_MODEL_QUICK` (optional fast model for quick intent)
