"""Validate independent review records; no automatic promotion of client labels."""
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from analysis.contracts import Eligibility, Outcome
from analysis.rules import judge

ROOT = Path(__file__).resolve().parents[1]


def validate_annotations(value: dict[str, Any], source_hash: str | None = None) -> None:
    schema = json.loads((ROOT / "datasets/annotation-schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    if source_hash is not None and value["source_sha256"] != source_hash:
        raise ValueError("Annotation source hash mismatch")
    ids = [x["id"] for x in value["examples"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate annotation IDs")
    for item in value["examples"]:
        if item["end_us"] < item["start_us"]:
            raise ValueError("Reversed evidence window")
        reviews = item["reviews"]
        reviewers = {r["reviewer"] for r in reviews}
        if len(reviewers) != len(reviews):
            raise ValueError("Independent reviewers required")
        judgments = {(r["eligibility"], r["outcome"]) for r in reviews}
        final = (item["eligibility"], item["outcome"])
        adjudication = item["adjudication"]
        if len(judgments) > 1 or final not in judgments:
            if not adjudication or adjudication["reviewer"] in reviewers:
                raise ValueError("Disagreement requires independent adjudication")
        derived = judge(item["conditions"], reviewed=True)
        if (Eligibility(item["eligibility"]), Outcome(item["outcome"])) != (
            derived.eligibility, derived.outcome
        ):
            raise ValueError("Final label contradicts mandatory evidence conditions")


def review_metrics(value: dict[str, Any]) -> dict[str, Any]:
    examples = value["examples"]
    disagreements = sum(len({(r["eligibility"], r["outcome"])
                             for r in x["reviews"]}) > 1 for x in examples)
    seconds = sum(sum(r["seconds"] for r in x["reviews"])
                  + (x["adjudication"]["seconds"] if x["adjudication"] else 0)
                  for x in examples)
    return {"review_seconds": seconds, "disagreement_count": disagreements,
            "disagreement_rate": disagreements / len(examples) if examples else None}
