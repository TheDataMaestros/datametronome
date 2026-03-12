# PostgreSQL Migration + Agent State Design

**Goal:** Migrate DataMetronome from SQLite to PostgreSQL as the default database, add a connector-agnostic abstraction layer, introduce a custom migration system, and add LangGraph-style agent state tables (checkpoints, workflow definitions, event log).

**Branch:** `feat/agents/multi-orchestration-agents` (continues from pydantic-ai migration)

---

## Architecture Overview

```
database_url ──► Connector Factory ──► PostgresPulse (default)
                                   └── SQLitePulse (fallback)
                                         │
                                    QueryAdapter
                                   (? → $1, bools, types)
                                         │
                              ┌──────────┼──────────┐
                              │          │          │
                         Migration    get_db()   workflow_state.py
                          Runner        │          │
                            │      agent_tools  orchestrator
                         sql/*.sql   services    (checkpoint +
                                     endpoints    event wiring)
```

---

## Component 1: Query Adapter

**File:** `core/query_adapter.py`

A stateless utility that translates SQL between SQLite and PostgreSQL dialects.

**Responsibilities:**
- Placeholder rewriting: `?` → `$1, $2, $3...` for PostgreSQL (no-op for SQLite)
- Boolean literal translation: `1/0` → `TRUE/FALSE` for PostgreSQL at query time
- Type mapping in DDL: `REAL` → `DOUBLE PRECISION`, `JSONB` → `TEXT` (for SQLite only)
- `adapt(sql, params, dialect)` → `(adapted_sql, adapted_params)`

**Dialect detection:** Based on a string enum (`"postgresql"` or `"sqlite"`) derived from the database URL at connector creation time.

**Consumers:** Only `database.py` uses it internally. All other code writes SQL with `?` placeholders and doesn't know which dialect is active.

---

## Component 2: Connector Factory + Database Layer

**File:** `core/database.py` (rewritten)

**Connector Factory** — `_create_connector(database_url)`:
- `postgresql://...` → `PostgresPulse` (from `metronome_pulse_postgres`, asyncpg-based)
  - URL is parsed via `urllib.parse.urlparse` to extract host, port, database, user, password (PostgresPulse takes individual params, not a URL string)
- `sqlite:///...` or `sqlite+aiosqlite:///...` → `SQLitePulse` (from `metronome_pulse_sqlite`)

**Connector normalization layer:**

SQLitePulse and PostgresPulse have incompatible method signatures despite sharing method names. `database.py` normalizes these differences:

- **`execute(sql, params)`**: SQLitePulse takes params as a list. PostgresPulse takes `*args` (variadic). The normalization layer splats the list for PostgreSQL: `connector.execute(sql, *params)`.
- **`query()`**: Both accept `{"sql": ..., "params": [...]}` dict format. PostgresPulse dispatches this as `type="custom"` internally and splats params. This works but must be tested.
- **`write()`**: SQLitePulse returns a bool. PostgresPulse returns None. The normalization layer wraps PostgresPulse's write to return `True` on success (no exception) and `False` on failure.
- **`write()` dict format**: Current code passes `{"table": "users", **data}` — the `"table"` key must be stripped before insert to avoid it being treated as a column. The normalization layer handles this.

**Global state:**
- `connector` replaces `sqlite_connector` (generic name)
- `dialect` stores `"postgresql"` or `"sqlite"`
- `get_db()`, `init_db()`, `close_db()` remain the public API
- Helper functions (`execute_query`, `execute_write`, `insert_data`, `update_data`, `delete_data`) remain but route through the query adapter and normalization layer

**`init_db()` becomes:**
1. Create connector via factory
2. Run migration runner (replaces inline `_create_tables()`)
3. Create default admin user

**Cleanup:** Remove `_agent_log`, debug prints, and inline DDL from `database.py`.

---

## Component 3: Migration System

**Package:** `core/migrations/`

### Runner (`core/migrations/runner.py`)

~50 lines. Responsibilities:
- Ensure `schema_migrations` table exists (columns: `id`, `filename`, `applied_at`)
- Scan `sql/` directory for `*.sql` files, sorted by numeric prefix
- Apply any migration not yet recorded in `schema_migrations`
- Uses the DataPulse connector from `get_db()` + `QueryAdapter` for dialect compatibility
- Called by `init_db()` — replaces `_create_tables()`

### SQL Files (`core/migrations/sql/`)

Migration files are written in **PostgreSQL dialect** as the primary. The QueryAdapter translates for SQLite when needed (placeholders, `JSONB` → `TEXT`, `DOUBLE PRECISION` → `REAL`). DDL uses `CREATE TABLE IF NOT EXISTS` for idempotency.

Each migration runs inside a **transaction**. If any statement fails, the entire migration rolls back and the runner stops with an error. No down/rollback migrations — this is a known limitation; manual intervention is required to undo a migration.

**`001_initial_schema.sql`** — all existing tables:
- `users`, `staves`, `clefs`, `checks`, `scheduler_jobs`, `job_executions`, `anomalies`, `chat_messages`, `agent_traces`
- All existing indexes

**`002_agent_state.sql`** — new workflow tables (see Component 4)

---

## Component 4: Agent State Tables

### `workflow_checkpoints`

Saves/restores orchestrator execution state for pause/resume.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| conversation_id | TEXT NOT NULL | |
| user_id | TEXT NOT NULL | |
| workflow_name | TEXT NOT NULL | e.g. "chain:investigation→report" |
| current_node | TEXT | Which agent/step is active |
| state_data | JSONB (PG) / TEXT (SQLite) | Intermediate outputs, routing decision, context |
| status | TEXT NOT NULL | running, paused, completed, failed |
| parent_checkpoint_id | TEXT | Nullable FK to self, for nested workflows |
| created_at | TEXT NOT NULL | |
| updated_at | TEXT NOT NULL | |

Indexes: `(conversation_id)`, `(status)`

### `workflow_definitions`

Reusable graph-like pipeline templates (schema-ready, not wired into orchestrator yet).

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| name | TEXT UNIQUE NOT NULL | |
| description | TEXT | |
| graph_data | JSONB (PG) / TEXT (SQLite) | Nodes, edges, conditions as JSON |
| is_active | BOOLEAN DEFAULT TRUE | |
| created_at | TEXT NOT NULL | |
| updated_at | TEXT NOT NULL | |

### `workflow_events`

Full audit trail — every state transition recorded.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | UUID |
| checkpoint_id | TEXT NOT NULL | FK → workflow_checkpoints |
| event_type | TEXT NOT NULL | node_entered, node_completed, tool_called, decision_made, error, human_input_requested |
| node_name | TEXT | Which agent/step |
| event_data | JSONB (PG) / TEXT (SQLite) | Inputs, outputs, tool results, error details |
| created_at | TEXT NOT NULL | |

Index: `(checkpoint_id, created_at)`

---

## Component 5: Workflow State Service

**File:** `services/workflow_state.py`

Thin service layer between orchestrator and state tables.

**Functions:**
- `create_checkpoint(conversation_id, user_id, workflow_name)` → checkpoint_id
- `update_checkpoint(checkpoint_id, current_node, state_data, status)`
- `load_checkpoint(checkpoint_id)` → checkpoint dict
- `find_active_checkpoint(conversation_id)` → latest running/paused checkpoint or None
- `log_event(checkpoint_id, event_type, node_name, event_data)`

All functions are async, use `get_db()` + `execute_query`/`insert_data` from `database.py`.

---

## Component 6: Orchestrator Wiring

**File:** `services/orchestrator.py` (modified, additive)

`run_chat()` gains state awareness:
1. Check for active paused checkpoint via `find_active_checkpoint(conversation_id)` → resume
2. If none, `create_checkpoint(conversation_id, user_id, workflow_name)`
3. Before each agent dispatch → `log_event("node_entered", ...)` + `update_checkpoint(current_node=...)`
4. After each agent returns → `log_event("node_completed", ..., event_data={output})` + update `state_data`
5. On completion → `update_checkpoint(status="completed")`
6. On error → `log_event("error", ...)` + `update_checkpoint(status="failed")`

**Signature change:** `run_chat()` needs `conversation_id` and `user_id` parameters (passed from `chat.py`).

**Modified file:** `api/v1/endpoints/chat.py` — update `run_chat()` call to pass `conversation_id` and `user_id` (both values already available in scope).

`_run_chain` and `_run_parallel` each log their transitions.

**Workflow definitions** are not wired yet — schema-ready for future API-driven pipeline creation.

---

## Infrastructure Changes

**`docker-compose.yml`:**
- Change podium's `DATAMETRONOME_DATABASE_URL` to `postgresql://testuser:testpass@postgres:5432/datametronome_test`

**`core/config.py`:**
- Change `database_url` default from `sqlite:///./data/datametronome.db` to `postgresql://testuser:testpass@localhost:5432/datametronome_test`

**`requirements.txt`:**
- Add `metronome-pulse-postgres` (if not already present)

**`env.example`:**
- Create this file (does not currently exist) with PostgreSQL default URL and AI config vars

---

## What Stays From Original Chunk 4

- Commit chunk 3 (uncommitted pydantic-ai work)
- End-to-end verification (adapted for PostgreSQL)
- `env.example` update

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Default DB | PostgreSQL | User preference, production-ready from start |
| SQLite support | Kept as fallback | Connector-agnostic layer supports both |
| PostgreSQL driver | asyncpg via DataPulse | Fastest async driver, existing connector available |
| Migration tool | Custom runner | No SQLAlchemy dependency, uses existing DataPulse connector, ~50 lines |
| Agent state | 3 tables (checkpoints, definitions, events) | Full LangGraph-equivalent: pause/resume, declarative workflows, audit trail |
| JSONB vs TEXT | JSONB on PG, TEXT on SQLite | Queryable JSON on PG, simple fallback on SQLite |
| Timestamps | TEXT (matching existing tables) | Consistency with existing schema; migrate to TIMESTAMPTZ as a future improvement |
| No rollback migrations | Forward-only, transactions per migration | Simplicity for ~50-line runner; manual intervention if needed |
| Status/type constraints | No CHECK constraints on workflow status/event_type | Flexibility; application-level validation in workflow_state.py |
| Connection pooling | PostgresPulse defaults (asyncpg pool) | Sufficient for now; expose pool config in config.py as a future improvement |
