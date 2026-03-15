# ADR-0004: PulseProtocol for Database-Agnostic Connectors

## Status

Implemented

## Context

DataMetronome connects to two categories of databases. First, its own application database -- PostgreSQL in production, SQLite in development. Second, customer databases being monitored (called "staves"), which can be PostgreSQL, MySQL, MongoDB, BigQuery, or other engines.

The check executor (ClefExecutor) needs to run validation queries against any of these databases without knowing or caring which engine is behind the connection. Similarly, background workers need isolated database sessions for the app database that follow the same lifecycle patterns. Without a unified interface, each new database type would require conditional logic throughout the codebase.

The project needed a connector interface that guaranteed a consistent API across all database types while keeping each connector thin -- a lightweight wrapper around native async drivers rather than a heavy abstraction layer.

## Decision

Define a **PulseProtocol** as a `@runtime_checkable Protocol` class that all database connectors must implement. Each connector lives in its own installable package (`metronome-pulse-postgres`, `metronome-pulse-sqlite`, etc.).

The protocol defines four groups of methods:

- **Lifecycle:** `connect()`, `close()`, `__aenter__()` / `__aexit__()` (async context manager)
- **Read:** `query()`, `query_with_params()`
- **Write:** `execute()`, `execute_many()`, `write()`
- **Introspection:** `list_tables()`, `get_table_info()`
- **Transactions:** `begin_transaction()`, `commit_transaction()`, `rollback_transaction()`

The same `async with connector:` pattern works for both the app database session (used by workers via `worker_db_session()`) and customer database connections (used by ClefExecutor to run checks). This means a worker creating an isolated session and a check running against a customer database use identical code paths.

Connectors implemented so far:

- `metronome-pulse-postgres` -- asyncpg-based, supports connection pooling
- `metronome-pulse-sqlite` -- aiosqlite-based, used in development and tests
- `metronome-pulse-bigquery` -- google-cloud-bigquery, for monitored BigQuery datasets

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| SQLAlchemy as the universal connector | Adds ORM overhead. Connectors need to be thin wrappers around native async drivers for performance. |
| No protocol, just duck typing | Loses IDE support and autocompletion. Makes it easy to ship incomplete connectors that fail at runtime. |
| Single monolithic connector package | Mixing all driver code in one package creates unnecessary dependencies (e.g., installing the BigQuery SDK just to use PostgreSQL). |

## Consequences

**Pros:**
- Adding a new connector means implementing PulseProtocol and publishing a package -- no changes to core code
- ClefExecutor doesn't need to know which database type it's checking
- Async context manager guarantees connection cleanup even on exceptions
- Workers can create isolated sessions via `async with connector:` without manual lifecycle management
- `@runtime_checkable` enables `isinstance()` checks to validate connectors at startup

**Cons:**
- Each connector is a separate package to version and maintain
- Python's `Protocol` can't enforce async method behavior at type-check time -- only at runtime via `@runtime_checkable`
- Connector authors need to understand the full protocol surface (11+ methods) to implement a new backend

## References

- Protocol definition: `datametronome/pulse/core/metronome_pulse_core/protocol.py`
- Postgres connector: `datametronome/pulse/postgres/`
- Worker DB session: `datametronome/podium/datametronome_podium/core/worker_db.py`
- Branch: `feat/agents/multi-orchestration-agents`
