"""Connectors disagree about how to spell a column description.

Everything downstream reads information_schema naming (column_name, data_type,
is_nullable). Postgres and Redshift query information_schema so they match;
BigQuery's client returns name/type/mode and DuckDB's DESCRIBE returns
column_name/column_type/null. Unnormalised, a BigQuery stave produced zero
check suggestions because every column name read back as "".

The BigQuery sample below is real output, captured from
bigquery-public-data.samples.shakespeare.
"""

import pytest

from datametronome_podium.services.agent_tools import (
    _analyze_table_structure,
    _as_information_schema,
)

POSTGRES = [
    {"column_name": "id", "data_type": "uuid", "is_nullable": "NO"},
    {"column_name": "created_at", "data_type": "timestamp", "is_nullable": "YES"},
]

BIGQUERY = [
    {"name": "word", "type": "STRING", "mode": "REQUIRED", "description": "A word."},
    {"name": "corpus_date", "type": "INTEGER", "mode": "NULLABLE"},
]

DUCKDB = [
    {"column_name": "id", "column_type": "BIGINT", "null": "NO"},
    {"column_name": "amount", "column_type": "DOUBLE", "null": "YES"},
]


@pytest.mark.parametrize(
    "columns,expected_names",
    [
        (POSTGRES, ["id", "created_at"]),
        (BIGQUERY, ["word", "corpus_date"]),
        (DUCKDB, ["id", "amount"]),
    ],
)
def test_every_shape_yields_column_names(columns, expected_names):
    assert [c["column_name"] for c in _as_information_schema(columns)] == expected_names


@pytest.mark.parametrize(
    "columns,expected_types",
    [
        (POSTGRES, ["uuid", "timestamp"]),
        (BIGQUERY, ["STRING", "INTEGER"]),
        (DUCKDB, ["BIGINT", "DOUBLE"]),
    ],
)
def test_every_shape_yields_data_types(columns, expected_types):
    assert [c["data_type"] for c in _as_information_schema(columns)] == expected_types


def test_bigquery_required_means_not_nullable():
    """BigQuery spells nullability as a mode, and only REQUIRED forbids NULL."""
    out = _as_information_schema(BIGQUERY)
    assert [c["is_nullable"] for c in out] == ["NO", "YES"]


def test_postgres_shape_is_untouched():
    assert [c["is_nullable"] for c in _as_information_schema(POSTGRES)] == ["NO", "YES"]


def test_non_dict_entries_are_dropped_rather_than_raising():
    """A connector returning strings must not take the whole tool down."""
    assert _as_information_schema(["id", None, {"name": "x"}]) == [
        {"name": "x", "column_name": "x", "data_type": "", "is_nullable": "YES"}
    ]


def test_bigquery_columns_actually_produce_suggestions():
    """The regression this was written for: BigQuery yielded an empty list."""
    columns = [
        {"name": "id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "created_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "email", "type": "STRING", "mode": "NULLABLE"},
    ]
    suggestions = _analyze_table_structure("users", columns, "bigquery")
    assert suggestions, "BigQuery schema produced no check suggestions"
