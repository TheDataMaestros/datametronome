"""Tests for LocalArtifactReader and CloudArtifactReader."""

import json
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from metronome_pulse_dbt.artifact_reader import (
    ArtifactReader,
    CloudArtifactReader,
    LocalArtifactReader,
)
from metronome_pulse_dbt.exceptions import (
    ArtifactNotFoundError,
    ArtifactParseError,
    CloudApiError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MANIFEST_FIXTURE: dict = {
    "metadata": {"dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v10/manifest.json"},
    "nodes": {},
    "sources": {},
}

RUN_RESULTS_FIXTURE: dict = {
    "metadata": {"dbt_schema_version": "https://schemas.getdbt.com/dbt/run-results/v4/run-results.json"},
    "results": [],
}

CATALOG_FIXTURE: dict = {
    "metadata": {"dbt_schema_version": "https://schemas.getdbt.com/dbt/catalog/v1/catalog.json"},
    "nodes": {},
    "sources": {},
}


def _write_json(directory: pathlib.Path, filename: str, data: dict) -> None:
    (directory / filename).write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


def test_artifact_reader_is_abstract():
    """ArtifactReader cannot be instantiated directly — it is an ABC."""
    with pytest.raises(TypeError):
        ArtifactReader()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# LocalArtifactReader — happy paths
# ---------------------------------------------------------------------------


async def test_local_read_all_artifacts(tmp_path: pathlib.Path):
    """All three artifact files present — all three return parsed dicts."""
    target = tmp_path / "target"
    target.mkdir()
    _write_json(target, "manifest.json", MANIFEST_FIXTURE)
    _write_json(target, "run_results.json", RUN_RESULTS_FIXTURE)
    _write_json(target, "catalog.json", CATALOG_FIXTURE)

    reader = LocalArtifactReader(str(tmp_path))

    manifest = await reader.read_manifest()
    run_results = await reader.read_run_results()
    catalog = await reader.read_catalog()

    assert manifest == MANIFEST_FIXTURE
    assert run_results == RUN_RESULTS_FIXTURE
    assert catalog == CATALOG_FIXTURE


async def test_local_manifest_only(tmp_path: pathlib.Path):
    """Only manifest present — run_results and catalog return None."""
    target = tmp_path / "target"
    target.mkdir()
    _write_json(target, "manifest.json", MANIFEST_FIXTURE)

    reader = LocalArtifactReader(str(tmp_path))

    assert await reader.read_manifest() == MANIFEST_FIXTURE
    assert await reader.read_run_results() is None
    assert await reader.read_catalog() is None


async def test_local_missing_manifest_raises(tmp_path: pathlib.Path):
    """Missing manifest.json → ArtifactNotFoundError."""
    target = tmp_path / "target"
    target.mkdir()
    # No manifest written

    reader = LocalArtifactReader(str(tmp_path))

    with pytest.raises(ArtifactNotFoundError, match="manifest.json"):
        await reader.read_manifest()


async def test_local_is_available_true(tmp_path: pathlib.Path):
    """manifest.json present → is_available() returns True."""
    target = tmp_path / "target"
    target.mkdir()
    _write_json(target, "manifest.json", MANIFEST_FIXTURE)

    reader = LocalArtifactReader(str(tmp_path))

    assert await reader.is_available() is True


async def test_local_is_available_false(tmp_path: pathlib.Path):
    """manifest.json absent → is_available() returns False."""
    target = tmp_path / "target"
    target.mkdir()

    reader = LocalArtifactReader(str(tmp_path))

    assert await reader.is_available() is False


async def test_local_invalid_json_raises(tmp_path: pathlib.Path):
    """Corrupt manifest.json → ArtifactParseError."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "manifest.json").write_text("{ not valid json }", encoding="utf-8")

    reader = LocalArtifactReader(str(tmp_path))

    with pytest.raises(ArtifactParseError, match="Invalid JSON"):
        await reader.read_manifest()


async def test_local_custom_target_path(tmp_path: pathlib.Path):
    """Non-default target path is respected."""
    custom_target = tmp_path / "compiled"
    custom_target.mkdir()
    _write_json(custom_target, "manifest.json", MANIFEST_FIXTURE)

    reader = LocalArtifactReader(str(tmp_path), target_path="compiled")

    assert await reader.read_manifest() == MANIFEST_FIXTURE


# ---------------------------------------------------------------------------
# CloudArtifactReader — mocked httpx
# ---------------------------------------------------------------------------


def _make_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a fake httpx.Response with the minimum interface we use."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.raise_for_status = MagicMock()
    return resp


def _cloud_reader() -> CloudArtifactReader:
    return CloudArtifactReader(
        api_token="tok123",
        account_id="42",
        job_id="99",
    )


async def test_cloud_fetch_artifacts(mocker):
    """Happy path: latest run resolved, manifest and run_results returned."""
    runs_body = {"data": [{"id": 7}]}
    manifest_body = MANIFEST_FIXTURE
    run_results_body = RUN_RESULTS_FIXTURE

    call_order = [
        # _get_latest_run_id (read_manifest)
        _make_response(200, runs_body),
        _make_response(200, manifest_body),
        # _get_latest_run_id (read_run_results)
        _make_response(200, runs_body),
        _make_response(200, run_results_body),
    ]

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=call_order)

    mocker.patch("metronome_pulse_dbt.artifact_reader.httpx.AsyncClient", return_value=mock_client)

    reader = _cloud_reader()

    manifest = await reader.read_manifest()
    run_results = await reader.read_run_results()

    assert manifest == MANIFEST_FIXTURE
    assert run_results == RUN_RESULTS_FIXTURE


async def test_cloud_latest_run_lookup(mocker):
    """Verifies the correct URL is constructed for the runs list endpoint."""
    runs_body = {"data": [{"id": 55}]}
    manifest_body = MANIFEST_FIXTURE

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=[
        _make_response(200, runs_body),
        _make_response(200, manifest_body),
    ])

    mocker.patch("metronome_pulse_dbt.artifact_reader.httpx.AsyncClient", return_value=mock_client)

    reader = CloudArtifactReader(
        api_token="tok",
        account_id="10",
        job_id="20",
        base_url="https://cloud.getdbt.com/api/v2",
    )
    await reader.read_manifest()

    first_call_url = mock_client.get.call_args_list[0][0][0]
    assert "accounts/10/runs/" in first_call_url
    assert "job_definition_id=20" in first_call_url
    assert "order_by=-finished_at" in first_call_url
    assert "limit=1" in first_call_url


async def test_cloud_404_optional_artifacts(mocker):
    """404 for catalog → None (optional artifact absent is not an error)."""
    runs_body = {"data": [{"id": 7}]}

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=[
        _make_response(200, runs_body),
        _make_response(404),
    ])

    mocker.patch("metronome_pulse_dbt.artifact_reader.httpx.AsyncClient", return_value=mock_client)

    reader = _cloud_reader()
    result = await reader.read_catalog()

    assert result is None


async def test_cloud_auth_failure(mocker):
    """401 on runs list → CloudApiError with correct status_code."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_make_response(401))

    mocker.patch("metronome_pulse_dbt.artifact_reader.httpx.AsyncClient", return_value=mock_client)

    reader = _cloud_reader()

    with pytest.raises(CloudApiError) as exc_info:
        await reader.read_manifest()

    assert exc_info.value.status_code == 401


async def test_cloud_auth_failure_403(mocker):
    """403 on artifact fetch → CloudApiError with status_code 403."""
    runs_body = {"data": [{"id": 7}]}

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=[
        _make_response(200, runs_body),
        _make_response(403),
    ])

    mocker.patch("metronome_pulse_dbt.artifact_reader.httpx.AsyncClient", return_value=mock_client)

    reader = _cloud_reader()

    with pytest.raises(CloudApiError) as exc_info:
        await reader.read_manifest()

    assert exc_info.value.status_code == 403


async def test_cloud_is_available(mocker):
    """Runs list returns 200 → is_available() is True."""
    runs_body = {"data": [{"id": 7}]}

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_make_response(200, runs_body))

    mocker.patch("metronome_pulse_dbt.artifact_reader.httpx.AsyncClient", return_value=mock_client)

    reader = _cloud_reader()
    assert await reader.is_available() is True


async def test_cloud_is_available_false_on_error(mocker):
    """Network error → is_available() returns False rather than raising."""
    import httpx as _httpx

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=_httpx.ConnectError("timeout"))

    mocker.patch("metronome_pulse_dbt.artifact_reader.httpx.AsyncClient", return_value=mock_client)

    reader = _cloud_reader()
    assert await reader.is_available() is False
