# DataMetronome Architecture

A comprehensive overview of the system architecture, data model, and request lifecycle.

---

## Table of Contents

- [System Overview](#system-overview)
- [Backend Architecture](#backend-architecture)
- [Database Layer](#database-layer)
- [Data Model](#data-model)
- [Request Flow](#request-flow)
- [Scheduling](#scheduling)
- [Authentication](#authentication)
- [Technology Stack](#technology-stack)
- [Deployment](#deployment)

---

## System Overview

DataMetronome is a data quality monitoring platform. Users connect data sources ("staves"), define quality checks ("clefs"), and schedule automated execution. An AI assistant provides conversational access to configuration, investigation, and reporting.

```mermaid
graph TB
    subgraph "Frontend"
        UI["Nuxt 3 SPA<br/>Dashboard, Chat, Reports"]
    end

    subgraph "API Layer"
        FASTAPI["FastAPI<br/>REST + JWT Auth"]
        MIDDLEWARE["Rate Limiting<br/>CORS<br/>Metrics"]
    end

    subgraph "AI Orchestration"
        ORCH["Orchestrator<br/>Router + Dispatch"]
        AGENTS["Sub-Agents<br/>Config | Investigation | Report"]
        TOOLS["11 Agent Tools<br/>DB access, analysis"]
    end

    subgraph "Feature Slices"
        STAVES["staves/"]
        CLEFS["clefs/"]
        CHECKS["checks/"]
        USERS["users/"]
        CHAT["chat/"]
        WF["workflows/"]
        TRACES["traces/"]
        SCHED["scheduler/"]
        ANALYTICS["analytics/"]
    end

    subgraph "Processing"
        SCHEDULER["APScheduler<br/>Cron Jobs"]
        EXECUTOR["ClefExecutor<br/>Check Runner"]
    end

    subgraph "Data Layer"
        QE["QueryExecutor"]
        QA["QueryAdapter<br/>SQLite / PostgreSQL"]
        PULSE["PulseConnector<br/>SQLitePulse | PostgresPulse"]
        DB[("PostgreSQL<br/>or SQLite")]
    end

    UI -->|HTTP/JSON| FASTAPI
    FASTAPI --> MIDDLEWARE
    FASTAPI --> ORCH
    FASTAPI --> STAVES & CLEFS & CHECKS & USERS
    ORCH --> AGENTS
    AGENTS --> TOOLS
    TOOLS --> QE
    STAVES & CLEFS & CHECKS --> QE
    SCHEDULER --> EXECUTOR
    EXECUTOR --> QE
    QE --> QA
    QA --> PULSE
    PULSE --> DB
```

### Key Characteristics

- **Async-first** -- built on `asyncio` and `asyncpg`/`aiosqlite` for non-blocking I/O
- **Feature-slice architecture** -- each domain (staves, clefs, checks, ...) owns its model, repo, router, and schema
- **Database-agnostic** -- the same codebase runs on SQLite (dev) and PostgreSQL (production)
- **Multi-agent AI** -- Pydantic AI agents with structured routing, tool calling, and workflow checkpoints
- **Observability** -- Prometheus metrics endpoint, agent traces, Logfire integration

---

## Backend Architecture

The backend lives in `datametronome/podium/datametronome_podium/` and follows a **feature-slice** pattern. Each feature is a self-contained package with up to four files:

```
datametronome_podium/
├── features/
│   ├── staves/        # Data sources
│   │   ├── model.py   # Pydantic domain model
│   │   ├── repo.py    # QueryExecutor-based SQL repository
│   │   ├── router.py  # FastAPI router (endpoints)
│   │   └── schema.py  # Request/Response DTOs
│   ├── clefs/         # Quality check definitions
│   ├── checks/        # Check execution results
│   ├── users/         # User accounts
│   ├── chat/          # Conversation messages
│   ├── workflows/     # Checkpoint + event state
│   ├── traces/        # Agent observability traces
│   ├── scheduler/     # Scheduler job persistence
│   └── analytics/     # Quality analytics queries
├── core/
│   ├── config.py      # Pydantic Settings (env-driven)
│   ├── database.py    # Connection lifecycle, get_executor()
│   ├── query.py       # QueryExecutor (all DB access)
│   ├── query_adapter.py  # SQLite <-> PostgreSQL translation
│   ├── scheduler.py   # APScheduler init + job management
│   ├── middleware.py   # MetricsMiddleware
│   └── rate_limit.py  # slowapi rate limiter
├── services/
│   ├── orchestrator.py    # Multi-agent routing + dispatch
│   ├── agent_factory.py   # Model builder (Anthropic/OpenAI/Gemini/Ollama)
│   ├── agent_tools.py     # 11 tools shared by all agents
│   ├── agents/
│   │   ├── router.py      # RouterAgent (intent classification)
│   │   ├── config.py      # ConfigAgent
│   │   ├── investigation.py  # InvestigationAgent
│   │   └── report.py      # ReportAgent
│   ├── clef_scheduler.py  # Scheduled check execution
│   ├── clef_executor.py   # Check runner
│   ├── workflow_state.py  # Checkpoint CRUD + event logging
│   └── agent_tracing.py   # Trace recording
├── api/
│   ├── deps.py        # get_current_user dependency
│   └── v1/            # API router aggregation
└── main.py            # FastAPI app factory + lifespan
```

### The Feature-Slice Pattern

Each feature follows the same four-file structure:

| File | Responsibility | Example |
|------|---------------|---------|
| `model.py` | Pydantic domain model with validation and business logic | `StaveModel`, `ClefModel` |
| `repo.py` | SQL queries via `QueryExecutor` -- no raw driver calls | `StaveRepo.get_by_id()`, `ClefRepo.list_active()` |
| `router.py` | FastAPI endpoints -- thin controllers that delegate to repos | `POST /staves`, `GET /clefs` |
| `schema.py` | Request/Response DTOs (separate from domain models) | `StaveCreate`, `StaveResponse` |

This separation ensures:
- **Testability** -- repos can be tested with a real `QueryExecutor` against an in-memory SQLite
- **No coupling** -- routers never import models directly, schemas never import repos
- **Consistency** -- every feature follows the same structure, easy to navigate

---

## Database Layer

DataMetronome uses a three-layer abstraction that lets the same application code run unchanged on both SQLite and PostgreSQL.

```mermaid
flowchart LR
    APP["Application Code<br/>(repos, services)"]
    QE["QueryExecutor<br/>query(), execute(), insert()"]
    QA["QueryAdapter<br/>adapt(sql, params)"]
    PULSE["PulseConnector<br/>query_with_params(), execute()"]
    DB[("Database<br/>SQLite or PostgreSQL")]

    APP -->|"SQL with ? placeholders"| QE
    QE -->|"(sql, params)"| QA
    QA -->|"translated SQL"| PULSE
    PULSE -->|"driver call"| DB

    style QE fill:#e1f5fe
    style QA fill:#fff3e0
    style PULSE fill:#e8f5e9
```

### How Placeholder Translation Works

All application SQL uses `?` as the placeholder character. The `QueryAdapter` rewrites these for the active dialect:

```mermaid
flowchart TD
    SQL["SELECT * FROM staves WHERE id = ? AND is_active = ?"]
    ADAPTER{QueryAdapter}

    ADAPTER -->|"dialect = sqlite"| SQLITE["SELECT * FROM staves WHERE id = ? AND is_active = ?<br/>params: ['stave-123', 1]<br/>(booleans converted to 0/1)"]

    ADAPTER -->|"dialect = postgresql"| PG["SELECT * FROM staves WHERE id = $1 AND is_active = $2<br/>params: ['stave-123', True]<br/>(? rewritten to $N)"]

    SQL --> ADAPTER
```

The adapter also handles DDL translation: `JSONB` becomes `TEXT` on SQLite, and `DOUBLE PRECISION` becomes `REAL`.

### QueryExecutor API

```python
# Core operations
await executor.query(sql, params)     # SELECT -> list[dict]
await executor.execute(sql, params)   # INSERT/UPDATE/DELETE -> rows affected
await executor.execute_ddl(sql)       # DDL with type translation

# CRUD helpers (single-table convenience)
await executor.select(table, columns, where, order_by, limit, offset)
await executor.insert(table, data_dict)
await executor.update(table, data_dict, where)
await executor.delete(table, where)

# Transactions
async with executor.transaction():
    await executor.insert("checks", check_data)
    await executor.update("clefs", {"last_run": now}, {"id": clef_id})
```

### Connection Lifecycle

On startup, `database.init_db()` parses the `DATAMETRONOME_DATABASE_URL` environment variable, creates the appropriate PulseConnector (`PostgresPulse` or `SQLitePulse`), wraps it with a `QueryAdapter`, and builds the global `QueryExecutor`:

```python
connector, dialect = await _create_connector(settings.database_url)
adapter = QueryAdapter(dialect)
_executor = QueryExecutor(connector, adapter)
await connector.connect()
```

All application code accesses the database through `get_executor()`.

---

## Data Model

```mermaid
erDiagram
    users {
        text id PK
        text username UK
        text email UK
        text hashed_password
        boolean is_active
        boolean is_superuser
        text created_at
        text updated_at
    }

    staves {
        text id PK
        text name
        text description
        text data_source_type
        text connection_config
        boolean is_active
        text created_at
        text updated_at
    }

    clefs {
        text id PK
        text stave_id FK
        text name
        text description
        text check_type
        text config
        text warn
        text fail
        text retry_config
        text schedule
        boolean is_active
        text created_at
        text updated_at
    }

    checks {
        text id PK
        text stave_id FK
        text clef_id FK
        text check_type
        text status
        text message
        text details
        text timestamp
        float execution_time
        int anomalies_count
        text severity
    }

    anomalies {
        text id PK
        text check_id FK
        text table_name
        text column_name
        text anomaly_type
        text description
        text severity
        text detected_at
        text data_sample
        text resolution_status
    }

    chat_messages {
        text id PK
        text conversation_id
        text user_id FK
        text role
        text content
        text tool_calls
        text tool_results
        text created_at
    }

    agent_traces {
        text id PK
        text conversation_id
        text user_id
        text user_message_preview
        text intent
        text model
        text tool_calls
        float duration_ms
        text created_at
    }

    workflow_checkpoints {
        text id PK
        text conversation_id
        text user_id
        text workflow_name
        text current_node
        jsonb state_data
        text status
        text parent_checkpoint_id FK
        text created_at
        text updated_at
    }

    workflow_events {
        text id PK
        text checkpoint_id FK
        text event_type
        text node_name
        jsonb event_data
        text created_at
    }

    workflow_definitions {
        text id PK
        text name UK
        text description
        jsonb graph_data
        boolean is_active
        text created_at
        text updated_at
    }

    scheduler_jobs {
        text id PK
        text clef_id FK
        text schedule
        boolean enabled
        text last_run_time
        text next_run_time
        int execution_count
        int failure_count
        text created_at
        text updated_at
    }

    job_executions {
        text id PK
        text job_id FK
        text clef_id FK
        text status
        float execution_time
        text error_message
        text started_at
        text completed_at
    }

    staves ||--o{ clefs : "has"
    staves ||--o{ checks : "produces"
    clefs ||--o{ checks : "generates"
    checks ||--o{ anomalies : "detects"
    users ||--o{ chat_messages : "sends"
    workflow_checkpoints ||--o{ workflow_events : "logs"
    workflow_checkpoints ||--o{ workflow_checkpoints : "parent"
    clefs ||--o{ scheduler_jobs : "scheduled by"
    scheduler_jobs ||--o{ job_executions : "tracks"
```

### Key Relationships

- A **stave** (data source) has many **clefs** (quality check definitions)
- A **clef** produces **checks** (execution results) each time it runs
- A **check** may detect **anomalies** in the data
- **Chat messages** belong to conversations and are linked to users
- **Workflow checkpoints** track multi-agent orchestration state, with **events** as an audit trail
- **Scheduler jobs** persist APScheduler state across restarts, with **job executions** tracking each run

---

## Request Flow

A typical authenticated API request follows this path:

```mermaid
sequenceDiagram
    actor Client
    participant MW as Middleware<br/>(Metrics + CORS + Rate Limit)
    participant Router as Feature Router<br/>(e.g. staves/router.py)
    participant Deps as deps.py<br/>get_current_user
    participant Auth as JWT Verification<br/>(python-jose)
    participant Repo as Feature Repo<br/>(e.g. staves/repo.py)
    participant QE as QueryExecutor
    participant QA as QueryAdapter
    participant Pulse as PulseConnector
    participant DB as Database

    Client->>MW: GET /api/v1/staves<br/>Authorization: Bearer <token>
    MW->>Router: forward request
    Router->>Deps: get_current_user(token)
    Deps->>Auth: jwt.decode(token, secret)
    Auth-->>Deps: {sub: "admin"}
    Deps->>QE: query("SELECT * FROM users WHERE username = ?", ["admin"])
    QE->>QA: adapt(sql, params)
    QA-->>QE: (adapted_sql, adapted_params)
    QE->>Pulse: query_with_params(sql, params)
    Pulse->>DB: execute
    DB-->>Pulse: rows
    Pulse-->>QE: list[dict]
    QE-->>Deps: user dict
    Deps-->>Router: current_user
    Router->>Repo: StaveRepo.list(executor)
    Repo->>QE: select("staves", ...)
    QE->>QA: adapt
    QA->>Pulse: query
    Pulse->>DB: SELECT
    DB-->>Pulse: rows
    Pulse-->>QE: list[dict]
    QE-->>Repo: stave dicts
    Repo-->>Router: list[StaveResponse]
    Router-->>MW: JSON response
    MW-->>Client: 200 OK + JSON
```

---

## Scheduling

DataMetronome uses [APScheduler](https://apscheduler.readthedocs.io/) (AsyncIOScheduler) to run clefs on cron schedules.

```mermaid
flowchart TD
    STARTUP["App Startup<br/>lifespan()"] --> INIT["init_scheduler()"]
    INIT --> RESTORE["Restore persisted jobs<br/>from scheduler_jobs table"]
    INIT --> LOAD["load_and_schedule_all_clefs()<br/>from clefs table"]

    RESTORE --> APS["APScheduler<br/>(AsyncIOScheduler)"]
    LOAD --> APS

    APS -->|"cron trigger fires"| EXEC["execute_scheduled_clef(clef_id)"]
    EXEC --> FETCH["Fetch clef + stave<br/>from database"]
    FETCH --> RUNNER["ClefExecutor.execute_clef()"]
    RUNNER --> STORE["Store check result<br/>in checks table"]
    STORE --> RECORD["Record job execution<br/>in job_executions table"]

    RUNNER -->|"failed + retry configured"| RETRY["Exponential backoff<br/>then retry"]
    RETRY --> EXEC
```

### Schedule Configuration

Clefs accept standard 5-field cron expressions or shorthands:

| Shorthand | Cron Expression | Meaning |
|-----------|----------------|---------|
| `@hourly` | `0 * * * *` | Every hour at minute 0 |
| `@daily` | `0 0 * * *` | Every day at midnight |
| `@weekly` | `0 0 * * 0` | Every Sunday at midnight |
| `@monthly` | `0 0 1 * *` | First of each month |
| `*/5 * * * *` | (as-is) | Every 5 minutes |

### Scheduler Settings

```bash
DATAMETRONOME_SCHEDULER_ENABLED=true
DATAMETRONOME_SCHEDULER_TIMEZONE=UTC
DATAMETRONOME_SCHEDULER_MAX_INSTANCES=3   # max concurrent runs of same job
DATAMETRONOME_SCHEDULER_MAX_WORKERS=10    # threadpool size for sync tasks
```

---

## Authentication

DataMetronome uses JWT (JSON Web Tokens) with bcrypt password hashing.

```mermaid
sequenceDiagram
    actor User
    participant API as POST /api/v1/auth/login
    participant Auth as Auth Module
    participant DB as Database

    User->>API: {username, password}
    API->>DB: SELECT * FROM users WHERE username = ?
    DB-->>API: user record
    API->>Auth: verify_password(password, hashed_password)
    Auth-->>API: valid

    API->>Auth: create_access_token({sub: username}, expires)
    Auth-->>API: JWT token (HS256)
    API-->>User: {access_token, token_type: "bearer"}

    Note over User,DB: Subsequent requests

    User->>API: GET /api/v1/staves<br/>Authorization: Bearer <jwt>
    API->>Auth: jwt.decode(token, SECRET_KEY, HS256)
    Auth-->>API: {sub: "admin"}
    API->>DB: SELECT * FROM users WHERE username = ?
    DB-->>API: user record
    API-->>User: 200 OK (authorized)
```

### Security Configuration

```bash
DATAMETRONOME_SECRET_KEY=<random-32+-char-string>
DATAMETRONOME_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

The secret key must be at least 32 characters. The default is only suitable for development.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Nuxt 3 (Vue 3) | SPA dashboard, chat interface |
| API | FastAPI 0.104+ | REST endpoints, OpenAPI docs |
| Validation | Pydantic v2 | Settings, schemas, domain models |
| AI Framework | Pydantic AI | Multi-agent orchestration |
| Auth | python-jose + passlib | JWT tokens, bcrypt hashing |
| Scheduler | APScheduler | Cron-based check execution |
| Rate Limiting | slowapi | Per-endpoint rate limits |
| Metrics | prometheus-client | /metrics endpoint |
| Observability | Logfire (optional) | Distributed tracing |
| Database (prod) | PostgreSQL + asyncpg | Primary data store |
| Database (dev) | SQLite + aiosqlite | Zero-config development |
| Containerization | Docker + docker-compose | Development and deployment |

---

## Deployment

### Docker Compose (Development)

```mermaid
graph LR
    subgraph "docker-compose"
        UI["ui-nuxt<br/>:3000"]
        API["podium<br/>:8001"]
        DB[("PostgreSQL<br/>:5432")]
    end

    DEV["Developer"] --> UI
    DEV --> API
    UI -->|HTTP| API
    API -->|asyncpg| DB
```

### Application Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Starting: uvicorn start
    Starting --> DBInit: init_db()
    DBInit --> SchedulerInit: init_scheduler()
    SchedulerInit --> Running: lifespan yield
    Running --> ShuttingDown: SIGTERM
    ShuttingDown --> SchedulerStop: shutdown_scheduler()
    SchedulerStop --> DBClose: close_db()
    DBClose --> [*]
```

The `lifespan()` context manager in `main.py` handles startup (database init, scheduler init) and shutdown (scheduler stop, database close) in the correct order.

---

**Last Updated**: March 2026
