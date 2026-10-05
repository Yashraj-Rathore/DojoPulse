"""Predeclared comparison scheduling and descriptive session adequacy; no causal power claim."""

import math
from collections import defaultdict
from typing import Any

import numpy as np
from scipy.stats import norm

from analysis.contracts import EvaluationSpec, Opportunity, aware_time
from analysis.statistics import summarize


def schedule(value: Any, spec: EvaluationSpec) -> dict[str, Any]:
    required = {"version", "expected_followup_sessions", "retention"}
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value["version"] != "comparison-schedule/1"
    ):
        raise ValueError("Use the exact comparison-schedule/1 contract")
    count = value["expected_followup_sessions"]
    if type(count) is not int or not spec.minimum_sessions <= count <= 100:
        raise ValueError("Declare the minimum required through 100 follow-up sessions")
    retention = value["retention"]
    if retention is not None:
        if not isinstance(retention, dict) or set(retention) != {
            "start",
            "end",
            "expected_sessions",
        }:
            raise ValueError("Retention requires start, end and expected_sessions")
        start, end = aware_time(retention["start"]), aware_time(retention["end"])
        if not aware_time(spec.followup_end) < start < end:
            raise ValueError("Retention must follow the complete initial follow-up window")
        count = retention["expected_sessions"]
        if type(count) is not int or not spec.minimum_sessions <= count <= 100:
            raise ValueError("Declare the minimum required through 100 retention sessions")
    end = aware_time(retention["end"] if retention else spec.followup_end)
    if (end - aware_time(spec.baseline_end)).total_seconds() > 366 * 86400:
        raise ValueError("Comparison collection is bounded to 366 days")
    return value


def diagnostics(events: list[Opportunity], spec: EvaluationSpec) -> dict[str, Any]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for event in events:
        if event.eligibility == "ELIGIBLE" and event.outcome in {"SUCCESS", "FAILURE"}:
            counts[event.session_id][0] += event.outcome == "SUCCESS"
            counts[event.session_id][1] += 1
    sizes = [row[1] for row in counts.values()]
    rates = [row[0] / row[1] for row in counts.values()]
    summary = summarize(events)
    variance = float(np.var(rates, ddof=1)) if len(rates) >= 2 else None
    reasons = []
    if summary["denominator"] < spec.minimum_sample:
        reasons.append("KNOWN_OUTCOME_FLOOR_NOT_MET")
    if len(sizes) < spec.minimum_sessions:
        reasons.append("INDEPENDENT_SESSION_FLOOR_NOT_MET")
    largest = max(sizes) / sum(sizes) if sizes else None
    if largest is not None and largest > 0.4:
        reasons.append("ONE_SESSION_DOMINATES_KNOWN_OUTCOMES")
    if len(rates) < 10:
        reasons.append("TOO_FEW_SESSIONS_FOR_VARIANCE_PLANNING")
    elif variance is None or variance <= 0:
        reasons.append("DEGENERATE_SESSION_VARIANCE")
    planned = None
    if len(rates) >= 10 and variance is not None and variance > 0:
        estimate = math.ceil(
            2
            * variance
            * (float(norm.ppf(0.975)) + float(norm.ppf(0.8))) ** 2
            / spec.meaningful_change**2
        )
        if estimate > 1000:
            reasons.append("PLANNING_ESTIMATE_EXCEEDS_LOCAL_BOUND")
        else:
            planned = max(spec.minimum_sessions, estimate)
    return {
        "version": "session-adequacy/1",
        "known_outcomes": summary["denominator"],
        "sessions": len(sizes),
        "minimum_known": spec.minimum_sample,
        "minimum_sessions": spec.minimum_sessions,
        "largest_session_share": largest,
        "minimum_session_known": min(sizes) if sizes else None,
        "maximum_session_known": max(sizes) if sizes else None,
        "session_rate_variance": variance,
        "reasons": reasons,
        "planning": {
            "version": "normal-session-variance/1",
            "sessions_per_period": planned,
            "alpha": 0.05,
            "target_power": 0.8,
            "meaningful_change": spec.meaningful_change,
            "actual_power_validated": False,
            "planning_only": True,
            "assumptions": [
                "independent equal-sized session-rate samples",
                "equal variance across periods",
                "normal approximation",
                "baseline-only variance; no post-hoc power",
            ],
        },
        "floor_is_power_guarantee": False,
        "causal": False,
    }
