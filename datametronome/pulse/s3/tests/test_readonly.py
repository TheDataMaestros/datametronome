"""The read-only guard.

DuckDB can write to S3 and to local disk, and its execute() runs every
statement in the string it is handed. The guard uses DuckDB's own parser to
classify the statement, so these tests are mostly about what that classifies
as a read.
"""

import pytest

from metronome_pulse_s3.connector import _assert_read_only


@pytest.mark.parametrize(
    "sql",
    [
        'SELECT COUNT(*) FROM "users"',
        "  select 1  ",
        "WITH t AS (SELECT 1) SELECT * FROM t",
        'DESCRIBE SELECT * FROM "users"',
        "EXPLAIN SELECT 1",
        'SUMMARIZE SELECT * FROM "orders"',
        "SELECT 1;",  # a single trailing semicolon is still one statement
    ],
)
def test_reads_are_allowed(sql):
    _assert_read_only(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "COPY users TO 's3://bucket/exfil.parquet'",
        "ATTACH 'other.db'",
        "INSTALL spatial",
        "LOAD spatial",
        "CREATE TABLE t AS SELECT 1",
        "DROP VIEW users",
        "INSERT INTO users VALUES (1)",
        "",  # parses to zero statements
    ],
)
def test_writes_are_rejected(sql):
    with pytest.raises(ValueError):
        _assert_read_only(sql)


def test_a_read_followed_by_a_write_is_rejected():
    # The case a leading-verb check would miss.
    with pytest.raises(ValueError, match="one statement"):
        _assert_read_only("SELECT 1; COPY users TO 's3://bucket/exfil.parquet'")


def test_semicolon_inside_a_literal_is_not_a_second_statement():
    _assert_read_only("SELECT * FROM t WHERE note = 'a; b'")


def test_a_literal_value_named_delete_is_allowed():
    # A keyword blocklist would reject this legitimate check.
    _assert_read_only("SELECT COUNT(*) FROM t WHERE action = 'delete'")


def test_unparseable_sql_is_rejected():
    with pytest.raises(Exception):
        _assert_read_only("not sql at all ((")
