"""End-to-end tests against real dbt artifacts downloaded from public projects.

These tests validate that our parsers and connector work correctly with
real-world dbt manifest/run_results/catalog files, not just our hand-crafted
fixtures.

Skipped if the artifacts have not been downloaded to /tmp/dbt-test-real/target/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metronome_pulse_dbt.artifact_reader import LocalArtifactReader
from metronome_pulse_dbt.connector import DbtReadonlyPulse
from metronome_pulse_dbt.parsers import (
    parse_columns,
    parse_exposures,
    parse_models,
    parse_sources,
    parse_test_results,
    parse_tests,
)

# ---------- Snowflake project (v11 manifest, all 3 artifacts) ----------

SNOWFLAKE_DIR = Path("/tmp/dbt-test-real")
SNOWFLAKE_MANIFEST = SNOWFLAKE_DIR / "target" / "manifest.json"
SNOWFLAKE_RUN_RESULTS = SNOWFLAKE_DIR / "target" / "run_results.json"
SNOWFLAKE_CATALOG = SNOWFLAKE_DIR / "target" / "catalog.json"

has_snowflake = SNOWFLAKE_MANIFEST.exists()

# ---------- Jaffle shop / dbt-docs (v9 manifest, catalog only) ----------

JAFFLE_DIR = Path("/tmp/dbt-test-jaffle")
JAFFLE_MANIFEST = JAFFLE_DIR / "target" / "manifest.json"
JAFFLE_CATALOG = JAFFLE_DIR / "target" / "catalog.json"

has_jaffle = JAFFLE_MANIFEST.exists()


# ============================================================
# Snowflake dbt project tests
# ============================================================


@pytest.mark.skipif(not has_snowflake, reason="Real Snowflake artifacts not downloaded")
class TestSnowflakeArtifacts:
    """Tests against a real Snowflake dbt project (v11 manifest, dbt 1.7.4)."""

    @pytest.fixture
    def manifest(self):
        return json.loads(SNOWFLAKE_MANIFEST.read_text())

    @pytest.fixture
    def run_results(self):
        return json.loads(SNOWFLAKE_RUN_RESULTS.read_text())

    @pytest.fixture
    def catalog(self):
        return json.loads(SNOWFLAKE_CATALOG.read_text())

    def test_manifest_metadata(self, manifest):
        meta = manifest["metadata"]
        assert "dbt_version" in meta
        assert "generated_at" in meta
        print(f"  dbt version: {meta['dbt_version']}")
        print(f"  schema: {meta.get('dbt_schema_version', 'unknown')}")

    def test_parse_models_non_empty(self, manifest):
        models = parse_models(manifest)
        assert len(models) > 0, "Expected at least 1 model"
        print(f"  Found {len(models)} models")
        for m in models[:5]:
            print(f"    - {m['name']} ({m['materialization']}) in {m['schema']}")

        # Every model should have required fields
        for m in models:
            assert m["unique_id"], f"Missing unique_id for {m}"
            assert m["name"], f"Missing name for {m['unique_id']}"

    def test_parse_sources(self, manifest):
        sources = parse_sources(manifest)
        print(f"  Found {len(sources)} sources")
        for s in sources[:5]:
            print(f"    - {s['source_name']}.{s['name']} in {s['schema']}")

    def test_parse_tests(self, manifest):
        tests = parse_tests(manifest)
        assert len(tests) > 0, "Expected at least 1 test"
        print(f"  Found {len(tests)} tests")
        types = set(t["test_type"] for t in tests)
        print(f"    Test types: {types}")
        for t in tests[:5]:
            print(f"    - {t['name']} ({t['test_type']}, severity={t['severity']})")

    def test_parse_test_results(self, run_results):
        results = parse_test_results(run_results)
        print(f"  Found {len(results)} test results")
        statuses = set(r["status"] for r in results)
        print(f"    Statuses: {statuses}")
        for r in results[:5]:
            print(f"    - {r['unique_id']}: {r['status']} ({r['execution_time']:.2f}s)")

    def test_parse_columns(self, catalog):
        columns = parse_columns(catalog)
        assert len(columns) > 0, "Expected columns from catalog"
        print(f"  Found {len(columns)} columns across all models/sources")
        # Group by model
        models = set(c["model_name"] for c in columns)
        print(f"    Across {len(models)} models/sources")

    def test_parse_exposures(self, manifest):
        exposures = parse_exposures(manifest)
        print(f"  Found {len(exposures)} exposures")

    async def test_artifact_reader(self):
        reader = LocalArtifactReader(str(SNOWFLAKE_DIR), "target")
        assert await reader.is_available()

        manifest = await reader.read_manifest()
        assert "nodes" in manifest
        assert "metadata" in manifest

        run_results = await reader.read_run_results()
        assert run_results is not None
        assert "results" in run_results

        catalog = await reader.read_catalog()
        assert catalog is not None
        assert "nodes" in catalog


@pytest.mark.skipif(not has_snowflake, reason="Real Snowflake artifacts not downloaded")
class TestSnowflakeConnector:
    """Full connector integration test against real Snowflake dbt artifacts."""

    async def test_connect_and_query(self):
        connector = DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR))
        await connector.connect()
        assert await connector.is_connected()

        # Query all virtual tables
        models = await connector.query("models")
        sources = await connector.query("sources")
        tests = await connector.query("tests")

        print(f"\n  Models: {len(models)}")
        print(f"  Sources: {len(sources)}")
        print(f"  Tests: {len(tests)}")

        assert len(models) > 0

        # list_tables returns model names
        table_names = await connector.list_tables()
        print(f"  list_tables() returned {len(table_names)} model names")
        assert len(table_names) == len(models)

        await connector.close()

    async def test_query_with_filters(self):
        async with DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR)) as conn:
            models = await conn.query("models")
            if not models:
                pytest.skip("No models found")

            # Get materializations used
            mats = set(m["materialization"] for m in models)
            print(f"  Materializations: {mats}")

            # Filter by first materialization found
            first_mat = next(iter(mats))
            filtered = await conn.query({
                "table": "models",
                "where": {"materialization": first_mat},
            })
            print(f"  Models with materialization='{first_mat}': {len(filtered)}")
            assert all(m["materialization"] == first_mat for m in filtered)

    async def test_get_table_info(self):
        async with DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR)) as conn:
            models = await conn.query("models")
            if not models:
                pytest.skip("No models")

            # Try getting column info for the first model
            first_model = models[0]["name"]
            cols = await conn.get_table_info(first_model)
            print(f"  Columns for '{first_model}': {len(cols)}")
            if cols:
                for c in cols[:5]:
                    print(f"    - {c['column_name']}: {c['column_type']}")

    async def test_test_results_available(self):
        async with DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR)) as conn:
            try:
                results = await conn.query("test_results")
                print(f"  Test results: {len(results)}")
                for r in results[:5]:
                    print(f"    - {r['unique_id']}: {r['status']}")
            except ValueError:
                print("  No test_results table (no run_results.json)")

    async def test_columns_virtual_table(self):
        async with DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR)) as conn:
            try:
                columns = await conn.query("columns")
                print(f"  Total columns: {len(columns)}")
                # Verify structure
                if columns:
                    first = columns[0]
                    assert "model_name" in first
                    assert "column_name" in first
                    assert "column_type" in first
            except ValueError:
                print("  No columns table (no catalog.json)")

    async def test_query_with_params_table_name(self):
        async with DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR)) as conn:
            # query_with_params should work for plain table identifiers
            models = await conn.query_with_params("models")
            assert len(models) > 0

    async def test_query_with_params_sql_rejected(self):
        async with DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR)) as conn:
            with pytest.raises(ValueError, match="SQL queries are not supported"):
                await conn.query_with_params("SELECT * FROM models")

    async def test_write_operations_rejected(self):
        async with DbtReadonlyPulse(mode="local", project_path=str(SNOWFLAKE_DIR)) as conn:
            with pytest.raises(NotImplementedError):
                await conn.execute("CREATE TABLE foo (id int)")
            with pytest.raises(NotImplementedError):
                await conn.execute_many("INSERT INTO foo VALUES (?)", [[1], [2]])
            with pytest.raises(NotImplementedError):
                await conn.write([{"a": 1}], "foo")


# ============================================================
# Jaffle shop / dbt-docs tests
# ============================================================


@pytest.mark.skipif(not has_jaffle, reason="Jaffle shop artifacts not downloaded")
class TestJaffleShopArtifacts:
    """Tests against dbt-labs/dbt-docs jaffle_shop artifacts (v9 manifest)."""

    @pytest.fixture
    def manifest(self):
        return json.loads(JAFFLE_MANIFEST.read_text())

    @pytest.fixture
    def catalog(self):
        return json.loads(JAFFLE_CATALOG.read_text())

    def test_manifest_metadata(self, manifest):
        meta = manifest["metadata"]
        print(f"  dbt version: {meta['dbt_version']}")
        print(f"  project: {meta.get('project_name', 'unknown')}")
        print(f"  adapter: {meta.get('adapter_type', 'unknown')}")

    def test_parse_models(self, manifest):
        models = parse_models(manifest)
        print(f"  Found {len(models)} models")
        for m in models[:10]:
            print(f"    - {m['name']} ({m['materialization']}) tags={m['tags']}")
        assert len(models) > 0

    def test_parse_sources(self, manifest):
        sources = parse_sources(manifest)
        print(f"  Found {len(sources)} sources")
        for s in sources:
            print(f"    - {s['source_name']}.{s['name']}")

    def test_parse_tests(self, manifest):
        tests = parse_tests(manifest)
        print(f"  Found {len(tests)} tests")
        generic_count = sum(1 for t in tests if t["test_type"] == "generic")
        singular_count = sum(1 for t in tests if t["test_type"] == "singular")
        print(f"    Generic: {generic_count}, Singular: {singular_count}")

    def test_parse_columns(self, catalog):
        columns = parse_columns(catalog)
        print(f"  Found {len(columns)} columns")
        models = set(c["model_name"] for c in columns)
        print(f"    Across {len(models)} models/sources: {models}")

    async def test_connector_full_lifecycle(self):
        """Full lifecycle: connect, query, list_tables, get_table_info, close."""
        connector = DbtReadonlyPulse(mode="local", project_path=str(JAFFLE_DIR))
        await connector.connect()

        models = await connector.query("models")
        sources = await connector.query("sources")
        tests = await connector.query("tests")
        exposures = await connector.query("exposures")

        print(f"\n  Jaffle shop summary:")
        print(f"    Models: {len(models)}")
        print(f"    Sources: {len(sources)}")
        print(f"    Tests: {len(tests)}")
        print(f"    Exposures: {len(exposures)}")

        # list_tables
        tables = await connector.list_tables()
        print(f"    list_tables: {tables}")

        # get_table_info for each model
        for name in tables[:3]:
            cols = await connector.get_table_info(name)
            print(f"    {name} columns: {[c['column_name'] for c in cols]}")

        # Filtered query
        if models:
            # Find a tag that exists
            all_tags = set()
            for m in models:
                all_tags.update(m.get("tags", []))
            if all_tags:
                tag = next(iter(all_tags))
                tagged = await connector.query({
                    "table": "models",
                    "where": {"tags": tag},
                })
                print(f"    Models with tag '{tag}': {len(tagged)}")

        await connector.close()
        assert not await connector.is_connected()
