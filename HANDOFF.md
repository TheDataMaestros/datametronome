# Worker Architecture — Check Execution Decoupling

**Branch:** `feat/agents/multi-orchestration-agents`
**Date:** 2026-03-14

---

## Goal

Decouple quality check execution from the Podium API process into Celery workers with RabbitMQ as the message broker. Support two deployment models:
- **Self-hosted**: customer installs everything in their infrastructure (docker-compose)
- **Hybrid**: lightweight agent in customer's network runs checks locally, pushes results to central platform via HTTPS

Keep Pydantic AI agents completely independent of check execution internals via a `CheckDispatcher` protocol.

---

## Current Progress

### Completed in this branch (prior work)
- **Pydantic AI Migration** — all 3 chunks done and committed
- **SRP Database Layer Refactor** — all 8 chunks done and committed
- **274 tests passing**, 62 API routes, app running in Docker

### Completed in this session
- **Design spec written and reviewed** (3 review rounds, all issues resolved)
  - `docs/superpowers/specs/2026-03-14-worker-architecture-design.md`
- **Technology decisions made**:
  - Celery + RabbitMQ (broker) + Redis (result backend/cache)
  - `celery-redbeat` for dynamic DB-backed schedules
  - `CheckDispatcher` protocol with 3 implementations (Celery, Inline, Remote)
  - Priority queues: `checks.high`, `checks.default`, `checks.bulk`, `checks.dlq`
  - Circuit breaker on staves (5 consecutive failures → pause)

### NOT yet started
- Implementation plan (next step: invoke `writing-plans` skill)
- Any code changes for the worker architecture

---

## What Worked

- **Approach 3 (Celery now, Kafka-ready later)** — chosen over pure Kafka (too heavy for self-hosted) or pure Redis broker (message loss on crash)
- **RabbitMQ over Redis as Celery broker** — persistent message delivery, purpose-built for task queues
- **CheckDispatcher protocol** — clean abstraction keeps agents decoupled; showcase/SQLite mode preserved via InlineDispatcher
- **Staff reviewer subagent** — caught 10 real issues in the spec (async bridging, Beat scheduler library, hybrid agent contradictions, etc.)

## What Didn't Work

- **Redis as Celery broker** — rejected due to message loss on crash (unacceptable for production checks)
- **Kafka** — rejected for now due to operational complexity for self-hosted deployments (ZooKeeper/KRaft, schema registry, consumer groups). Design is Kafka-ready via the dispatcher protocol.
- **APScheduler for distributed scheduling** — current in-process scheduler can't handle multiple API instances (duplicate executions)

---

## Next Steps

### Immediate
1. **Write implementation plan** — invoke `writing-plans` skill using the design spec
2. **Implement in chunks** per the plan (estimated 7-9 migration steps in the spec)

### Key implementation milestones (from spec's Migration Path)
1. Add `CheckDispatcher` protocol + `InlineDispatcher` (current behavior behind interface)
2. Add Celery app, RabbitMQ + Redis to docker-compose (dev and prod)
3. Implement `CeleryDispatcher` + check tasks (async bridging via `asyncio.run()`)
4. Replace APScheduler with Celery Beat + `celery-redbeat`
5. Migrate existing clef schedules to RedBeat entries
6. Switch API endpoints to use dispatcher
7. Add circuit breaker (`stave.paused` column, Redis counters, unpause endpoint)
8. Add `RemoteDispatcher` + `ResultPusher` for hybrid mode
9. Remove old scheduler code

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/superpowers/specs/2026-03-14-worker-architecture-design.md` | Full design spec (READ THIS FIRST) |
| `docs/superpowers/plans/2026-03-13-srp-database-layer.md` | SRP refactor plan (completed) |
| `docs/superpowers/plans/2026-03-11-pydantic-ai-migration.md` | Pydantic AI migration plan (completed) |
| `datametronome/podium/datametronome_podium/services/clef_executor.py` | Check execution engine (2,337 lines, to be wrapped by Celery tasks) |
| `datametronome/podium/datametronome_podium/core/scheduler.py` | Current APScheduler (to be replaced by Celery Beat) |
| `datametronome/podium/datametronome_podium/services/clef_scheduler.py` | Current scheduled execution (to be replaced by check tasks) |

## Key Conventions

- Always use `.venv/bin/python` from `datametronome/podium/` (not `python3`)
- Always use `docker-compose` for running/testing
- Tests: `.venv/bin/python -m pytest` with `--timeout=10`
- asyncio mode: STRICT (`@pytest.mark.asyncio` required)
- Pre-commit hooks have pre-existing failures — use `--no-verify` for commits

## Running Tests

```bash
cd datametronome/podium
.venv/bin/python -m pytest --timeout=10 -v
# Expected: 274 passed
```
