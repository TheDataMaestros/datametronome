"""The fail/warn/condition ladder that decides a check's status.

The ordering is not obvious: an explicit `fail` outranks an explicit `warn`,
both outrank the condition parsed from the check config, and a condition that
trips with no `fail` set degrades to a warn rather than failing.
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


def grade(c, observed, parsed=None):
    return ClefExecutor()._grade(c, observed, parsed or {}, "Observed")


@pytest.mark.parametrize(
    "c, observed, parsed",
    [
        (clef(), 0, {}),
        (clef(warn="> 100", fail="> 200"), 10, {"operator": ">", "value": 50}),
    ],
)
def test_nothing_tripped_returns_none(c, observed, parsed):
    # None means "no verdict"; the caller supplies its own pass message.
    assert grade(c, observed, parsed) is None


def test_fail_wins_when_both_would_trip():
    status, message = grade(clef(warn="> 5", fail="> 5"), 10)
    assert status == "fail"
    assert message == "Observed violates fail condition (> 5)"


def test_warn_applies_when_only_warn_trips():
    status, message = grade(clef(warn="> 5", fail="> 100"), 10)
    assert status == "warn"
    assert message == "Observed breaches warning condition (> 5)"


def test_an_empty_parsed_condition_means_greater_than_zero():
    """Pinning existing behaviour, not endorsing it: parsed.get defaults of
    ">" and 0 grade any positive observation as a violation, so a condition
    that failed to parse reports fail instead of "could not evaluate"."""
    assert grade(clef(fail="> 999"), 10, {}) == (
        "fail",
        "Observed violates condition (> 999)",
    )
    assert grade(clef(fail="> 999"), 0, {}) is None


def test_parsed_condition_fails_when_a_fail_is_configured():
    # The condition is the last resort, and it borrows fail's severity.
    status, _ = grade(clef(fail="> 999"), 10, {"operator": ">", "value": 5})
    assert status == "fail"


def test_parsed_condition_only_warns_with_no_fail_configured():
    # The asymmetry worth pinning: same trip, softer verdict.
    status, _ = grade(clef(warn="> 999"), 10, {"operator": ">", "value": 5})
    assert status == "warn"
