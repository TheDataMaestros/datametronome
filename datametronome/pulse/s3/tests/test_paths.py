"""Path to S3 URI.

Format detection is DuckDB's job, not this module's, so there is nothing here
about extensions. test_connector.py covers a CSV and a Parquet table side by
side, which is what proves the detection works.
"""

from metronome_pulse_s3.paths import quote_literal, scan_expression


def test_relative_path_is_resolved_against_the_bucket():
    assert scan_expression("analytics", "users/*.parquet") == (
        "'s3://analytics/users/*.parquet'"
    )


def test_leading_slash_does_not_double_up():
    assert scan_expression("analytics", "/users/a.parquet") == (
        "'s3://analytics/users/a.parquet'"
    )


def test_absolute_uri_overrides_the_bucket():
    # A stave that has to span buckets sets a full URI on the one table.
    assert scan_expression("analytics", "s3://other/x.csv") == "'s3://other/x.csv'"


def test_quote_doubles_embedded_quotes():
    # Without this, a path with an apostrophe closes the literal and the rest
    # of it parses as SQL.
    assert quote_literal("o'brien") == "'o''brien'"


def test_path_with_a_quote_stays_inside_the_literal():
    expr = scan_expression("b", "x'; DROP TABLE t; --.parquet")
    assert expr.count("'") % 2 == 0
    assert "''" in expr
