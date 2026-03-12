# PostgreSQL Migration + Agent State Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate from SQLite to PostgreSQL as default database, add connector-agnostic abstraction, custom migration system, and LangGraph-style agent state tables.

**Architecture:** A `QueryAdapter` translates SQL dialects. A connector factory picks `PostgresPulse` or `SQLitePulse` based on `database_url`. A lightweight migration runner applies numbered `.sql` files. Three new tables (`workflow_checkpoints`, `workflow_definitions`, `workflow_events`) enable stateful agent orchestration with full audit trail.

**Tech Stack:** `metronome-pulse-postgres` (asyncpg), `metronome-pulse-sqlite`, FastAPI, pydantic-ai, Python 3.13

**Spec:** `docs/superpowers/specs/2026-03-12-postgresql-migration-agent-state-design.md`

---

## File Map

### New files
| Path | Responsibility |
|------|---------------|
| `core/query_adapter.py` | SQL dialect translation (placeholders, booleans, DDL types) |
| `core/migrations/__init__.py` | Package marker |
| `core/migrations/runner.py` | Migration runner (scan sql/, track in schema_migrations) |
| `core/migrations/sql/001_initial_schema.sql` | All existing tables + indexes |
| `core/migrations/sql/002_agent_state.sql` | workflow_checkpoints, workflow_definitions, workflow_events |
| `services/workflow_state.py` | CRUD for checkpoints + event logging |
| `tests/test_query_adapter.py` | Unit tests for QueryAdapter |
| `tests/test_migration_runner.py` | Unit tests for migration runner |
| `tests/test_workflow_state.py` | Unit tests for workflow state service |
| `tests/test_database.py` | Unit tests for connector factory + normalization |

### Modified files
| Path | Change |
|------|--------|
| `core/database.py` | Rewrite: connector factory, normalization layer, remove inline DDL |
| `core/config.py` | Change database_url default to postgresql:// |
| `services/orchestrator.py` | Add checkpoint/event wiring to run_chat |
| `api/v1/endpoints/chat.py` | Pass conversation_id + user_id to run_chat |
| `requirements.txt` | Add metronome-pulse-postgres |
| `docker-compose.yml` | Update podium DATABASE_URL to postgresql:// |

### Key connector differences (reference for implementation)

| Method | SQLitePulse | PostgresPulse |
|--------|-------------|---------------|
| `__init__` | `(database_path)` | `(host, port, database, user, password, **kwargs)` |
| `execute` | `(sql, params=None)` — params is a list | `(query, *args, **kwargs)` — params are variadic |
| `query` | dict `{"sql":..., "params":[...]}` — params passed as list to `cursor.execute` | dict `{"sql":..., "params":[...]}` — defaults to type="custom", splats `*params` |
| `write` | `(data, destination)` — adds "table" key, writeonly strips it before INSERT | `(data, destination)` — does NOT strip "table" key → would cause column error |
| `write` return | returns result (truthy) | returns `None` |

---

## Chunk 1: Query Adapter

### Task 1: QueryAdapter with placeholder rewriting

**Context:** The adapter translates `?` placeholders to `$1, $2, $3...` for PostgreSQL. It also maps DDL types (`JSONB` → `TEXT` for SQLite, `REAL` → `DOUBLE PRECISION` for PostgreSQL) and boolean literals.

**Files:**
- Create: `datametronome/podium/datametronome_podium/core/query_adapter.py`
- Create: `datametronome/podium/tests/test_query_adapter.py`

- [ ] **Step 1.1: Write failing tests for placeholder rewriting**

```python
"""Tests for QueryAdapter SQL dialect translation."""
import pytest

from datametronome_podium.core.query_adapter import QueryAdapter


class TestPlaceholderRewriting:
    def test_sqlite_no_change(self):
        adapter = QueryAdapter("sqlite")
        sql, params = adapter.adapt("SELECT * FROM users WHERE id = ?", [1])
        assert sql == "SELECT * FROM users WHERE id = ?"
        assert params == [1]

    def test_postgresql_single_param(self):
        adapter = QueryAdapter("postgresql")
        sql, params = adapter.adapt("SELECT * FROM users WHERE id = ?", [1])
        assert sql == "SELECT * FROM users WHERE id = $1"
        assert params == [1]

    def test_postgresql_multiple_params(self):
        adapter = QueryAdapter("postgresql")
        sql, params = adapter.adapt(
            "SELECT * FROM t WHERE a = ? AND b = ? AND c = ?", [1, 2, 3]
        )
        assert sql == "SELECT * FROM t WHERE a = $1 AND b = $2 AND c = $3"
        assert params == [1, 2, 3]

    def test_postgresql_no_params(self):
        adapter = QueryAdapter("postgresql")
        sql, params = adapter.adapt("SELECT * FROM users", [])
        assert sql == "SELECT * FROM users"
        assert params == []

    def test_question_mark_in_string_literal_not_replaced(self):
        adapter = QueryAdapter("postgresql")
        sql, params = adapter.adapt(
            "SELECT * FROM t WHERE name = ? AND desc LIKE '%?%'", ["test"]
        )
        # The ? inside quotes should not be replaced
        assert "$1" in sql
        assert params == ["test"]

    def test_doubled_quotes_handled(self):
        """PostgreSQL uses '' for escaping inside strings, not backslash."""
        adapter = QueryAdapter("postgresql")
        sql, params = adapter.adapt(
            "SELECT * FROM t WHERE name = ? AND note = 'it''s fine'", ["test"]
        )
        assert sql == "SELECT * FROM t WHERE name = $1 AND note = 'it''s fine'"
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
cd datametronome/podium && python3 -m pytest tests/test_query_adapter.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'datametronome_podium.core.query_adapter'`

- [ ] **Step 1.3: Write QueryAdapter implementation**

```python
"""SQL dialect translation between SQLite and PostgreSQL.

Translates placeholders, boolean literals, and DDL type names so that
all application code can write SQL with `?` placeholders regardless
of the active database backend.
"""
import re


class QueryAdapter:
    """Translates SQL between SQLite and PostgreSQL dialects."""

    def __init__(self, dialect: str) -> None:
        if dialect not in ("sqlite", "postgresql"):
            raise ValueError(f"Unsupported dialect: {dialect}")
        self.dialect = dialect

    def adapt(self, sql: str, params: list | None = None) -> tuple[str, list]:
        """Adapt SQL and params for the active dialect.

        Args:
            sql: SQL string with `?` placeholders
            params: Parameter list (may be empty or None)

        Returns:
            (adapted_sql, adapted_params)
        """
        params = list(params) if params else []
        if self.dialect == "postgresql":
            sql = self._rewrite_placeholders(sql)
        elif self.dialect == "sqlite":
            # SQLite needs bools as 1/0
            params = [int(p) if isinstance(p, bool) else p for p in params]
        return sql, params

    def adapt_ddl(self, sql: str) -> str:
        """Adapt DDL statements for the active dialect.

        PostgreSQL DDL is the canonical format. This method translates
        for SQLite when needed.
        """
        if self.dialect == "sqlite":
            sql = sql.replace("JSONB", "TEXT")
            sql = sql.replace("DOUBLE PRECISION", "REAL")
        return sql

    def _rewrite_placeholders(self, sql: str) -> str:
        """Replace ? placeholders with $1, $2, ... for PostgreSQL.

        Skips ? characters inside string literals (single quotes).
        Handles PostgreSQL-style escaped quotes ('') correctly.
        """
        result = []
        param_index = 0
        in_string = False

        i = 0
        while i < len(sql):
            char = sql[i]
            if char == "'":
                # Check for doubled quote ('') — escaped single quote
                if in_string and i + 1 < len(sql) and sql[i + 1] == "'":
                    result.append("''")
                    i += 2
                    continue
                in_string = not in_string
                result.append(char)
            elif char == "?" and not in_string:
                param_index += 1
                result.append(f"${param_index}")
            else:
                result.append(char)
            i += 1

        return "".join(result)
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
cd datametronome/podium && python3 -m pytest tests/test_query_adapter.py -v
```
Expected: all PASS

- [ ] **Step 1.5: Write failing tests for DDL adaptation**

Add to `tests/test_query_adapter.py`:

```python
class TestDDLAdaptation:
    def test_sqlite_jsonb_to_text(self):
        adapter = QueryAdapter("sqlite")
        ddl = adapter.adapt_ddl("CREATE TABLE t (data JSONB NOT NULL)")
        assert "TEXT" in ddl
        assert "JSONB" not in ddl

    def test_sqlite_double_precision_to_real(self):
        adapter = QueryAdapter("sqlite")
        ddl = adapter.adapt_ddl(
            "CREATE TABLE t (val DOUBLE PRECISION DEFAULT 0)"
        )
        assert "REAL" in ddl
        assert "DOUBLE PRECISION" not in ddl

    def test_postgresql_ddl_unchanged(self):
        adapter = QueryAdapter("postgresql")
        original = "CREATE TABLE t (data JSONB NOT NULL, val DOUBLE PRECISION)"
        ddl = adapter.adapt_ddl(original)
        assert ddl == original

    def test_invalid_dialect_raises(self):
        with pytest.raises(ValueError, match="Unsupported dialect"):
            QueryAdapter("mysql")


class TestBooleanAdaptation:
    def test_postgresql_bool_params_unchanged(self):
        """PostgreSQL handles Python bools natively via asyncpg."""
        adapter = QueryAdapter("postgresql")
        sql, params = adapter.adapt("INSERT INTO t (active) VALUES (?)", [True])
        assert params == [True]

    def test_sqlite_bool_params_to_int(self):
        """SQLite needs bools as 1/0."""
        adapter = QueryAdapter("sqlite")
        sql, params = adapter.adapt(
            "INSERT INTO t (active, deleted) VALUES (?, ?)", [True, False]
        )
        assert params == [1, 0]
```

- [ ] **Step 1.6: Run tests to verify they pass**

```bash
cd datametronome/podium && python3 -m pytest tests/test_query_adapter.py -v
```
Expected: all PASS

- [ ] **Step 1.7: Commit**

```bash
cd datametronome/podium
git add datametronome_podium/core/query_adapter.py tests/test_query_adapter.py
git commit -m "feat: add QueryAdapter for SQL dialect translation (sqlite/postgresql)"
```

---

## Chunk 2: Connector Factory + Database Layer Rewrite

### Task 2: Rewrite database.py with connector factory and normalization

**Context:** Replace the SQLite-hardcoded `database.py` with a connector-agnostic version. The factory parses `database_url` to pick the right connector. A normalization layer bridges the API differences between `SQLitePulse` and `PostgresPulse`.

**Files:**
- Modify: `datametronome/podium/datametronome_podium/core/database.py`
- Modify: `datametronome/podium/datametronome_podium/core/config.py` (line 37-40, database_url default)
- Modify: `datametronome/podium/requirements.txt`

- [ ] **Step 2.1: Add metronome-pulse-postgres to requirements.txt**

Add after the `pydantic-ai` line:

```
# Database connectors (DataPulse)
metronome-pulse-postgres>=0.1.0
```

- [ ] **Step 2.2: Update config.py database_url default**

In `core/config.py` line 37-40, change:

```python
    database_url: str = Field(
        default="postgresql://testuser:testpass@localhost:5432/datametronome_test",
        validation_alias="DATAMETRONOME_DATABASE_URL",
    )
```

- [ ] **Step 2.3: Rewrite database.py**

Replace the entire file with:

```python
"""
Database initialization and management for DataMetronome Podium.

Connector-agnostic: picks PostgresPulse or SQLitePulse based on database_url.
"""
import logging
from typing import Any
from urllib.parse import urlparse

from datametronome_podium.core.query_adapter import QueryAdapter

logger = logging.getLogger(__name__)

# Global state
connector: Any | None = None
dialect: str = "postgresql"
_adapter: QueryAdapter | None = None


def _parse_pg_url(url: str) -> dict[str, Any]:
    """Parse a postgresql:// URL into PostgresPulse constructor kwargs."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") or None,
        "user": parsed.username or None,
        "password": parsed.password or None,
    }


def _parse_sqlite_path(url: str) -> str:
    """Extract file path from a sqlite:// URL."""
    import os

    path = (
        url.replace("sqlite+aiosqlite:///", "")
        .replace("sqlite:///", "")
        .replace("./", "")
    )
    if not os.path.isabs(path):
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        podium_dir = os.path.dirname(os.path.dirname(current_file_dir))
        path = os.path.abspath(os.path.join(podium_dir, path))
    return path


async def _create_connector(database_url: str) -> tuple[Any, str]:
    """Create the appropriate DataPulse connector from the database URL.

    Returns:
        (connector_instance, dialect_string)
    """
    if database_url.startswith("postgresql"):
        from metronome_pulse_postgres import PostgresPulse

        kwargs = _parse_pg_url(database_url)
        conn = PostgresPulse(**kwargs)
        return conn, "postgresql"
    else:
        from metronome_pulse_sqlite import SQLitePulse

        path = _parse_sqlite_path(database_url)
        conn = SQLitePulse(path)
        return conn, "sqlite"


def _get_adapter() -> QueryAdapter:
    """Get the QueryAdapter for the current dialect."""
    global _adapter
    if _adapter is None:
        _adapter = QueryAdapter(dialect)
    return _adapter


async def init_db() -> None:
    """Initialize database: create connector, run migrations, seed data."""
    global connector, dialect, _adapter

    from datametronome_podium.core.config import settings

    connector, dialect = await _create_connector(settings.database_url)
    _adapter = QueryAdapter(dialect)

    await connector.connect()
    logger.info("Database connected (dialect=%s)", dialect)

    # Run migrations (pass connector directly to avoid circular imports)
    from datametronome_podium.core.migrations.runner import run_migrations

    await run_migrations(connector, dialect)

    # Create default admin user
    await _create_default_admin()

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close the database connector."""
    global connector
    if connector:
        await connector.close()
        connector = None


async def get_db():
    """Get the DataPulse connector instance."""
    global connector
    if not connector:
        await init_db()
    return connector


# --- Normalized helper functions ---
# These bridge the API differences between SQLitePulse and PostgresPulse.


async def execute_query(
    sql: str, params: list[Any] | None = None
) -> list[dict[str, Any]]:
    """Execute a query and return results as list of dicts."""
    adapter = _get_adapter()
    adapted_sql, adapted_params = adapter.adapt(sql, params)
    conn = await get_db()

    if adapted_params:
        return await conn.query({"sql": adapted_sql, "params": adapted_params})
    else:
        return await conn.query(adapted_sql)


async def execute_write(sql: str, params: list[Any] | None = None) -> bool:
    """Execute a write statement (INSERT/UPDATE/DELETE).

    Returns True on success, False on failure.
    """
    adapter = _get_adapter()
    adapted_sql, adapted_params = adapter.adapt(sql, params)
    conn = await get_db()

    try:
        if dialect == "postgresql":
            await conn.execute(adapted_sql, *adapted_params) if adapted_params else await conn.execute(adapted_sql)
        else:
            await conn.execute(adapted_sql, adapted_params) if adapted_params else await conn.execute(adapted_sql)
        return True
    except Exception:
        logger.exception("execute_write failed")
        return False


async def insert_data(table: str, data: dict[str, Any]) -> bool:
    """Insert a single row into a table.

    Normalizes the write() call between SQLitePulse and PostgresPulse.
    SQLitePulse expects {"table": ..., **columns} in the data list.
    PostgresPulse _simple_insert does NOT strip "table" key, so we
    must handle this differently per dialect.
    """
    conn = await get_db()

    try:
        if dialect == "sqlite":
            # SQLitePulse write() expects data dicts WITHOUT "table" key —
            # it adds the key internally, and writeonly strips it before INSERT.
            result = await conn.write([data], table)
            return bool(result) if result is not None else True
        else:
            # PostgresPulse: build INSERT manually to avoid "table" column issue
            columns = list(data.keys())
            placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
            col_names = ", ".join(columns)
            sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
            values = list(data.values())
            await conn.execute(sql, *values)
            return True
    except Exception:
        logger.exception("insert_data failed for table=%s", table)
        return False


async def update_data(
    table: str, data: dict[str, Any], where_clause: str, where_params: list[Any]
) -> bool:
    """Update rows in a table."""
    adapter = _get_adapter()

    # Build SQL with ? placeholders (adapter translates for dialect)
    set_clauses = [f"{k} = ?" for k in data.keys()]
    set_values = list(data.values())
    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_clause}"
    all_params = set_values + where_params

    adapted_sql, adapted_params = adapter.adapt(sql, all_params)
    conn = await get_db()

    try:
        if dialect == "postgresql":
            await conn.execute(adapted_sql, *adapted_params)
        else:
            await conn.execute(adapted_sql, adapted_params)
        return True
    except Exception:
        logger.exception("update_data failed")
        return False


async def delete_data(table: str, where_clause: str, where_params: list[Any]) -> bool:
    """Delete rows from a table."""
    adapter = _get_adapter()
    adapted_where, adapted_params = adapter.adapt(
        f"DELETE FROM {table} WHERE {where_clause}", where_params
    )
    conn = await get_db()

    try:
        if dialect == "postgresql":
            await conn.execute(adapted_where, *adapted_params) if adapted_params else await conn.execute(adapted_where)
        else:
            await conn.execute(adapted_where, adapted_params) if adapted_params else await conn.execute(adapted_where)
        return True
    except Exception:
        logger.exception("delete_data failed")
        return False


async def get_db_connection_status() -> bool:
    """Check database connection health."""
    global connector
    try:
        if not connector:
            return False
        result = await connector.query("SELECT 1")
        return result is not None
    except Exception:
        logger.error("Database health check failed", exc_info=True)
        return False


async def _create_default_admin() -> None:
    """Create default admin user for development."""
    try:
        existing = await execute_query(
            "SELECT * FROM users WHERE username = ?", ["admin"]
        )
        if existing:
            logger.info("Admin user already exists")
            return

        from datametronome_podium.api.v1.endpoints.auth import get_password_hash

        await insert_data("users", {
            "id": "admin-001",
            "username": "admin",
            "email": "admin@datametronome.dev",
            "hashed_password": get_password_hash("admin"),
            "is_active": True,
            "is_superuser": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        })
        logger.info("Default admin user created (admin/admin)")
    except Exception as e:
        logger.warning("Could not create default admin user: %s", e)
```

- [ ] **Step 2.4: Run existing tests to check for import breakage**

```bash
cd datametronome/podium && python3 -m pytest tests/ -v -k "not integration" --tb=short 2>&1 | tail -40
```
Expected: tests that mock `get_db` should still pass. Some may need `sqlite_connector` references updated — note any failures.

- [ ] **Step 2.5: Fix any test failures from the global rename**

If tests reference `sqlite_connector` or `from datametronome_podium.core.database import sqlite_connector`, update them to use `connector` instead.

Check `agent_tools.py` line 9 — it imports `get_db` which is unchanged, so it should be fine.

- [ ] **Step 2.6: Write tests for the database normalization layer**

Create `datametronome/podium/tests/test_database.py`:

```python
"""Tests for database connector factory and normalization."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from datametronome_podium.core.database import (
    _parse_pg_url,
    _parse_sqlite_path,
    execute_query,
    execute_write,
    insert_data,
)


class TestParseURL:
    def test_parse_pg_url(self):
        result = _parse_pg_url("postgresql://user:pass@host:5432/mydb")
        assert result["host"] == "host"
        assert result["port"] == 5432
        assert result["database"] == "mydb"
        assert result["user"] == "user"
        assert result["password"] == "pass"

    def test_parse_pg_url_defaults(self):
        result = _parse_pg_url("postgresql:///mydb")
        assert result["host"] == "localhost"
        assert result["port"] == 5432

    def test_parse_sqlite_path(self):
        path = _parse_sqlite_path("sqlite:///./data/test.db")
        assert path.endswith("data/test.db")


@pytest.mark.asyncio
async def test_execute_query_sqlite():
    """execute_query should pass params as list for SQLite."""
    mock_conn = AsyncMock()
    mock_conn.query = AsyncMock(return_value=[{"id": 1}])

    with patch("datametronome_podium.core.database.get_db", return_value=mock_conn), \
         patch("datametronome_podium.core.database.dialect", "sqlite"), \
         patch("datametronome_podium.core.database._adapter", None):
        result = await execute_query("SELECT * FROM t WHERE id = ?", [1])
        assert result == [{"id": 1}]


@pytest.mark.asyncio
async def test_execute_write_postgresql():
    """execute_write should splat params for PostgreSQL."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    with patch("datametronome_podium.core.database.get_db", return_value=mock_conn), \
         patch("datametronome_podium.core.database.dialect", "postgresql"), \
         patch("datametronome_podium.core.database._adapter", None):
        result = await execute_write("INSERT INTO t (id) VALUES (?)", [1])
        assert result is True
        # PostgreSQL should splat: execute(sql, 1) not execute(sql, [1])
        mock_conn.execute.assert_called_once()
        args = mock_conn.execute.call_args[0]
        assert args[0] == "INSERT INTO t (id) VALUES ($1)"
        assert args[1] == 1  # splatted, not [1]


@pytest.mark.asyncio
async def test_insert_data_postgresql():
    """insert_data for PostgreSQL should build raw INSERT, not use write()."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    with patch("datametronome_podium.core.database.get_db", return_value=mock_conn), \
         patch("datametronome_podium.core.database.dialect", "postgresql"), \
         patch("datametronome_podium.core.database._adapter", None):
        result = await insert_data("users", {"id": "1", "name": "test"})
        assert result is True
        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO users" in sql
        assert "$1" in sql
```

- [ ] **Step 2.7: Run database tests**

```bash
cd datametronome/podium && python3 -m pytest tests/test_database.py -v
```
Expected: all PASS

- [ ] **Step 2.8: Commit**

```bash
cd datametronome/podium
git add datametronome_podium/core/database.py datametronome_podium/core/config.py requirements.txt tests/test_database.py
git add -u  # catch any test fixes
git commit -m "feat: connector-agnostic database layer with PostgreSQL as default"
```

> **Note:** After this commit, the app will not start until Chunk 3 (migration runner) is also applied, because `init_db()` imports `run_migrations`. Proceed to Chunk 3 immediately.

---

## Chunk 3: Migration System

### Task 3: Migration runner

**Context:** A lightweight migration runner that applies numbered SQL files and tracks them in a `schema_migrations` table. Replaces the inline `_create_tables()` that was in `database.py`.

**Files:**
- Create: `datametronome/podium/datametronome_podium/core/migrations/__init__.py`
- Create: `datametronome/podium/datametronome_podium/core/migrations/runner.py`
- Create: `datametronome/podium/tests/test_migration_runner.py`

- [ ] **Step 3.1: Write failing test for migration runner**

```python
"""Tests for the migration runner."""
import pytest
from unittest.mock import AsyncMock, patch

from datametronome_podium.core.migrations.runner import run_migrations


@pytest.mark.asyncio
async def test_runner_creates_schema_migrations_table():
    """Runner should create schema_migrations table on first run."""
    mock_db = AsyncMock()
    mock_db.query = AsyncMock(return_value=[])
    mock_db.execute = AsyncMock()

    with patch(
        "datametronome_podium.core.migrations.runner._get_sql_files",
        return_value=[],
    ):
        await run_migrations(mock_db, "sqlite")

    # Should have called execute with CREATE TABLE schema_migrations
    create_calls = [
        c for c in mock_db.execute.call_args_list
        if "schema_migrations" in str(c)
    ]
    assert len(create_calls) >= 1


@pytest.mark.asyncio
async def test_runner_applies_new_migration():
    """Runner should apply SQL files not yet in schema_migrations."""
    mock_db = AsyncMock()
    # schema_migrations is empty — no migrations applied yet
    mock_db.query = AsyncMock(return_value=[])
    mock_db.execute = AsyncMock()

    fake_sql = "CREATE TABLE IF NOT EXISTS test_table (id TEXT PRIMARY KEY);"

    with patch(
        "datametronome_podium.core.migrations.runner._get_sql_files",
        return_value=[("001_initial.sql", fake_sql)],
    ):
        await run_migrations(mock_db, "sqlite")

    # Should have executed the migration SQL
    execute_calls = [str(c) for c in mock_db.execute.call_args_list]
    assert any("test_table" in c for c in execute_calls)


@pytest.mark.asyncio
async def test_runner_skips_already_applied():
    """Runner should skip migrations already in schema_migrations."""
    mock_db = AsyncMock()
    # 001 already applied
    mock_db.query = AsyncMock(return_value=[{"filename": "001_initial.sql"}])
    mock_db.execute = AsyncMock()

    fake_sql = "CREATE TABLE IF NOT EXISTS test_table (id TEXT PRIMARY KEY);"

    with patch(
        "datametronome_podium.core.migrations.runner._get_sql_files",
        return_value=[("001_initial.sql", fake_sql)],
    ):
        await run_migrations(mock_db, "sqlite")

    # Should NOT have executed the migration SQL (only schema_migrations CREATE)
    execute_calls = [str(c) for c in mock_db.execute.call_args_list]
    assert not any("test_table" in c for c in execute_calls)
```

- [ ] **Step 3.2: Run tests to verify they fail**

```bash
cd datametronome/podium && python3 -m pytest tests/test_migration_runner.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3.3: Create migrations package marker**

```python
# datametronome/podium/datametronome_podium/core/migrations/__init__.py
```
(empty file)

- [ ] **Step 3.4: Write migration runner**

```python
"""
Lightweight forward-only migration runner.

Scans core/migrations/sql/ for numbered .sql files, applies any not yet
recorded in the schema_migrations table. Each migration runs in a
transaction (where supported).
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_SQL_DIR = os.path.join(os.path.dirname(__file__), "sql")


def _get_sql_files() -> list[tuple[str, str]]:
    """Scan the sql/ directory for migration files, sorted by name.

    Returns:
        List of (filename, sql_content) tuples, sorted by filename.
    """
    if not os.path.isdir(_SQL_DIR):
        logger.warning("Migration sql/ directory not found: %s", _SQL_DIR)
        return []

    files = sorted(f for f in os.listdir(_SQL_DIR) if f.endswith(".sql"))
    result = []
    for fname in files:
        path = os.path.join(_SQL_DIR, fname)
        with open(path, encoding="utf-8") as fh:
            result.append((fname, fh.read()))
    return result


async def run_migrations(db: Any, dialect: str) -> None:
    """Apply any pending migrations.

    Args:
        db: The already-connected DataPulse connector instance.
        dialect: "postgresql" or "sqlite"

    Note: db and dialect are passed in from init_db() to avoid
    circular imports (runner -> get_db -> init_db -> runner).
    """
    from datametronome_podium.core.query_adapter import QueryAdapter

    adapter = QueryAdapter(dialect)

    # Ensure schema_migrations table exists
    create_table_sql = adapter.adapt_ddl(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "  id TEXT PRIMARY KEY,"
        "  filename TEXT NOT NULL,"
        "  applied_at TEXT NOT NULL"
        ")"
    )
    if dialect == "postgresql":
        await db.execute(create_table_sql)
    else:
        await db.execute(create_table_sql)

    # Get already-applied migrations
    applied_rows = await db.query(
        {"sql": "SELECT filename FROM schema_migrations", "params": []}
    )
    applied = {row["filename"] for row in applied_rows}

    # Apply pending migrations
    sql_files = _get_sql_files()
    for filename, sql_content in sql_files:
        if filename in applied:
            logger.debug("Migration already applied: %s", filename)
            continue

        logger.info("Applying migration: %s", filename)
        adapted_sql = adapter.adapt_ddl(sql_content)

        # Execute each statement in the migration file
        statements = [s.strip() for s in adapted_sql.split(";") if s.strip()]
        for stmt in statements:
            if dialect == "postgresql":
                await db.execute(stmt)
            else:
                await db.execute(stmt)

        # Record the migration
        now = datetime.now(timezone.utc).isoformat()
        migration_id = filename.split("_")[0]  # e.g. "001"

        if dialect == "postgresql":
            await db.execute(
                "INSERT INTO schema_migrations (id, filename, applied_at) VALUES ($1, $2, $3)",
                migration_id, filename, now,
            )
        else:
            await db.execute(
                "INSERT INTO schema_migrations (id, filename, applied_at) VALUES (?, ?, ?)",
                [migration_id, filename, now],
            )

        logger.info("Migration applied: %s", filename)

# Note: Migrations do NOT run inside transactions currently.
# If a migration partially fails, manual cleanup is required.
# This is a known limitation of this lightweight runner.
# Transaction wrapping can be added later if needed.
```

- [ ] **Step 3.5: Run tests to verify they pass**

```bash
cd datametronome/podium && python3 -m pytest tests/test_migration_runner.py -v
```
Expected: all PASS

- [ ] **Step 3.6: Commit**

```bash
cd datametronome/podium
git add datametronome_podium/core/migrations/__init__.py datametronome_podium/core/migrations/runner.py tests/test_migration_runner.py
git commit -m "feat: add lightweight forward-only migration runner"
```

### Task 4: Initial schema migration file

**Context:** Move all existing table DDL from the old `database.py` into a proper migration file. Written in PostgreSQL dialect; the adapter translates for SQLite.

**Files:**
- Create: `datametronome/podium/datametronome_podium/core/migrations/sql/001_initial_schema.sql`

- [ ] **Step 4.1: Create the SQL directory**

```bash
mkdir -p datametronome/podium/datametronome_podium/core/migrations/sql
```

- [ ] **Step 4.2: Write the initial schema migration**

```sql
-- 001_initial_schema.sql
-- All existing DataMetronome tables, ported from inline DDL in database.py.
-- Written in PostgreSQL dialect. The QueryAdapter translates JSONB→TEXT
-- and DOUBLE PRECISION→REAL for SQLite.

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staves (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    data_source_type TEXT NOT NULL,
    connection_config TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clefs (
    id TEXT PRIMARY KEY,
    stave_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    check_type TEXT NOT NULL,
    config TEXT NOT NULL,
    warn TEXT,
    fail TEXT,
    retry_config TEXT,
    schedule TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (stave_id) REFERENCES staves (id)
);

CREATE TABLE IF NOT EXISTS checks (
    id TEXT PRIMARY KEY,
    stave_id TEXT NOT NULL,
    clef_id TEXT NOT NULL,
    check_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    details TEXT,
    timestamp TEXT NOT NULL,
    execution_time DOUBLE PRECISION,
    anomalies_count INTEGER DEFAULT 0,
    severity TEXT DEFAULT 'medium',
    FOREIGN KEY (stave_id) REFERENCES staves (id),
    FOREIGN KEY (clef_id) REFERENCES clefs (id)
);

CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id TEXT PRIMARY KEY,
    clef_id TEXT NOT NULL,
    schedule TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    last_run_time TEXT,
    next_run_time TEXT,
    execution_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_executions (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    clef_id TEXT NOT NULL,
    status TEXT NOT NULL,
    execution_time DOUBLE PRECISION,
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (job_id) REFERENCES scheduler_jobs (id) ON DELETE CASCADE,
    FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anomalies (
    id TEXT PRIMARY KEY,
    check_id TEXT NOT NULL,
    table_name TEXT,
    column_name TEXT,
    anomaly_type TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'medium',
    detected_at TEXT NOT NULL,
    data_sample TEXT,
    resolution_status TEXT DEFAULT 'investigating',
    FOREIGN KEY (check_id) REFERENCES checks (id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls TEXT,
    tool_results TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_traces (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_message_preview TEXT,
    intent TEXT,
    model TEXT,
    tool_calls TEXT,
    duration_ms DOUBLE PRECISION,
    created_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_traces_conversation_id ON agent_traces(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_user_id ON agent_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_created_at ON agent_traces(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_traces_intent ON agent_traces(intent);
```

Note: The `CHECK(role IN ('user', 'assistant', 'system'))` constraint from the original DDL is removed — PostgreSQL handles this fine but it adds no value since the application already validates roles. `REAL` has been changed to `DOUBLE PRECISION` (PostgreSQL canonical; adapter maps to `REAL` for SQLite).

- [ ] **Step 4.3: Verify the migration runner picks up the file**

```bash
cd datametronome/podium && python3 -c "
from datametronome_podium.core.migrations.runner import _get_sql_files
files = _get_sql_files()
print(f'Found {len(files)} migration(s): {[f[0] for f in files]}')
assert len(files) == 1
assert files[0][0] == '001_initial_schema.sql'
print('OK')
"
```
Expected: `Found 1 migration(s): ['001_initial_schema.sql']` + `OK`

- [ ] **Step 4.4: Commit**

```bash
cd datametronome/podium
git add datametronome_podium/core/migrations/sql/001_initial_schema.sql
git commit -m "feat: add 001_initial_schema.sql migration (all existing tables)"
```

---

## Chunk 4: Agent State Tables

### Task 5: Agent state migration file

**Files:**
- Create: `datametronome/podium/datametronome_podium/core/migrations/sql/002_agent_state.sql`

- [ ] **Step 5.1: Write the agent state migration**

```sql
-- 002_agent_state.sql
-- LangGraph-style agent workflow state tables.
-- Enables: checkpointing (pause/resume), declarative workflow definitions,
-- and full event audit trail with replay capability.

CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    current_node TEXT,
    state_data JSONB,
    status TEXT NOT NULL DEFAULT 'running',
    parent_checkpoint_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (parent_checkpoint_id) REFERENCES workflow_checkpoints (id)
);

CREATE INDEX IF NOT EXISTS idx_wf_checkpoints_conversation ON workflow_checkpoints(conversation_id);
CREATE INDEX IF NOT EXISTS idx_wf_checkpoints_status ON workflow_checkpoints(status);

CREATE TABLE IF NOT EXISTS workflow_definitions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    graph_data JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id TEXT PRIMARY KEY,
    checkpoint_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    node_name TEXT,
    event_data JSONB,
    created_at TEXT NOT NULL,
    FOREIGN KEY (checkpoint_id) REFERENCES workflow_checkpoints (id)
);

CREATE INDEX IF NOT EXISTS idx_wf_events_checkpoint_created ON workflow_events(checkpoint_id, created_at);
```

- [ ] **Step 5.2: Verify the runner sees both migration files**

```bash
cd datametronome/podium && python3 -c "
from datametronome_podium.core.migrations.runner import _get_sql_files
files = _get_sql_files()
print(f'Found {len(files)} migration(s): {[f[0] for f in files]}')
assert len(files) == 2
print('OK')
"
```
Expected: `Found 2 migration(s): ['001_initial_schema.sql', '002_agent_state.sql']` + `OK`

- [ ] **Step 5.3: Commit**

```bash
cd datametronome/podium
git add datametronome_podium/core/migrations/sql/002_agent_state.sql
git commit -m "feat: add 002_agent_state.sql migration (checkpoints, definitions, events)"
```

### Task 6: Workflow state service

**Context:** A thin async service that wraps the workflow tables with CRUD operations. The orchestrator will call these functions to save/restore state and log events.

**Files:**
- Create: `datametronome/podium/datametronome_podium/services/workflow_state.py`
- Create: `datametronome/podium/tests/test_workflow_state.py`

- [ ] **Step 6.1: Write failing tests for workflow state service**

```python
"""Tests for workflow state service."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from datametronome_podium.services.workflow_state import (
    create_checkpoint,
    update_checkpoint,
    load_checkpoint,
    find_active_checkpoint,
    log_event,
)


@pytest.mark.asyncio
async def test_create_checkpoint():
    """create_checkpoint should insert a row and return the checkpoint ID."""
    with patch(
        "datametronome_podium.services.workflow_state.insert_data",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_insert:
        cp_id = await create_checkpoint("conv-1", "user-1", "chain:inv→report")

        assert cp_id is not None
        assert isinstance(cp_id, str)
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "workflow_checkpoints"
        data = call_args[0][1]
        assert data["conversation_id"] == "conv-1"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_update_checkpoint():
    """update_checkpoint should update status and state_data."""
    with patch(
        "datametronome_podium.services.workflow_state.execute_write",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_write:
        await update_checkpoint(
            "cp-1", current_node="investigation", state_data={"step": 1}, status="running"
        )
        mock_write.assert_called_once()
        sql = mock_write.call_args[0][0]
        assert "UPDATE workflow_checkpoints" in sql


@pytest.mark.asyncio
async def test_load_checkpoint():
    """load_checkpoint should return the checkpoint dict."""
    fake_row = {
        "id": "cp-1",
        "conversation_id": "conv-1",
        "workflow_name": "single:report",
        "current_node": "report",
        "state_data": '{"step": 1}',
        "status": "running",
    }
    with patch(
        "datametronome_podium.services.workflow_state.execute_query",
        new_callable=AsyncMock,
        return_value=[fake_row],
    ):
        result = await load_checkpoint("cp-1")
        assert result["id"] == "cp-1"
        assert result["status"] == "running"


@pytest.mark.asyncio
async def test_find_active_checkpoint_found():
    """find_active_checkpoint should return latest running/paused checkpoint."""
    fake_row = {"id": "cp-2", "status": "paused", "workflow_name": "chain:inv→report"}
    with patch(
        "datametronome_podium.services.workflow_state.execute_query",
        new_callable=AsyncMock,
        return_value=[fake_row],
    ):
        result = await find_active_checkpoint("conv-1")
        assert result is not None
        assert result["id"] == "cp-2"


@pytest.mark.asyncio
async def test_find_active_checkpoint_none():
    """find_active_checkpoint should return None when no active checkpoint."""
    with patch(
        "datametronome_podium.services.workflow_state.execute_query",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await find_active_checkpoint("conv-1")
        assert result is None


@pytest.mark.asyncio
async def test_log_event():
    """log_event should insert a workflow_events row."""
    with patch(
        "datametronome_podium.services.workflow_state.insert_data",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_insert:
        await log_event("cp-1", "node_entered", "investigation", {"message": "start"})

        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "workflow_events"
        data = call_args[0][1]
        assert data["checkpoint_id"] == "cp-1"
        assert data["event_type"] == "node_entered"
```

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
cd datametronome/podium && python3 -m pytest tests/test_workflow_state.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 6.3: Write workflow state service**

```python
"""
Workflow state service — CRUD for agent checkpoints and event logging.

Provides the persistence layer for LangGraph-style stateful orchestration:
- Checkpoints: save/restore orchestrator execution state
- Events: full audit trail of every state transition
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from datametronome_podium.core.database import execute_query, execute_write, insert_data

logger = logging.getLogger(__name__)


async def create_checkpoint(
    conversation_id: str,
    user_id: str,
    workflow_name: str,
) -> str:
    """Create a new workflow checkpoint.

    Returns:
        The checkpoint ID.
    """
    checkpoint_id = f"wf-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    await insert_data("workflow_checkpoints", {
        "id": checkpoint_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "workflow_name": workflow_name,
        "current_node": None,
        "state_data": json.dumps({}),
        "status": "running",
        "parent_checkpoint_id": None,
        "created_at": now,
        "updated_at": now,
    })

    logger.info("Created checkpoint %s for %s", checkpoint_id, workflow_name)
    return checkpoint_id


async def update_checkpoint(
    checkpoint_id: str,
    *,
    current_node: str | None = None,
    state_data: dict | None = None,
    status: str | None = None,
) -> None:
    """Update a checkpoint's current state."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    set_parts = ["updated_at = ?"]
    params: list = [now]

    if current_node is not None:
        set_parts.append("current_node = ?")
        params.append(current_node)
    if state_data is not None:
        set_parts.append("state_data = ?")
        params.append(json.dumps(state_data))
    if status is not None:
        set_parts.append("status = ?")
        params.append(status)

    params.append(checkpoint_id)
    sql = f"UPDATE workflow_checkpoints SET {', '.join(set_parts)} WHERE id = ?"
    await execute_write(sql, params)


async def load_checkpoint(checkpoint_id: str) -> dict | None:
    """Load a checkpoint by ID. Returns None if not found."""
    rows = await execute_query(
        "SELECT * FROM workflow_checkpoints WHERE id = ?", [checkpoint_id]
    )
    return rows[0] if rows else None


async def find_active_checkpoint(conversation_id: str) -> dict | None:
    """Find the latest running or paused checkpoint for a conversation."""
    rows = await execute_query(
        "SELECT * FROM workflow_checkpoints "
        "WHERE conversation_id = ? AND status IN ('running', 'paused') "
        "ORDER BY created_at DESC LIMIT 1",
        [conversation_id],
    )
    return rows[0] if rows else None


async def log_event(
    checkpoint_id: str,
    event_type: str,
    node_name: str | None,
    event_data: dict | None = None,
) -> None:
    """Log a workflow event (state transition, tool call, error, etc.)."""
    event_id = f"evt-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    await insert_data("workflow_events", {
        "id": event_id,
        "checkpoint_id": checkpoint_id,
        "event_type": event_type,
        "node_name": node_name,
        "event_data": json.dumps(event_data) if event_data else None,
        "created_at": now,
    })
```

- [ ] **Step 6.4: Run tests to verify they pass**

```bash
cd datametronome/podium && python3 -m pytest tests/test_workflow_state.py -v
```
Expected: all PASS

- [ ] **Step 6.5: Commit**

```bash
cd datametronome/podium
git add datametronome_podium/services/workflow_state.py tests/test_workflow_state.py
git commit -m "feat: add workflow state service (checkpoints + event logging)"
```

---

## Chunk 5: Orchestrator Wiring + Endpoint Update

### Task 7: Wire orchestrator with checkpoint and event logging

**Context:** `run_chat()` gains state awareness — creates checkpoints, logs events on state transitions, handles resume from paused checkpoints. The changes are additive.

**Files:**
- Modify: `datametronome/podium/datametronome_podium/services/orchestrator.py`
- Modify: `datametronome/podium/datametronome_podium/api/v1/endpoints/chat.py` (line 198-201)
- Modify: `datametronome/podium/tests/test_orchestrator.py`

- [ ] **Step 7.1: Write failing test for orchestrator checkpoint integration**

Add to `tests/test_orchestrator.py`:

```python
@pytest.mark.asyncio
async def test_run_chat_creates_checkpoint(monkeypatch):
    """run_chat should create a checkpoint and log events."""
    from datametronome_podium.services import orchestrator
    from unittest.mock import AsyncMock, call

    # Mock router
    mock_router = AsyncMock()
    mock_router.run = AsyncMock(return_value=AsyncMock(
        output=RoutingDecision(intent="quick", mode="single", agents=["report"], reasoning="test")
    ))
    monkeypatch.setattr(orchestrator, "_get_router_agent", lambda: mock_router)

    # Mock report agent
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=AsyncMock(output="Test response"))
    monkeypatch.setattr(orchestrator, "_get_report_agent", lambda: mock_agent)

    # Mock workflow state functions
    mock_create = AsyncMock(return_value="cp-123")
    mock_update = AsyncMock()
    mock_log = AsyncMock()
    mock_find = AsyncMock(return_value=None)

    monkeypatch.setattr(orchestrator, "create_checkpoint", mock_create)
    monkeypatch.setattr(orchestrator, "update_checkpoint", mock_update)
    monkeypatch.setattr(orchestrator, "log_event", mock_log)
    monkeypatch.setattr(orchestrator, "find_active_checkpoint", mock_find)

    result = await orchestrator.run_chat(
        message="Hello",
        history=[],
        conversation_id="conv-1",
        user_id="user-1",
    )

    assert result["message"] == "Test response"
    mock_create.assert_called_once()
    # Should log at least node_entered and node_completed
    assert mock_log.call_count >= 2
    # Should update checkpoint to completed
    completed_calls = [
        c for c in mock_update.call_args_list
        if c.kwargs.get("status") == "completed"
    ]
    assert len(completed_calls) == 1
```

- [ ] **Step 7.2: Run test to verify it fails**

```bash
cd datametronome/podium && python3 -m pytest tests/test_orchestrator.py::test_run_chat_creates_checkpoint -v
```
Expected: FAIL

- [ ] **Step 7.3: Update orchestrator.py with checkpoint wiring**

Add imports at the top of `orchestrator.py`:

```python
from datametronome_podium.services.workflow_state import (
    create_checkpoint,
    update_checkpoint,
    find_active_checkpoint,
    log_event,
)
```

Update `run_chat()` signature and body:

```python
async def run_chat(
    message: str,
    history: list[dict],
    *,
    conversation_id: str | None = None,
    user_id: str | None = None,
    router_history_window: int = 6,
) -> dict[str, Any]:
    """Run the full chat pipeline: route -> dispatch -> respond.

    Args:
        message: Current user message
        history: Full conversation history as list of {role, content} dicts
        conversation_id: Conversation ID for checkpoint tracking
        user_id: User ID for checkpoint tracking
        router_history_window: How many recent messages to send to the router

    Returns:
        dict with keys: message, intent, mode, agents, model
    """
    all_history = convert_history_to_messages(history)
    router_history = all_history[-router_history_window:] if all_history else []

    router = _get_router_agent()
    routing_result = await router.run(message, message_history=router_history)
    decision: RoutingDecision = routing_result.output

    logger.info(
        "Router decision: intent=%s mode=%s agents=%s reasoning=%r",
        decision.intent, decision.mode, decision.agents, decision.reasoning,
    )

    # Check for paused checkpoint to resume, or create a new one
    checkpoint_id = None
    if conversation_id and user_id:
        existing = await find_active_checkpoint(conversation_id)
        if existing and existing["status"] == "paused":
            checkpoint_id = existing["id"]
            logger.info("Resuming paused checkpoint %s", checkpoint_id)
            await update_checkpoint(checkpoint_id, status="running")
            await log_event(checkpoint_id, "node_entered", "resume", {
                "resumed_from": existing.get("current_node"),
            })
        else:
            workflow_name = f"{decision.mode}:{'+'.join(decision.agents)}"
            checkpoint_id = await create_checkpoint(conversation_id, user_id, workflow_name)
        await log_event(checkpoint_id, "decision_made", "router", {
            "intent": decision.intent,
            "mode": decision.mode,
            "agents": decision.agents,
            "reasoning": decision.reasoning,
        })

    try:
        if decision.mode == "parallel" and len(decision.agents) >= 2:
            response_message = await _run_parallel(message, decision, all_history, checkpoint_id)
        elif decision.mode == "chain" and len(decision.agents) >= 2:
            response_message = await _run_chain(message, decision, all_history, checkpoint_id)
        else:
            response_message = await _run_single(message, decision, all_history, checkpoint_id)

        if checkpoint_id:
            await update_checkpoint(checkpoint_id, status="completed")

    except Exception as e:
        if checkpoint_id:
            await log_event(checkpoint_id, "error", None, {"error": str(e)})
            await update_checkpoint(checkpoint_id, status="failed")
        raise

    return {
        "message": response_message,
        "intent": decision.intent,
        "mode": decision.mode,
        "agents": decision.agents,
        "model": "pydantic-ai",
    }
```

Update `_run_single`:

```python
async def _run_single(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
    checkpoint_id: str | None = None,
) -> str:
    agent_type = decision.agents[0] if decision.agents else "report"

    if checkpoint_id:
        await log_event(checkpoint_id, "node_entered", agent_type)
        await update_checkpoint(checkpoint_id, current_node=agent_type)

    agent = _get_agent_builder(agent_type)()
    result = await agent.run(message, message_history=history)
    output = str(result.output)

    if checkpoint_id:
        await log_event(checkpoint_id, "node_completed", agent_type, {
            "output_preview": output[:200],
        })

    return output
```

Update `_run_chain`:

```python
async def _run_chain(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
    checkpoint_id: str | None = None,
) -> str:
    """Run agents in sequence. Each agent after the first receives the previous output."""
    previous_output = ""
    last_result = ""

    for i, agent_type in enumerate(decision.agents):
        if checkpoint_id:
            await log_event(checkpoint_id, "node_entered", agent_type, {"step": i})
            await update_checkpoint(checkpoint_id, current_node=agent_type)

        agent = _get_agent_builder(agent_type)()

        if i == 0:
            msg_to_send = message
        else:
            msg_to_send = (
                f"INVESTIGATION FINDINGS:\n{previous_output}\n\n"
                f"USER'S REQUEST: {message}\n\n"
                "Using the findings above, address the user's request "
                "(suggest fixes, recommend checks, or propose remedial actions)."
            )

        result = await agent.run(msg_to_send, message_history=history)
        previous_output = str(result.output)
        last_result = previous_output

        if checkpoint_id:
            await log_event(checkpoint_id, "node_completed", agent_type, {
                "step": i,
                "output_preview": previous_output[:200],
            })
            await update_checkpoint(
                checkpoint_id,
                state_data={"step": i, "agent": agent_type, "output": previous_output[:500]},
            )

    return last_result
```

Update `_run_parallel`:

```python
async def _run_parallel(
    message: str,
    decision: RoutingDecision,
    history: list[ModelMessage],
    checkpoint_id: str | None = None,
) -> str:
    """Run agents concurrently, combine their outputs."""
    if checkpoint_id:
        for agent_type in decision.agents:
            await log_event(checkpoint_id, "node_entered", agent_type)
        await update_checkpoint(checkpoint_id, current_node=",".join(decision.agents))

    async def run_agent(agent_type: str) -> tuple[str, str]:
        agent = _get_agent_builder(agent_type)()
        result = await agent.run(message, message_history=history)
        return agent_type, str(result.output)

    results = await asyncio.gather(
        *[run_agent(atype) for atype in decision.agents],
        return_exceptions=True,
    )

    parts = []
    for r in results:
        if isinstance(r, Exception):
            parts.append(f"[Error: {r}]")
            if checkpoint_id:
                await log_event(checkpoint_id, "error", None, {"error": str(r)})
        else:
            agent_type, text = r
            if text:
                parts.append(f"**{agent_type.title()}:**\n{text}")
            if checkpoint_id:
                await log_event(checkpoint_id, "node_completed", agent_type, {
                    "output_preview": text[:200],
                })

    return "\n\n---\n\n".join(parts) if parts else "No responses received."
```

- [ ] **Step 7.4: Update chat.py to pass conversation_id and user_id to run_chat**

In `api/v1/endpoints/chat.py` lines 198-201, change:

```python
        # Run the AI pipeline (router → sub-agents)
        agent_result = await run_chat(
            message=request.message,
            history=history_messages,
            conversation_id=conversation_id,
            user_id=user_id,
        )
```

- [ ] **Step 7.5: Run tests**

```bash
cd datametronome/podium && python3 -m pytest tests/test_orchestrator.py -v
```
Expected: all PASS (existing tests should still pass since conversation_id/user_id default to None, which skips checkpointing)

- [ ] **Step 7.6: Commit**

```bash
cd datametronome/podium
git add datametronome_podium/services/orchestrator.py datametronome_podium/api/v1/endpoints/chat.py tests/test_orchestrator.py
git commit -m "feat: wire orchestrator with checkpoint + event logging"
```

---

## Chunk 6: Infrastructure + E2E Verification

### Task 8: Update docker-compose and create env.example

**Files:**
- Modify: `docker-compose.yml`
- Create: `env.example`

- [ ] **Step 8.1: Update docker-compose.yml podium DATABASE_URL**

In `docker-compose.yml` line 33, change:

```yaml
      - DATAMETRONOME_DATABASE_URL=postgresql://testuser:testpass@postgres:5432/datametronome_test
```

- [ ] **Step 8.2: Create env.example**

```bash
# DataMetronome Podium Environment Configuration

# Database (PostgreSQL is the default; SQLite supported as fallback)
DATAMETRONOME_DATABASE_URL=postgresql://testuser:testpass@localhost:5432/datametronome_test
# For SQLite fallback:
# DATAMETRONOME_DATABASE_URL=sqlite:///./data/datametronome.db

# Security
DATAMETRONOME_SECRET_KEY=your-super-secret-key-that-is-at-least-32-characters-long

# Server
DATAMETRONOME_HOST=0.0.0.0
DATAMETRONOME_PORT=8001
DATAMETRONOME_DEBUG=true

# CORS
DATAMETRONOME_ALLOWED_ORIGINS=http://localhost:3000

# AI Agent Configuration
# Provider: anthropic | openai | gemini | ollama (default: ollama)
DATAMETRONOME_AI_PROVIDER=ollama

# Model name for the main agents
DATAMETRONOME_AI_MODEL=qwen2.5

# API key (not needed for Ollama)
# DATAMETRONOME_AI_API_KEY=your-api-key-here

# Optional: cheaper/faster model for the routing step only
# DATAMETRONOME_AI_ROUTER_MODEL=claude-haiku-4-5

# Base URL (required for Ollama; optional for custom OpenAI-compatible endpoints)
# DATAMETRONOME_AI_BASE_URL=http://localhost:11434/v1

# Ollama API base (legacy — used when AI_PROVIDER=ollama and AI_BASE_URL is unset)
# OLLAMA_API_BASE=http://localhost:11434

# Examples for other providers:
# Anthropic (Claude):
#   DATAMETRONOME_AI_PROVIDER=anthropic
#   DATAMETRONOME_AI_MODEL=claude-sonnet-4-6
#   DATAMETRONOME_AI_API_KEY=sk-ant-...
#   DATAMETRONOME_AI_ROUTER_MODEL=claude-haiku-4-5

# OpenAI:
#   DATAMETRONOME_AI_PROVIDER=openai
#   DATAMETRONOME_AI_MODEL=gpt-4o
#   DATAMETRONOME_AI_API_KEY=sk-...

# Google Gemini:
#   DATAMETRONOME_AI_PROVIDER=gemini
#   DATAMETRONOME_AI_MODEL=gemini-1.5-flash
#   DATAMETRONOME_AI_API_KEY=your-gemini-key
```

- [ ] **Step 8.3: Commit**

```bash
git add docker-compose.yml env.example
git commit -m "chore: update docker-compose for PostgreSQL default, add env.example"
```

### Task 9: End-to-end verification

- [ ] **Step 9.1: Start PostgreSQL via docker-compose**

```bash
docker-compose up -d postgres
docker-compose exec postgres pg_isready -U testuser -d datametronome_test
```
Expected: `accepting connections`

- [ ] **Step 9.2: Run the full test suite**

```bash
cd datametronome/podium && python3 -m pytest tests/ -v -k "not integration" 2>&1 | tail -60
```
Expected: all PASS

- [ ] **Step 9.3: Start the server against PostgreSQL**

```bash
cd datametronome/podium
export DATAMETRONOME_DATABASE_URL=postgresql://testuser:testpass@localhost:5432/datametronome_test
export DATAMETRONOME_AI_PROVIDER=ollama
export DATAMETRONOME_AI_MODEL=qwen2.5
python3 -m uvicorn datametronome_podium.main:app --port 8001 --reload
```

- [ ] **Step 9.4: Verify tables were created**

```bash
docker-compose exec postgres psql -U testuser -d datametronome_test -c "\dt"
```
Expected: all tables including `schema_migrations`, `workflow_checkpoints`, `workflow_definitions`, `workflow_events`

- [ ] **Step 9.5: Send a test chat request**

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/token \
  -d "username=admin&password=admin" | jq -r .access_token)

curl -s -X POST http://localhost:8001/api/v1/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "How many data sources do I have?"}' | jq .
```
Expected: JSON response with `intent`, `orchestrationMode`, `agentType` fields

- [ ] **Step 9.6: Verify checkpoint was created**

```bash
docker-compose exec postgres psql -U testuser -d datametronome_test -c \
  "SELECT id, workflow_name, status, current_node FROM workflow_checkpoints ORDER BY created_at DESC LIMIT 5;"
```
Expected: at least one row with `status = 'completed'`

- [ ] **Step 9.7: Verify events were logged**

```bash
docker-compose exec postgres psql -U testuser -d datametronome_test -c \
  "SELECT event_type, node_name, created_at FROM workflow_events ORDER BY created_at DESC LIMIT 10;"
```
Expected: `decision_made`, `node_entered`, `node_completed` events

- [ ] **Step 9.8: Run all tests one final time**

```bash
cd datametronome/podium && python3 -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 9.9: Final commit**

```bash
git add -A
git commit -m "feat: complete PostgreSQL migration with agent state management"
```

---

## Summary

| Chunk | Tasks | What it delivers |
|-------|-------|-----------------|
| 1 | QueryAdapter | SQL dialect translation (placeholders, DDL types, booleans) |
| 2 | Database rewrite | Connector factory, normalization layer, PostgreSQL default |
| 3 | Migration system | Runner + 001_initial_schema.sql |
| 4 | Agent state | 002_agent_state.sql + workflow_state.py service |
| 5 | Orchestrator wiring | Checkpoint/event integration in run_chat + chat.py update |
| 6 | Infrastructure + E2E | docker-compose, env.example, end-to-end verification |
