"""Unit tests for registration duplicate-key detection."""

import importlib.util
import sqlite3

import pytest

from datametronome_podium.features.auth.router import (
    _is_duplicate_user_insert,
    _pg_unique_violation,
)


def test_sqlite_unique_constraint_is_duplicate() -> None:
    e = sqlite3.IntegrityError("UNIQUE constraint failed: users.username")
    assert _is_duplicate_user_insert(e)


def test_sqlite_not_null_is_not_duplicate() -> None:
    e = sqlite3.IntegrityError("NOT NULL constraint failed: users.email")
    assert not _is_duplicate_user_insert(e)


def test_pg_sqlstate_23505_on_wrapped_exception() -> None:
    class Fake23505(Exception):
        sqlstate = "23505"

    assert _pg_unique_violation(Fake23505())
    assert _is_duplicate_user_insert(Fake23505())


@pytest.mark.skipif(
    importlib.util.find_spec("asyncpg") is None,
    reason="asyncpg not installed",
)
def test_asyncpg_unique_violation() -> None:
    import asyncpg

    e = asyncpg.exceptions.UniqueViolationError("duplicate key value")
    assert _pg_unique_violation(e)
    assert _is_duplicate_user_insert(e)
