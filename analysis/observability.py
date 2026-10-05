"""Aggregate G1 evidence from a sealed snapshot; no scientific or release approval."""

from collections import Counter
from statistics import median
from typing import Any

from jsonschema import ValidationError

from analysis.contracts import digest
from analysis.datasets import CATEGORIES, SPLITS, validate_snapshot
from analysis.rules import EXCLUDED, REQUIRED, judge

POLICY: dict[str, Any] = {
    "id": "g1-observability-proposal/1",
    "minimum_captures": 20,
    "minimum_players": 2,
    "minimum_sessions": 2,
    "minimum_resolvable_rate": 0.9,
    "narrow_above_unresolved_rate": 0.2,
    "maximum_uncertainty_us": 16667,
}


def visibility(label: dict[str, Any]) -> str:
    value = label.get("visibility")
    if not isinstance(value, str) or value not in {"RESOLVABLE", "UNCERTAIN", "UNOBSERVABLE"}:
        raise ValueError("Explicit observability visibility required")
    return value


def window(task: dict[str, Any]) -> dict[str, Any]:
    label = task["label"]
    conditions = label["conditions"]
    reasons = []
    if visibility(label) != "RESOLVABLE":
        reasons.append(visibility(label))
    if set(conditions) != {*REQUIRED, "punish_confirmed", "failure_confirmed", "uncertainty_us"}:
        raise ValueError("Explicit observability conditions required")
    if any(
        type(v) is not bool and v is not None
        for k, v in conditions.items()
        if k != "uncertainty_us"
    ):
        raise ValueError("Observability conditions must be Boolean or unknown")
    uncertainty = conditions["uncertainty_us"]
    if type(uncertainty) is not int or not 0 <= uncertainty <= 1000000:
        raise ValueError("Invalid observability uncertainty")
    judgment = judge(conditions, reviewed=True)
    if (label["eligibility"], label["outcome"]) != (
        judgment.eligibility.value,
        judgment.outcome.value,
    ):
        raise ValueError("Observability label contradicts mandatory evidence")
    # An exclusion does not rescue an unidentified move/actor or an incomplete window.
    if any(conditions[k] is not True for k in REQUIRED if k not in EXCLUDED):
        reasons.append("MISSING_CRITICAL_CONDITIONS")
    if judgment.eligibility.value == "UNKNOWN":
        reasons.append("UNKNOWN_ELIGIBILITY")
    elif judgment.eligibility.value == "ELIGIBLE" and judgment.outcome.value == "UNKNOWN":
        reasons.append("UNKNOWN_OUTCOME")
    if uncertainty > POLICY["maximum_uncertainty_us"]:
        reasons.append("HIGH_TIMESTAMP_UNCERTAINTY")
    reviews = task["reviews"]
    for review in reviews:
        visibility(review["label"])
    # Timing completeness is separate from human resolvability, not frame-accuracy proof.
    timings = [r["label"]["timing"] for r in reviews]
    reference = label["timing"]
    audited = all(
        t["start_us"] is not None and t["frame_duration_us"] is not None for t in timings[:2]
    )
    reference_audited = (
        reference["start_us"] is not None and reference["frame_duration_us"] is not None
    )
    pair_gap = (
        abs(timings[0]["start_us"] - timings[1]["start_us"])
        if all(t["start_us"] is not None for t in timings[:2])
        else None
    )
    return {
        "resolvable": not reasons,
        "reasons": reasons,
        "timing_audited": audited and reference_audited,
        "reviewer_start_gap_us": pair_gap,
        "uncertainty_us": uncertainty,
        "category": label["outcome"]
        if label["outcome"] != "UNKNOWN"
        else "NEAR_MISS"
        if label["eligibility"] == "INELIGIBLE"
        else "UNCERTAIN",
    }


def summarize(sources: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [s for s in sources if s["annotations"]["source_kind"] == "ranked"]
    windows, source_rates = [], []
    categories: Counter[str] = Counter()
    qc_visibility: Counter[str] = Counter()
    uncovered = review_seconds = 0
    for source in selected:
        qc_visibility[visibility(source["qc"]["label"])] += 1
        targets = [t for t in source["tasks"] if t["kind"] == "TARGET"]
        if any(t["kind"] not in {"TARGET", "TRIAL"} for t in source["tasks"]):
            raise ValueError("Invalid observability task kind")
        if source["qc"]["label"]["target_absent"]:
            categories["TARGET_ABSENT"] += 1
        elif not targets:
            uncovered += 1
        current = [window(t) for t in targets]
        windows.extend(current)
        categories.update(w["category"] for w in current)
        if current:
            source_rates.append(sum(w["resolvable"] for w in current) / len(current))
        review_seconds += sum(r["seconds"] for t in [source["qc"], *targets] for r in t["reviews"])
    resolved = sum(w["resolvable"] for w in windows)
    gaps = [w["reviewer_start_gap_us"] for w in windows if w["reviewer_start_gap_us"] is not None]
    return {
        "captures": len(selected),
        "excluded_non_ranked_captures": len(sources) - len(selected),
        "players": len({s["player_id"] for s in selected}),
        "sessions": len({s["session_id"] for s in selected}),
        "critical_windows": len(windows),
        "resolvable_windows": resolved,
        "unresolved_windows": len(windows) - resolved,
        "resolvable_rate": resolved / len(windows) if windows else None,
        "unresolved_rate": (len(windows) - resolved) / len(windows) if windows else None,
        "source_resolvable_rate_minimum": min(source_rates) if source_rates else None,
        "source_resolvable_rate_median": median(source_rates) if source_rates else None,
        "qc_visibility": {v: qc_visibility[v] for v in ("RESOLVABLE", "UNCERTAIN", "UNOBSERVABLE")},
        "sources_without_target_review_or_absence": uncovered,
        "categories": {k: categories[k] for k in CATEGORIES},
        "missing_categories": [k for k in CATEGORIES if not categories[k]],
        "unresolved_reasons": dict(
            sorted(Counter(r for w in windows for r in w["reasons"]).items())
        ),
        "timing_unaudited_windows": sum(not w["timing_audited"] for w in windows),
        "uncertainty_max_us": max((w["uncertainty_us"] for w in windows), default=None),
        "reviewer_start_gap_max_us": max(gaps, default=None),
        "review_seconds": review_seconds,
    }


def assess(bundle: dict[str, Any]) -> dict[str, Any]:
    """Reproducible offline assessment, including every source and unresolved target window."""
    try:
        validate_snapshot(bundle)
    except ValidationError as error:
        raise ValueError("Invalid annotation contract in observability snapshot") from error
    data = bundle["data"]
    if sum(len(s["tasks"]) + 1 for s in data["sources"]) > 10000:
        raise ValueError("Observability task capacity exceeded")
    sessions = [s for study in data["inputs"] for s in study["sessions"]]
    inventory = {(s["player_id"], s["session_id"], s["split"]): s for s in sessions}
    source_sessions = set()
    seen = set()
    for source in data["sources"]:
        key = (source["player_id"], source["session_id"], source["split"])
        session = inventory.get(key)
        phases = (
            {"BASELINE", "FOLLOWUP"}
            if source["annotations"]["source_kind"] == "ranked"
            else {"PRACTICE"}
        )
        if session is None or session["state"] != "CAPTURED" or session["phase"] not in phases:
            raise ValueError("Observability source must match the recorded session inventory")
        source_sessions.add(key)
        qc = source["qc"]
        if qc["kind"] != "QC" or any(
            type(qc["label"].get(k)) is not bool for k in ("profile_valid", "target_absent")
        ):
            raise ValueError("Explicit capture QC required for observability")
        for review in qc["reviews"]:
            visibility(review["label"])
        visibility(qc["label"])
        for task in source["tasks"]:
            if task["id"] in seen or task["kind"] not in {"TARGET", "TRIAL"}:
                raise ValueError("Duplicate or invalid observability task")
            seen.add(task["id"])
            if (task["kind"] == "TARGET") != (source["annotations"]["source_kind"] == "ranked"):
                raise ValueError("Target and practice evidence must remain separate")
            window(task)
    totals = summarize(data["sources"])
    missing_sessions = sum(
        s["state"] == "CAPTURED" and key not in source_sessions for key, s in inventory.items()
    )
    blockers = [
        "SOURCE_BYTES_NOT_VERIFIED",
        "CURRENT_PERMISSIONS_NOT_VERIFIED",
        "EXPERT_QUALIFICATION_NOT_VERIFIED",
        "PROSPECTIVE_PROTOCOL_NOT_APPROVED",
    ]
    if data["dataset_kind"] != "real":
        blockers.append("SYNTHETIC_DATA")
    for field, minimum in (("captures", 20), ("players", 2), ("sessions", 2)):
        if totals[field] < minimum:
            blockers.append(f"INSUFFICIENT_{field.upper()}")
    if not totals["critical_windows"]:
        blockers.append("NO_CRITICAL_WINDOWS")
    if totals["missing_categories"]:
        blockers.append("MISSING_REPRESENTATIVE_CATEGORIES")
    if totals["timing_unaudited_windows"]:
        blockers.append("INCOMPLETE_TIMING_AUDIT")
    if totals["sources_without_target_review_or_absence"]:
        blockers.append("INCOMPLETE_TARGET_INVENTORY")
    if missing_sessions:
        blockers.append("CAPTURED_SESSIONS_WITHOUT_SOURCES")
    if totals["qc_visibility"]["UNCERTAIN"] or totals["qc_visibility"]["UNOBSERVABLE"]:
        blockers.append("UNRESOLVED_CAPTURE_QC")
    if totals["captures"] < 20 or not totals["critical_windows"]:
        threshold = "INSUFFICIENT_EVIDENCE"
    elif totals["resolvable_windows"] * 10 >= totals["critical_windows"] * 9:
        threshold = "MEETS_PROPOSED_THRESHOLD"
    elif totals["unresolved_windows"] * 5 > totals["critical_windows"]:
        threshold = "NARROW_REQUIRED"
    else:
        threshold = "REVIEW_REQUIRED"
    result = {
        "schema_version": "observability-assessment/1",
        "policy": dict(POLICY),
        "snapshot_hash": bundle["content_hash"],
        "dataset_kind": data["dataset_kind"],
        "measurement": data["measurement"],
        "session_inventory": data["qa"]["session_inventory"],
        "captured_sessions_without_sources": missing_sessions,
        "totals": totals,
        "splits": {
            split: summarize([s for s in data["sources"] if s["split"] == split])
            for split in SPLITS
        },
        "proposed_threshold_result": threshold,
        "blockers": blockers,
        "scientific_gate": "NOT_RUN",
        "release_approval": False,
        "source_bytes_verified": False,
        "current_permissions_verified": False,
        "interpretation": "Proposed G1 thresholds describe reviewed ranked target windows. Practice and target-absent controls cannot inflate the window denominator. Timing completeness and reviewer agreement do not prove frame accuracy, expert qualification or automatic recognition. No source/reviewer identities or labels are included.",
    }
    return {"content_hash": digest(result), "data": result}
