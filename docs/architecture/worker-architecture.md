# Worker Architecture

## Overview

DataMetronome decouples check execution from the API process using a **CheckDispatcher protocol** with pluggable backends. The API dispatches checks without knowing how they execute — the same protocol works for inline execution (showcase mode), Celery workers (production), or remote agents (hybrid deployment).

## Components

```mermaid
graph TB
    subgraph "API Process (Podium)"
        API["FastAPI Endpoints"]
        DF["dispatcher_factory.py<br/>get_dispatcher()"]
        API --> DF
    end

    subgraph "Dispatchers"
        DF -->|dispatch_mode=inline| ID["InlineDispatcher<br/>core/check_dispatcher.py"]
        DF -->|dispatch_mode=celery| CD["CeleryDispatcher<br/>core/celery_dispatcher.py"]
        DF -.->|dispatch_mode=remote| RD["RemoteDispatcher<br/>(future)"]
    end

    subgraph "Celery Infrastructure"
        CD -->|apply_async| RMQ["RabbitMQ<br/>amqp://rabbitmq:5672"]
        RMQ --> W["Celery Worker<br/>tasks/check_tasks.py"]
        W -->|result| REDIS["Redis<br/>redis://redis:6379"]
        BEAT["Celery Beat<br/>+ celery-redbeat"] -->|send_task| RMQ
        BEAT -.->|schedules| REDIS
    end

    subgraph "Execution"
        ID --> EXEC["ClefExecutor<br/>services/clef_executor.py"]
        W --> WDB["worker_db_session()<br/>core/worker_db.py"]
        WDB --> EXEC
        EXEC --> CUST["Customer DB<br/>(stave)"]
        EXEC --> PG["Postgres<br/>(checks table)"]
    end

    subgraph "Circuit Breaker"
        W --> CB["StaveCircuitBreaker<br/>core/circuit_breaker.py"]
        CB -->|failure counter| REDIS
        CB -->|paused=true| PG
    end
```

## File Map

All paths relative to `datametronome/podium/datametronome_podium/`.

| File | Responsibility |
|------|---------------|
| `core/check_dispatcher.py` | `CheckDispatcher` protocol, `JobStatus` enum, `InlineDispatcher` |
| `core/celery_dispatcher.py` | `CeleryDispatcher` — enqueues to RabbitMQ via Celery |
| `core/dispatcher_factory.py` | Singleton factory — selects dispatcher based on `settings.dispatch_mode` |
| `core/celery_app.py` | Celery application config, queue definitions, RedBeat scheduler |
| `core/worker_db.py` | Per-task DB session factory (`worker_db_session()` context manager) |
| `core/circuit_breaker.py` | `StaveCircuitBreaker` — Redis counters, Postgres pause flag |
| `tasks/__init__.py` | Tasks package marker |
| `tasks/check_tasks.py` | `execute_check` Celery task — wraps ClefExecutor with async bridging |
| `tasks/result_pusher.py` | `ResultPusher` — HTTPS push for hybrid mode |

## Dispatch Modes

### Inline (`dispatch_mode=inline`)

Default mode. No broker required. Checks execute immediately in the API process. Used for:
- Showcase/demo deployments
- SQLite-based single-container setups
- Development without Docker infrastructure

```
API → InlineDispatcher → ClefExecutor → result stored → job_id returned
```

The entire cycle completes before `dispatch()` returns. The 202 response is technically synchronous but uses the same job tracking interface.

### Celery (`dispatch_mode=celery`)

Production mode. Requires RabbitMQ + Redis + worker container.

```
API → CeleryDispatcher → RabbitMQ → Worker picks up → ClefExecutor → result in Redis + Postgres
API ← polls get_status(job_id) ← Redis
```

**Queue priority**: "Run Now" and agent-triggered checks go to `checks.high`, scheduled checks to `checks.default`. Workers consume all queues with high taking priority.

### Remote (`dispatch_mode=remote`) — Future

For hybrid deployments where checks run in the customer's network. A standalone agent process executes checks locally and pushes results to the central API via `ResultPusher`.

## Docker Containers

### Development (`docker-compose.yml`)

| Container | Service | Profile | Always running? |
|---|---|---|---|
| `podium` | FastAPI API | default | Yes |
| `postgres` | App database | default | Yes |
| `rabbitmq` | Message broker | default | Yes (needed if celery mode) |
| `redis` | Result backend + cache | default | Yes (needed if celery mode) |
| `podium-worker` | Celery worker | `worker` | Only with `--profile worker` |
| `podium-beat` | Celery Beat scheduler | `worker` | Only with `--profile worker` |
| `ui` | Nuxt frontend | `full` | Only with `--profile full` |

**Quick start (inline mode):**
```bash
docker-compose up -d postgres podium
```

**Full stack (celery mode):**
```bash
echo "DATAMETRONOME_DISPATCH_MODE=celery" >> .env
docker-compose --profile worker up -d
```

## Configuration

All settings in `core/config.py`, configurable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATAMETRONOME_DISPATCH_MODE` | `inline` | `inline`, `celery`, or `remote` |
| `DATAMETRONOME_CELERY_BROKER_URL` | `amqp://guest:guest@rabbitmq:5672//` | RabbitMQ connection |
| `DATAMETRONOME_CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Redis result backend |
| `DATAMETRONOME_REDIS_URL` | `redis://redis:6379/0` | Redis for cache + RedBeat |
| `DATAMETRONOME_CELERY_CONCURRENCY` | `4` | Worker process count |

## Circuit Breaker

Tracks consecutive failures per stave in Redis (`circuit:{stave_id}:failures`).

| Event | Action |
|---|---|
| Check passes or warns | Counter reset to 0 |
| Check fails | Counter incremented |
| Counter reaches 5 | `staves.paused = True`, clef schedules removed |
| `POST /staves/{id}/unpause` | Counter reset, `paused = False` |

The circuit breaker fails open — if Redis is unavailable, checks proceed without circuit breaker protection.

## API Changes

| Endpoint | Before | After |
|---|---|---|
| `POST /clefs/{id}/run-now` | Executes inline, returns 200 with result | Dispatches via CheckDispatcher, returns **202** with `job_id` |
| `GET /clefs/jobs/{job_id}/status` | N/A (new) | Returns job status + result when completed |
| `POST /staves/{id}/unpause` | N/A (new) | Resets circuit breaker, unpauses stave |

## Testing

50+ new tests across 9 test files. All use mocked Celery/Redis — no broker needed to run tests.

```bash
cd datametronome/podium
.venv/bin/python -m pytest --timeout=10 -q
# 330 passed, 1 skipped
```
