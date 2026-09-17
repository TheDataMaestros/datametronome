"""Every accepted check type must have something that runs it, and vice versa.

`python` was accepted by the model and the API schema with no runner behind it,
so a clef created with it failed every run with "Unknown check type".
"""

import pytest

from datametronome_podium.features.clefs.model import Clef, SUPPORTED_CHECK_TYPES
from datametronome_podium.features.clefs.schema import VALID_CHECK_TYPES
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.services.clef_executor import ClefExecutor


def _runners() -> set[str]:
    return {
        name[len("_execute_") : -len("_check")]
        for name in dir(ClefExecutor)
        if name.startswith("_execute_") and name.endswith("_check")
    }


def test_the_api_accepts_what_the_model_supports():
    assert sorted(VALID_CHECK_TYPES) == sorted(SUPPORTED_CHECK_TYPES)


def test_every_accepted_check_type_has_a_runner_and_no_runner_is_unreachable():
    assert _runners() == set(SUPPORTED_CHECK_TYPES)


@pytest.mark.asyncio
async def test_a_type_with_no_runner_is_reported_not_raised():
    """The model rejects unknown types, so this branch is only reachable past
    validation. It still has to answer, not AttributeError."""
    clef = Clef.model_construct(
        id="c1", stave_id="s1", name="n", check_type="nope",
        config={"table": "t"}, warn=None, fail=None,
    )
    stave = Stave(
        id="s1", name="s", data_source_type="sqlite",
        connection_config={"database_path": ":memory:"},
    )
    result = await ClefExecutor().execute_clef(clef, stave)
    assert result.details["error"] == "unsupported_check_type"


@pytest.mark.asyncio
@pytest.mark.parametrize("check_type", SUPPORTED_CHECK_TYPES)
async def test_no_check_reports_pass_without_querying_anything(check_type):
    """Green means "I queried the data and it was fine", never "I did nothing".

    lookup_validation used to return a hardcoded pass with an invented 98%
    success rate. On a data quality tool a check that always reports green is
    worse than one that errors: the fake number reaches trends and reports.
    """
    clef = Clef.model_construct(
        id="c1", stave_id="s1", name="n", check_type=check_type,
        config={"table": "t", "column": "c"}, warn=None, fail=None,
    )
    stave = Stave(
        id="s1", name="s", data_source_type="sqlite",
        connection_config={"database_path": ":memory:"},
    )
    runner = getattr(ClefExecutor(), f"_execute_{check_type}_check")
    result = await runner(clef, stave, None)
    assert result.status != "pass", f"{check_type} passed with no connector"
