"""Conservative target rule. Never infer a miss from absent input/status."""
from dataclasses import dataclass
from typing import Any

from analysis.contracts import Eligibility, Outcome


@dataclass(frozen=True)
class Judgment:
    eligibility: Eligibility
    outcome: Outcome
    reasons: tuple[str, ...]


REQUIRED = (
    "build_verified", "knowledge_verified", "move_verified", "block_verified",
    "actor_verified", "standing", "reach_validated", "alignment_validated",
    "window_complete", "timing_validated", "wall_clear", "resource_independent",
)
EXCLUDED = ("standing", "reach_validated", "alignment_validated", "wall_clear",
            "resource_independent")


def judge(conditions: dict[str, Any], *, reviewed: bool, max_uncertainty_us: int = 16667) -> Judgment:
    if not reviewed:
        return Judgment(Eligibility.UNKNOWN, Outcome.UNKNOWN, ("REVIEW_REQUIRED",))
    missing = tuple(key.upper() for key in REQUIRED if conditions.get(key) is not True)
    if any(conditions.get(key) is False for key in EXCLUDED):
        return Judgment(Eligibility.INELIGIBLE, Outcome.UNKNOWN, missing)
    uncertainty = conditions.get("uncertainty_us")
    if (
        isinstance(uncertainty, bool) or not isinstance(uncertainty, int)
        or uncertainty < 0 or uncertainty > max_uncertainty_us
    ):
        missing += ("TIMING_UNCERTAINTY",)
    if missing:
        return Judgment(Eligibility.UNKNOWN, Outcome.UNKNOWN, missing)
    success = conditions.get("punish_confirmed") is True
    failure = conditions.get("failure_confirmed") is True
    if success and failure:
        return Judgment(Eligibility.ELIGIBLE, Outcome.UNKNOWN, ("CONFLICTING_OUTCOMES",))
    if success:
        return Judgment(Eligibility.ELIGIBLE, Outcome.SUCCESS, ())
    if failure:
        return Judgment(Eligibility.ELIGIBLE, Outcome.FAILURE, ())
    return Judgment(Eligibility.ELIGIBLE, Outcome.UNKNOWN, ("OUTCOME_UNOBSERVED",))
