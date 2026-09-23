"""Frozen evidence comparison. Output is association, never causal efficacy."""

from collections import defaultdict
from dataclasses import asdict
from typing import Any

import numpy as np
from scipy.stats import beta

from analysis.contracts import Eligibility, EvaluationSpec, Opportunity, Outcome, aware_time, digest
from analysis.statistics import summarize

NEXT_ACTION = {
    "NOT_COMPARABLE": "Repair evidence, chronology or measurement compatibility.",
    "INSUFFICIENT_EXPOSURE": "Collect more verified practice or comparable match opportunities.",
    "INCONCLUSIVE": "Gather independent sessions; do not claim improvement.",
    "NO_MEANINGFUL_CHANGE": "Review adherence and revise the drill if appropriate.",
    "OBSERVED_IMPROVEMENT": "Maintain practice and check retention; causality is not established.",
    "OBSERVED_DETERIORATION": "Review context and the intervention before continuing.",
}


def _clusters(events: list[Opportunity]) -> np.ndarray:
    buckets: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for event in events:
        if event.eligibility == Eligibility.ELIGIBLE and event.outcome != Outcome.UNKNOWN:
            buckets[event.session_id][0] += event.outcome == Outcome.SUCCESS
            buckets[event.session_id][1] += 1
    return np.asarray([buckets[k] for k in sorted(buckets)], dtype=float)


def evaluate(
    plan: EvaluationSpec,
    baseline: list[Opportunity],
    followup: list[Opportunity],
    *,
    verified_practice: int,
    practice_completed_at: str | None,
    observed_minutes: tuple[float | None, float | None] = (None, None),
) -> dict[str, Any]:
    if verified_practice < 0:
        raise ValueError("Practice count cannot be negative")
    if any(m is not None and m <= 0 for m in observed_minutes):
        raise ValueError("Observed duration must be positive or unknown")
    if len({e.id for e in baseline + followup}) != len(baseline + followup):
        raise ValueError("Duplicate evidence IDs")
    if set(e.played_key for e in baseline) & set(e.played_key for e in followup):
        raise ValueError("Same played opportunity cannot be in both periods")
    before, after = summarize(baseline), summarize(followup)
    issues: list[str] = []
    membership = tuple(sorted((e.id, e.content_hash) for e in baseline))
    if membership != tuple(sorted(plan.baseline_membership)):
        issues.append("BASELINE_MEMBERSHIP_CHANGED")
    if not plan.measurement_approved:
        issues.append("MEASUREMENT_NOT_APPROVED")
    for event in baseline + followup:
        if event.deleted:
            issues.append("DELETED_EVIDENCE")
        if (
            event.situation != plan.situation
            or event.metric != plan.metric
            or event.context != plan.context
            or event.game_build not in plan.compatible_builds
            or event.detector_version not in plan.compatible_detectors
            or event.knowledge_revision not in plan.compatible_knowledge
            or event.dataset_kind != plan.dataset_kind
            or event.mode != "ranked"
        ):
            issues.append("INCOMPATIBLE_EVIDENCE")
    if any(aware_time(e.played_at) > aware_time(plan.baseline_end) for e in baseline):
        issues.append("BASELINE_OUTSIDE_WINDOW")
    if any(
        not aware_time(plan.followup_start)
        <= aware_time(e.played_at)
        <= aware_time(plan.followup_end)
        for e in followup
    ):
        issues.append("FOLLOWUP_OUTSIDE_WINDOW")
    if practice_completed_at is not None:
        exposure = aware_time(practice_completed_at)
        if exposure < aware_time(plan.baseline_end) or exposure > aware_time(plan.followup_start):
            issues.append("PRACTICE_CHRONOLOGY")
        if any(aware_time(e.played_at) <= exposure for e in followup):
            issues.append("MATCH_PRECEDES_PRACTICE")
    change = (
        after["rate"] - before["rate"]
        if after["rate"] is not None and before["rate"] is not None
        else None
    )
    result: dict[str, Any] = {
        "schema_version": "evaluation/1",
        "dataset_kind": plan.dataset_kind,
        "baseline": before,
        "followup": after,
        "observed_change": change,
        "change_interval": None,
        "interval_method": "session-cluster-bootstrap/v1",
        "verified_practice": verified_practice,
        "causal": False,
        "plan_hash": digest(asdict(plan)),
        "followup_membership": sorted((e.id, e.content_hash) for e in followup),
        "versions": sorted(
            {(e.game_build, e.knowledge_revision, e.detector_version) for e in baseline + followup}
        ),
        "opportunities_per_minute": [
            (stats["denominator"] + stats["eligible_unknown"]) / minutes if minutes else None
            for stats, minutes in zip((before, after), observed_minutes, strict=True)
        ],
    }
    if issues:
        status = "NOT_COMPARABLE"
    elif (
        verified_practice < plan.minimum_practice
        or practice_completed_at is None
        or min(before["denominator"], after["denominator"]) < plan.minimum_sample
        or min(before["sessions"], after["sessions"]) < plan.minimum_sessions
    ):
        status = "INSUFFICIENT_EXPOSURE"
    elif (
        min(before["coverage"], after["coverage"]) < plan.minimum_coverage
        or abs(before["coverage"] - after["coverage"]) > plan.max_coverage_difference
        or min(before["eligibility_coverage"], after["eligibility_coverage"])
        < plan.minimum_coverage
        or abs(before["eligibility_coverage"] - after["eligibility_coverage"])
        > plan.max_coverage_difference
    ):
        status = "NOT_COMPARABLE"
        issues.append("OUTCOME_OR_ELIGIBILITY_COVERAGE_SHIFT")
    else:
        rng = np.random.default_rng(plan.seed)
        distributions = []
        for period in (baseline, followup):
            clusters = _clusters(period)
            choices = rng.integers(0, len(clusters), (plan.bootstrap_samples, len(clusters)))
            totals = clusters[choices].sum(axis=1)
            distributions.append(totals[:, 0] / totals[:, 1])
        low, high = map(float, np.quantile(distributions[1] - distributions[0], [0.025, 0.975]))
        # Bootstrap can collapse at identical session rates or boundary outcomes.
        # Preserve a finite-sample uncertainty floor using a conservative simultaneous
        # 97.5% Beta interval per period (Bonferroni envelope for their difference).
        before_bounds = beta.ppf([0.0125, 0.9875], before["numerator"] + 1, before["failures"] + 1)
        after_bounds = beta.ppf([0.0125, 0.9875], after["numerator"] + 1, after["failures"] + 1)
        low = min(low, float(after_bounds[0] - before_bounds[1]))
        high = max(high, float(after_bounds[1] - before_bounds[0]))
        result["interval_method"] = "session-cluster-bootstrap-with-beta-envelope/v1"
        result["change_interval"] = [low, high]
        delta = plan.meaningful_change
        if low > delta:
            status = "OBSERVED_IMPROVEMENT"
        elif high < -delta:
            status = "OBSERVED_DETERIORATION"
        elif low >= -delta and high <= delta:
            status = "NO_MEANINGFUL_CHANGE"
        else:
            status = "INCONCLUSIVE"
    result.update(status=status, reasons=sorted(set(issues)), next_action=NEXT_ACTION[status])
    return result
