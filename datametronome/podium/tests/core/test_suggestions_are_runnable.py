"""A suggested check must be one the executor can actually run.

The suggester emitted two conditions that could not: "if_out_of_range > 5%",
which no parser has ever recognised, and "if_not_in: [] > 5%", whose empty
list the executor rejects as missing_allowed_values. Both were found by
running the suggester over real BigQuery columns and reading what came out.

A suggestion the user accepts and that then fails with a config error is worse
than no suggestion: it looks like a configured check and reports nothing.
"""

import pytest

from datametronome_podium.features.clefs.model import SUPPORTED_CHECK_TYPES
from datametronome_podium.services.agent_tools import _analyze_table_structure
from datametronome_podium.services.clef_executor import ClefExecutor

# Shapes taken from real connector output: information_schema for postgres,
# the BigQuery client's own naming, and DuckDB's DESCRIBE.
COLUMN_SETS = {
    "postgres": [
        {"column_name": "id", "data_type": "uuid", "is_nullable": "NO"},
        {"column_name": "status", "data_type": "text", "is_nullable": "YES"},
        {"column_name": "amount", "data_type": "numeric", "is_nullable": "YES"},
        {"column_name": "created_at", "data_type": "timestamp", "is_nullable": "YES"},
        {"column_name": "email", "data_type": "text", "is_nullable": "YES"},
    ],
    "bigquery": [
        {"name": "id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "state", "type": "STRING", "mode": "NULLABLE"},
        {"name": "mother_age", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "percent_complete", "type": "FLOAT", "mode": "NULLABLE"},
        {"name": "updated_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
    ],
    "s3": [
        {"column_name": "order_id", "column_type": "BIGINT", "null": "NO"},
        {"column_name": "category", "column_type": "VARCHAR", "null": "YES"},
        {"column_name": "price", "column_type": "DOUBLE", "null": "YES"},
    ],
}


def _conditions(source):
    """Every warn/fail string the suggester produces for that source."""
    out = []
    for s in _analyze_table_structure("t", COLUMN_SETS[source], source):
        out.extend(c for c in (s.get("warn"), s.get("fail")) if c)
    return out


@pytest.mark.parametrize("source", sorted(COLUMN_SETS))
def test_suggestions_are_produced_at_all(source):
    assert _analyze_table_structure("t", COLUMN_SETS[source], source)


@pytest.mark.parametrize("source", sorted(COLUMN_SETS))
def test_every_suggested_check_type_is_supported(source):
    for s in _analyze_table_structure("t", COLUMN_SETS[source], source):
        assert s["check_type"] in SUPPORTED_CHECK_TYPES


@pytest.mark.parametrize("source", sorted(COLUMN_SETS))
def test_every_suggested_column_condition_parses(source):
    """column_values conditions must not come back type 'unknown'."""
    executor = ClefExecutor()
    for s in _analyze_table_structure("t", COLUMN_SETS[source], source):
        if s["check_type"] != "column_values":
            continue
        for condition in (s.get("warn"), s.get("fail")):
            if not condition:
                continue
            parsed = executor._parse_column_values_condition(condition)
            assert parsed["type"] != "unknown", (
                f"{source}: suggested {condition!r}, which the executor cannot "
                f"parse: {parsed.get('error')}"
            )


@pytest.mark.parametrize("source", sorted(COLUMN_SETS))
def test_no_suggestion_ships_an_empty_allowed_list(source):
    """if_not_in with no values is rejected by the executor as missing config."""
    executor = ClefExecutor()
    for condition in _conditions(source):
        parsed = executor._parse_column_values_condition(condition)
        if parsed.get("type") == "if_not_in":
            assert parsed.get("values"), (
                f"{source}: suggested {condition!r} with an empty allowed list, "
                f"which always fails as missing_allowed_values"
            )
