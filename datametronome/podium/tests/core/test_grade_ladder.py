"""The fail/warn/condition ladder that decides a check's status.

Three checks carried this verbatim. The ordering matters and is not obvious:
an explicit `fail` outranks an explicit `warn`, both outrank the condition
parsed from the check config, and a condition that trips with no `fail` set
degrades to a warn rather than failing.

Nothing tested it directly, only through whole-check paths.
"""

import pytest

from datametronome_podium.features.clefs.model import Clef
from datametronome_podium.services.clef_executor import ClefExecutor


def clef(warn=None, fail=None) -> Clef:
    return Clef(
        id="c1",
        stave_id="s1",
        name="n",
        check_type="row_count",
        config={"table": "t"},
        warn=warn,
        fail=fail,
    )


@pytest.fixture
def grade():
    executor = ClefExecutor()
    return lambda c, observed, parsed=None: executor._grade(
        c, observed, parsed or {}, "Observed"
    )


def test_nothing_set_and_nothing_tripped_returns_none(grade):
    # None means "no verdict"; the caller supplies its own pass message.
    assert grade(clef(), 0) is None


def test_fail_wins_when_both_would_trip(grade):
    # A value over both thresholds is a failure, not a warning.
    status, message = grade(clef(warn="> 5", fail="> 5"), 10)
    assert status == "fail"
    assert "fail condition" in message


def test_warn_applies_when_only_warn_trips(grade):
    status, message = grade(clef(warn="> 5", fail="> 100"), 10)
    assert status == "warn"
    assert "warning condition" in message


def test_neither_threshold_tripped_returns_none(grade):
    assert grade(clef(warn="> 100", fail="> 200"), 10, {"operator": ">", "value": 50}) is None


def test_an_empty_parsed_condition_means_greater_than_zero(grade):
    """Pinning existing behaviour, not endorsing it.

    parsed.get("operator", ">") and parsed.get("value", 0) mean an absent or
    unparsed condition grades any positive observation as a violation. A check
    whose condition failed to parse therefore reports fail rather than saying
    it could not be evaluated.

    Left as is because this is a refactor, and changing it would change check
    outcomes. Worth revisiting on its own.
    """
    assert grade(clef(fail="> 999"), 10, {}) == (
        "fail",
        "Observed violates condition (> 999)",
    )
    assert grade(clef(fail="> 999"), 0, {}) is None


def test_parsed_condition_fails_when_a_fail_is_configured(grade):
    # The condition is the last resort, and it borrows fail's severity.
    status, _ = grade(clef(fail="> 999"), 10, {"operator": ">", "value": 5})
    assert status == "fail"


def test_parsed_condition_only_warns_with_no_fail_configured(grade):
    # This is the asymmetry worth pinning: same trip, softer verdict.
    status, _ = grade(clef(warn="> 999"), 10, {"operator": ">", "value": 5})
    assert status == "warn"


def test_the_subject_leads_the_message(grade):
    _, message = grade(clef(fail="> 5"), 10)
    assert message.startswith("Observed ")
