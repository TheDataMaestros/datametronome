"""Tests for database connector factory and normalization."""
import pytest

from datametronome_podium.core.database import (
    _parse_pg_url,
    _parse_sqlite_path,
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


class TestDeprecatedFunctionsRemoved:
    """Verify deprecated functions were removed from the public API."""

    def test_execute_query_not_exported(self):
        import datametronome_podium.core.database as db_module
        assert not hasattr(db_module, "execute_query")

    def test_execute_write_not_exported(self):
        import datametronome_podium.core.database as db_module
        assert not hasattr(db_module, "execute_write")

    def test_insert_data_not_exported(self):
        import datametronome_podium.core.database as db_module
        assert not hasattr(db_module, "insert_data")
