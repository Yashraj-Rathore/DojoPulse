"""Repeat local analysis and report measured cost inputs, never a fabricated cloud bill."""

import argparse
import json
import statistics
from pathlib import Path

from tools.analyze_capture import analyze


def aggregate_costs(
    reports: list[dict],
    *,
    hourly_review_usd: float | None = None,
    cloud_usd: float | None = None,
    loops: int = 0,
    comparable: int = 0,
) -> dict:
    if min(hourly_review_usd or 0, cloud_usd or 0, loops, comparable) < 0:
        raise ValueError("Negative cost/count")
    costs = [r["cost"] for r in reports]
    completed = sum(not c["failed"] for c in costs)
    review_seconds = sum(c.get("human_review_seconds", 0) for c in costs)
    total = (
        cloud_usd + review_seconds / 3600 * hourly_review_usd
        if cloud_usd is not None and hourly_review_usd is not None
        else None
    )
    hashes = [r["source"]["source_sha256"] for r in reports if "source" in r]
    return {
        "captures": len(reports),
        "completed": completed,
        "failures": len(reports) - completed,
        "review_seconds": review_seconds,
        "unique_sources": len(set(hashes)),
        "reprocessed_sources": len(hashes) - len(set(hashes)),
        "decoder_cpu_seconds": sum(c.get("decoder_cpu_seconds", 0) for c in costs),
        "decoder_peak_rss_bytes": max(
            (c.get("decoder_peak_rss_bytes", 0) for c in costs), default=0
        ),
        "source_bytes_processed": sum(c.get("source_bytes", 0) for c in costs),
        "derived_bytes_stored": sum(c.get("derived_bytes", 0) for c in costs),
        "review_rate_usd_per_hour": hourly_review_usd,
        "metered_cloud_usd": cloud_usd,
        "total_recurring_usd": total,
        "cost_per_capture": total / len(reports) if reports and total is not None else None,
        "cost_per_completed_analysis": total / completed
        if completed and total is not None
        else None,
        "cost_per_complete_loop": total / loops if loops and total is not None else None,
        "cost_per_comparable_evaluation": total / comparable
        if comparable and total is not None
        else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/benchmark.json"))
    args = parser.parse_args()
    reports = [
        analyze(p, args.output.parent / f"capture-{i}.json") for i, p in enumerate(args.captures)
    ]
    result = aggregate_costs(reports)
    times = [r["cost"]["processing_seconds"] for r in reports]
    result["median_seconds"] = statistics.median(times)
    result["cloud_cost_measured"] = False
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
