# Project Status Report · DataMetronome

_Date generated: September 13, 2026_

## Overview

| Metric | Status |
| --- | --- |
| Current Focus | dbt connector rollout, alerting depth, test coverage |
| Project Health | Green |
| Backend Tests | 623 passing |

## Architecture Decisions

### Scheduling and dispatch: Celery Beat + RedBeat + `dispatch_mode`

**Authoritative detail**: See [docs/architecture.md](architecture.md). In-process
APScheduler has been removed from Podium.

**Job scheduling**:
- **Celery Beat + RedBeat** drive cron-style clef schedules; state lives in
  **`scheduler_jobs`** / **`job_executions`** (persistence, retries, API under `/scheduler/*`).

**Check execution**:
- **`DATAMETRONOME_DISPATCH_MODE`**: `inline`, **`celery`**, or `remote` — how clef checks run once scheduled.
- **`make up-workers`**: RabbitMQ, Redis, Celery worker(s), Beat — see `docker-compose.yml`.

**Takeaway**: Beat decides when jobs fire; `dispatch_mode` decides whether runs
are in-process, queued, or remote.

### Code organisation

All endpoints live in `features/{name}/` slices (model, repo, schema, router).
The legacy `api/v1/endpoints/` tree no longer exists. All database access goes
through `get_executor()` returning a `QueryExecutor`; `get_db()` and
`execute_query()` are gone.

## Delivered

| Area | State |
| --- | --- |
| DataPulse Ecosystem | core, postgres (×3 drivers), sqlite, bigquery, dbt |
| Backend | FastAPI Podium, 15 feature slices, Alembic migrations |
| Checks | Level 1 declarative checks (row_count, freshness, column_values) with all condition types |
| Stave Lifecycle | YAML ingestion, env interpolation, hot reload, scheduler integration |
| Scheduler | Persisted jobs, Celery Beat/RedBeat, retry/backoff, execution history, scheduler API |
| Workers | Celery + RabbitMQ + Redis, pluggable dispatch, circuit breaker |
| AI | Pydantic AI multi-agent orchestration, data intelligence layer, per-user memory |
| Security | Credential encryption at rest, RBAC (admin/editor/viewer), hardened endpoints |
| Observability | Health endpoint, Prometheus metrics, structured logging, tracing |
| Alerting | Global webhook on check failure, configured in app settings |
| CI/CD | Type check + full backend/connector suites on 3.12 and 3.13, frontend lint/build, tag-driven PyPI release |

## Outstanding Gaps

| Capability Cluster | Status |
| --- | --- |
| Tiered Check System | Level 1 complete; Levels 2-4 pending |
| Alerting | Single global webhook only — no per-stave routing, severity thresholds, retry or dedupe |
| Frontend Testing | No tests at all; CI runs lint and build only |
| Unbuilt UI pages | `reports.vue` and `investigation.vue` are "coming soon" placeholders — the reports backend exists and is unused. Dashboard System Health Trend and Anomaly Distribution charts are placeholders too |
| Chat context | Agents lose stave context across turns and re-ask "which stave?" |
| Connector Testing | `pulse/bigquery` and `pulse/api` ship no tests |
| Connector Coverage | MySQL, MongoDB, Snowflake and Redis have UI forms but no Pulse connector |
| Brain Libraries | `brain/base` ships forecasting + drift helpers; deeper tier still evolving |
| Ecosystem | Great Expectations plugin not started (dbt connector shipped) |
| Packaging | Only `pulse/core` and `pulse/sqlite` carry a CHANGELOG |
| Observability | Real-time streaming features outstanding |

## Next Steps

### Immediate
1. Merge the dbt connector (PR #13)
2. Add frontend test infrastructure — currently the largest untested surface
3. Backfill CHANGELOGs for the Pulse packages before the next tagged release

### Short Term
1. Level 2 checks on top of `brain/base` (SARIMA forecasting, KS drift)
2. Alerting depth: per-stave routing, severity thresholds, retry and dedupe
3. Decide whether to implement or remove the connector types that exist only in the UI picker

### Medium Term
1. Level 3/4 checks (`lookup_validation`, reconciliation, Python script runner)
2. Plugin support beyond dbt

## Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Untested frontend | Lint and build gate in CI today; add component tests before major UI work |
| UI/backend divergence | Connector types in the picker must map to a real Pulse connector |
| Documentation drift | Docs claiming status must be dated and checked against the code |

## Alignment Notes

- Roadmap: [ROADMAP.md](../ROADMAP.md)
- Architecture: [docs/architecture.md](architecture.md)
- Specs and plans: `docs/superpowers/`
