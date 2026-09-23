from dataclasses import replace

import pytest

from analysis.contracts import Eligibility, Outcome
from analysis.evaluation import evaluate
from tests.factories import event, plan_for


def histories():
    return (
        [event(i, success=i % 10 < 2) for i in range(100)],
        [event(i, followup=True, success=i % 10 < 8) for i in range(100)],
    )


def run(plan, baseline, followup, **kwargs):
    return evaluate(
        plan,
        baseline,
        followup,
        verified_practice=40,
        practice_completed_at="2026-09-15T12:00:00Z",
        **kwargs,
    )


def test_improvement_is_observational_and_membership_frozen():
    before, after = histories()
    result = run(plan_for(before), before, after)
    assert result["status"] == "OBSERVED_IMPROVEMENT"
    assert result["causal"] is False and result["dataset_kind"] == "synthetic"
    assert len(result["followup_membership"]) == 100


def test_deterioration_and_no_meaningful_change():
    before, after = histories()
    before = [
        replace(e, outcome=Outcome.SUCCESS if i % 10 < 8 else Outcome.FAILURE)
        for i, e in enumerate(before)
    ]
    after_bad = [
        replace(e, outcome=Outcome.SUCCESS if i % 10 < 2 else Outcome.FAILURE)
        for i, e in enumerate(after)
    ]
    assert run(plan_for(before), before, after_bad)["status"] == "OBSERVED_DETERIORATION"
    assert (
        run(plan_for(before, meaningful_change=0.25), before, after)["status"]
        == "NO_MEANINGFUL_CHANGE"
    )


def test_no_followup_is_insufficient_not_improved():
    before, _ = histories()
    assert run(plan_for(before), before, [])["status"] == "INSUFFICIENT_EXPOSURE"


@pytest.mark.parametrize(
    "change",
    [
        {"detector_version": "new-unapproved"},
        {"game_build": "new-build"},
        {"context": "other"},
        {"mode": "practice"},
        {"deleted": True},
        {"played_at": "2026-09-01T12:00:00Z"},
    ],
)
def test_incompatible_evidence_blocks_claim(change):
    before, after = histories()
    after[0] = replace(after[0], **change)
    assert run(plan_for(before), before, after)["status"] == "NOT_COMPARABLE"


def test_baseline_correction_cannot_silently_change_plan():
    before, after = histories()
    plan = plan_for(before)
    before[0] = replace(before[0], outcome=Outcome.FAILURE)
    assert run(plan, before, after)["status"] == "NOT_COMPARABLE"


def test_differential_outcome_coverage_blocks_claim():
    before, after = histories()
    after[:20] = [replace(e, outcome=Outcome.UNKNOWN) for e in after[:20]]
    assert run(plan_for(before), before, after)["status"] == "NOT_COMPARABLE"


def test_differential_eligibility_coverage_blocks_claim():
    before, after = histories()
    after[:20] = [
        replace(e, eligibility=Eligibility.UNKNOWN, outcome=Outcome.UNKNOWN) for e in after[:20]
    ]
    assert run(plan_for(before), before, after)["status"] == "NOT_COMPARABLE"


def test_missing_practice_and_unapproved_measurement():
    before, after = histories()
    assert (
        evaluate(plan_for(before), before, after, verified_practice=0, practice_completed_at=None)[
            "status"
        ]
        == "INSUFFICIENT_EXPOSURE"
    )
    assert (
        run(plan_for(before, measurement_approved=False), before, after)["status"]
        == "NOT_COMPARABLE"
    )


def test_few_independent_sessions_and_wide_cluster_uncertainty():
    before, after = histories()
    after = [replace(e, session_id="one") for e in after]
    assert run(plan_for(before), before, after)["status"] == "INSUFFICIENT_EXPOSURE"
    after = [
        replace(
            e, session_id=f"f{i // 10}", outcome=Outcome.SUCCESS if i // 10 % 2 else Outcome.FAILURE
        )
        for i, e in enumerate(after)
    ]
    assert run(plan_for(before), before, after)["status"] == "INCONCLUSIVE"


def test_duplicate_cross_period_evidence_raises():
    before, _ = histories()
    with pytest.raises(ValueError):
        run(plan_for(before), before, before)


def test_windows_require_timezone_and_order():
    before, _ = histories()
    with pytest.raises(ValueError):
        plan_for(before, baseline_end="2026-09-10")
