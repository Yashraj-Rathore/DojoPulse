"""Prepare/check private replay-acquisition evidence without accessing the game or network."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ingestion.acquisition import assess, new_plan, validate_plan


def reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON numbers are not permitted")


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--init", action="store_true", help="Create a new empty private plan")
    parser.add_argument(
        "--native-control",
        choices=["AVAILABLE", "UNAVAILABLE", "UNVERIFIED", "NOT_APPLICABLE"],
        default="UNVERIFIED",
    )
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.init and (args.evidence_dir is None or args.output is None):
        parser.error("Assessment requires --evidence-dir and --output")
    if args.init and (args.evidence_dir is not None or args.output is not None):
        parser.error("Initialization does not assess evidence or write a report")
    try:
        if args.init:
            plan = new_plan(native_control=args.native_control)
            validate_plan(plan)
            write_new(args.plan, plan)
            print(
                json.dumps(
                    {
                        "schema_version": plan["schema_version"],
                        "trial_count": 0,
                        "runtime_enabled": False,
                    }
                )
            )
            return
        if args.plan.stat().st_size > 1_048_576:
            raise ValueError("Plan exceeds one MiB input limit")
        plan = json.loads(args.plan.read_text(encoding="utf-8"), parse_constant=reject_constant)
        report = assess(plan, args.evidence_dir, now=datetime.now(UTC))
        write_new(args.output, report)
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        # Do not echo paths, personal evidence, schema values or identifiers from exceptions.
        parser.exit(
            2,
            "Replay qualification failed; check schema, confined evidence, checksums and output availability.\n",
        )
    print(
        json.dumps(
            {
                "content_hash": report["content_hash"],
                "first_replay_evidence_status": report["data"]["first_replay_evidence_status"],
                "runtime_enabled": False,
                "release_approval": False,
            }
        )
    )


if __name__ == "__main__":
    main()
