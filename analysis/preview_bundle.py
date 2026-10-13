"""Bounded, shaped preview artifacts. Recorded coverage never grants gameplay approval."""

import json
import math
import stat
from pathlib import Path
from typing import Any

from analysis.contracts import digest
from analysis.media import file_hash
from analysis.normalization import policy
from analysis.timing import timing_quality

PIPELINE = "recording-preview/1"
FILES = {"preview.mp4": 536870912, "report.json": 8388608, "timeline.json": 2097152}
MAX_BYTES = sum(FILES.values())


def read_json(path: Path, maximum: int) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("INVALID_PREVIEW_BUNDLE")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("INVALID_PREVIEW_BUNDLE")
            result[key] = value
        return result

    def invalid(value: str) -> None:
        raise ValueError("INVALID_PREVIEW_BUNDLE")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("INVALID_PREVIEW_BUNDLE") from exc
    if not isinstance(value, dict):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    return value


def validate_bundle(directory: Path, source_sha256: str) -> dict[str, Any]:
    if {p.name for p in directory.iterdir()} != set(FILES):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    for name, maximum in FILES.items():
        info = (directory / name).lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 < info.st_size <= maximum:
            raise ValueError("INVALID_PREVIEW_BUNDLE")
    report = read_json(directory / "report.json", FILES["report.json"])
    timeline = read_json(directory / "timeline.json", FILES["timeline.json"])
    if any(
        not isinstance(report.get(key), dict)
        for key in ("source", "timeline", "quality", "preservation", "derivative")
    ):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    limits = policy()
    if (
        report.get("status") != "PREVIEW_READY"
        or report.get("policy_id") != limits["id"]
        or report.get("policy_sha256") != digest(limits)
        or report.get("source", {}).get("sha256") != source_sha256
        or timeline.get("source_sha256") != source_sha256
        or report.get("timeline", {}).get("content_hash") != digest(timeline)
        or report.get("canonical_publication") is not False
        or report.get("precise_gameplay_analysis_approved") is not False
        or report.get("scientific_gate_approval") is not False
    ):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    before, after = timeline.get("source_pts_us"), timeline.get("derived_pts_us")
    if (
        not isinstance(before, list)
        or not isinstance(after, list)
        or len(before) != len(after)
        or any(type(t) is not int for t in [*before, *after])
        or not 2 <= len(before) <= limits["max_frames"]
        or any(
            abs(a - b) > limits["timestamp_preservation_tolerance_us"]
            for a, b in zip(before, after, strict=True)
        )
    ):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    quality = timing_quality(before, limits)
    if quality != report.get("quality") or timing_quality(after, limits) != quality:
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    preservation = report.get("preservation", {})
    if any(
        preservation.get(key) is not True
        for key in (
            "frame_count_preserved",
            "audio_packet_count_preserved",
            "audio_payloads_preserved",
            "unknown_intervals_preserved",
        )
    ) or any(
        type(preservation.get(key)) is not int or not 0 <= preservation[key] <= maximum
        for key, maximum in (
            ("maximum_video_pts_error_us", 2),
            ("maximum_audio_timestamp_error_us", 22),
        )
    ):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    derived = report.get("derivative", {})
    if (
        derived.get("codec") != "h264"
        or derived.get("bytes") != (directory / "preview.mp4").stat().st_size
        or derived.get("sha256") != file_hash(directory / "preview.mp4")
    ):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    duration = derived.get("duration_seconds")
    if type(duration) not in {int, float} or not math.isfinite(duration) or not 0 < duration <= 600:
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    return {
        "duration_seconds": duration,
        "frame_count": quality["frame_count"],
        "gaps_over_limit": quality["gaps_over_limit"],
        "irregular_intervals": len(quality["unknown_intervals"]),
        "max_frame_gap_us": quality["max_frame_gap_us"],
        "first_pts_us": quality["first_pts_us"],
        "last_pts_us": quality["last_pts_us"],
        "timing_matches_declared_profile": quality["timing_matches_declared_profile"],
        "precise_gameplay_analysis_approved": False,
        "canonical_publication": False,
        "scientific_gate_approval": False,
        "cuts_pauses_rewinds_takeover_verified": False,
    }
