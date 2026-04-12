"""Tests for BigQuery QueryJobConfig helper (named vs positional)."""

import pytest

pytest.importorskip("google.cloud.bigquery")

from metronome_pulse_bigquery.job_config import build_query_job_config


def test_named_limit_parameter() -> None:
    cfg = build_query_job_config(None, {"lim": 42})
    assert cfg is not None
    assert len(cfg.query_parameters) == 1
    assert cfg.query_parameters[0].name == "lim"
    assert cfg.query_parameters[0].value == 42


def test_positional_legacy() -> None:
    cfg = build_query_job_config([1, "x"], None)
    assert cfg is not None
    assert len(cfg.query_parameters) == 2
