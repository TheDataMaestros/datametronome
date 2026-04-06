# DataMetronome

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

## Common Gotchas

- The `Settings` class uses `validation_alias` for env vars (e.g., `DATAMETRONOME_DATABASE_URL`), not the `env_prefix` alone.
- `agent_tools.py` still uses the old `get_db()` pattern. Migration to `get_executor()` is pending.
- Some complex endpoints remain in `api/v1/endpoints/` alongside the newer `features/` pattern. Check both locations when looking for route handlers.
- Celery workers need their own DB sessions via `worker_db_session()` context manager. They cannot use the global singleton.
- Musical terminology is pervasive. Search for "stave" not "data source", "clef" not "check definition".
