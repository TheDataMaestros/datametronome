# Data Intelligence Layer — Phase 2: Chat UX + Dashboard

**Branch:** `feat/data-intelligence`
**Date:** 2026-03-15

---

## Goal

DataMetronome's data intelligence layer is implemented and working end-to-end. Now we need:
1. **Deepen the chat experience** — the InsightAgent should proactively analyze business health, not just list tables
2. **Expand the dashboard frontend** — show intelligence data (health scores, anomalies, suggestions, domain classification) with improved visual design
3. **Fix remaining issues** — conversation context loss, session expiry

---

## Current Progress

### Completed (this session — all on `feat/data-intelligence`)

**Backend intelligence layer (23 tasks, 8 chunks, 420+ tests):**
- Domain models: DataProfile, BaselineSnapshot, InsightReport, InsightSuggestion, InsightCreatedCheck
- Alembic migration for 5 intelligence store tables
- InsightsRepo with full CRUD
- API router with 11+ endpoints at `/api/v1/insights/`
- Domain archetypes (YAML): e-commerce, SaaS, IoT, CRM, generic
- Archetype loader with deterministic signature matching
- Intelligence Celery queue + tasks with Redis concurrency lock
- InsightAgent with dynamic system prompt + 9 tools (including `get_stave_intelligence`, `trigger_stave_analysis`)
- LLM output models for structured analysis (LLMInsightReport, LLMDomainClassification)
- InsightPipelineService with 5 stages (discover → classify → baseline → analyze → persist)
- Router/orchestrator wiring with `insight` intent
- Auto-scan trigger on stave creation with retry + Beat schedule registration
- Stave lifecycle hooks (pause/unpause/delete)
- Snapshot pruning with weekly aggregation

**Bug fixes applied:**
- `asyncio.run()` → `_run_async()` (new event loop per Celery task — fixes "Event loop is closed")
- Row count extraction via schema-qualified `COUNT(*)` queries
- Schema-qualified SQL in `get_table_sample` agent tool (`"olist"."customers"` not `"customers"`)
- InsightAgent system prompt rewritten for conversational chat (was returning JSON)
- Dashboard `/metrics/dashboard` enhanced with `intelligence` section
- PostgreSQL boolean fix (`is_active = TRUE` not `= 1`)
- `ai_heavy_model` setting for complex analysis (gemini-2.5-pro)
- Auto-scan dispatch retry with background thread

**Real data loaded:**
- Olist Brazilian E-Commerce: 550K+ rows, 8 tables (orders, customers, products, payments, reviews, sellers, items, categories)
- Downloaded from `github.com/olist/work-at-olist-data` (no auth needed)
- Schema: `olist` in PostgreSQL `datametronome_test`

**Verified working:**
- Auto-scan fires on stave creation, classifies domain as e-commerce (70% confidence)
- Chat routes to insight intent, agent explores tables conversationally
- Gemini 2.5 Pro gives rich business analysis ("97 delivered, 2 shipped, healthy fulfillment")
- Chat history persists and displays correctly
- Dashboard shows active sources, intelligence metrics via API

### DONE this session (2026-03-15 evening)
- **Dashboard Intelligence Pulse** — full UI section with animated health gauge (SVG arc), source coverage progress bar, suggestions + critical anomaly cards, "Explore Insights" CTA. Uses `intelligence` field from `/metrics/dashboard`.
- **Chat proactive insights** — InsightAgent system prompt updated: step 0 = always call `get_stave_intelligence` first, lead with health score. Verified in Chrome: AI responded with "critical state, health score 35" immediately.
- **`avg_health_score` NaN bug** — `WHERE report_type != 'initial'` excluded ALL auto_scan reports → NULL avg → NaN on frontend. Fixed: removed filter, added `?? 0` guards.
- **`run_auto_scan` now runs stage 4** — previously skipped business analysis (health_score=50 hardcoded default, no suggestions/anomalies). Now runs full pipeline including Gemini 2.5 Pro analysis. Falls back gracefully if LLM fails.
- **`asyncio.set_event_loop(loop)` fix** — second Celery task on same worker process got "Event loop is closed". Fixed by adding `asyncio.set_event_loop(loop)` in `_run_async` so httpx/asyncpg get the fresh loop.

**Current live state** (Olist stave `f3c5d3a5`):
- Health score: **35/100** (critical — data freshness anomaly detected)
- 2 analysis reports, 1 suggestion, 1 critical anomaly
- Dashboard gauge shows red arc with "Needs Attention"

### NOT yet done
- **Conversation context loss** — Gemini loses stave context across turns (asks "which stave?" again)
- **Session expiry** — JWT TTL is too short, Chrome demos get interrupted by login redirects
- **Dashboard charts** — System Health Trend and Anomaly Distribution still show "coming soon" placeholders

---

## What Worked

- **Subagent-driven development** — dispatched 8 implementer agents in parallel chunks, all completed with reviews. 420 tests, zero regressions.
- **Gemini 2.5 Pro for insight analysis** — dramatically better than 2.0 Flash for tool use and conversational quality. Flash still fine for routing.
- **Schema-qualified SQL** — Postgres schemas (`olist."customers"`) need explicit quoting in all raw SQL paths (agent tools, pipeline discovery, COUNT queries).
- **`_run_async()` pattern** — Celery prefork workers close the event loop after `asyncio.run()`. Creating a fresh `asyncio.new_event_loop()` per task fixes it.
- **Olist dataset** — real data with 8 related tables, perfect for e-commerce archetype matching. Direct download from GitHub, no auth.
- **Background thread for auto-scan dispatch** — `threading.Thread(target=_dispatch, daemon=True)` avoids blocking the API response and allows retry.

## What Didn't Work

- **`asyncio.run()` in Celery prefork** — second task on same worker process crashes with "Event loop is closed"
- **Unqualified table names in SQL** — `SELECT * FROM "customers"` fails when tables are in a schema like `olist`
- **InsightAgent with structured output prompt** — "Output must follow the exact schema" in system prompt made it return JSON in chat instead of conversational text
- **Gemini 2.0 Flash for tool use** — unreliable with multi-tool calls, misinterprets tool results, loses context across turns
- **Chat widget for demos** — session expires during LLM calls, widget closes on click-away. Full chat page (`/chat`) is more reliable.
- **Docker env vars** — `docker compose restart` doesn't pick up new env vars; need `docker compose up -d` to recreate containers

---

## Next Steps

### 1. Chat proactive insights (backend)
The InsightAgent lists tables but doesn't proactively call `get_stave_intelligence` to show health/anomalies. Fix:
- Update the system prompt to instruct: "When a user asks about their data, ALWAYS call get_stave_intelligence first to check if analysis exists. If it does, lead with the health score and key findings."
- Consider injecting a summary of all profiled staves into the system prompt at build time (in `_get_insight_agent()` in orchestrator.py)

### 2. Dashboard frontend expansion (Nuxt)
**Key files:**
- `ui-nuxt/pages/index.vue` — dashboard page
- `ui-nuxt/services/dashboard.ts` — API service (`getMetrics()`)
- `ui-nuxt/composables/useDashboard.ts` — composable

**What the API already provides** (GET `/api/v1/metrics/dashboard`):
```json
{
  "success_rate": 100.0,
  "active_sources": 1,
  "intelligence": {
    "avg_health_score": 53.6,
    "total_reports": 7,
    "profiled_sources": 4,
    "pending_suggestions": 9,
    "insight_anomalies": 1,
    "critical_anomalies": 1
  }
}
```

**What to build:**
- Intelligence health card showing avg_health_score with color coding (green >80, yellow >50, red <50)
- Profiled sources count with progress bar (profiled/total)
- Pending suggestions badge with link to act
- Recent anomalies list from latest insight reports
- Per-stave health breakdown (needs new API endpoint or expand overview)

### 3. Fix conversation context loss
Options:
- Inject stave summary into system prompt at agent build time
- Use Pydantic AI's message_history more aggressively
- Add a "current stave" sticky context in the orchestrator

### 4. Session expiry
- Increase JWT TTL in auth config
- Or add token refresh in the Nuxt frontend

---

## Architecture Reference

| Component | File | Purpose |
|-----------|------|---------|
| InsightAgent | `podium/datametronome_podium/services/agents/insight.py` | Chat agent with 9 tools |
| Agent tools | `podium/datametronome_podium/services/agent_tools.py` | `get_stave_intelligence`, `trigger_stave_analysis` + 11 others |
| Pipeline service | `podium/datametronome_podium/features/insights/service.py` | 5-stage analysis pipeline |
| Celery tasks | `podium/datametronome_podium/tasks/intelligence_tasks.py` | auto-scan, daily, on-demand, pruning |
| InsightsRepo | `podium/datametronome_podium/features/insights/repo.py` | CRUD for 5 intelligence tables |
| API router | `podium/datametronome_podium/features/insights/router.py` | 11 endpoints at `/insights/` |
| Archetypes | `podium/datametronome_podium/archetypes/*.yaml` | Domain signature matching |
| Scheduler | `podium/datametronome_podium/services/intelligence_scheduler.py` | RedBeat daily schedules |
| Dashboard metrics | `podium/datametronome_podium/api/v1/endpoints/metrics.py` | `/metrics/dashboard` with intelligence section |
| Dashboard frontend | `ui-nuxt/pages/index.vue` | Nuxt dashboard (needs intelligence cards) |
| Config | `podium/datametronome_podium/core/config.py` | `ai_heavy_model` setting |
| Agent factory | `podium/datametronome_podium/services/agent_factory.py` | `build_heavy_model_from_settings()` |
| Orchestrator | `podium/datametronome_podium/services/orchestrator.py` | Routes `insight` intent to InsightAgent |

## Key Conventions

- Always use `.venv/bin/python` from `datametronome/podium/` (not `python3`)
- Always use `docker-compose` for running/testing
- Tests: `.venv/bin/python -m pytest` with `--timeout=10`
- asyncio mode: STRICT (`@pytest.mark.asyncio` required)
- Pre-commit hooks have pre-existing failures — use `--no-verify` for commits
- Force-add files under `docs/superpowers/` (gitignored) with `git add -f`
- Gemini models: `gemini-2.0-flash` (routing/default), `gemini-2.5-pro` (insight analysis)
- Docker: use `docker compose up -d` not `restart` when env vars change

## Running Tests

```bash
cd datametronome/podium
.venv/bin/python -m pytest --timeout=10 -v
# Expected: 420+ passed
```

## Test Data

Olist dataset already loaded in PostgreSQL (`olist` schema):
- 99K customers, 99K orders, 112K items, 103K payments, 99K reviews, 33K products, 3K sellers
- To reload: `docker cp test_data/olist datametronome-postgres-1:/tmp/olist` then run `test_data/04_olist_ecommerce.sql`
