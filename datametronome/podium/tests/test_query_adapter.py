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
        assert "$1" in sql
        assert params == ["test"]

    def test_doubled_quotes_handled(self):
        """PostgreSQL uses '' for escaping inside strings, not backslash."""
        adapter = QueryAdapter("postgresql")
        sql, params = adapter.adapt(
            "SELECT * FROM t WHERE name = ? AND note = 'it''s fine'", ["test"]
        )
        assert sql == "SELECT * FROM t WHERE name = $1 AND note = 'it''s fine'"


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
