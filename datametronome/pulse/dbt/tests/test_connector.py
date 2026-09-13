"""Tests for DbtReadonlyPulse connector."""

from __future__ import annotations

import json
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from metronome_pulse_dbt.connector import DbtReadonlyPulse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def _write_artifacts(target_dir: pathlib.Path, *, include_run_results: bool = True, include_catalog: bool = True) -> None:
    """Write fixture JSON files into target_dir for local-mode tests."""
    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text())
    (target_dir / "manifest.json").write_text(json.dumps(manifest))

    if include_run_results:
        run_results = json.loads((FIXTURES_DIR / "run_results.json").read_text())
        (target_dir / "run_results.json").write_text(json.dumps(run_results))

    if include_catalog:
        catalog = json.loads((FIXTURES_DIR / "catalog.json").read_text())
        (target_dir / "catalog.json").write_text(json.dumps(catalog))


@pytest.fixture
async def connected_local(tmp_path: pathlib.Path) -> DbtReadonlyPulse:
    """Yield a connected DbtReadonlyPulse using local fixtures."""
    target = tmp_path / "target"
    target.mkdir()
    _write_artifacts(target)

    connector = DbtReadonlyPulse(mode="local", project_path=str(tmp_path))
    await connector.connect()
    return connector


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_local_mode_requires_path():
    """Omitting project_path in local mode raises ValueError immediately."""
    with pytest.raises(ValueError, match="project_path"):
        DbtReadonlyPulse(mode="local", project_path="")


def test_cloud_mode_requires_credentials():
    """Missing cloud credentials raise ValueError immediately."""
    with pytest.raises(ValueError, match="api_token"):
        DbtReadonlyPulse(mode="cloud")


def test_cloud_mode_partial_credentials_raises():
    """Partial cloud credentials (missing job_id) raise ValueError."""
    with pytest.raises(ValueError, match="api_token"):
        DbtReadonlyPulse(mode="cloud", api_token="tok", account_id="42")


def test_invalid_mode_raises():
    """Unknown mode raises ValueError with the bad value in the message."""
    with pytest.raises(ValueError, match="Unsupported mode.*ftp"):
        DbtReadonlyPulse(mode="ftp", project_path="/tmp")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def test_connect_local(tmp_path: pathlib.Path):
    """Connecting with valid local artifacts sets connected=True."""
    target = tmp_path / "target"
    target.mkdir()
    _write_artifacts(target)

    connector = DbtReadonlyPulse(mode="local", project_path=str(tmp_path))
    assert not await connector.is_connected()

    await connector.connect()
    assert await connector.is_connected()


async def test_connect_idempotent(tmp_path: pathlib.Path):
    """Calling connect() twice does not raise and stays connected."""
    target = tmp_path / "target"
    target.mkdir()
    _write_artifacts(target)

    connector = DbtReadonlyPulse(mode="local", project_path=str(tmp_path))
    await connector.connect()
    await connector.connect()  # second call must be a no-op
    assert await connector.is_connected()


async def test_close(connected_local: DbtReadonlyPulse):
    """close() transitions connected → disconnected."""
    await connected_local.close()
    assert not await connected_local.is_connected()


async def test_connect_cloud(mocker):
    """Cloud mode: mocked reader methods → connect succeeds."""
    # Fixtures loaded from real fixture files
    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text())
    run_results = json.loads((FIXTURES_DIR / "run_results.json").read_text())
    catalog = json.loads((FIXTURES_DIR / "catalog.json").read_text())

    mock_reader = MagicMock()
    mock_reader.read_manifest = AsyncMock(return_value=manifest)
    mock_reader.read_run_results = AsyncMock(return_value=run_results)
    mock_reader.read_catalog = AsyncMock(return_value=catalog)

    # Patch CloudArtifactReader so the connector uses our mock instead
    mocker.patch(
        "metronome_pulse_dbt.connector.CloudArtifactReader",
        return_value=mock_reader,
    )

    connector = DbtReadonlyPulse(
        mode="cloud",
        api_token="tok",
        account_id="42",
        job_id="99",
    )
    await connector.connect()
    assert await connector.is_connected()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


async def test_context_manager(tmp_path: pathlib.Path):
    """async with connects on entry and disconnects on exit."""
    target = tmp_path / "target"
    target.mkdir()
    _write_artifacts(target)

    connector = DbtReadonlyPulse(mode="local", project_path=str(tmp_path))
    async with connector as ctx:
        assert await ctx.is_connected()
    assert not await connector.is_connected()


# ---------------------------------------------------------------------------
# query()
# ---------------------------------------------------------------------------


async def test_query_models(connected_local: DbtReadonlyPulse):
    """query('models') returns model rows loaded from manifest."""
    rows = await connected_local.query("models")
    assert len(rows) == 3
    names = {r["name"] for r in rows}
    assert names == {"stg_customers", "stg_orders", "fct_orders"}


async def test_query_dict(connected_local: DbtReadonlyPulse):
    """query(dict) passes through to VirtualTableEngine with filtering."""
    rows = await connected_local.query({
        "table": "models",
        "where": {"materialization": "table"},
    })
    assert len(rows) == 1
    assert rows[0]["name"] == "fct_orders"


async def test_query_not_connected():
    """query() before connect() raises RuntimeError."""
    connector = DbtReadonlyPulse(mode="local", project_path="/tmp/fake_does_not_matter")
    with pytest.raises(RuntimeError, match="connect"):
        await connector.query("models")


async def test_query_test_results(connected_local: DbtReadonlyPulse):
    """test_results virtual table contains only test-type results from run_results."""
    rows = await connected_local.query("test_results")
    # fixture run_results has 3 test entries (2 model runs are excluded)
    assert len(rows) == 3
    for row in rows:
        assert row["unique_id"].startswith("test.")


async def test_query_columns_table(connected_local: DbtReadonlyPulse):
    """columns virtual table is populated from catalog.json."""
    rows = await connected_local.query("columns")
    assert len(rows) > 0
    assert "column_name" in rows[0]
    assert "column_type" in rows[0]


# ---------------------------------------------------------------------------
# query_with_params()
# ---------------------------------------------------------------------------


async def test_query_with_params_table_name(connected_local: DbtReadonlyPulse):
    """query_with_params with a bare identifier delegates to query()."""
    rows = await connected_local.query_with_params("models")
    assert len(rows) == 3


async def test_query_with_params_sql_raises(connected_local: DbtReadonlyPulse):
    """query_with_params with a SQL string raises ValueError."""
    with pytest.raises(ValueError, match="SQL queries are not supported"):
        await connected_local.query_with_params("SELECT * FROM models")


async def test_query_with_params_not_connected():
    """query_with_params before connect() raises RuntimeError via query()."""
    connector = DbtReadonlyPulse(mode="local", project_path="/tmp/fake")
    with pytest.raises(RuntimeError, match="connect"):
        await connector.query_with_params("models")


# ---------------------------------------------------------------------------
# list_tables() — returns dbt model names, not virtual table names
# ---------------------------------------------------------------------------


async def test_list_tables(connected_local: DbtReadonlyPulse):
    """list_tables() returns model names from the models virtual table."""
    names = await connected_local.list_tables()
    assert set(names) == {"stg_customers", "stg_orders", "fct_orders"}


async def test_list_tables_not_connected():
    """list_tables() before connect() raises RuntimeError."""
    connector = DbtReadonlyPulse(mode="local", project_path="/tmp/fake")
    with pytest.raises(RuntimeError, match="connect"):
        await connector.list_tables()


# ---------------------------------------------------------------------------
# get_table_info()
# ---------------------------------------------------------------------------


async def test_get_table_info(connected_local: DbtReadonlyPulse):
    """get_table_info for a model with catalog data returns column list."""
    cols = await connected_local.get_table_info("stg_customers")
    assert len(cols) == 3
    col_map = {c["column_name"]: c["column_type"] for c in cols}
    assert col_map["id"] == "integer"
    assert col_map["name"] == "text"
    assert col_map["email"] == "text"


async def test_get_table_info_no_catalog(tmp_path: pathlib.Path):
    """When catalog is absent, get_table_info returns empty list."""
    target = tmp_path / "target"
    target.mkdir()
    # Only manifest — no catalog
    _write_artifacts(target, include_run_results=False, include_catalog=False)

    connector = DbtReadonlyPulse(mode="local", project_path=str(tmp_path))
    await connector.connect()

    result = await connector.get_table_info("stg_customers")
    assert result == []


async def test_get_table_info_not_connected():
    """get_table_info() before connect() raises RuntimeError."""
    connector = DbtReadonlyPulse(mode="local", project_path="/tmp/fake")
    with pytest.raises(RuntimeError, match="connect"):
        await connector.get_table_info("stg_customers")


# ---------------------------------------------------------------------------
# Write operations (all must raise NotImplementedError)
# ---------------------------------------------------------------------------


async def test_execute_raises(connected_local: DbtReadonlyPulse):
    with pytest.raises(NotImplementedError, match="read-only"):
        await connected_local.execute("DELETE FROM models")


async def test_execute_many_raises(connected_local: DbtReadonlyPulse):
    with pytest.raises(NotImplementedError, match="read-only"):
        await connected_local.execute_many("INSERT INTO t VALUES (?)", [["a"]])


async def test_write_raises(connected_local: DbtReadonlyPulse):
    with pytest.raises(NotImplementedError, match="read-only"):
        await connected_local.write([{"x": 1}], "models")


# ---------------------------------------------------------------------------
# Transactions (no-ops — must not raise)
# ---------------------------------------------------------------------------


async def test_transactions_are_noop(connected_local: DbtReadonlyPulse):
    """Transaction methods are no-ops and return None without raising."""
    await connected_local.begin_transaction()
    await connected_local.commit_transaction()
    await connected_local.rollback_transaction()
