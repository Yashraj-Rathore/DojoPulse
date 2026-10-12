"""Create a verified H.264 preview from an explicitly selected trusted local recording."""

import argparse
import json
from pathlib import Path

from analysis.normalization import normalize

SAFE_ERRORS = {
    "DECODER_TIMEOUT",
    "DECODER_MEMORY_LIMIT",
    "DECODER_OUTPUT_LIMIT",
    "DECODER_FILE_LIMIT",
    "DECODER_REPORTED_ERRORS",
    "DECODER_REJECTED_INPUT",
    "SOURCE_CHANGED",
    "FRAME_COUNT_CHANGED",
    "FRAME_TIMESTAMPS_CHANGED",
    "AUDIO_STREAM_CHANGED",
    "AUDIO_PACKET_COUNT_CHANGED",
    "AUDIO_DATA_CHANGED",
    "AUDIO_TIMESTAMPS_CHANGED",
    "QUALITY_INTERVALS_CHANGED",
    "OUTPUT_CODEC_CHANGED",
    "COLOR_DECLARATIONS_CHANGED",
    "LINKED_PATH_UNSUPPORTED",
    "LOCAL_MP4_REQUIRED",
    "FILE_TOO_LARGE",
    "DURATION_LIMIT",
    "UNSUPPORTED_CODEC",
    "UNSUPPORTED_RESOLUTION",
    "UNSUPPORTED_PIXEL_FORMAT",
    "HDR_UNSUPPORTED",
    "UNSUPPORTED_STREAMS",
    "UNSUPPORTED_AUDIO",
    "UNSUPPORTED_COLOR_RANGE",
    "UNSUPPORTED_COLOR_SPACE",
    "UNSUPPORTED_COLOR_DECLARATIONS",
    "INTERLACING_UNSUPPORTED",
    "ROTATION_UNSUPPORTED",
    "UNSUPPORTED_NOMINAL_RATE",
    "AUDIO_PACKET_LIMIT",
    "AUDIO_TIMELINE_LIMIT",
    "FRAME_COUNT_LIMIT",
    "TIMELINE_LIMIT",
    "NON_INCREASING_TIMESTAMPS",
    "FFMPEG_NOT_INSTALLED",
    "FFPROBE_NOT_INSTALLED",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Trusted local owner-provided MP4")
    parser.add_argument("--output-dir", required=True, type=Path, help="New private directory")
    parser.add_argument("--game-build", help="Operator declaration, not verified game knowledge")
    args = parser.parse_args()
    try:
        report = normalize(args.source, args.output_dir, game_build=args.game_build)
    except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError) as exc:
        code = (
            str(exc)
            if isinstance(exc, ValueError) and str(exc) in SAFE_ERRORS
            else "INVALID_INPUT_OR_OUTPUT"
        )
        parser.exit(
            2,
            "Recording conversion failed ("
            + code
            + "); check media, limits and new output directory.\n",
        )
    # Never echo private source paths, hashes, build declarations or participant identifiers.
    print(
        json.dumps(
            {
                "status": report["status"],
                "frame_count": report["quality"]["frame_count"],
                "gaps_over_limit": report["quality"]["gaps_over_limit"],
                "strict_capture_profile_media_compatible": report[
                    "strict_capture_profile_media_compatible"
                ],
                "precise_gameplay_analysis_approved": False,
            }
        )
    )


if __name__ == "__main__":
    main()
