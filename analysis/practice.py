"""Reviewed practice workflow contracts and conservative research progression."""

import math
from typing import Any

from analysis.contracts import Opportunity, digest
from analysis.statistics import summarize


def workflow(value: Any) -> dict[str, Any]:
    required = {
        "version",
        "context",
        "response",
        "success_criteria",
        "setup_steps",
        "alternatives",
        "capture_steps",
        "progression",
    }
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value["version"] != "practice-workflow/1"
    ):
        raise ValueError("Use the exact practice-workflow/1 contract")
    if value["context"] != "jin/jin":
        raise ValueError("Only the supported Jin/Jin context is implemented")
    for field in ("response", "success_criteria"):
        if not isinstance(value[field], str) or not 5 <= len(value[field].strip()) <= 500:
            raise ValueError("Reviewed response and success criteria are required")
    for field in ("setup_steps", "alternatives", "capture_steps"):
        rows = value[field]
        if (
            not isinstance(rows, list)
            or not 1 <= len(rows) <= 12
            or any(not isinstance(row, str) or not 5 <= len(row.strip()) <= 500 for row in rows)
        ):
            raise ValueError(
                "Use bounded reviewed native setup, alternatives and capture instructions"
            )
    rules = value["progression"]
    if (
        not isinstance(rules, dict)
        or set(rules)
        != {
            "version",
            "minimum_known",
            "minimum_sessions",
            "minimum_coverage",
            "minimum_agreement",
            "ready_lower_bound",
        }
        or rules["version"] != "practice-progression/1"
    ):
        raise ValueError("Use the exact practice-progression/1 contract")
    if type(rules["minimum_known"]) is not int or not 40 <= rules["minimum_known"] <= 200:
        raise ValueError("At least 40 and at most 200 known trials are required")
    if type(rules["minimum_sessions"]) is not int or not 2 <= rules["minimum_sessions"] <= 10:
        raise ValueError("Use 2-10 distinct reviewed sessions")
    for field, low in (
        ("minimum_coverage", 0.9),
        ("minimum_agreement", 0.8),
        ("ready_lower_bound", 0.5),
    ):
        number = rules[field]
        if type(number) not in (int, float) or not math.isfinite(number) or not low <= number <= 1:
            raise ValueError("Progression bounds must be finite conservative fractions")
    return value


def progression(
    events: list[Opportunity],
    rules: dict[str, Any],
    *,
    reviewed: int,
    agreement: float | None,
    minimum_plan_practice: int,
    dataset_kind: str,
    baseline_available: bool,
    unavailable: int = 0,
) -> dict[str, Any]:
    if dataset_kind not in {"real", "synthetic"} or any(
        e.dataset_kind != dataset_kind for e in events
    ):
        raise ValueError("Practice dataset scope must match the declared plan")
    if any(e.deleted or e.mode != "practice" for e in events):
        raise ValueError("Progression requires available practice observations")
    if (
        len(
            {
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
        )
        > 1
    ):
        raise ValueError("Practice measurements cannot be pooled")
    if not 0 <= reviewed <= len(events) or (agreement is not None and not 0 <= agreement <= 1):
        raise ValueError("Invalid review completeness/agreement")
    summary = summarize(events)
    reasons = []
    if not baseline_available:
        state = "BASELINE_REVIEW_REQUIRED"
    elif unavailable:
        state = "EVIDENCE_REVIEW_REQUIRED"
        reasons.append("UNAVAILABLE_OR_INCOMPATIBLE_LINKED_TRIALS")
    elif (
        summary["denominator"] < max(rules["minimum_known"], minimum_plan_practice)
        or summary["sessions"] < rules["minimum_sessions"]
    ):
        state = "MORE_REVIEWED_PRACTICE_NEEDED"
    elif (summary["coverage"] or 0) < rules["minimum_coverage"] or (
        summary["eligibility_coverage"] or 0
    ) < rules["minimum_coverage"]:
        state = "EVIDENCE_REVIEW_REQUIRED"
        reasons.append("OUTCOME_OR_ELIGIBILITY_COVERAGE")
    elif reviewed != len(events) or agreement is None or agreement < rules["minimum_agreement"]:
        state = "EVIDENCE_REVIEW_REQUIRED"
        reasons.append("INDEPENDENT_REVIEW_AGREEMENT")
    elif dataset_kind == "real":
        state = "REAL_PRACTICE_VALIDATION_PENDING"
    elif summary["credible_interval"][0] >= rules["ready_lower_bound"]:
        state = "READY_FOR_FOLLOWUP"
    else:
        state = "REPEAT_REVIEWED_SETUP"
    actions = {
        "BASELINE_REVIEW_REQUIRED": "Review or rebuild the frozen baseline before progressing.",
        "EVIDENCE_REVIEW_REQUIRED": "Review missing, uncertain or incompatible source evidence; do not advance.",
        "MORE_REVIEWED_PRACTICE_NEEDED": "Collect enough compatible reviewed trials across distinct sessions.",
        "REAL_PRACTICE_VALIDATION_PENDING": "Expert and G4 qualification are required before real progression advice.",
        "READY_FOR_FOLLOWUP": "Keep the reviewed drill and frozen dates; collect later comparable matches.",
        "REPEAT_REVIEWED_SETUP": "Repeat the same reviewed setup or ask for a new independently reviewed drill version.",
    }
    return {
        "state": state,
        "next_action": actions[state],
        "reasons": reasons,
        "summary": summary,
        "rules": rules,
        "rules_hash": digest(rules),
        "reviewed": reviewed,
        "agreement": agreement,
        "release_approved": False,
        "causal": False,
    }
