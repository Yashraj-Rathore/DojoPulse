"""One-to-one held-out matching with separate success/failure and eligibility slices."""

from typing import Any

import numpy as np
from scipy.stats import beta


def score_predictions(
    truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    tolerance_us: int = 16667,
) -> dict[str, Any]:
    if tolerance_us < 0:
        raise ValueError("Negative timestamp tolerance")
    for values in (truth, predictions):
        ids = [(v["source_id"], v["id"]) for v in values]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate event IDs")
    available = set(range(len(truth)))
    matches: list[tuple[dict[str, Any] | None, dict[str, Any] | None]] = []
    errors = []
    for prediction in sorted(predictions, key=lambda v: v["start_us"]):
        candidates = [
            index
            for index in available
            if truth[index]["source_id"] == prediction["source_id"]
            and abs(truth[index]["start_us"] - prediction["start_us"]) <= tolerance_us
        ]
        if candidates:
            index = min(
                candidates, key=lambda i: abs(truth[i]["start_us"] - prediction["start_us"])
            )
            available.remove(index)
            matches.append((truth[index], prediction))
            errors.append(abs(truth[index]["start_us"] - prediction["start_us"]))
        else:
            matches.append((None, prediction))
    matches.extend((truth[i], None) for i in sorted(available))

    def label(event: dict[str, Any] | None, target: str) -> bool:
        if not event:
            return False
        if target == "eligible":
            return event["eligibility"] == "ELIGIBLE"
        return event["eligibility"] == "ELIGIBLE" and event["outcome"] == target

    slices: dict[str, Any] = {}
    for target in ("eligible", "SUCCESS", "FAILURE"):
        tp = sum(label(t, target) and label(p, target) for t, p in matches)
        fp = sum(not label(t, target) and label(p, target) for t, p in matches)
        fn = sum(label(t, target) and not label(p, target) for t, p in matches)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        slices[target] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "one_sided_precision_lower_95": float(beta.ppf(0.05, tp, fp + 1)) if tp else 0.0,
        }
    unknown = sum(p["eligibility"] == "UNKNOWN" or p["outcome"] == "UNKNOWN" for p in predictions)
    observable = sum(t["eligibility"] == "ELIGIBLE" and t["outcome"] != "UNKNOWN" for t in truth)
    accepted_on_truth = sum(
        t is not None
        and t["eligibility"] == "ELIGIBLE"
        and t["outcome"] != "UNKNOWN"
        and p is not None
        and p["eligibility"] == "ELIGIBLE"
        and p["outcome"] != "UNKNOWN"
        for t, p in matches
    )
    return {
        "slices": slices,
        "abstention_rate": unknown / len(predictions) if predictions else None,
        "observable_outcome_coverage": accepted_on_truth / observable if observable else None,
        "timestamp_error_us": {
            "median": float(np.median(errors)) if errors else None,
            "p95": float(np.quantile(errors, 0.95)) if errors else None,
        },
        "truth_count": len(truth),
        "prediction_count": len(predictions),
    }
