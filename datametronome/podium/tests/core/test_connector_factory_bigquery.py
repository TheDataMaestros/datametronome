"""The factory's BigQuery branch.

The package is built and published by the release job but was never installed
in CI, so this branch was only ever reached as an ImportError. Nothing checked
that stave config reaches the connector under the right names.
"""

import pytest

from datametronome_podium.core.connector_factory import _build_bigquery_connector

pytest.importorskip("metronome_pulse_bigquery")


class _FakePulse:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture
def patched(monkeypatch):
    import metronome_pulse_bigquery

    monkeypatch.setattr(metronome_pulse_bigquery, "BigQueryPulse", _FakePulse)
    monkeypatch.setattr(metronome_pulse_bigquery, "BigQueryReadonlyPulse", _FakePulse)


def test_config_reaches_the_connector(patched):
    conn = _build_bigquery_connector(
        {
            "project_id": "my-gcp-project",
            "credentials_json": {"type": "service_account"},
            "dataset": "analytics",
            "location": "EU",
        },
    )

    assert conn.kwargs["project_id"] == "my-gcp-project"
    assert conn.kwargs["credentials_json"] == {"type": "service_account"}
    assert conn.kwargs["dataset"] == "analytics"
    assert conn.kwargs["location"] == "EU"


def test_location_defaults_to_us(patched):
    conn = _build_bigquery_connector({"project_id": "p"})
    assert conn.kwargs["location"] == "US"


def test_missing_project_id_is_reported_as_a_missing_field(patched):
    # create_connector turns this KeyError into "Missing required connection
    # field: 'project_id'" rather than a bare traceback.
    with pytest.raises(KeyError, match="project_id"):
        _build_bigquery_connector({"dataset": "analytics"})
