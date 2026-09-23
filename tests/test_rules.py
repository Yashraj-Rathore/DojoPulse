from dataclasses import replace

import pytest

from analysis.contracts import Eligibility, Outcome
from analysis.rules import judge
from analysis.statistics import categorical, summarize
from tests.factories import conditions, event


def test_no_attack_or_absent_indicator_is_not_a_miss():
    result = judge(conditions(), reviewed=True)
    assert result.eligibility == Eligibility.ELIGIBLE
    assert result.outcome == Outcome.UNKNOWN


@pytest.mark.parametrize(
    "missing",
    [
        "build_verified",
        "knowledge_verified",
        "move_verified",
        "block_verified",
        "actor_verified",
        "reach_validated",
        "alignment_validated",
        "window_complete",
    ],
)
def test_missing_mandatory_evidence_abstains(missing):
    result = judge(conditions(**{missing: None, "failure_confirmed": True}), reviewed=True)
    assert result.outcome == Outcome.UNKNOWN


@pytest.mark.parametrize(
    "condition", ["wall_clear", "standing", "resource_independent", "reach_validated"]
)
def test_invalid_context_is_excluded(condition):
    result = judge(conditions(**{condition: False, "punish_confirmed": True}), reviewed=True)
    assert result.eligibility == Eligibility.INELIGIBLE


def test_uncertain_timing_and_conflict_abstain():
    assert (
        judge(conditions(uncertainty_us=20000, punish_confirmed=True), reviewed=True).outcome
        == Outcome.UNKNOWN
    )
    assert (
        judge(conditions(punish_confirmed=True, failure_confirmed=True), reviewed=True).outcome
        == Outcome.UNKNOWN
    )


def test_unreviewed_is_not_verified():
    assert judge(conditions(punish_confirmed=True), reviewed=False).outcome == Outcome.UNKNOWN


def test_known_outcome_requires_eligible_verified_evidence():
    with pytest.raises(ValueError):
        replace(event(), verified=False)
    with pytest.raises(ValueError):
        replace(event(), eligibility=Eligibility.UNKNOWN)


def test_unknown_is_not_failure_and_coverage_is_visible():
    events = [event(0), event(1, success=False), replace(event(2), outcome=Outcome.UNKNOWN)]
    summary = summarize(events)
    assert summary["denominator"] == 2 and summary["rate"] == 0.5
    assert summary["eligible_unknown"] == 1 and summary["coverage"] == 2 / 3
    assert summary["credible_interval"][0] < 0.5 < summary["credible_interval"][1]


def test_duplicate_played_opportunity_rejected():
    with pytest.raises(ValueError):
        summarize([event(), replace(event(), id="another-revision")])


def test_empty_stats_and_categorical_prior():
    assert summarize([])["rate"] is None
    assert categorical(["a", "a"], ("a", "b"))["posterior_mean"] == {"a": 0.75, "b": 0.25}
