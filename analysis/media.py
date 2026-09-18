"""Strict capture admission, timestamp audit and bounded FFmpeg sampling."""
import hashlib
import json
import math
import shutil
from fractions import Fraction
from pathlib import Path
from typing import Any

from analysis.process import run_bounded

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def profile() -> dict[str, Any]:
    return json.loads((ROOT / "contracts/capture-profile-v1.json").read_text(encoding="utf-8"))


def probe(path: Path, limits: dict[str, Any] | None = None) -> dict[str, Any]:
    limits = limits or profile()
    if not path.is_file() or path.suffix.lower() != ".mp4":
        raise ValueError("LOCAL_MP4_REQUIRED")
    if path.stat().st_size > limits["max_bytes"]:
        raise ValueError("FILE_TOO_LARGE")
    binary = shutil.which("ffprobe")
    if not binary:
        raise ValueError("FFPROBE_NOT_INSTALLED")
    result = run_bounded([
        binary, "-v", "error", "-protocol_whitelist", "file", "-show_format",
        "-show_streams", "-of", "json", str(path.resolve()),
    ])
    data = json.loads(result.stdout)
    videos = [s for s in data["streams"] if s["codec_type"] == "video"]
    if len(videos) != 1 or any(s["codec_type"] not in {"video", "audio"} for s in data["streams"]):
        raise ValueError("UNSUPPORTED_STREAMS")
    video = videos[0]
    if video.get("codec_name") != limits["video_codec"]:
        raise ValueError("UNSUPPORTED_CODEC")
    if (video["width"], video["height"]) != (limits["width"], limits["height"]):
        raise ValueError("UNSUPPORTED_RESOLUTION")
    if video.get("pix_fmt") not in {"yuv420p", "yuvj420p"}:
        raise ValueError("UNSUPPORTED_PIXEL_FORMAT")
    if video.get("color_transfer") in {"smpte2084", "arib-std-b67"}:
        raise ValueError("HDR_UNSUPPORTED")
    if any(int(s.get("rotation", 0)) != 0 for s in video.get("side_data_list", [])):
        raise ValueError("ROTATION_UNSUPPORTED")
    duration = float(data["format"].get("duration", 0))
    if not math.isfinite(duration) or not 0 < duration <= limits["max_duration_seconds"]:
        raise ValueError("DURATION_LIMIT")
    if Fraction(video.get("avg_frame_rate", "0/1")) != limits["fps"]:
        raise ValueError("UNSUPPORTED_FRAME_RATE")
    timing = run_bounded([
        binary, "-v", "error", "-protocol_whitelist", "file", "-select_streams", "v:0",
        "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(path.resolve()),
    ], timeout=90, max_output=8_000_000)
    frames = json.loads(timing.stdout).get("frames", [])
    if not 2 <= len(frames) <= limits["max_frames"]:
        raise ValueError("FRAME_COUNT_LIMIT")
    times = [round(float(f["best_effort_timestamp_time"]) * 1_000_000) for f in frames]
    gaps = [b - a for a, b in zip(times, times[1:])]
    nominal = 1_000_000 / limits["fps"]
    if min(gaps) <= 0 or max(gaps) > limits["max_frame_gap_us"]:
        raise ValueError("TIMESTAMP_DISCONTINUITY")
    if any(abs(g - nominal) > 1000 for g in gaps):
        raise ValueError("VARIABLE_FRAME_RATE")
    return {
        "duration_seconds": duration, "bytes": path.stat().st_size,
        "frame_count": len(times), "width": video["width"], "height": video["height"],
        "codec": video["codec_name"], "fps": limits["fps"], "first_pts_us": times[0],
        "max_frame_gap_us": max(gaps), "source_sha256": file_hash(path),
        "probe_seconds": result.seconds + timing.seconds,
        "probe_cpu_seconds": result.cpu_seconds + timing.cpu_seconds,
        "probe_peak_rss_bytes": max(result.peak_rss_bytes, timing.peak_rss_bytes),
    }


def extract_samples(path: Path, destination: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Coarse review frames. Not a native-rate timing detector or released move recognizer."""
    binary = shutil.which("ffmpeg")
    if not binary:
        raise ValueError("FFMPEG_NOT_INSTALLED")
    destination.mkdir(parents=True, exist_ok=False)
    stride = max(1, math.ceil(metadata["frame_count"] / profile()["max_samples"]))
    result = run_bounded([
        binary, "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-threads", "1",
        "-i", str(path.resolve()), "-an", "-vf", f"select=not(mod(n\\,{stride}))",
        "-fps_mode", "vfr", "-frames:v", str(profile()["max_samples"]),
        str(destination.resolve() / "sample-%04d.png"),
    ], timeout=180)
    paths = sorted(destination.glob("*.png"))
    return {
        "sampling": "coarse-review-only", "stride_frames": stride,
        "samples": [{"file": p.name, "timestamp_us": metadata["first_pts_us"]
                     + round(i * stride / metadata["fps"] * 1_000_000)}
                    for i, p in enumerate(paths)],
        "stored_bytes": sum(p.stat().st_size for p in paths),
        "seconds": result.seconds, "cpu_seconds": result.cpu_seconds,
        "peak_rss_bytes": result.peak_rss_bytes,
    }
