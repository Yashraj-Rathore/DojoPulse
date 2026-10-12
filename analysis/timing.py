"""Provider-independent recorded-frame coverage; never approval of gameplay facts."""

from fractions import Fraction
from typing import Any


def timing_quality(times: list[int], policy: dict[str, Any]) -> dict[str, Any]:
    if not 2 <= len(times) <= policy["max_frames"]:
        raise ValueError("FRAME_COUNT_LIMIT")
    if times[0] < 0 or times[-1] > policy["max_duration_seconds"] * 1_000_000:
        raise ValueError("TIMELINE_LIMIT")
    gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
    if min(gaps) <= 0:
        raise ValueError("NON_INCREASING_TIMESTAMPS")
    nominal = Fraction(1_000_000, policy["nominal_fps"])
    unknown = [
        {
            "after_frame_index": index,
            "start_us": times[index],
            "end_us": times[index + 1],
            "gap_us": gap,
            "reason": "FRAME_GAP" if gap > policy["max_frame_gap_us"] else "IRREGULAR_PERIOD",
        }
        for index, gap in enumerate(gaps)
        if gap > policy["max_frame_gap_us"]
        or abs(gap - nominal) > policy["frame_period_tolerance_us"]
    ]
    return {
        "frame_count": len(times),
        "first_pts_us": times[0],
        "last_pts_us": times[-1],
        "max_frame_gap_us": max(gaps),
        "gaps_over_limit": sum(g > policy["max_frame_gap_us"] for g in gaps),
        "timing_matches_declared_profile": not unknown,
        "unknown_intervals": unknown,
        "cuts_pauses_rewinds_takeover_verified": False,
        "precise_gameplay_analysis_approved": False,
    }


def timing_window_supported(quality: dict[str, Any], start_us: int, end_us: int) -> bool:
    """Check only recorded-frame continuity. A True result is not semantic eligibility."""
    if not quality["first_pts_us"] <= start_us < end_us <= quality["last_pts_us"]:
        return False
    return not any(
        start_us < gap["end_us"] and end_us > gap["start_us"]
        for gap in quality["unknown_intervals"]
    )
