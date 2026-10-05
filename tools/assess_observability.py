"""Assess G1 observability from a private M08 snapshot, without fetching or decoding media."""

import argparse
import json
from pathlib import Path

from jsonschema import ValidationError

from analysis.observability import assess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.snapshot.stat().st_size > 16_777_216:
            raise ValueError("Snapshot exceeds 16 MiB offline input limit")
        bundle = json.loads(args.snapshot.read_text(encoding="utf-8"))
        report = assess(bundle)
        if args.snapshot.resolve() == args.output.resolve():
            raise ValueError("Output cannot overwrite the source snapshot")
    except (OSError, ValueError, KeyError, TypeError, ValidationError) as error:
        parser.exit(2, f"Observability assessment failed: {error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "content_hash": report["content_hash"],
                "scientific_gate": "NOT_RUN",
                "release_approval": False,
            }
        )
    )


if __name__ == "__main__":
    main()
