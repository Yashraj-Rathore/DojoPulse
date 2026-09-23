"""Transparent counts, outcome coverage and descriptive Bayesian intervals."""

from collections import Counter
from typing import Any

from scipy.stats import beta

from analysis.contracts import Eligibility, Opportunity, Outcome


def summarize(events: list[Opportunity]) -> dict[str, Any]:
    keys = [e.played_key for e in events]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate played opportunity in selected evidence")
    eligible = [e for e in events if e.eligibility == Eligibility.ELIGIBLE]
    successes = sum(e.outcome == Outcome.SUCCESS for e in eligible)
    failures = sum(e.outcome == Outcome.FAILURE for e in eligible)
    known = successes + failures
    unknown = len(eligible) - known
    return {
        "numerator": successes,
        "denominator": known,
        "failures": failures,
        "eligible_unknown": unknown,
        "unknown_eligibility": sum(e.eligibility == Eligibility.UNKNOWN for e in events),
        "excluded": sum(e.eligibility == Eligibility.INELIGIBLE for e in events),
        "coverage": known / len(eligible) if eligible else None,
        "rate": successes / known if known else None,
        "posterior_mean": (successes + 1) / (known + 2) if known else None,
        "credible_interval": list(map(float, beta.ppf([0.025, 0.975], successes + 1, failures + 1)))
        if known
        else None,
        "interval_method": "Beta(1+k,1+n-k), independent events, descriptive",
        "sessions": len({e.session_id for e in eligible if e.outcome != Outcome.UNKNOWN}),
        "count": len(events),
        "eligibility_coverage": sum(e.eligibility != Eligibility.UNKNOWN for e in events)
        / len(events)
        if events
        else None,
    }


def categorical(
    actions: list[str], taxonomy: tuple[str, ...], prior: float = 1.0
) -> dict[str, Any]:
    if not taxonomy or len(set(taxonomy)) != len(taxonomy) or prior <= 0:
        raise ValueError("Invalid categorical prior/taxonomy")
    if any(a not in taxonomy for a in actions):
        raise ValueError("Action not in frozen taxonomy")
    counts = Counter(actions)
    total = len(actions) + prior * len(taxonomy)
    return {
        "n": len(actions),
        "prior": prior,
        "counts": {a: counts[a] for a in taxonomy},
        "posterior_mean": {a: (counts[a] + prior) / total for a in taxonomy},
    }
