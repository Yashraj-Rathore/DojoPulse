"""Reproduce candidate/held-out receipts offline. Does not decode video or load plugins."""

import argparse
import json
from pathlib import Path

from analysis.contracts import digest
from analysis.recognition import benchmark, candidates


def read(path: Path) -> dict:
    if path.stat().st_size > 2_000_000:
        raise ValueError("Portable recognition input exceeds 2 MB")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("observations", type=Path, nargs="?")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--receipt", type=Path, help="Reproduce an owned, current benchmark export")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt:
        if args.manifest or args.observations or args.snapshot:
            parser.error("Use either a reproduction receipt or manifest/observations inputs")
        receipt = read(args.receipt)
        if (
            receipt.get("schema_version") != "recognition-reproduction/1"
            or digest(receipt["observations"]) != receipt["input_hash"]
        ):
            raise ValueError("Invalid reproduction receipt input hash")
        result = benchmark(receipt["manifest"], receipt["snapshot"], receipt["observations"])
        if digest(result) != receipt["content_hash"] or result != receipt["report"]:
            raise ValueError("Reproduced report differs from the exported receipt")
    else:
        if not args.manifest or not args.observations:
            parser.error("Manifest and observations are required")
        config, observations = read(args.manifest), read(args.observations)
        result = (
            benchmark(config, read(args.snapshot), observations)
            if args.snapshot
            else candidates(config, observations)
        )
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
