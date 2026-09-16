"""Every accepted check type must have something that runs it.

`python` was accepted by the model and the API schema and had no runner, so a
clef created with it failed every execution with "Unknown check type". It read
as a broken check rather than an unimplemented feature, and the dispatch was an
if/elif chain, so nothing compared the two lists.

Same guard as test_data_source_coverage.py, for the other half of a check.
"""

import pytest

from datametronome_podium.features.clefs.model import SUPPORTED_CHECK_TYPES
from datametronome_podium.features.clefs.schema import VALID_CHECK_TYPES
from datametronome_podium.services.clef_executor import ClefExecutor


def test_the_api_accepts_what_the_model_supports():
    assert sorted(VALID_CHECK_TYPES) == sorted(SUPPORTED_CHECK_TYPES)


@pytest.mark.parametrize("check_type", SUPPORTED_CHECK_TYPES)
def test_every_accepted_check_type_has_a_runner(check_type):
    assert check_type in ClefExecutor._RUNNERS, (
        f"clefs can be created with check_type {check_type} but every run "
        "would return 'Unknown check type'"
    )


def test_no_runner_exists_for_a_type_that_cannot_be_created():
    orphans = set(ClefExecutor._RUNNERS) - set(SUPPORTED_CHECK_TYPES)
    assert not orphans, f"unreachable check runners: {sorted(orphans)}"


def test_the_tier_lists_add_up_to_the_supported_list():
    from datametronome_podium.features.clefs import model

    tiers = (
        model.LEVEL_1_CHECKS
        + model.LEVEL_2_CHECKS
        + model.LEVEL_3_CHECKS
        + model.LEVEL_4_CHECKS
    )
    assert tiers == SUPPORTED_CHECK_TYPES
