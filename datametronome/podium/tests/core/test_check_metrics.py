"""Running a check must move the Prometheus counters.

check_runs_total, check_run_duration_seconds and anomalies_detected_total were
declared for months and never incremented, so /metrics served permanent zeros
and the Grafana panels built on them drew flat lines. A monitoring product
reporting "0 checks run" while running checks is the same class of lie as a
check reporting pass without querying anything.
"""

import pytest

from datametronome_podium.core import metrics
from datametronome_podium.features.clefs.model import Clef
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.services.clef_executor import CheckResult, ClefExecutor


def _value(counter, **labels):
    c = counter.labels(**labels) if labels else counter
    return c._value.get()


def test_a_completed_check_increments_its_status_counter():
    before = _value(metrics.check_runs_total, status="fail")
    ClefExecutor()._update_stats(
        CheckResult(clef_id="c", stave_id="s", status="fail", message="m")
    )
    assert _value(metrics.check_runs_total, status="fail") == before + 1


def test_anomalous_rows_are_counted():
    before = _value(metrics.anomalies_detected_total)
    ClefExecutor()._update_stats(
        CheckResult(
            clef_id="c", stave_id="s", status="fail", message="m", anomalies_count=7
        )
    )
    assert _value(metrics.anomalies_detected_total) == before + 7


def test_a_clean_check_adds_no_anomalies():
    before = _value(metrics.anomalies_detected_total)
    ClefExecutor()._update_stats(
        CheckResult(clef_id="c", stave_id="s", status="pass", message="m")
    )
    assert _value(metrics.anomalies_detected_total) == before


def test_duration_is_observed():
    before = metrics.check_run_duration_seconds._sum.get()
    ClefExecutor()._update_stats(
        CheckResult(
            clef_id="c", stave_id="s", status="pass", message="m", execution_time=1.5
        )
    )
    assert metrics.check_run_duration_seconds._sum.get() == pytest.approx(before + 1.5)


@pytest.mark.asyncio
async def test_the_counter_moves_through_a_real_execute_clef():
    """_update_stats is reachable from the public entry point, not just directly."""
    before = _value(metrics.check_runs_total, status="fail")
    clef = Clef.model_construct(
        id="c1", stave_id="s1", name="n", check_type="row_count",
        config={}, warn=None, fail=None,
    )
    stave = Stave(
        id="s1", name="s", data_source_type="sqlite",
        connection_config={"database_path": ":memory:"},
    )
    await ClefExecutor().execute_clef(clef, stave)
    assert _value(metrics.check_runs_total, status="fail") == before + 1
