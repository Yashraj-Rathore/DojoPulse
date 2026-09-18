"""Create an intentionally incomplete review sidecar for a private capture."""
import argparse
import json
from pathlib import Path

from analysis.media import file_hash


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--played-at", required=True)
    parser.add_argument("--mode", choices=["ranked", "practice", "takeover"], required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite existing annotations")
    value = {"schema_version": "annotation/1", "source_id": args.source.stem,
             "source_sha256": file_hash(args.source), "dataset_kind": "real",
             "game_build": args.build, "session_id": args.session, "source_kind": args.mode,
             "played_at": args.played_at, "examples": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2), encoding="utf-8")
    print("Blank sidecar created. Empty examples are not completed annotation or negative evidence.")


if __name__ == "__main__":
    main()
