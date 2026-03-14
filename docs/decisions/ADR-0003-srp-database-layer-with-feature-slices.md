# ADR-0003: SRP Database Layer with Feature Slices

## Status

Implemented

## Context

The original codebase had a monolithic `database.py` exceeding 500 lines that mixed connection management, query execution, SQL dialect translation, and table CRUD operations into a single file. Models were scattered between a `models/` directory and inline definitions in service files. API endpoints performed raw SQL inline, creating tight coupling between the HTTP layer and the database.

This made the codebase hard to test in isolation -- testing a single feature required standing up the entire database layer. It was hard to extend -- adding a new domain concept meant touching multiple unrelated files. And it created implicit dependencies that made refactoring risky.

The project needed a clear separation of concerns in the database layer and a consistent structure for organizing domain logic so that each feature could be developed, tested, and maintained independently.

## Decision

Refactor into a **Single Responsibility Principle (SRP) database layer** with a **feature-slice architecture**:

**Core layer** (3 focused classes):

1. **QueryExecutor** (`core/query.py`) -- Single class for all database access. Uses `?` placeholders everywhere, regardless of the underlying database.
2. **QueryAdapter** (`core/query_adapter.py`) -- Translates `?` placeholders to database-specific syntax (`$1` for PostgreSQL) and handles type mapping (e.g., `JSONB` to `TEXT` for SQLite).
3. **PulseConnector** (`core/database.py`) -- Connection lifecycle only. Creates a `PostgresPulse` or `SQLitePulse` instance based on the database URL.

**Feature slices** (`features/{name}/`) -- Each domain has 4 files:

- `model.py` -- Pydantic domain model (the canonical representation)
- `repo.py` -- SQL repository using QueryExecutor (all queries live here)
- `router.py` -- FastAPI router (thin controller, no business logic)
- `schema.py` -- Request/Response DTOs (decoupled from domain models)

Feature slices created: staves, clefs, checks, users, chat, workflows, traces, scheduler, analytics (9 total).

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| SQLAlchemy ORM | Would require rewriting all SQL and adding a model mapping layer. The project uses raw SQL intentionally for performance and control. |
| Keep monolithic `database.py` | Growing unmaintainable, mixing 4+ concerns in one file |
| Django-style apps | Too opinionated for a FastAPI project, would fight the framework |
| Repository pattern without feature slices | Would still leave models and routers scattered across the codebase |

## Consequences

**Pros:**
- Each feature is self-contained and independently testable
- QueryExecutor is the single entry point for all database access, making it easy to audit and mock
- Same application code runs on both SQLite (dev) and PostgreSQL (prod) via QueryAdapter
- 274 tests passing after the full refactor with no regressions
- New features follow a predictable 4-file pattern that reduces onboarding friction

**Cons:**
- More files to navigate (4 per feature x 9 features = 36 new files)
- Some duplication in boilerplate across repos (each has similar CRUD patterns)
- Complex endpoints (auth, chat actions, scheduler) still live outside the feature-slice structure

## References

- Design spec: `docs/superpowers/specs/2026-03-13-srp-database-layer-design.md`
- Plan: `docs/superpowers/plans/2026-03-13-srp-database-layer.md`
- Branch: `feat/agents/multi-orchestration-agents`
