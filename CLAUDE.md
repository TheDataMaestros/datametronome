# DataMetronome

## Architecture Reference

Full architecture reference: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

Covers: system topology, request flow, AI agent design, feature slice conventions,
database access layers (QueryExecutor / QueryAdapter / Pulse), and worker architecture.

## Project Overview

DataMetronome is an open-source data quality monitoring platform with AI-powered multi-agent assistance. The stack is Python 3.13 + FastAPI backend, Nuxt 3 frontend, PostgreSQL database, and Celery workers with RabbitMQ as broker and Redis as result backend.

## Glossary (Musical Terms to Engineering Concepts)

The codebase uses musical metaphors throughout. You must understand these to navigate the code:

- **Stave** = Data source (a database, schema, or table to monitor)
- **Clef** = Quality check definition (a rule attached to a stave)
- **Check** = Execution result of a clef (pass/warn/fail)
- **Podium** = The FastAPI backend API server
- **Pulse** = Database connector library (postgres, sqlite, bigquery adapters)
- **Brain** = ML/statistics engine (SARIMA forecasting, drift detection, isolation forest)
- **Orchestrator** = AI chat router that classifies intent and dispatches to sub-agents

Search for "stave" not "data source", "clef" not "check definition". The musical terminology is pervasive.

## Project Structure

```
datametronome/
  datametronome/podium/              # FastAPI backend
    datametronome_podium/
      api/v1/endpoints/              # Complex endpoints (auth, chat, scheduler, stave_actions, etc.)
      features/                      # Feature slices (staves, clefs, checks, chat, insights, user_memory, etc.)
        {feature}/                   # model.py, repo.py, schema.py, router.py
      core/                          # Config, database, query executor, middleware, metrics
      services/                      # Business logic, agents, orchestrator
      tasks/                         # Celery task definitions
      archetypes/                    # Domain classification YAML templates
    alembic/                         # Database migrations
    tests/                           # pytest tests
  datametronome/pulse/               # Database connectors (core, postgres, sqlite, bigquery)
  datametronome/brain/               # ML models
  ui-nuxt/                           # Nuxt 3 frontend
  docker-compose.yml                 # Full stack: postgres + rabbitmq + redis + podium + worker + beat + UI
  Makefile                           # Docker-first commands
```

## Build and Test Commands

```bash
# Start full stack (API + Postgres + Redis + RabbitMQ)
make up

# Start with workers (adds Celery worker + Beat scheduler)
make up-workers

# Stop everything
make down

# Run tests (fast, uses SQLite, runs locally)
make test
# Or directly:
cd datametronome/podium && .venv/bin/python -m pytest --timeout=10 -q

# Run Alembic migrations inside Docker
make migrate
```

## Environment Variables

All configuration is driven by `DATAMETRONOME_*` environment variables. The
`Settings` class uses `validation_alias` fields -- the `env_prefix` alone is not
sufficient (see `core/config.py`).

| Variable | Default | Purpose |
|---|---|---|
| `DATAMETRONOME_DEBUG` | `false` | Enable debug mode |
| `DATAMETRONOME_HOST` | `0.0.0.0` | Server bind address |
| `DATAMETRONOME_PORT` | `8001` | Server port |
| `DATAMETRONOME_SECRET_KEY` | (dev default) | JWT signing key -- must be 32+ chars |
| `DATAMETRONOME_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT TTL in minutes |
| `DATAMETRONOME_DATABASE_URL` | `postgresql://testuser:testpass@localhost:5432/datametronome_test` | Primary DB URL |
| `DATAMETRONOME_ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:8501"]` | CORS origins |
| `DATAMETRONOME_SCHEDULER_ENABLED` | `true` | Enable check scheduler |
| `DATAMETRONOME_SCHEDULER_TIMEZONE` | `UTC` | Scheduler timezone |
| `DATAMETRONOME_SCHEDULER_MAX_INSTANCES` | `3` | Max concurrent scheduler instances |
| `DATAMETRONOME_SCHEDULER_MAX_WORKERS` | `10` | Thread pool for scheduler |
| `DATAMETRONOME_JOB_QUEUE_SIZE` | `1000` | In-memory job queue size |
| `DATAMETRONOME_WORKER_POOL_SIZE` | `4` | Worker pool threads |
| `DATAMETRONOME_DISPATCH_MODE` | `inline` | Check dispatch: `inline` / `celery` / `remote` |
| `DATAMETRONOME_CELERY_BROKER_URL` | `amqp://guest:guest@rabbitmq:5672//` | RabbitMQ URL |
| `DATAMETRONOME_CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Redis result backend |
| `DATAMETRONOME_REDIS_URL` | `redis://redis:6379/0` | Redis URL (circuit breaker + cache) |
| `DATAMETRONOME_CELERY_CONCURRENCY` | `4` | Celery worker concurrency |
| `DATAMETRONOME_METRICS_ENABLED` | `true` | Expose Prometheus `/metrics` endpoint |
| `DATAMETRONOME_METRICS_RETENTION_DAYS` | `90` | Days to retain metric data |
| `DATAMETRONOME_AI_PROVIDER` | `ollama` | AI provider: `anthropic` / `openai` / `gemini` / `ollama` |
| `DATAMETRONOME_AI_MODEL` | `qwen2.5` | Main agent model name |
| `DATAMETRONOME_AI_API_KEY` | `` | API key (not needed for Ollama) |
| `DATAMETRONOME_AI_ROUTER_MODEL` | (uses `AI_MODEL`) | Cheaper model for intent routing |
| `DATAMETRONOME_AI_HEAVY_MODEL` | (uses `AI_MODEL`) | Stronger model for complex analysis |
| `DATAMETRONOME_AI_BASE_URL` | `null` | Custom base URL (required for Ollama: `http://localhost:11434/v1`) |
| `OLLAMA_API_BASE` | `http://localhost:11434` | Ollama base URL (legacy compat) |

For production, always set `DATAMETRONOME_SECRET_KEY` to a random 32+ char string:

```bash
openssl rand -hex 32
```

## Key Conventions

- **Feature slices**: New features go in `features/{name}/` with model.py, repo.py, schema.py, router.py.
- **Database access**: Always use `get_executor()` to obtain a `QueryExecutor`. Never call `get_db()` directly (deprecated).
- **SQL placeholders**: Use `?` everywhere. `QueryAdapter` translates to `$1, $2, ...` for PostgreSQL at runtime.
- **Authentication**: Import `get_current_user` from `datametronome_podium.api.v1.endpoints.auth`. All endpoints require auth via `Depends(get_current_user)`.
- **AI agents**: Built with Pydantic AI. A router agent classifies intent, and the orchestrator dispatches to config/investigation/report/insight agents.
- **Tests**: pytest with asyncio strict mode. Use `@pytest.mark.asyncio` for async tests. Timeout: 10s.
- **Docker first**: Always use `docker-compose` for running the full stack. Use `.venv/bin/python` (not `python3`) for local commands from `datametronome/podium/`.
- **Commits**: Use conventional commits format (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- **Pre-commit hooks**: Have pre-existing failures. Use `--no-verify` for commits.

## Migration State

The codebase is mid-migration toward the feature-slice pattern:

- **`features/`** -- current pattern. Uses `get_executor()` to obtain a `QueryExecutor`.
  All new code goes here.
- **`api/v1/endpoints/`** -- legacy pattern. Complex endpoints (auth, chat, scheduler,
  stave_actions, clef_actions, metrics, reports, trends, import_config) still use the
  old `execute_query()` call directly. These have not been migrated yet.

**Rule: all new code must use `get_executor()`**. Never call `execute_query()` or
`get_db()` in new files.

## Common Gotchas

- The `Settings` class uses `validation_alias` for env vars (e.g., `DATAMETRONOME_DATABASE_URL`), not the `env_prefix` alone.
- `agent_tools.py` still uses the old `get_db()` pattern. Migration to `get_executor()` is pending.
- Some complex endpoints remain in `api/v1/endpoints/` alongside the newer `features/` pattern. Check both locations when looking for route handlers.
- Celery workers need their own DB sessions via `worker_db_session()` context manager. They cannot use the global singleton.
- Musical terminology is pervasive. Search for "stave" not "data source", "clef" not "check definition".
