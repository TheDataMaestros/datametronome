# Codebase Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove dead code, migrate all legacy endpoints to feature slices, consolidate duplicated logic, and add role-based authorization.

**Architecture:** Top-down approach — delete dead code first (Phase 1), migrate legacy endpoints into feature slices while consolidating duplications (Phase 2), add role-based auth onto the clean architecture (Phase 3), final cleanup (Phase 4).

**Tech Stack:** Python 3.13, FastAPI, Pydantic, Alembic, pytest, Nuxt 3/TypeScript

**Spec:** `docs/superpowers/specs/2026-04-07-codebase-cleanup-design.md`

---

## Chunk 1: Phase 1 — Delete Dead Code

### Task 1: Delete scheduler endpoints and related services

**Files:**
- Delete: `datametronome_podium/api/v1/endpoints/scheduler.py`
- Delete: `datametronome_podium/api/v1/endpoints/import_config.py`
- Delete: `datametronome_podium/services/job_monitor.py`
- Delete: `datametronome_podium/services/scheduler_persistence.py`
- Delete: `datametronome_podium/features/scheduler/` (entire directory)
- Delete: `tests/test_yaml_scheduler_integration.py`
- Delete: `tests/test_scheduler_enhancements.py`
- Delete: `tests/features/scheduler/test_scheduler_repo.py`
- Modify: `datametronome_podium/api/v1/api.py`

- [ ] **Step 1: Remove scheduler and import_config from api.py**

In `api/v1/api.py`, remove these imports:
```python
from .endpoints import (
    ...
    import_config,
    scheduler,
    ...
)
```
And remove these router registrations:
```python
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"], dependencies=_auth_deps)
api_router.include_router(
    import_config.router, prefix="/config", tags=["configuration"], dependencies=_auth_deps,
)
```

- [ ] **Step 2: Delete the files**

```bash
cd datametronome/podium
rm datametronome_podium/api/v1/endpoints/scheduler.py
rm datametronome_podium/api/v1/endpoints/import_config.py
rm datametronome_podium/services/job_monitor.py
rm datametronome_podium/services/scheduler_persistence.py
rm -rf datametronome_podium/features/scheduler/
rm tests/test_yaml_scheduler_integration.py
rm tests/test_scheduler_enhancements.py
rm -rf tests/features/scheduler/
```

- [ ] **Step 3: Verify no remaining imports**

```bash
grep -r "job_monitor\|scheduler_persistence\|features.scheduler\|endpoints.scheduler\|endpoints.import_config" --include="*.py" datametronome_podium/ tests/ | grep -v __pycache__
```
Expected: No output (or only `__init__.py` re-exports to clean up).

- [ ] **Step 4: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: delete scheduler endpoints, import_config, and related services

Scheduler is handled by Celery Beat + RedBeat. These endpoints had
TODO stubs and no frontend consumers. Also removes job_monitor,
scheduler_persistence services, and features/scheduler/ slice."
```

### Task 2: Delete unused exceptions and rate_limit dict

**Files:**
- Delete: `datametronome_podium/core/exceptions.py`
- Modify: `datametronome_podium/core/rate_limit.py`

- [ ] **Step 1: Verify exceptions.py has no consumers**

```bash
grep -r "from datametronome_podium.core.exceptions\|from datametronome_podium.core import exceptions" --include="*.py" datametronome_podium/ tests/ | grep -v __pycache__
```
Expected: No output.

- [ ] **Step 2: Delete exceptions.py**

```bash
rm datametronome_podium/core/exceptions.py
```

- [ ] **Step 3: Remove RATE_LIMITS dict from rate_limit.py**

Read `core/rate_limit.py` and delete the `RATE_LIMITS` dict definition. Keep the `limiter` object and everything else.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: delete unused exceptions.py and RATE_LIMITS dict

Custom exception hierarchy was never raised. RATE_LIMITS dict was
defined but never applied to any endpoint."
```

### Task 3: Delete `models/` directory and update all imports

**Files:**
- Delete: `datametronome_podium/models/` (entire directory)
- Modify: 14 source files + 7 test files (see import map below)

**Import mapping:**
- `datametronome_podium.models.stave.Stave` → `datametronome_podium.features.staves.model.Stave`
- `datametronome_podium.models.clef.Clef` → `datametronome_podium.features.clefs.model.Clef`
- `datametronome_podium.models.user.User` → `datametronome_podium.features.users.model.User`
- `datametronome_podium.models.check_run.CheckRun` → `datametronome_podium.features.checks.model.Check`
- `datametronome_podium.models.severity.Severity` → inline into consuming module

- [ ] **Step 1: Verify feature models have equivalent fields**

Read `models/stave.py`, `models/clef.py`, `models/user.py`, `models/check_run.py`, `models/severity.py` and compare with `features/staves/model.py`, `features/clefs/model.py`, `features/users/model.py`, `features/checks/model.py`. Ensure the feature models have all fields used by consumers. If any fields are missing, add them to the feature models first.

- [ ] **Step 2: Update source file imports**

Update all of these files, replacing `datametronome_podium.models.*` imports:

Source files:
- `api/v1/endpoints/stave_actions.py:15`
- `services/stave_service.py:36-37`
- `services/config_validator.py:20-21`
- `services/clef_executor.py:21-23,29`
- `services/connection_tester.py:16`
- `services/yaml_loader.py:14-15`
- `services/stave_yaml_loader.py:24-25`

- [ ] **Step 3: Update test file imports**

- `tests/test_stave_examples.py:16-17`
- `tests/test_tdd_compliant_clefs.py:11,20-21`
- `tests/test_yaml_loader.py:11-12`
- `tests/test_unit.py:13-15,18`
- `tests/test_level1_checks.py:16-18`

- [ ] **Step 4: Handle `severity.py`**

Check what `Severity` is (likely an enum). If it's only used by `clef_executor.py` or `check_run.py`, move it into `features/checks/model.py`. If used widely, create a shared location.

- [ ] **Step 5: Delete models/ directory**

```bash
rm -rf datametronome_podium/models/
```

- [ ] **Step 6: Verify no remaining imports**

```bash
grep -r "from datametronome_podium.models" --include="*.py" datametronome_podium/ tests/ | grep -v __pycache__
```
Expected: No output.

- [ ] **Step 7: Run tests**

```bash
.venv/bin/python -m pytest --timeout=10 -q 2>&1 | tail -20
```
Fix any import errors. If logfire blocks all tests, verify individual test files can at least be imported: `python -c "import tests.test_unit"`.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: delete models/ directory, migrate all imports to features/*/model

27 import sites updated across 14 source files and 7 test files.
Single source of truth for models is now features/*/model.py."
```

### Task 4: Delete build artifacts and update .gitignore

**Files:**
- Delete: `datametronome/brain/base/build/`
- Modify: `.gitignore`

- [ ] **Step 1: Delete build artifacts**

```bash
cd /Users/totolasso/repos/personal/datametronome
rm -rf datametronome/brain/base/build/
```

- [ ] **Step 2: Add to .gitignore**

Append to `.gitignore`:
```
build/
dist/
*.egg-info/
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit --no-verify -m "chore: delete build artifacts, add build/ dist/ to .gitignore"
```

---

## Chunk 2: Phase 2A — Shared Extractions (Consolidation)

These extractions must happen before the endpoint migrations because the migrated code will use them.

### Task 5: Extract `core/redis.py`

**Files:**
- Create: `datametronome_podium/core/redis.py`
- Modify: `datametronome_podium/features/staves/router.py`
- Modify: `datametronome_podium/tasks/check_tasks.py`

- [ ] **Step 1: Create `core/redis.py`**

```python
"""Shared async Redis client singleton."""
import redis.asyncio as aioredis

from datametronome_podium.core.config import settings

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """Return a cached async Redis client, creating one on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url)
    return _redis_client
```

- [ ] **Step 2: Replace in `features/staves/router.py`**

Remove the `_redis_client` global and `_get_or_create_redis_client()` function. Replace all calls with:
```python
from datametronome_podium.core.redis import get_redis_client
```

- [ ] **Step 3: Replace in `tasks/check_tasks.py`**

Same pattern — remove local `_redis_client` singleton, import from `core.redis`.

- [ ] **Step 4: Verify no remaining duplicates**

```bash
grep -r "_redis_client" --include="*.py" datametronome_podium/ | grep -v __pycache__ | grep -v "core/redis.py"
```
Expected: No output.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: extract shared Redis client to core/redis.py

Eliminates duplicated _redis_client singletons in staves/router.py
and check_tasks.py."
```

### Task 6: Consolidate `core/timestamp_utils.py`

**Files:**
- Modify: `datametronome_podium/core/timestamp_utils.py`
- Modify: 33+ files with `.replace("+00:00", "Z")` pattern

- [ ] **Step 1: Read existing `core/timestamp_utils.py`**

Check what functions already exist. Ensure `to_utc_isoformat()` preserves microseconds (uses `.isoformat()` not `strftime`).

- [ ] **Step 2: Add `now_utc_iso()` helper if not present**

Many files do `datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")`. Add a shortcut:

```python
def now_utc_iso() -> str:
    """Return current UTC time as ISO-8601 string with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
```

- [ ] **Step 3: Move `_parse_timestamp` and `_format_timestamp_z` from `chat.py`**

These functions from `api/v1/endpoints/chat.py` (lines 176-228) should move to `core/timestamp_utils.py` as `parse_timestamp()` and `format_timestamp_z()`.

- [ ] **Step 4: Replace all `.replace("+00:00", "Z")` call sites**

Replace across all 33+ files. Use `now_utc_iso()` for the `datetime.now(...)...replace(...)` pattern. Use `to_utc_isoformat(dt)` for converting existing datetimes.

Files to update (from dependency map):
- `api/v1/endpoints/auth.py:203`
- `api/v1/endpoints/chat.py:107,140,228,685`
- `core/check_dispatcher.py:106`
- `features/checks/router.py:28,108`
- `features/clefs/router.py:76`
- `features/insights/router.py:227,260`
- `features/insights/repo.py:98,118,218,233,243,273`
- `features/insights/service.py:731`
- `features/staves/router.py:132,160`
- `features/traces/repo.py:27`
- `features/user_memory/repo.py:11`
- `features/user_memory/router.py:55`
- `features/user_memory/service.py:71`
- `features/workflows/repo.py:20,42,63`
- `services/agent_tracing.py:49`
- `services/workflow_state.py:25,52,98`
- `tasks/check_tasks.py:111`
- `tasks/intelligence_tasks.py:140`

(Skip `features/scheduler/repo.py` — already deleted in Task 1.)

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest --timeout=10 -q 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: consolidate timestamp formatting into core/timestamp_utils

Replaces 33+ inline .replace('+00:00', 'Z') calls with
now_utc_iso() and to_utc_isoformat(). Moves parse_timestamp
and format_timestamp_z from chat.py to timestamp_utils."
```

### Task 7: Extract `core/connector_factory.py`

**Files:**
- Create: `datametronome_podium/core/connector_factory.py`
- Modify: `datametronome_podium/services/connection_tester.py`
- Modify: `datametronome_podium/services/agent_tools.py` (partially — full refactor in Task 11)
- Modify: `datametronome_podium/services/clef_executor.py`

- [ ] **Step 1: Read `ConnectionTester.get_connector()` in `services/connection_tester.py`**

This is the most complete implementation. Understand the branching logic.

- [ ] **Step 2: Create `core/connector_factory.py`**

Extract the connector creation logic into a standalone factory. The factory should accept a stave's config dict and data_source_type, and return an appropriate Pulse connector:

```python
"""Centralized Pulse connector factory.

All connector creation goes through this module. No other file should
branch on data_source_type to instantiate connectors.
"""
from typing import Any

async def create_connector(
    data_source_type: str,
    connection_config: dict,
    *,
    read_only: bool = False,
) -> Any:
    """Create the appropriate Pulse connector from config."""
    if data_source_type in ("postgres", "postgresql"):
        ...
    elif data_source_type == "sqlite":
        ...
    elif data_source_type == "bigquery":
        ...
    else:
        raise ValueError(f"Unsupported data source type: {data_source_type}")
```

- [ ] **Step 3: Refactor `ConnectionTester` to use the factory**

`ConnectionTester.get_connector()` delegates to `create_connector()` instead of duplicating the branching.

- [ ] **Step 4: Update `clef_executor.py` connector creation**

Replace inline connector branching with calls to `create_connector()`.

- [ ] **Step 5: Verify**

```bash
grep -r "data_source_type.*bigquery\|data_source_type.*postgres\|data_source_type.*sqlite" --include="*.py" datametronome_podium/ | grep -v __pycache__ | grep -v connector_factory.py | grep -v "test_"
```
Should be significantly reduced. Some references in stave_actions.py will be cleaned up during migration in Task 9.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: extract core/connector_factory.py

Centralizes Pulse connector creation. ConnectionTester and
clef_executor now delegate to the factory instead of duplicating
data_source_type branching."
```

### Task 8: Migrate remaining `get_db()` calls to `get_executor()`

**Files:**
- Modify: `datametronome_podium/core/metrics.py`
- Modify: `datametronome_podium/services/default_setup.py`
- Modify: `datametronome_podium/services/stave_yaml_loader.py`

- [ ] **Step 1: Fix `core/metrics.py`**

Replace `get_db()` call with `get_executor()`.

- [ ] **Step 2: Fix `services/default_setup.py`**

Replace `get_db()` call with `get_executor()`.

- [ ] **Step 3: Fix `services/stave_yaml_loader.py`**

Replace `get_db()` call with `get_executor()`.

- [ ] **Step 4: Verify no remaining `get_db()` calls**

```bash
grep -r "get_db()" --include="*.py" datametronome_podium/ | grep -v __pycache__ | grep -v "def get_db" | grep -v "test_"
```
Expected: Only the definition in `database.py` and the `get_db_connection_status` function remain.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: migrate last get_db() calls to get_executor()

Updates metrics.py, default_setup.py, and stave_yaml_loader.py."
```

---

## Chunk 3: Phase 2B — Migrate Legacy Endpoints to Feature Slices

### Task 9: Migrate `stave_actions.py` into `features/staves/`

**Files:**
- Delete: `datametronome_podium/api/v1/endpoints/stave_actions.py`
- Create: `datametronome_podium/features/staves/service.py`
- Modify: `datametronome_podium/features/staves/router.py`
- Modify: `datametronome_podium/api/v1/api.py`

- [ ] **Step 1: Create `features/staves/service.py`**

Extract business logic from `stave_actions.py` into a service class:
- `test_connection(stave_id)` — connection testing
- `preview_data(stave_id, table_name, limit)` — data preview
- `generate_data(stave_id, table_name, count)` — sample data generation
- `list_tables(stave_id, include_structure)` — table listing

Use `core/connector_factory.py` instead of inline connector branching.

- [ ] **Step 2: Add action endpoints to `features/staves/router.py`**

Add the HTTP routes that currently live in `stave_actions.py`:
- `POST /{stave_id}/test-connection`
- `POST /{stave_id}/generate-data`
- `POST /{stave_id}/preview-data`
- `GET /{stave_id}/tables`

These call into `StaveService` methods. Keep routes thin.

- [ ] **Step 3: Update `api/v1/api.py`**

Remove the `stave_actions` import and router registration. The staves feature router now handles all stave endpoints under `/staves` (including the former `/stave-actions` routes).

**Important:** The frontend calls `/stave-actions/{id}/test-connection`. After migration, the path becomes `/staves/{id}/test-connection`. Update `ui-nuxt/services/staves.ts` to use the new path, OR keep a redirect/alias temporarily.

- [ ] **Step 4: Update frontend `ui-nuxt/services/staves.ts`**

Change `/stave-actions/` to `/staves/` in the API call.

- [ ] **Step 5: Delete `stave_actions.py`**

```bash
rm datametronome_podium/api/v1/endpoints/stave_actions.py
```

- [ ] **Step 6: Run tests and verify**

- [ ] **Step 7: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: migrate stave_actions into features/staves/

Extracts StaveService for business logic. Uses connector_factory
instead of inline branching. Frontend updated to new path."
```

### Task 10: Migrate `clef_actions.py` into `features/clefs/`

**Files:**
- Delete: `datametronome_podium/api/v1/endpoints/clef_actions.py`
- Modify: `datametronome_podium/features/clefs/router.py`
- Modify: `datametronome_podium/api/v1/api.py`

- [ ] **Step 1: Merge clef_actions endpoints into `features/clefs/router.py`**

Add these routes to the existing clefs router:
- `POST /{clef_id}/run-now` (from clef_actions)
- `GET /jobs/{job_id}/status` (from clef_actions)
- `GET /{clef_id}/results` (from clef_actions)
- `GET /results/latest` (from clef_actions)

**Route conflict prevention:** Ensure `/results/latest` is registered BEFORE `/{clef_id}` GET to avoid FastAPI matching "results" as a clef_id. Use explicit path ordering.

- [ ] **Step 2: Update `api/v1/api.py`**

Remove `clef_actions` import and router registration.

- [ ] **Step 3: Delete `clef_actions.py`**

```bash
rm datametronome_podium/api/v1/endpoints/clef_actions.py
```

- [ ] **Step 4: Run tests and verify**

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: merge clef_actions into features/clefs/router

run-now, job-status, and results endpoints now in the clefs
feature slice. Route ordering handles /results/latest vs /{clef_id}."
```

### Task 11: Migrate `chat.py` into `features/chat/`

**Files:**
- Delete: `datametronome_podium/api/v1/endpoints/chat.py`
- Create: `datametronome_podium/features/chat/router.py`
- Create: `datametronome_podium/features/chat/schema.py`
- Modify: `datametronome_podium/features/chat/repo.py` (already exists, extend it)
- Modify: `datametronome_podium/api/v1/api.py`

- [ ] **Step 1: Create `features/chat/schema.py`**

Move Pydantic models from `chat.py` (lines 231-278):
- `ToolCall`, `ToolResult`, `ChatMessage`, `ChatRequest`, `ChatResponse`

- [ ] **Step 2: Extend `features/chat/repo.py`**

Move `_persist_messages` and `_load_history` into `ChatRepo` class methods. Use `core/timestamp_utils.py` functions instead of inline timestamp handling.

- [ ] **Step 3: Create `features/chat/router.py`**

Move route handlers from `chat.py`:
- `POST /` — send_chat_message
- `GET /conversations/{conversation_id}` — get_conversation_history
- `DELETE /conversations/{conversation_id}` — delete_conversation
- `GET /conversations` — list_conversations

Import schemas from `schema.py`, use `ChatRepo` for persistence. Move `_user_friendly_error_detail` and `_get_user_id` as module-level helpers in the router.

Timestamp parsing functions (`_parse_timestamp`, `_format_timestamp_z`) should already be in `core/timestamp_utils.py` from Task 6.

- [ ] **Step 4: Update `api/v1/api.py`**

Replace `chat.router` import with `features.chat.router`.

- [ ] **Step 5: Delete `endpoints/chat.py`**

```bash
rm datametronome_podium/api/v1/endpoints/chat.py
```

- [ ] **Step 6: Run tests and verify**

- [ ] **Step 7: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: migrate chat.py into features/chat/

Splits 700-line monolith into router.py (thin HTTP), schema.py
(Pydantic models), and repo.py (persistence). Timestamp parsing
uses core/timestamp_utils."
```

### Task 12: Migrate `metrics.py`, `reports.py`, `trends.py` into feature slices

**Files:**
- Delete: `datametronome_podium/api/v1/endpoints/metrics.py`
- Delete: `datametronome_podium/api/v1/endpoints/reports.py`
- Delete: `datametronome_podium/api/v1/endpoints/trends.py`
- Create: `datametronome_podium/features/metrics/` (`__init__.py`, `router.py`)
- Create: `datametronome_podium/features/reports/` (`__init__.py`, `router.py`)
- Create: `datametronome_podium/features/trends/` (`__init__.py`, `router.py`)
- Modify: `datametronome_podium/api/v1/api.py`

- [ ] **Step 1: Create `features/metrics/router.py`**

Move endpoints from `endpoints/metrics.py` into a feature router.

- [ ] **Step 2: Create `features/reports/router.py`**

Move endpoints from `endpoints/reports.py` into a feature router.

- [ ] **Step 3: Create `features/trends/router.py`**

Move endpoints from `endpoints/trends.py` into a feature router.

- [ ] **Step 4: Update `api/v1/api.py`**

Replace all three endpoint imports with feature router imports.

- [ ] **Step 5: Delete old endpoint files**

```bash
rm datametronome_podium/api/v1/endpoints/metrics.py
rm datametronome_podium/api/v1/endpoints/reports.py
rm datametronome_podium/api/v1/endpoints/trends.py
```

- [ ] **Step 6: Run tests and verify**

- [ ] **Step 7: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: migrate metrics, reports, trends into feature slices

Three new feature slices. All API paths unchanged."
```

### Task 13: Refactor `agent_tools.py` to call repos

**Files:**
- Modify: `datametronome_podium/services/agent_tools.py`

- [ ] **Step 1: Identify which tool functions duplicate repo queries**

Read `agent_tools.py`. Functions like `list_staves`, `get_stave`, `list_clefs`, `get_clef` duplicate `StaveRepo`/`ClefRepo` queries.

- [ ] **Step 2: Refactor to use repos and connector_factory**

Replace raw SQL with repo calls:
```python
from datametronome_podium.features.staves.repo import StaveRepo
from datametronome_podium.core.database import get_executor

async def list_staves(...):
    repo = StaveRepo(get_executor())
    staves = await repo.list(limit=limit, offset=skip)
    ...
```

For connector-dependent operations (list_tables, get_table_sample), use `core/connector_factory.py`.

- [ ] **Step 3: Run tests**

```bash
.venv/bin/python -m pytest tests/test_agent_tools.py --timeout=10 -q 2>&1 | tail -20
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: agent_tools.py calls repos instead of raw SQL

Eliminates ~1000 lines of duplicated SQL. Tool functions now
delegate to StaveRepo, ClefRepo, CheckRepo and connector_factory."
```

---

## Chunk 4: Phase 3 — Role-Based Auth

### Task 14: Create `core/auth.py` and move auth utilities

**Files:**
- Create: `datametronome_podium/core/auth.py`
- Modify: `datametronome_podium/api/v1/endpoints/auth.py`
- Modify: 9 files that import `get_current_user` (see dependency map)

- [ ] **Step 1: Create `core/auth.py`**

Move `get_current_user`, `create_access_token` from `endpoints/auth.py`. Add role-based dependency helpers:

```python
"""Authentication and authorization utilities."""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_executor

security = HTTPBearer()


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    users = await get_executor().query(
        """SELECT id, username, email, role, is_active,
               dashboard_prefs, created_at, updated_at
        FROM users WHERE username = ?""",
        [username],
    )
    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return dict(users[0])


def require_role(*allowed_roles: str):
    """FastAPI dependency that checks user role."""
    async def _check(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _check


require_editor = require_role("admin", "editor")
require_admin = require_role("admin")
```

- [ ] **Step 2: Update `endpoints/auth.py`**

Remove `get_current_user`, `create_access_token`, `security` from this file. Import them from `core.auth` instead. Keep only the route handlers.

- [ ] **Step 3: Update all import sites**

Replace `from datametronome_podium.api.v1.endpoints.auth import get_current_user` with `from datametronome_podium.core.auth import get_current_user` in:

- `api/v1/api.py:12`
- `features/checks/router.py:9`
- `features/insights/router.py:8`
- `features/user_memory/router.py:11`
- `features/staves/router.py:9`
- `features/clefs/router.py:9`
- `features/chat/router.py` (new file from Task 11)
- `tests/test_user_memory_router.py:7`
- `tests/test_stave_unpause.py:13`

- [ ] **Step 4: Update `api/v1/api.py` router registration**

Add `dependencies=[Depends(get_current_user)]` to ALL routers (staves, clefs, checks, user_memory) for consistency. Remove redundant per-endpoint `Depends(get_current_user)` from feature routers where router-level deps now cover it. (But keep per-endpoint role checks like `Depends(require_editor)` — these are additive.)

- [ ] **Step 5: Run tests**

- [ ] **Step 6: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: extract core/auth.py, update all import sites

Moves get_current_user and create_access_token to core/auth.py.
Adds require_role, require_editor, require_admin dependencies.
Updates 9 import sites."
```

### Task 15: Alembic migration — add `role` column

**Files:**
- Create: `alembic/versions/xxxx_add_role_column.py`

- [ ] **Step 1: Generate migration**

```bash
cd datametronome/podium
DATABASE_URL=$DATAMETRONOME_DATABASE_URL .venv/bin/python -m alembic revision --autogenerate -m "add role column to users"
```

If autogenerate doesn't detect the change (since models are Pydantic, not SQLAlchemy ORM), create manually:

```python
def upgrade():
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='viewer'))
    op.execute("UPDATE users SET role = 'admin' WHERE is_superuser = TRUE")
    op.execute("UPDATE users SET role = 'editor' WHERE is_superuser = FALSE AND role = 'viewer'")


def downgrade():
    op.drop_column('users', 'role')
```

- [ ] **Step 2: Update DDL in `core/seeding.py`**

Add `role` column to the `CREATE TABLE users` DDL used for SQLite test setup.

- [ ] **Step 3: Update `features/users/model.py`**

Add `role: str = "viewer"` field to the User model. Remove `is_superuser` references.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit --no-verify -m "feat: add role column to users table (migration 1 of 2)

Adds role column with default 'viewer'. Backfills from is_superuser.
is_superuser column kept for rollback safety — dropped in next migration."
```

### Task 16: Apply role checks to all routers

**Files:**
- Modify: `datametronome_podium/features/staves/router.py`
- Modify: `datametronome_podium/features/clefs/router.py`
- Modify: `datametronome_podium/features/checks/router.py`
- Modify: Any other router with write/delete operations

- [ ] **Step 1: Add role requirements to staves router**

- `POST /` (create) → `Depends(require_editor)`
- `PUT /{id}` (update) → `Depends(require_editor)`
- `DELETE /{id}` → `Depends(require_admin)`
- `POST /{id}/generate-data` → `Depends(require_editor)`
- `POST /{id}/test-connection` → `Depends(require_editor)`
- GET endpoints remain accessible to all authenticated users

- [ ] **Step 2: Add role requirements to clefs router**

- `POST /` (create) → `Depends(require_editor)`
- `PUT /{id}` (update) → `Depends(require_editor)`
- `DELETE /{id}` → `Depends(require_admin)`
- `POST /{id}/run-now` → `Depends(require_editor)`

- [ ] **Step 3: Add role requirements to checks router**

- `POST /` (create) → `Depends(require_editor)`
- `PUT /{id}` (update) → `Depends(require_editor)`
- `DELETE /{id}` → `Depends(require_admin)`

- [ ] **Step 4: Fix auth.py PATCH /me**

Replace `body: dict[str, Any]` with a Pydantic schema:
```python
class PatchUserRequest(BaseModel):
    dashboard_prefs: dict[str, Any]
```

- [ ] **Step 5: Fix auth.py register — SELECT * → SELECT 1**

Change:
```python
existing_users = await get_executor().query(
    "SELECT * FROM users WHERE username = ?", [user_data.username]
)
```
To:
```python
existing_users = await get_executor().query(
    "SELECT 1 FROM users WHERE username = ?", [user_data.username]
)
```

- [ ] **Step 6: Run tests**

- [ ] **Step 7: Commit**

```bash
git add -A && git commit --no-verify -m "feat: apply role-based auth to all routers

Admin: delete operations. Editor: create/update/run. Viewer: read-only.
Fixes PATCH /me schema validation and register SELECT *."
```

### Task 17: Alembic migration 2 — drop `is_superuser`

**Files:**
- Create: `alembic/versions/xxxx_drop_is_superuser.py`
- Modify: `datametronome_podium/api/v1/endpoints/auth.py` (or `features/auth/router.py`)

- [ ] **Step 1: Verify all code uses `role` not `is_superuser`**

```bash
grep -r "is_superuser" --include="*.py" datametronome_podium/ | grep -v __pycache__
```
Fix any remaining references.

- [ ] **Step 2: Create migration**

```python
def upgrade():
    op.drop_column('users', 'is_superuser')

def downgrade():
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
    op.execute("UPDATE users SET is_superuser = TRUE WHERE role = 'admin'")
```

- [ ] **Step 3: Update frontend `ui-nuxt/stores/auth.ts`**

Replace `is_superuser` with `role` in the `User` interface:
```typescript
export interface User {
  username: string
  email: string
  name: string
  role: 'admin' | 'editor' | 'viewer'
  is_active?: boolean
}
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit --no-verify -m "feat: drop is_superuser column (migration 2 of 2)

All code now uses role column. Frontend updated to use role
instead of is_superuser."
```

---

## Chunk 5: Phase 4 — Final Cleanup

### Task 18: Migrate `auth.py` to `features/auth/router.py`

**Files:**
- Delete: `datametronome_podium/api/v1/endpoints/auth.py`
- Create: `datametronome_podium/features/auth/` (`__init__.py`, `router.py`)
- Modify: `datametronome_podium/api/v1/api.py`

- [ ] **Step 1: Create `features/auth/router.py`**

Move route handlers (login, register, /me, PATCH /me) from `endpoints/auth.py`. Import auth utilities from `core/auth.py`.

- [ ] **Step 2: Update `api/v1/api.py`**

Replace `auth.router` with `features.auth.router`.

- [ ] **Step 3: Delete `endpoints/auth.py`**

- [ ] **Step 4: Delete `api/v1/endpoints/` directory** if now empty

```bash
rm datametronome_podium/api/v1/endpoints/auth.py
rmdir datametronome_podium/api/v1/endpoints/ 2>/dev/null || true
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: migrate auth.py to features/auth/router.py

api/v1/endpoints/ directory is now empty and removed.
All endpoints live in features/*/ slices."
```

### Task 19: Fix `pyproject.toml` and `pytest.ini`

**Files:**
- Modify: `pyproject.toml` (root)
- Modify: `datametronome/podium/pytest.ini`

- [ ] **Step 1: Fix `pyproject.toml`**

- Remove dev tools (`pytest`, `black`, `isort`, `flake8`, `mypy`) from `[project.dependencies]` — keep them only in `[project.optional-dependencies.dev]` or `[dependency-groups.dev]`
- Remove duplicate `[dependency-groups.dev]` section if it repeats `[project.dependencies]`
- Check if `litellm` is imported anywhere; if not, remove it
- Verify the actual source of dependencies (inline vs `requirements.txt`)

- [ ] **Step 2: Fix `pytest.ini`**

Add `asyncio_mode = strict` under the `[tool:pytest]` section. Remove `--disable-warnings` from `addopts`.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit --no-verify -m "chore: fix pyproject.toml deps, add asyncio_mode=strict to pytest.ini"
```

### Task 20: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Update CLAUDE.md**

- Remove "Migration State" section about two coexisting patterns
- Remove `get_db()` references from "Key Conventions"
- Update "Key Conventions" to mention role-based auth (`require_editor`, `require_admin`)
- Update "Project Structure" to show current feature slices
- Remove `api/v1/endpoints/` from structure (now only `features/`)
- Update "Common Gotchas" to remove stale entries

- [ ] **Step 2: Update `docs/ARCHITECTURE.md`**

- Reflect single architectural pattern (feature slices only)
- Update auth section to describe role-based system
- Remove references to scheduler endpoints
- Update key source locations

- [ ] **Step 3: Commit**

```bash
git add -A && git commit --no-verify -m "docs: update CLAUDE.md and ARCHITECTURE.md for post-cleanup state"
```

### Task 21: Console.log cleanup and final verification

**Files:**
- Modify: `ui-nuxt/services/api.ts`
- Modify: `ui-nuxt/services/trends.ts`

- [ ] **Step 1: Clean up frontend console.log statements**

Remove or guard behind dev-mode check in `api.ts` and `trends.ts`.

- [ ] **Step 2: Run full test suite**

```bash
cd datametronome/podium && .venv/bin/python -m pytest --timeout=10 -q
```

Fix any remaining failures.

- [ ] **Step 3: Verify all API paths still work**

```bash
make up
# Test a few key endpoints
curl -s http://localhost:8001/health | python3 -m json.tool
curl -s http://localhost:8001/api/v1/staves/ -H "Authorization: Bearer <token>" | head
```

- [ ] **Step 4: Final commit**

```bash
git add -A && git commit --no-verify -m "chore: frontend console.log cleanup, final verification"
```
