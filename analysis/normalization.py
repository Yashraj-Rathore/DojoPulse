"""Trusted-local recording normalization. Not a hosted upload/media admission path."""

import hashlib
import json
import math
import shutil
import stat
import tempfile
import time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

from analysis.contracts import digest
from analysis.media import ROOT, file_hash
from analysis.process import run_bounded
from analysis.timing import timing_quality


def policy() -> dict[str, Any]:
    return json.loads((ROOT / "contracts/recording-normalization-v1.json").read_text("utf-8"))


def unlinked(path: Path) -> Path:
    """Reject links/reparse points in the selected path, including existing ancestors."""
    absolute = path.absolute()
    for candidate in (absolute, *absolute.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError("LINKED_PATH_UNSUPPORTED")
    return absolute.resolve()


def timestamp(value: str) -> int:
    try:
        number = Decimal(value) * 1_000_000
        if not number.is_finite():
            raise ValueError("INVALID_TIMESTAMP")
        return int(number.to_integral_value(rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc


def probe_json(path: Path, args: list[str], limits: dict[str, Any]) -> dict[str, Any]:
    binary = shutil.which("ffprobe")
    if not binary:
        raise ValueError("FFPROBE_NOT_INSTALLED")
    result = run_bounded(
        [
            binary,
            "-v",
            "error",
            "-protocol_whitelist",
            "file",
            "-threads",
            "2",
            "-err_detect",
            "explode",
            *args,
            "-of",
            "json",
            str(path),
        ],
        timeout=limits["probe_timeout_seconds"],
        max_output=16_000_000,
        max_rss=limits["max_process_rss_bytes"],
        reject_stderr=True,
    )
    return json.loads(result.stdout)


def inspect(path: Path, limits: dict[str, Any]) -> dict[str, Any]:
    data = probe_json(path, ["-show_streams", "-show_format"], limits)
    streams = data["streams"]
    videos = [s for s in streams if s["codec_type"] == "video"]
    audios = [s for s in streams if s["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) > 1 or len(streams) != len(videos) + len(audios):
        raise ValueError("UNSUPPORTED_STREAMS")
    video = videos[0]
    if video.get("codec_name") not in limits["input_codecs"]:
        raise ValueError("UNSUPPORTED_CODEC")
    if (video.get("width"), video.get("height")) != (limits["width"], limits["height"]):
        raise ValueError("UNSUPPORTED_RESOLUTION")
    if video.get("pix_fmt") not in {"yuv420p", "yuvj420p"}:
        raise ValueError("UNSUPPORTED_PIXEL_FORMAT")
    if video.get("color_transfer") in {"smpte2084", "arib-std-b67"}:
        raise ValueError("HDR_UNSUPPORTED")
    if video.get("color_range", "unknown") not in {"pc", "tv", "unknown"}:
        raise ValueError("UNSUPPORTED_COLOR_RANGE")
    if video.get("color_space", "unknown") not in {"bt709", "unknown"}:
        raise ValueError("UNSUPPORTED_COLOR_SPACE")
    if any(
        video.get(key, "unknown") not in {"bt709", "unknown"}
        for key in ("color_transfer", "color_primaries")
    ):
        raise ValueError("UNSUPPORTED_COLOR_DECLARATIONS")
    if video.get("field_order", "unknown") not in {"progressive", "unknown"}:
        raise ValueError("INTERLACING_UNSUPPORTED")
    if video.get("tags", {}).get("rotate", "0") != "0" or any(
        side.get("rotation", 0) != 0 for side in video.get("side_data_list", [])
    ):
        raise ValueError("ROTATION_UNSUPPORTED")
    if Fraction(video.get("r_frame_rate", "0/1")) != limits["nominal_fps"]:
        raise ValueError("UNSUPPORTED_NOMINAL_RATE")
    duration = float(data["format"].get("duration", 0))
    if not math.isfinite(duration) or not 0 < duration <= limits["max_duration_seconds"]:
        raise ValueError("DURATION_LIMIT")
    if "mp4" not in data["format"]["format_name"].split(","):
        raise ValueError("MP4_REQUIRED")
    if audios and (
        audios[0].get("codec_name") != "aac"
        or not 1 <= int(audios[0].get("channels", 0)) <= 2
        or not 8000 <= int(audios[0].get("sample_rate", 0)) <= 48000
    ):
        raise ValueError("UNSUPPORTED_AUDIO")
    frames = probe_json(
        path,
        [
            "-select_streams",
            "v:0",
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time",
        ],
        limits,
    ).get("frames", [])
    times = [timestamp(frame["best_effort_timestamp_time"]) for frame in frames]
    quality = timing_quality(times, limits)
    packets = []
    if audios:
        packets = probe_json(
            path,
            [
                "-select_streams",
                "a:0",
                "-show_packets",
                "-show_data_hash",
                "sha256",
                "-show_entries",
                "packet=pts_time,dts_time,duration_time,data_hash",
            ],
            limits,
        ).get("packets", [])
        if not 1 <= len(packets) <= limits["max_audio_packets"]:
            raise ValueError("AUDIO_PACKET_LIMIT")
        packets = [
            {
                "pts_us": timestamp(p["pts_time"]),
                "dts_us": timestamp(p["dts_time"]),
                "duration_us": timestamp(p["duration_time"]),
                "data_hash": p["data_hash"],
            }
            for p in packets
        ]
        if any(
            not -100000 <= p["pts_us"] <= limits["max_duration_seconds"] * 1_000_000
            or not -100000 <= p["dts_us"] <= limits["max_duration_seconds"] * 1_000_000
            or not 0 < p["duration_us"] <= 1_000_000
            for p in packets
        ):
            raise ValueError("AUDIO_TIMELINE_LIMIT")
    return {
        "video": video,
        "audio": audios[0] if audios else None,
        "duration_seconds": duration,
        "times_us": times,
        "audio_packets": packets,
        "quality": quality,
    }


def verify_preservation(
    original: dict[str, Any], derived: dict[str, Any], limits: dict[str, Any]
) -> dict[str, Any]:
    before, after = original["times_us"], derived["times_us"]
    if len(before) != len(after):
        raise ValueError("FRAME_COUNT_CHANGED")
    error = max(abs(a - b) for a, b in zip(before, after, strict=True))
    if error > limits["timestamp_preservation_tolerance_us"]:
        raise ValueError("FRAME_TIMESTAMPS_CHANGED")
    if (original["audio"] is None) != (derived["audio"] is None):
        raise ValueError("AUDIO_STREAM_CHANGED")
    audio_before, audio_after = original["audio_packets"], derived["audio_packets"]
    if len(audio_before) != len(audio_after):
        raise ValueError("AUDIO_PACKET_COUNT_CHANGED")
    audio_error = 0
    for a, b in zip(audio_before, audio_after, strict=True):
        if a["data_hash"] != b["data_hash"]:
            raise ValueError("AUDIO_DATA_CHANGED")
        audio_error = max(
            audio_error, *(abs(a[k] - b[k]) for k in ("pts_us", "dts_us", "duration_us"))
        )
    if audio_error > limits["audio_timestamp_tolerance_us"]:
        raise ValueError("AUDIO_TIMESTAMPS_CHANGED")
    if original["quality"]["unknown_intervals"] != derived["quality"]["unknown_intervals"]:
        # Conservative: even tiny rounding cannot hide/change a quality boundary.
        raise ValueError("QUALITY_INTERVALS_CHANGED")
    if derived["video"]["codec_name"] != limits["output_codec"]:
        raise ValueError("OUTPUT_CODEC_CHANGED")
    for key in ("color_range", "color_space", "color_transfer", "color_primaries"):
        if original["video"].get(key, "unknown") != derived["video"].get(key, "unknown"):
            raise ValueError("COLOR_DECLARATIONS_CHANGED")
    return {
        "frame_count_preserved": True,
        "maximum_video_pts_error_us": error,
        "audio_packet_count_preserved": True,
        "audio_payloads_preserved": True,
        "maximum_audio_timestamp_error_us": audio_error,
        "unknown_intervals_preserved": True,
    }


def normalize(source: Path, destination: Path, *, game_build: str | None = None) -> dict[str, Any]:
    """Create a private H.264 preview bundle, or clean all owned outputs on failure.

    Destination must be new. Only explicitly selected trusted local MP4s are supported;
    this function must not be called by the public upload/worker paths.
    """
    started = time.monotonic()
    limits = policy()
    original_path = unlinked(source)
    destination = unlinked(destination)
    if not original_path.is_file() or original_path.suffix.lower() != ".mp4":
        raise ValueError("LOCAL_MP4_REQUIRED")
    if original_path.stat().st_size > limits["max_bytes"]:
        raise ValueError("FILE_TOO_LARGE")
    if game_build is not None and (not game_build or len(game_build) > 80):
        raise ValueError("INVALID_BUILD_DECLARATION")
    binary = shutil.which("ffmpeg")
    if not binary:
        raise ValueError("FFMPEG_NOT_INSTALLED")
    destination.parent.mkdir(parents=True, exist_ok=True)
    unlinked(destination.parent)
    destination.mkdir(exist_ok=False)
    output = destination / "preview.mp4"
    owned = [output, destination / "timeline.json", destination / "report.json"]
    try:
        with tempfile.TemporaryDirectory(prefix=".source-", dir=destination) as temporary:
            snapshot = Path(temporary) / "source.mp4"
            before = original_path.stat()
            total = 0
            sha = hashlib.sha256()
            with original_path.open("rb") as stream, snapshot.open("xb") as copy:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    total += len(block)
                    if total > limits["max_bytes"]:
                        raise ValueError("FILE_TOO_LARGE")
                    copy.write(block)
                    sha.update(block)
            after = original_path.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino, before.st_dev) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ino,
                after.st_dev,
            ) or total != before.st_size:
                raise ValueError("SOURCE_CHANGED")
            original_hash = sha.hexdigest()
            original = inspect(snapshot, limits)
            video = original["video"]
            # Explicit range handling avoids implicitly converting full-range Steam footage.
            range_name = "pc" if video.get("color_range") == "pc" else "tv"
            color = []
            if video.get("color_range") in {"pc", "tv"}:
                color.extend(
                    [
                        "-bsf:v",
                        "h264_metadata=video_full_range_flag="
                        + ("1" if video["color_range"] == "pc" else "0"),
                    ]
                )
            for field in ("color_range", "color_space", "color_transfer", "color_primaries"):
                value = video.get(field)
                if value and value != "unknown":
                    option = {"color_space": "colorspace", "color_transfer": "color_trc"}.get(
                        field, field
                    )
                    color.extend(["-" + option, value])
            argv = [
                binary,
                "-nostdin",
                "-v",
                "error",
                "-n",
                "-protocol_whitelist",
                "file",
                "-threads",
                str(limits["threads"]),
                "-err_detect",
                "explode",
                "-copyts",
                "-i",
                str(snapshot),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-map_metadata",
                "-1",
                "-map_chapters",
                "-1",
                "-c:v",
                limits["encoder"],
                "-threads",
                str(limits["threads"]),
                "-preset",
                limits["preset"],
                "-crf",
                str(limits["crf"]),
                "-vf",
                f"scale=in_range={range_name}:out_range={range_name},format=yuv420p",
                "-fps_mode",
                "passthrough",
                "-enc_time_base",
                "1:" + str(limits["video_track_timescale"]),
                "-video_track_timescale",
                str(limits["video_track_timescale"]),
                "-c:a",
                "copy",
                "-avoid_negative_ts",
                "disabled",
                *color,
                "-movflags",
                "+faststart",
                str(output),
            ]
            conversion = run_bounded(
                argv,
                timeout=limits["conversion_timeout_seconds"],
                max_rss=limits["max_process_rss_bytes"],
                file_limits={output: limits["max_bytes"]},
                reject_stderr=True,
            )
            derived = inspect(output, limits)
            preserved = verify_preservation(original, derived, limits)
            if unlinked(source) != original_path or file_hash(original_path) != original_hash:
                raise ValueError("SOURCE_CHANGED")
            timeline = {
                "schema_version": "recording-timeline/1",
                "source_sha256": original_hash,
                "source_pts_us": original["times_us"],
                "derived_pts_us": derived["times_us"],
                "mapping": "SAME_FRAME_INDEX_SAME_RECORDED_TIME",
            }
            version = (
                run_bounded([binary, "-version"], max_output=65536)
                .stdout.decode("utf-8", errors="replace")
                .splitlines()[0]
            )
            blockers = []
            if not original["quality"]["timing_matches_declared_profile"]:
                blockers.append("RECORDED_TIMING_OUTSIDE_DECLARED_PROFILE")
            if Fraction(derived["video"]["avg_frame_rate"]) != limits["nominal_fps"]:
                blockers.append("AVERAGE_RATE_OUTSIDE_DECLARED_PROFILE")
            report = {
                "schema_version": "recording-normalization-report/1",
                "analysis_version": "local-recording-normalizer/1",
                "status": "PREVIEW_READY",
                "scope": limits["scope"],
                "policy_id": limits["id"],
                "policy_sha256": digest(limits),
                "source": {
                    "sha256": original_hash,
                    "bytes": total,
                    "codec": video["codec_name"],
                    "duration_seconds": original["duration_seconds"],
                    "color": {
                        key: video.get(key, "unknown")
                        for key in (
                            "color_range",
                            "color_space",
                            "color_transfer",
                            "color_primaries",
                        )
                    },
                },
                "derivative": {
                    "file": output.name,
                    "sha256": file_hash(output),
                    "bytes": output.stat().st_size,
                    "codec": "h264",
                    "duration_seconds": derived["duration_seconds"],
                    "color": {
                        key: derived["video"].get(key, "unknown")
                        for key in (
                            "color_range",
                            "color_space",
                            "color_transfer",
                            "color_primaries",
                        )
                    },
                },
                "timeline": {"file": "timeline.json", "content_hash": digest(timeline)},
                "provenance": {
                    "access_class": "USER_UPLOAD",
                    "automatic_acquisition": False,
                    "game_build": game_build,
                    "build_evidence": "OPERATOR_DECLARED" if game_build else "UNKNOWN",
                    "build_verified": False,
                    "source_preserved": True,
                },
                "transform": {
                    "ffmpeg_version": version,
                    "encoder": limits["encoder"],
                    "preset": limits["preset"],
                    "crf": limits["crf"],
                    "frame_policy": limits["frame_policy"],
                    "audio_policy": limits["audio_policy"],
                    "lossy_video": True,
                },
                "preservation": preserved,
                "quality": original["quality"],
                "strict_capture_profile_media_compatible": not blockers,
                "profile_blockers": blockers,
                "canonical_publication": False,
                "precise_gameplay_analysis_approved": False,
                "scientific_gate_approval": False,
                "cost": {
                    "conversion_seconds": conversion.seconds,
                    "conversion_cpu_seconds": conversion.cpu_seconds,
                    "conversion_peak_rss_bytes": conversion.peak_rss_bytes,
                    "total_seconds": time.monotonic() - started,
                },
            }
            for path, value in ((owned[1], timeline), (owned[2], report)):
                with path.open("x", encoding="utf-8") as stream:
                    stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
            return report
    except BaseException:
        for path in owned:
            path.unlink(missing_ok=True)
        destination.rmdir()
        raise
