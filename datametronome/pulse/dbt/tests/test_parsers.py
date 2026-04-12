"""Tests for all six parser functions against the fixture artifacts."""

import json
from pathlib import Path

import pytest

from metronome_pulse_dbt.parsers import (
    parse_columns,
    parse_exposures,
    parse_models,
    parse_sources,
    parse_test_results,
    parse_tests,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text())


@pytest.fixture
def run_results() -> dict:
    return json.loads((FIXTURES / "run_results.json").read_text())


@pytest.fixture
def catalog() -> dict:
    return json.loads((FIXTURES / "catalog.json").read_text())


# ---------------------------------------------------------------------------
# parse_models
# ---------------------------------------------------------------------------


def test_parse_models(manifest):
    """Three model nodes produce three rows with correct fields."""
    rows = parse_models(manifest)

    assert len(rows) == 3

    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {"stg_customers", "stg_orders", "fct_orders"}

    stg = by_name["stg_customers"]
    assert stg["unique_id"] == "model.my_project.stg_customers"
    assert stg["schema"] == "public"
    assert stg["database"] == "analytics"
    assert stg["materialization"] == "view"
    assert stg["tags"] == ["staging"]
    assert stg["depends_on"] == ["source.my_project.raw.customers"]
    assert stg["path"] == "staging/stg_customers.sql"

    fct = by_name["fct_orders"]
    assert fct["materialization"] == "table"
    assert set(fct["depends_on"]) == {
        "model.my_project.stg_customers",
        "model.my_project.stg_orders",
    }
    assert "finance" in fct["tags"]


def test_parse_models_empty():
    """Empty manifest returns an empty list without error."""
    assert parse_models({}) == []
    assert parse_models({"nodes": {}}) == []


def test_parse_models_skips_tests(manifest):
    """Test nodes in manifest.nodes are not included in model output."""
    rows = parse_models(manifest)
    unique_ids = [r["unique_id"] for r in rows]
    assert not any(uid.startswith("test.") for uid in unique_ids)


# ---------------------------------------------------------------------------
# parse_sources
# ---------------------------------------------------------------------------


def test_parse_sources(manifest):
    """Two source entries produce two rows with correct fields."""
    rows = parse_sources(manifest)

    assert len(rows) == 2

    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {"customers", "orders"}

    customers = by_name["customers"]
    assert customers["unique_id"] == "source.my_project.raw.customers"
    assert customers["source_name"] == "raw"
    assert customers["schema"] == "raw"
    assert customers["database"] == "analytics"
    assert customers["identifier"] == "customers"
    # Freshness thresholds are preserved as dicts, not flattened
    assert customers["freshness_warn_after"] == {"count": 24, "period": "hour"}
    assert customers["freshness_error_after"] == {"count": 48, "period": "hour"}

    orders = by_name["orders"]
    assert orders["freshness_warn_after"] == {"count": 6, "period": "hour"}


def test_parse_sources_no_freshness():
    """Sources without freshness config produce None for both fields."""
    manifest = {
        "sources": {
            "source.proj.raw.tbl": {
                "name": "tbl",
                "source_name": "raw",
                "schema": "raw",
                "database": "db",
            }
        }
    }
    rows = parse_sources(manifest)
    assert rows[0]["freshness_warn_after"] is None
    assert rows[0]["freshness_error_after"] is None


# ---------------------------------------------------------------------------
# parse_tests
# ---------------------------------------------------------------------------


def test_parse_tests(manifest):
    """Three test nodes produce three rows with correct type classification."""
    rows = parse_tests(manifest)

    assert len(rows) == 3

    by_name = {r["name"]: r for r in rows}

    # Both not_null and unique are generic tests (carry test_metadata)
    nn = by_name["not_null_stg_customers_id"]
    assert nn["test_type"] == "generic"
    assert nn["model"] == "model.my_project.stg_customers"
    assert nn["column_name"] == "id"
    assert nn["severity"] == "ERROR"

    av = by_name["accepted_values_stg_orders_status"]
    assert av["test_type"] == "generic"
    assert av["model"] == "model.my_project.stg_orders"
    assert av["column_name"] == "status"
    assert av["severity"] == "WARN"
    assert "data-quality" in av["tags"]


def test_parse_tests_singular_classification():
    """A test node without test_metadata is classified as singular."""
    manifest = {
        "nodes": {
            "test.proj.my_data_test.aaa": {
                "name": "my_data_test",
                "resource_type": "test",
                "depends_on": {"nodes": ["model.proj.orders"]},
                "column_name": "",
                "config": {"severity": "ERROR"},
                "tags": [],
                # No test_metadata key → singular
            }
        }
    }
    rows = parse_tests(manifest)
    assert len(rows) == 1
    assert rows[0]["test_type"] == "singular"
    assert rows[0]["model"] == "model.proj.orders"


def test_parse_tests_skips_models(manifest):
    """Model nodes in manifest.nodes are not included in test output."""
    rows = parse_tests(manifest)
    unique_ids = [r["unique_id"] for r in rows]
    assert not any(uid.startswith("model.") for uid in unique_ids)


# ---------------------------------------------------------------------------
# parse_test_results
# ---------------------------------------------------------------------------


def test_parse_test_results(run_results):
    """Only test results (unique_id starts with 'test.') are returned."""
    rows = parse_test_results(run_results)

    # 5 results total; 2 are model results → 3 test results expected
    assert len(rows) == 3

    by_id = {r["unique_id"]: r for r in rows}

    not_null = by_id["test.my_project.not_null_stg_customers_id.abc123"]
    assert not_null["status"] == "pass"
    assert not_null["failures"] == 0
    assert not_null["execution_time"] == 0.5

    failing = by_id["test.my_project.accepted_values_stg_orders_status.ghi789"]
    assert failing["status"] == "fail"
    assert failing["failures"] == 2
    assert "Got 2 results" in failing["message"]


def test_parse_test_results_excludes_model_runs(run_results):
    """Model run entries (unique_id starting 'model.') are filtered out."""
    rows = parse_test_results(run_results)
    unique_ids = [r["unique_id"] for r in rows]
    assert not any(uid.startswith("model.") for uid in unique_ids)


def test_parse_test_results_timestamp_attached(run_results):
    """generated_at from metadata is attached to every test result row."""
    rows = parse_test_results(run_results)
    assert all(r["timestamp"] == "2026-04-12T10:05:00Z" for r in rows)


def test_parse_test_results_empty():
    """Empty run_results returns an empty list."""
    assert parse_test_results({}) == []
    assert parse_test_results({"results": []}) == []


# ---------------------------------------------------------------------------
# parse_columns
# ---------------------------------------------------------------------------


def test_parse_columns(catalog):
    """Columns are extracted from both nodes and sources sections."""
    rows = parse_columns(catalog)

    # nodes: stg_customers(3) + stg_orders(4) + fct_orders(4) = 11
    # sources: raw.customers(3)
    assert len(rows) == 14

    # Verify a specific column from the nodes section
    stg_cust_cols = [r for r in rows if r["model_unique_id"] == "model.my_project.stg_customers"]
    assert len(stg_cust_cols) == 3

    col_names = {r["column_name"] for r in stg_cust_cols}
    assert col_names == {"id", "name", "email"}

    id_col = next(r for r in stg_cust_cols if r["column_name"] == "id")
    assert id_col["model_name"] == "stg_customers"
    assert id_col["column_type"] == "integer"
    assert id_col["description"] == "Primary key"


def test_parse_columns_source_section(catalog):
    """Columns from the sources section are included in output."""
    rows = parse_columns(catalog)
    source_rows = [r for r in rows if r["model_unique_id"].startswith("source.")]
    # raw.customers has 3 columns
    assert len(source_rows) == 3
    assert all(r["model_name"] == "customers" for r in source_rows)


def test_parse_columns_empty():
    """Empty catalog returns an empty list."""
    assert parse_columns({}) == []
    assert parse_columns({"nodes": {}, "sources": {}}) == []


# ---------------------------------------------------------------------------
# parse_exposures
# ---------------------------------------------------------------------------


def test_parse_exposures(manifest):
    """One exposure is parsed with correct type, owner, and depends_on."""
    rows = parse_exposures(manifest)

    assert len(rows) == 1
    exp = rows[0]
    assert exp["unique_id"] == "exposure.my_project.weekly_report"
    assert exp["name"] == "weekly_report"
    assert exp["type"] == "dashboard"
    assert exp["owner"] == "Finance Team"
    assert exp["depends_on"] == ["model.my_project.fct_orders"]


def test_parse_exposures_empty():
    """Manifest with no exposures key returns an empty list."""
    assert parse_exposures({}) == []
    assert parse_exposures({"exposures": {}}) == []


def test_parse_exposures_string_owner():
    """Older dbt schemas may store owner as a plain string instead of a dict."""
    manifest = {
        "exposures": {
            "exposure.proj.report": {
                "name": "report",
                "type": "analysis",
                "owner": "Alice",
                "depends_on": {"nodes": []},
            }
        }
    }
    rows = parse_exposures(manifest)
    assert rows[0]["owner"] == "Alice"


# ---------------------------------------------------------------------------
# Defensive: missing fields must not crash any parser
# ---------------------------------------------------------------------------


def test_parse_defensive_missing_fields():
    """All parsers tolerate manifests where optional fields are absent."""
    bare_manifest = {
        "nodes": {
            "model.p.bare_model": {"resource_type": "model"},
            "test.p.bare_test": {"resource_type": "test"},
        },
        "sources": {"source.p.s.t": {}},
        "exposures": {"exposure.p.exp": {}},
    }
    bare_run_results = {"results": [{"unique_id": "test.p.t"}]}
    bare_catalog = {"nodes": {"model.p.m": {"columns": {"col": {}}}}}

    # None of these should raise
    models = parse_models(bare_manifest)
    sources = parse_sources(bare_manifest)
    tests = parse_tests(bare_manifest)
    test_results = parse_test_results(bare_run_results)
    columns = parse_columns(bare_catalog)
    exposures = parse_exposures(bare_manifest)

    assert len(models) == 1
    assert models[0]["materialization"] == ""

    assert len(sources) == 1
    assert sources[0]["freshness_warn_after"] is None

    assert len(tests) == 1
    assert tests[0]["model"] == ""
    assert tests[0]["severity"] == "ERROR"

    assert len(test_results) == 1
    assert test_results[0]["timestamp"] == ""

    assert len(columns) == 1
    assert columns[0]["column_type"] == ""

    assert len(exposures) == 1
    assert exposures[0]["type"] == ""
    assert exposures[0]["owner"] == ""
