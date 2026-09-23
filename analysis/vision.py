"""Template observations only: similarity is not calibrated probability."""

from pathlib import Path
from typing import Any

import cv2


def template_candidates(
    frame: Path,
    template: Path,
    region: tuple[int, int, int, int],
    threshold: float,
) -> dict[str, Any] | None:
    if not 0 < threshold <= 1:
        raise ValueError("Invalid template threshold")
    source = cv2.imread(str(frame), cv2.IMREAD_GRAYSCALE)
    target = cv2.imread(str(template), cv2.IMREAD_GRAYSCALE)
    if source is None or target is None or target.std() < 1:
        raise ValueError("Invalid or uninformative template")
    x, y, width, height = region
    if min(x, y) < 0 or min(width, height) <= 0:
        raise ValueError("Invalid crop")
    if x + width > source.shape[1] or y + height > source.shape[0]:
        raise ValueError("Crop exceeds frame")
    crop = source[y : y + height, x : x + width]
    if target.shape[0] > height or target.shape[1] > width:
        raise ValueError("Template exceeds crop")
    scores = cv2.matchTemplate(crop, target, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(scores)
    if score < threshold:
        return None
    return {
        "similarity": score,
        "confidence": None,
        "status": "CANDIDATE",
        "x": x + location[0],
        "y": y + location[1],
    }


def reconcile(observations: list[dict[str, Any]], max_gap_us: int) -> list[dict[str, Any]]:
    """Collapse repeated text observations; absence/gaps never establish a failure."""
    if max_gap_us < 0:
        raise ValueError("Negative gap")
    results: list[dict[str, Any]] = []
    active: dict[str, dict[str, Any]] = {}
    for observation in sorted(observations, key=lambda v: v["timestamp_us"]):
        label = observation["label"]
        moment = observation["timestamp_us"]
        last = active.get(label)
        if last and moment - last["end_us"] <= max_gap_us:
            last["end_us"] = moment
            last["sample_count"] += 1
        else:
            current = {
                "label": label,
                "start_us": moment,
                "end_us": moment,
                "sample_count": 1,
                "status": "CANDIDATE",
                "confidence": None,
            }
            active[label] = current
            results.append(current)
    return results
