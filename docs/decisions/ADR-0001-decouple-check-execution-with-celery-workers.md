# ADR-0001: Decouple Check Execution with Celery Workers

## Status
Implemented

## Context

Quality checks (ClefExecutor, APScheduler, connections to customer databases) were running inside the Podium API process. This created several problems:

- **Resource contention**: long-running checks blocked API request handling
- **Scaling limitations**: could only scale checks by scaling the entire API
- **Duplicate execution**: APScheduler ran in-process, so multiple API replicas would execute the same scheduled check
- **No hybrid deployment**: credentials had to live on the same machine as the API — no way to run checks in a customer's network while centralizing the dashboard
- **No priority separation**: a user clicking "Run Now" waited behind hundreds of scheduled checks

The architecture needed to support two deployment models:
1. **Self-hosted**: customer installs everything in their infrastructure
2. **Hybrid**: lightweight agent in customer's network runs checks locally, pushes results to central platform

## Decision

Use **Celery + RabbitMQ** as the task queue with **Redis** as the result backend, behind a **CheckDispatcher protocol** that keeps agents and API endpoints fully decoupled from the execution mechanism.

### CheckDispatcher Protocol

```python
class CheckDispatcher(Protocol):
    async def dispatch(self, clef_id: str) -> str: ...
    async def get_status(self, job_id: str) -> JobStatus: ...
    async def get_result(self, job_id: str) -> dict | None: ...
```

Three implementations:
- **InlineDispatcher**: showcase/SQLite mode — executes immediately, no broker needed
- **CeleryDispatcher**: production — enqueues to RabbitMQ via Celery
- **RemoteDispatcher**: hybrid agent — executes locally, pushes results to central (future)

A singleton factory (`get_dispatcher()`) selects the implementation based on `settings.dispatch_mode`.

### Queue Topology

| Queue | Purpose |
|---|---|
| `checks.high` | Manual "run now" + agent-triggered (user is waiting) |
| `checks.default` | Scheduled checks |
| `checks.bulk` | Batch operations |
| `checks.dlq` | Dead letter queue |

### Scheduling

**celery-redbeat** replaces APScheduler. Beat runs as a single container — no duplicate execution. Schedules stored in Redis, updated atomically.

### Circuit Breaker

If a stave fails 5 consecutive checks, it is paused (`staves.paused = True`). Failure counter tracked in Redis. Manual unpause via `POST /staves/{id}/unpause`.

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| **Kafka** | Too heavy for self-hosted deployments (ZooKeeper/KRaft, schema registry, consumer groups). Design is Kafka-ready via the dispatcher protocol if scale demands it later. |
| **Redis as Celery broker** | Message loss on crash — Redis broker does not persist messages. Unacceptable for production checks where a missed check could mask data quality issues. |
| **Keep APScheduler, add threading** | Doesn't solve duplicate execution across replicas, no priority queues, no hybrid deployment support. |
| **Dramatiq** | Smaller ecosystem, less battle-tested than Celery. Celery's Redis result backend + RedBeat scheduler integration was a better fit. |

## Consequences

**Pros:**
- API and workers scale independently
- Priority queues ensure "Run Now" is fast regardless of scheduled check volume
- Celery Beat as single container eliminates duplicate execution
- InlineDispatcher preserves showcase mode (no broker needed)
- Agents (Pydantic AI) are completely decoupled — they call `dispatcher.dispatch()`, never import Celery
- Circuit breaker prevents hammering a dead database
- Foundation for hybrid deployment (RemoteDispatcher + ResultPusher)

**Cons:**
- Two additional containers in production (RabbitMQ, worker) — operational overhead
- Async bridging (`asyncio.run()` per task) adds slight overhead vs direct async execution
- InlineDispatcher stores job state in memory (bounded growth needed for long-running showcase instances)
- RedBeat schedule migration from APScheduler requires one-time script

## Architecture / Flow

```mermaid
flowchart LR
    UI["UI / Agent"] -->|POST /run-now| API["Podium API"]
    API -->|dispatch()| DP["CheckDispatcher"]
    DP -->|CeleryDispatcher| RMQ["RabbitMQ"]
    DP -.->|InlineDispatcher| EXEC["ClefExecutor"]
    RMQ --> W["Celery Worker"]
    W --> EXEC
    EXEC --> PG["Postgres (checks)"]
    W -->|result| REDIS["Redis (result backend)"]
    API -->|get_status()| REDIS
    BEAT["Celery Beat"] -->|send_task()| RMQ
    BEAT -.->|schedules| REDIS
```

## Implementation Notes

- **Async bridging**: Each Celery task uses `asyncio.run()` to execute the async `ClefExecutor`. Safe because each task is an isolated unit of work.
- **Worker DB lifecycle**: Workers create their own DB session per task via `worker_db_session()` context manager — independent of the API's global `get_db()`.
- **Task name**: `datametronome.execute_check` (registered via `celery_app.conf.include`)
- **Config**: `DATAMETRONOME_DISPATCH_MODE` controls which dispatcher is used (`inline` | `celery` | `remote`)
- **Docker profiles**: Worker and Beat are behind `profiles: [worker]` in dev compose, always-on in prod

## Follow-ups

- Implement `RemoteDispatcher` for hybrid deployment
- Add Prometheus metrics (`checks_enqueued_total`, `checks_completed_total`, etc.)
- Wire DLQ routing with RabbitMQ dead-letter exchange
- Add LRU eviction to InlineDispatcher's job state dicts
- Pool Redis client in circuit breaker (currently creates new connection per task)
- One-time migration script to move APScheduler jobs to RedBeat entries

## References

- Design spec: `docs/superpowers/specs/2026-03-14-worker-architecture-design.md`
- Implementation plan: `docs/superpowers/plans/2026-03-14-worker-architecture.md`
- Branch: `feat/agents/multi-orchestration-agents`
