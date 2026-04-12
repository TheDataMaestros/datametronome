# Codebase Cleanup: Dead Code, Feature-Slice Migration, Role-Based Auth

**Date:** 2026-04-07
**Branch:** `fix/security-hardening-round2` (or new branch)
**Status:** Design

---

## Problem

The codebase has accumulated debt from iterative development:

1. **Dead code:** Unused exception hierarchy, unused rate-limit dict, orphaned scheduler endpoints, build artifacts in git, duplicate `models/` directory.
2. **Duplicated logic:** Connector creation branching in 11+ call sites across 4 files, `agent_tools.py` (1,270 lines) duplicating repo SQL, Redis singleton copy-pasted in 3 files, `.replace("+00:00", "Z")` in 35+ instances.
3. **Two architectural patterns coexisting:** Feature slices (`features/*/`) and legacy endpoints (`api/v1/endpoints/`). CLAUDE.md documents this as a gotcha.
4. **No authorization beyond "is logged in":** Any authenticated user can delete any stave/clef/check. No role differentiation.
5. **Monolith endpoints:** `chat.py` (700 lines) and `stave_actions.py` (590 lines) mix models, repos, business logic, and HTTP handlers.
6. **Massive `services/` directory:** 9,490 lines across 17 files, not organized into feature slices, multiple `get_db()` calls.

## Approach

Top-down: clean dead code, migrate structure into feature slices (consolidating duplications during migration), then add role-based auth onto the clean architecture.

Four phases, each independently shippable.

---

## Phase 1 — Delete Dead Code & Build Artifacts

Pure deletion. Zero new code.

### Files to delete

| File/Directory | Reason |
|---|---|
| `datametronome_podium/models/` (entire directory) | Superseded by `features/*/model.py`. All 25+ import sites must be updated (see below). |
| `datametronome_podium/core/exceptions.py` | 7 custom exception types, none raised anywhere in non-test code. |
| `datametronome_podium/api/v1/endpoints/scheduler.py` | Frontend doesn't use it. Multiple TODO stubs. Celery Beat handles scheduling. |
| `datametronome_podium/api/v1/endpoints/import_config.py` | Frontend doesn't reference it. YAML config import feature removed entirely (endpoint + HTTP layer only; `yaml_loader.py` and `yaml_watcher.py` services stay — they are imported by `stave_yaml_loader.py` and other live code). |
| `datametronome_podium/services/job_monitor.py` | Only imported by `scheduler.py`. |
| `datametronome_podium/services/scheduler_persistence.py` | Only imported by `scheduler.py`. |
| `datametronome_podium/features/scheduler/` (entire directory) | Dead feature slice for the removed scheduler. `model.py`, `repo.py`, `__init__.py`. |
| `datametronome/brain/base/build/lib/` | Build artifacts — duplicate source checked into git. |

### Code to remove (in files that stay)

| File | What to remove |
|---|---|
| `core/rate_limit.py` | Delete the `RATE_LIMITS` dict (lines ~48-55). Keep the `limiter` object. |
| `api/v1/api.py` | Remove `scheduler` and `import_config` router registrations and imports. |

### Orphaned tests to delete

Tests that only exercise deleted modules:
- `tests/test_yaml_scheduler_integration.py`
- `tests/test_scheduler_enhancements.py`
- `tests/features/scheduler/test_scheduler_repo.py`
- Any test importing from `services/job_monitor` or `services/scheduler_persistence`

### .gitignore additions

```
build/
dist/
*.egg-info/
```

### Import updates for `models/` deletion

All files importing from `datametronome_podium.models.*` must be updated. Mapping:
- `models.stave.Stave` → `features.staves.model.Stave`
- `models.clef.Clef` → `features.clefs.model.Clef`
- `models.user.User` → `features.users.model.User`
- `models.check_run.CheckRun` → `features.checks.model.Check`
- `models.severity.*` → inline into consuming module or `features/checks/model.py`

**Known consumers (25+ files, must grep to confirm full list):**
- `services/stave_service.py`
- `services/config_validator.py`
- `services/clef_executor.py`
- `services/stave_yaml_loader.py`
- `services/yaml_loader.py`
- `services/connection_tester.py`
- `api/v1/endpoints/stave_actions.py`
- `features/staves/router.py` (if it still imports from models)
- 7+ test files (`test_unit.py`, `test_stave_examples.py`, etc.)

**Implementation note:** Run `grep -r "from datametronome_podium.models" --include="*.py"` before deleting to capture the full list. Update all imports in the same commit as the deletion to avoid any window of breakage.

---

## Phase 2 — Migrate Legacy Endpoints to Feature Slices

Move every remaining `api/v1/endpoints/` file (except `auth.py`) into feature slices. Consolidate duplications during migration. API URL paths do not change.

### Migration map

| Source | Target | Structural changes |
|---|---|---|
| `endpoints/chat.py` | `features/chat/router.py`, `schema.py`, `repo.py` | Extract Pydantic models → `schema.py`. Extract `_persist_messages`, `_load_history` → `ChatRepo`. Move `_parse_timestamp`, `_format_timestamp_z` → `core/timestamp_utils.py`. Router stays thin. |
| `endpoints/stave_actions.py` | `features/staves/router.py` (merge) + `features/staves/service.py` | test-connection, preview-data, generate-data, list-tables move into staves feature. Connector branching extracted to `core/connector_factory.py`. |
| `endpoints/clef_actions.py` | `features/clefs/router.py` (merge) | run-now, job-status, results endpoints merge alongside existing CRUD. **Note:** Both `clef_actions.py` and `clefs/router.py` currently share the `/clefs` prefix in `api.py`. During merge, ensure no route conflicts — `/{clef_id}/run-now`, `/{clef_id}/results`, `/jobs/{job_id}/status`, `/results/latest` must not collide with `/{clef_id}` GET. Use explicit path ordering or sub-routers. |
| `endpoints/metrics.py` | `features/metrics/router.py`, `schema.py` | New feature slice. |
| `endpoints/reports.py` | `features/reports/router.py`, `schema.py` | New feature slice. |
| `endpoints/trends.py` | `features/trends/router.py`, `schema.py` | New feature slice. |

### `services/` directory disposition

The `services/` directory (9,490 lines, 17 files) is **explicitly out of scope for migration into feature slices**. Rationale: these are shared cross-cutting services, not feature-specific code. They serve multiple features and don't map 1:1 to slices.

However, during Phase 2 the following services are touched:
- `agent_tools.py` — refactored to call repos (see below)
- `connection_tester.py` — may be simplified when `core/connector_factory.py` is extracted
- `orchestrator.py` — no changes needed
- `job_monitor.py`, `scheduler_persistence.py` — already deleted in Phase 1

Remaining `get_db()` calls in services must be migrated to `get_executor()`:
- `core/metrics.py` (line ~187)
- `services/default_setup.py` (line ~24)
- Any other `get_db()` call sites found during implementation

### `features/analytics/` note

The `analytics` feature slice already exists (`repo.py`, `schema.py`, tests). It is not affected by this migration. `metrics.py` and `trends.py` endpoints are separate concerns and get their own slices.

### Shared extractions (consolidation)

#### 1. `core/connector_factory.py`

Extract the `if data_source_type == "bigquery" / "postgres" / "sqlite"` connector creation logic into a single factory:

```python
async def create_connector(stave: Stave, *, read_only: bool = False) -> Any:
    """Create the appropriate Pulse connector from a stave's config."""
    ...
```

**Known call sites (11+ across 4 files):**
- `agent_tools.py` (4 locations)
- `connection_tester.py` (2 locations)
- `clef_executor.py` (2 locations — this 2,324-line file is the heaviest consumer)
- `stave_actions.py` → `staves/service.py` (3 locations)

Existing `ConnectionTester.get_connector()` serves as the basis. Evaluate whether `ConnectionTester` can be replaced by the factory or simplified to delegate to it.

#### 2. `core/redis.py`

Extract the `_redis_client` / `_get_or_create_redis_client()` pattern into one module:

```python
def get_redis_client() -> redis.asyncio.Redis:
    ...
```

Replace duplicated singletons in: `features/staves/router.py`, `tasks/check_tasks.py`, and any other file with a `_redis_client` global.

#### 3. `core/timestamp_utils.py` — consolidation

Already exists with `to_utc_isoformat()`. Replace all 35+ instances of `.replace("+00:00", "Z")` across the codebase. Move `_parse_timestamp` and `_format_timestamp_z` from `chat.py` into this module.

**Precision note:** The existing `to_utc_isoformat()` may drop sub-second precision (uses `%S` strftime). Verify that it preserves microseconds from `.isoformat()` calls, or update it to do so. Changing timestamp precision could break test assertions that compare exact strings.

#### 4. `agent_tools.py` → calls repos

Rewrite agent tool functions to call `StaveRepo`, `ClefRepo`, `CheckRepo` instead of duplicating raw SQL. For connector-dependent operations (list tables, sample data), call the new `core/connector_factory.py`. Target: cut from 1,270 lines to ~300.

### Post-migration state

`api/v1/endpoints/` contains only `auth.py` (moves to `features/auth/router.py` in Phase 3). `api/v1/api.py` imports feature routers + auth. `services/` stays as shared cross-cutting services.

---

## Phase 3 — Role-Based Auth Hardening

### Data model

**Two-step Alembic migration for safety:**

Migration 1 (additive — safe to deploy, safe to roll back):
```sql
ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'viewer';
UPDATE users SET role = 'admin' WHERE is_superuser = TRUE;
UPDATE users SET role = 'editor' WHERE is_superuser = FALSE;
```

Migration 2 (destructive — deploy only after all code uses `role`):
```sql
ALTER TABLE users DROP COLUMN is_superuser;
```

This two-step approach means if the deployment fails after Migration 1, the app can roll back to code that still reads `is_superuser` without data loss. Migration 2 runs only after all code paths are verified.

Role values: `admin`, `editor`, `viewer`.

### Permission matrix

| Action | Admin | Editor | Viewer |
|--------|-------|--------|--------|
| Read staves/clefs/checks/insights/trends/reports/metrics | Yes | Yes | Yes |
| Create/update staves/clefs | Yes | Yes | No |
| Delete staves/clefs | Yes | No | No |
| Run checks (run-now) | Yes | Yes | No |
| Chat with agents | Yes | Yes | Yes |
| View/search user memory (own) | Yes | Yes | Yes |
| Generate sample data | Yes | Yes | No |
| Test connections | Yes | Yes | No |
| Manage users / assign roles | Yes | No | No |

### Auth module refactor

Move `get_current_user` and `create_access_token` from `endpoints/auth.py` into `core/auth.py`. They are imported by nearly every module — they belong in core, not in an endpoint file.

**Import blast radius (12+ files):** All 6 feature routers, `api.py`, `chat.py` (now `features/chat/router.py`), and 4+ test files currently import from `datametronome_podium.api.v1.endpoints.auth`. All must be updated to `datametronome_podium.core.auth`.

`endpoints/auth.py` retains only the HTTP route handlers (login, register, /me, PATCH /me) and becomes `features/auth/router.py`.

New dependency helpers in `core/auth.py`:

```python
def require_role(*allowed_roles: str):
    """FastAPI dependency that checks user role."""
    async def _check(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _check

require_editor = require_role("admin", "editor")
require_admin = require_role("admin")
```

### Router registration pattern

All routers registered with `dependencies=[Depends(get_current_user)]` at `api.py` level for consistent baseline auth. Write/destructive endpoints add `Depends(require_editor)` or `Depends(require_admin)` per-endpoint.

### Auth fixes from roast

| Issue | Fix |
|---|---|
| `PATCH /me` accepts `dict[str, Any]` | Replace with Pydantic schema: `class PatchUserRequest(BaseModel): dashboard_prefs: DashboardPrefs` |
| `POST /register` does `SELECT * FROM users` | Change to `SELECT 1 FROM users WHERE username = ?` |
| Inconsistent auth registration | All routers get `dependencies=_auth_deps` at api.py level |

**User ID migration (deferred):** The current pattern of `id = username` is noted but deferred to a future change. Migrating existing user IDs from usernames to UUIDs requires updating all foreign key references across `chat_messages`, `user_memories`, `conversation_extraction_status`, and potentially other tables. This is a significant data migration that deserves its own spec.

### Frontend update

Add `role` to the `User` interface in `ui-nuxt/stores/auth.ts`:

```typescript
export interface User {
  username: string
  email: string
  name: string
  role: 'admin' | 'editor' | 'viewer'
  is_active?: boolean
}
```

Remove `is_superuser` references (only after Migration 2 drops the column).

---

## Phase 4 — Cleanup & Verification

1. **Delete emptied directories:** `api/v1/endpoints/` (now empty), `models/` (done in Phase 1), `features/scheduler/` (done in Phase 1).
2. **Fix `pyproject.toml`:** Remove duplicate `[dependency-groups.dev]` entries. Move `pytest`, `black`, `isort`, `flake8`, `mypy` out of `[project.dependencies]` into `[project.optional-dependencies.dev]` only. Remove unused `litellm` if confirmed unused. **Note:** Check whether dependencies come from `requirements.txt` via dynamic metadata or are inline — fix the actual source.
3. **Fix `pytest.ini`:** Add `asyncio_mode = strict` (verify correct section: `[tool:pytest]` for ini format, `[tool.pytest.ini_options]` for pyproject.toml). Remove `--disable-warnings`.
4. **Update CLAUDE.md:** Remove migration-state caveats ("check both locations"). Remove `get_db()` references. Update auth conventions to describe role-based pattern. Update feature-slice list.
5. **Update `docs/ARCHITECTURE.md`:** Reflect single architectural pattern, role-based auth, removed scheduler endpoints.
6. **Run full test suite.** Fix any broken imports or assertions from structural changes.
7. **Console.log cleanup in frontend:** Remove or guard API response body logging in `ui-nuxt/services/api.ts` and `ui-nuxt/services/trends.ts`.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Import breakage from `models/` deletion (25+ files) | Run grep before deleting; update all imports in same commit; test immediately |
| API path changes breaking frontend | API paths stay the same — only Python source location changes |
| `is_superuser` column drop losing data | Two-step migration: add `role` + backfill first, drop `is_superuser` separately after code is verified |
| `agent_tools.py` refactor breaking agent behavior | Agent tools return the same data shapes — only the internal implementation changes (repo calls instead of raw SQL) |
| Deleting scheduler endpoints that something depends on | Verified: no frontend references, only test files import from scheduler services |
| `/clefs` prefix route conflicts during merge | Explicit path ordering and testing of all clef routes after merge |
| Timestamp precision change from consolidation | Verify `to_utc_isoformat()` preserves microseconds before replacing inline calls |

## Out of Scope

- Migrating `services/` directory into feature slices (they are shared cross-cutting services)
- Rewriting `clef_executor.py` (2,324 lines — separate effort)
- User ID migration from username to UUID (requires FK updates across multiple tables — separate spec)
- Connection pooling for Redis (Phase 2 extracts the singleton; pooling is a future concern)
- Granular permissions beyond admin/editor/viewer (YAGNI — can evolve later)
- Rewriting Pulse connectors
- Fixing the `logfire` dependency conflict (separate issue)
