"""Parsers that normalize dbt artifact JSON into flat row dicts.

Each function accepts the raw parsed JSON dict for one artifact file and
returns a list of row dicts — one row per logical entity. All field access
uses .get() so the parsers tolerate missing keys across dbt schema versions
(v9 through v12 differ in which fields are present).
"""
from __future__ import annotations

from typing import Any


def parse_models(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract models from manifest.json nodes where resource_type == 'model'."""
    rows = []
    for uid, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue
        rows.append({
            "unique_id": uid,
            "name": node.get("name", ""),
            "schema": node.get("schema", ""),
            "database": node.get("database", ""),
            # config.materialized is the canonical field; absent in older schemas
            "materialization": node.get("config", {}).get("materialized", ""),
            "tags": node.get("tags", []),
            "description": node.get("description", ""),
            "depends_on": node.get("depends_on", {}).get("nodes", []),
            "path": node.get("path", ""),
        })
    return rows


def parse_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract sources from manifest.json sources section."""
    rows = []
    for uid, source in manifest.get("sources", {}).items():
        freshness = source.get("freshness", {})
        # identifier falls back to name when not explicitly set in dbt YAML
        rows.append({
            "unique_id": uid,
            "name": source.get("name", ""),
            "source_name": source.get("source_name", ""),
            "schema": source.get("schema", ""),
            "database": source.get("database", ""),
            "identifier": source.get("identifier", source.get("name", "")),
            "freshness_warn_after": freshness.get("warn_after"),
            "freshness_error_after": freshness.get("error_after"),
        })
    return rows


def parse_tests(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tests from manifest.json nodes where resource_type == 'test'.

    dbt has two test kinds:
      - generic (schema) tests: defined in YAML, carry test_metadata
      - singular (data) tests: standalone .sql files, no test_metadata
    """
    rows = []
    for uid, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "test":
            continue
        test_metadata = node.get("test_metadata", {})
        # Presence of test_metadata distinguishes generic from singular tests
        test_type = "generic" if test_metadata else "singular"

        # First node in depends_on is the model under test (may be absent for
        # singular tests that join multiple models)
        depends_on_nodes = node.get("depends_on", {}).get("nodes", [])
        model = depends_on_nodes[0] if depends_on_nodes else ""

        rows.append({
            "unique_id": uid,
            "name": node.get("name", ""),
            "test_type": test_type,
            "model": model,
            "column_name": node.get("column_name", ""),
            # severity defaults to ERROR per dbt spec when config is absent
            "severity": node.get("config", {}).get("severity", "ERROR"),
            "tags": node.get("tags", []),
        })
    return rows


def parse_test_results(run_results: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract test results from run_results.json, filtering to test nodes only.

    run_results.json mixes model runs and test runs; unique_id prefix 'test.'
    is the only reliable discriminator between the two.
    """
    rows = []
    # generated_at lives under metadata, not per-result; attach it to every row
    timestamp = run_results.get("metadata", {}).get("generated_at", "")
    for result in run_results.get("results", []):
        uid = result.get("unique_id", "")
        if not uid.startswith("test."):
            continue
        rows.append({
            "unique_id": uid,
            "status": result.get("status", ""),
            "execution_time": result.get("execution_time", 0.0),
            "message": result.get("message", ""),
            "failures": result.get("failures"),
            "timestamp": timestamp,
        })
    return rows


def parse_columns(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract column info from catalog.json nodes and sources.

    catalog.json organises entries under 'nodes' (models/seeds/snapshots) and
    'sources', both with the same structure. We flatten both into one list so
    callers don't need to treat them differently.
    """
    rows = []
    for section in ("nodes", "sources"):
        for uid, entry in catalog.get(section, {}).items():
            model_name = entry.get("metadata", {}).get("name", "")
            for col_name, col_info in entry.get("columns", {}).items():
                rows.append({
                    "model_unique_id": uid,
                    "model_name": model_name,
                    "column_name": col_name,
                    # catalog stores the DB-native type string in 'type'
                    "column_type": col_info.get("type", ""),
                    # dbt writes column descriptions into 'comment' in catalog
                    "description": col_info.get("comment", ""),
                })
    return rows


def parse_exposures(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract exposures from manifest.json exposures section."""
    rows = []
    for uid, exposure in manifest.get("exposures", {}).items():
        owner = exposure.get("owner", {})
        # owner may be a dict with 'name'/'email', or a plain string in older schemas
        owner_name = owner.get("name", "") if isinstance(owner, dict) else str(owner)
        rows.append({
            "unique_id": uid,
            "name": exposure.get("name", ""),
            "type": exposure.get("type", ""),
            "owner": owner_name,
            "depends_on": exposure.get("depends_on", {}).get("nodes", []),
        })
    return rows
