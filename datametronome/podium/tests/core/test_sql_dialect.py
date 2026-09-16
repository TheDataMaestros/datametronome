"""The dialect table that replaced the per-check if/elif chains.

Those chains were the bug surface: most arms held byte-identical SQL, they
disagreed with each other about which sources a check supported, and a new
source meant finding all seven. These tests pin the parts that genuinely
differ so the table can be extended without reading the check code.
"""

import pytest

from datametronome_podium.core.sql_dialect import (
    DIALECTS,
    Dialect,
    dialect_for,
    quote_literal,
)


def d(name: str) -> Dialect:
    """Look a dialect up and fail loudly if it is missing."""
    dialect = dialect_for(name)
    assert dialect is not None, f"no dialect registered for {name!r}"
    return dialect


def test_every_source_the_connector_factory_builds_has_a_dialect():
    # A stave type with a connector but no dialect can be created and can pass
    # a connection test, and then every check against it fails as
    # unsupported_data_source. Keep the two lists in step.
    from datametronome_podium.features.staves.model import SUPPORTED_DATA_SOURCES

    missing = [t for t in SUPPORTED_DATA_SOURCES if dialect_for(t) is None]
    # dbt is artifact metadata, not a SQL target, so it has no dialect.
    assert missing == ["dbt"]


def test_unknown_source_returns_none():
    assert dialect_for("cassandra") is None
    assert dialect_for("") is None
    assert dialect_for(None) is None


def test_lookup_is_case_insensitive():
    assert dialect_for("PostgreSQL") is DIALECTS["postgresql"]


class TestQuoting:
    def test_ansi_sources_use_double_quotes(self):
        assert d("postgres").quote("users") == '"users"'
        assert d("redshift").quote("users") == '"users"'
        assert d("s3").quote("users") == '"users"'

    def test_bigquery_uses_backticks(self):
        assert d("bigquery").quote("users") == "`users`"

    def test_dotted_names_quote_each_segment(self):
        assert d("postgres").quote("public.users") == '"public"."users"'


class TestCountIf:
    def test_most_sources_use_case_when(self):
        assert (
            d("postgres").counted("x > 1")
            == "COUNT(CASE WHEN x > 1 THEN 1 END)"
        )

    def test_bigquery_uses_countif(self):
        assert d("bigquery").counted("x > 1") == "COUNTIF(x > 1)"


class TestRegex:
    def test_postgres_and_redshift_use_the_posix_operator(self):
        for name in ("postgres", "postgresql", "redshift"):
            assert d(name).matches('"c"', "^a") == "\"c\" ~ '^a'"

    def test_duckdb_has_no_tilde_operator(self):
        # An s3 stave running ~ would fail at parse time.
        expr = d("s3").matches('"c"', "^a")
        assert expr == "regexp_matches(\"c\", '^a')"
        assert "~" not in expr

    def test_bigquery_keeps_the_raw_string_prefix(self):
        # Without r, BigQuery consumes backslashes as string escapes before
        # the regex engine sees them, so \d stops meaning a digit.
        expr = d("bigquery").matches("`c`", r"\d+")
        assert expr == "REGEXP_CONTAINS(`c`, r'\\d+')"

    def test_mysql_uses_the_regexp_keyword(self):
        assert d("mysql").matches("`c`", "^a") == "`c` REGEXP '^a'"

    def test_sqlite_declares_no_regex_support(self):
        assert d("sqlite").supports_regex is False
        with pytest.raises(ValueError, match="no regular expression support"):
            d("sqlite").matches('"c"', "^a")

    def test_a_quote_in_a_pattern_cannot_escape_the_literal(self):
        expr = d("postgres").matches('"c"', "it's")
        assert expr == "\"c\" ~ 'it''s'"


class TestInList:
    def test_values_are_quoted_individually(self):
        assert d("postgres").in_list('"c"', ["a", "b"]) == (
            "\"c\" IN ('a', 'b')"
        )

    def test_non_strings_are_coerced(self):
        assert d("postgres").in_list('"c"', [1, 2]) == "\"c\" IN ('1', '2')"

    def test_an_embedded_quote_is_doubled(self):
        # The old code did this by hand in four places, each spelled slightly
        # differently.
        assert d("postgres").in_list('"c"', ["o'brien"]) == (
            "\"c\" IN ('o''brien')"
        )

    def test_a_value_cannot_close_the_list_and_append_sql(self):
        sql = d("postgres").in_list('"c"', ["x') OR 1=1 --"])
        assert sql.count("'") % 2 == 0
        assert "''" in sql


def test_quote_literal_doubles_quotes():
    assert quote_literal("a'b") == "'a''b'"
    assert quote_literal("plain") == "'plain'"
