"""Score explicit held-out ground truth; synthetic results never pass a gameplay gate."""

import argparse
import json
from pathlib import Path

from analysis.perception_metrics import score_predictions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("truth", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    if truth["split"] != "held-out" or truth["dataset_kind"] != predictions["dataset_kind"]:
        raise ValueError("Held-out truth and matching dataset kind required")
    report = score_predictions(truth["events"], predictions["events"])
    report["dataset_kind"] = truth["dataset_kind"]
    report["decision"] = "REVIEW_REQUIRED"
    if truth["dataset_kind"] == "synthetic":
        report["decision"] = "SOFTWARE_CHECK_ONLY"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
