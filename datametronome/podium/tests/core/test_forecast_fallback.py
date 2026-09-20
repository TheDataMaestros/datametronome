"""The forecast check's no-SARIMA fallback: mean ± k*std over recent history.

This path only runs when statsmodels/pandas are missing, which is why it had
no coverage. It still decides pass/fail on real data, so the band it computes
is worth pinning.
"""

import pytest

from datametronome_podium.features.clefs.model import Clef
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.services import clef_executor
from datametronome_podium.services.clef_executor import ClefExecutor


class FakeConnector:
    def __init__(self, values):
        self.values = values

    async def query(self, _):
        return [{"value": v} for v in self.values]


@pytest.fixture
def no_sarima(monkeypatch):
    monkeypatch.setattr(clef_executor, "SarimaForecaster", None)
    monkeypatch.setattr(clef_executor, "pd", None)


def _clef(**config):
    return Clef(
        id="c1",
        stave_id="s1",
        name="n",
        check_type="forecast",
        config={"query": "SELECT 1", **config},
    )


STAVE = Stave(
    id="s1",
    name="s",
    data_source_type="sqlite",
    connection_config={"database_path": ":memory:"},
)


async def run(values, **config):
    return await ClefExecutor()._execute_forecast_check(
        _clef(**config), STAVE, FakeConnector(values)
    )


@pytest.mark.asyncio
async def test_a_value_inside_the_band_passes(no_sarima):
    # Steady history, last value one of the crowd.
    result = await run([10, 11, 9, 10, 11, 9, 10, 11, 9, 10, 10])
    assert result.status == "pass"
    assert result.details["method"] == "fallback_band"


@pytest.mark.asyncio
async def test_a_value_outside_the_band_fails(no_sarima):
    result = await run([10, 11, 9, 10, 11, 9, 10, 11, 9, 10, 500])
    assert result.status == "fail"
    assert result.observed_value == 500
    assert result.details["upper_bound"] < 500


@pytest.mark.asyncio
async def test_the_band_is_centred_on_the_mean_not_trend_projected(no_sarima):
    """A rising series is graded against a band centred on the window mean.

    Deliberate: the fallback is crude on purpose and SARIMA is the path that
    models trend. A trend term would shift the band's centre off the mean,
    which is what this pins.
    """
    result = await run(list(range(1, 21)))  # 1..20, last observed is 20
    band = result.details
    centre = (band["lower_bound"] + band["upper_bound"]) / 2
    assert centre == pytest.approx(band["mean"])


@pytest.mark.asyncio
async def test_sigma_width_is_configurable(no_sarima):
    values = [10, 11, 9, 10, 11, 9, 10, 11, 9, 10, 14]
    assert (await run(values, fallback_sigma=0.5)).status == "fail"
    assert (await run(values, fallback_sigma=10)).status == "pass"


@pytest.mark.asyncio
async def test_too_little_history_warns_instead_of_guessing(no_sarima):
    result = await run([1, 2, 3])
    assert result.status == "warn"
