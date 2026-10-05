"""Versioned, descriptive diagnosis policy; proposed thresholds are not release evidence."""

import math
from dataclasses import asdict, dataclass
from typing import Any

from analysis.contracts import Opportunity, digest
from analysis.statistics import summarize


@dataclass(frozen=True)
class DiagnosisPolicy:
    version: str = "diagnosis-policy/1"
    minimum_known: int = 40
    minimum_sessions: int = 5
    minimum_outcome_coverage: float = 0.9
    minimum_eligibility_coverage: float = 0.9
    minimum_review_agreement: float = 0.8
    minimum_failure_lower_bound: float = 0.2
    maximum_priorities: int = 3


POLICY = DiagnosisPolicy()


def priority_assessment(value: Any) -> dict[str, Any]:
    """A reviewed drill may carry explicit relative value/feasibility, never a damage claim."""
    if not isinstance(value, dict) or set(value) != {
        "version",
        "value",
        "trainability",
        "rationale",
    }:
        raise ValueError("Priority assessment needs version, value, trainability and rationale")
    if value["version"] != "priority-assessment/1":
        raise ValueError("Unsupported priority assessment version")
    for field in ("value", "trainability"):
        number = value[field]
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError("Priority value and trainability must be finite fractions")
    if not isinstance(value["rationale"], str) or not 5 <= len(value["rationale"].strip()) <= 2000:
        raise ValueError("Priority assessment requires a bounded review rationale")
    return dict(value)


def diagnose(
    events: list[Opportunity],
    *,
    independent_reviews: int,
    review_agreement: float | None,
    assessment: dict[str, Any] | None,
    supported: bool,
) -> dict[str, Any]:
    if any(e.deleted or e.mode != "ranked" for e in events):
        raise ValueError("Diagnosis requires current ranked evidence")
    scopes = {
        (
            e.situation,
            e.metric,
            e.context,
            e.game_build,
            e.knowledge_revision,
            e.detector_version,
            e.dataset_kind,
        )
        for e in events
    }
    if len(scopes) > 1:
        raise ValueError("Diagnosis cannot mix measurement/context versions")
    if not 0 <= independent_reviews <= len(events) or (
        review_agreement is not None and not 0 <= review_agreement <= 1
    ):
        raise ValueError("Invalid review coverage/agreement")
    assessment = priority_assessment(assessment) if assessment is not None else None
    summary = summarize(events)
    interval = summary["credible_interval"]
    failure_interval = [1 - interval[1], 1 - interval[0]] if interval else None
    reasons = []
    if summary["denominator"] < POLICY.minimum_known:
        reasons.append("MINIMUM_KNOWN_OUTCOMES")
    if summary["sessions"] < POLICY.minimum_sessions:
        reasons.append("MINIMUM_SESSIONS")
    if (summary["coverage"] or 0) < POLICY.minimum_outcome_coverage:
        reasons.append("OUTCOME_COVERAGE")
    if (summary["eligibility_coverage"] or 0) < POLICY.minimum_eligibility_coverage:
        reasons.append("ELIGIBILITY_COVERAGE")
    review_ready = independent_reviews == len(events) and (
        review_agreement is not None and review_agreement >= POLICY.minimum_review_agreement
    )
    if not supported:
        state = "UNSUPPORTED_SCOPE"
    elif reasons:
        state = "INSUFFICIENT_EVIDENCE"
    elif not review_ready:
        state = "REVIEW_REQUIRED"
        reasons.append("INDEPENDENT_REVIEW_AGREEMENT")
    elif events[0].dataset_kind == "real":
        state = "REAL_VALIDATION_PENDING"
        reasons.append("EXPERT_AND_USER_UTILITY_VALIDATION")
    elif failure_interval and failure_interval[0] >= POLICY.minimum_failure_lower_bound:
        state = "OBSERVED_FAILURE_PATTERN"
    else:
        state = "NO_CLEAR_FAILURE_PATTERN"
    eligible = summary["denominator"] + summary["eligible_unknown"]
    frequency = eligible / summary["count"] if summary["count"] else None
    certainty = (
        failure_interval[0] * review_agreement
        if failure_interval and review_agreement is not None
        else None
    )
    score = None
    if state == "OBSERVED_FAILURE_PATTERN" and assessment is not None:
        assert frequency is not None and certainty is not None
        score = frequency * assessment["value"] * certainty * assessment["trainability"]
    if assessment is None:
        reasons.append("REVIEWED_PRIORITY_ASSESSMENT_MISSING")
    return {
        "state": state,
        "reasons": reasons,
        "summary": summary,
        "failure_interval": failure_interval,
        "review": {"independently_reviewed": independent_reviews, "agreement": review_agreement},
        "score": score,
        "factors": {
            "frequency": frequency,
            "value": assessment["value"] if assessment else None,
            "certainty": certainty,
            "trainability": assessment["trainability"] if assessment else None,
        },
        "assessment": assessment,
        "policy_version": POLICY.version,
        "policy_hash": digest(asdict(POLICY)),
        "release_approved": False,
    }


def rank_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(cards, key=lambda c: (c["score"] is None, -(c["score"] or 0), c["id"]))
    for index, card in enumerate(ordered):
        card["priority_rank"] = (
            index + 1 if card["score"] is not None and index < POLICY.maximum_priorities else None
        )
    return ordered
