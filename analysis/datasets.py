"""Portable dataset receipts. Labels and synthetic metrics never approve a detector."""

from collections import Counter
from statistics import median
from typing import Any

from analysis.annotations import validate_annotations
from analysis.contracts import digest
from analysis.perception_metrics import score_predictions

SPLITS = ("development", "validation", "held-out")
CATEGORIES = ("SUCCESS", "FAILURE", "NEAR_MISS", "UNCERTAIN", "TARGET_ABSENT")


def quality(
    sources: list[dict[str, Any]], inputs: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    slices: dict[str, Any] = {}
    for split in SPLITS:
        selected = [s for s in sources if s["split"] == split]
        counts: Counter[str] = Counter()
        uncertainties, gaps, frames, truth, predictions = [], [], [], [], []
        disagreements = review_seconds = audited = tasks = 0
        versions: set[str] = set()
        for source in selected:
            if source["qc"]["label"]["target_absent"]:
                counts["TARGET_ABSENT"] += 1
            for review in source["qc"]["reviews"]:
                review_seconds += review["seconds"]
            disagreements += source["qc"]["state"] == "ADJUDICATED"
            for task in source["tasks"]:
                tasks += 1
                label = task["label"]
                category = (
                    label["outcome"]
                    if label["outcome"] in {"SUCCESS", "FAILURE"}
                    else "NEAR_MISS"
                    if label["eligibility"] == "INELIGIBLE"
                    else "UNCERTAIN"
                )
                counts[category] += 1
                uncertainties.append(label["conditions"]["uncertainty_us"])
                disagreements += task["state"] == "ADJUDICATED"
                for review in task["reviews"]:
                    review_seconds += review["seconds"]
                pair = task["reviews"][:2]
                timing = [r["label"].get("timing", {}) for r in pair]
                if all(t.get("start_us") is not None for t in timing):
                    audited += 1
                    gaps.append(abs(timing[0]["start_us"] - timing[1]["start_us"]))
                    if all(t.get("frame_duration_us") is not None for t in timing):
                        frames.append(gaps[-1] / max(t["frame_duration_us"] for t in timing))
                base = {"id": task["id"], "source_id": source["source_id"]}
                # Timing metrics require an explicit independently reviewed reference.
                final_time = label.get("timing", {}).get("start_us")
                if final_time is not None and task["kind"] == "TARGET":
                    truth.append(
                        {
                            **base,
                            "start_us": final_time,
                            "eligibility": label["eligibility"],
                            "outcome": label["outcome"],
                        }
                    )
                    if task["prediction"]:
                        prediction = task["prediction"]
                        versions.add(prediction["detector_version"])
                        predictions.append(
                            {
                                **base,
                                **{
                                    k: prediction[k] for k in ("start_us", "eligibility", "outcome")
                                },
                            }
                        )
        slices[split] = {
            "sources": len(selected),
            "players": len({s["player_id"] for s in selected}),
            "sessions": len({s["session_id"] for s in selected}),
            "tasks": tasks,
            "categories": {key: counts[key] for key in CATEGORIES},
            "missing_categories": [key for key in CATEGORIES if not counts[key]],
            "adjudicated": disagreements,
            "structured_agreement_rate": (tasks + len(selected) - disagreements)
            / (tasks + len(selected))
            if tasks + len(selected)
            else None,
            "review_seconds": review_seconds,
            "timing": {
                "independently_audited": audited,
                "unaudited": tasks - audited,
                "uncertainty_median_us": median(uncertainties) if uncertainties else None,
                "uncertainty_max_us": max(uncertainties) if uncertainties else None,
                "reviewer_start_gap_median_us": median(gaps) if gaps else None,
                "reviewer_start_gap_max_us": max(gaps) if gaps else None,
                "reviewer_gap_median_frames": median(frames) if frames else None,
            },
            "detector_versions": sorted(versions),
            "recognition": score_predictions(truth, predictions) if len(versions) == 1 else None,
        }
    sessions = [s for study in (inputs or []) for s in study["sessions"]]
    return {
        "session_inventory": {
            "recorded": len(sessions),
            "states": dict(sorted(Counter(s["state"] for s in sessions).items())),
            "unknown_playable_duration": sum(s["playable_seconds"] is None for s in sessions),
        },
        "splits": slices,
        "representative_coverage": all(not s["missing_categories"] for s in slices.values()),
        "scientific_gate": "NOT_RUN",
        "release_approval": False,
        "timing_interpretation": "Reviewer agreement and reference-relative prediction error; neither establishes real frame accuracy.",
    }


def validate_snapshot(bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate a portable service export without opening or claiming to verify media bytes."""
    if set(bundle) != {"content_hash", "data"} or digest(bundle["data"]) != bundle["content_hash"]:
        raise ValueError("Dataset content hash mismatch")
    data = bundle["data"]
    if set(data) != {
        "schema_version",
        "dataset_id",
        "dataset_kind",
        "measurement",
        "sampling",
        "inputs",
        "sources",
        "qa",
        "automatic_publication",
        "training_permission_included",
    }:
        raise ValueError("Unexpected dataset receipt fields")
    if data["schema_version"] != "dataset-snapshot/1" or data["dataset_kind"] not in {
        "synthetic",
        "real",
    }:
        raise ValueError("Unsupported dataset receipt")
    if (
        data["automatic_publication"] is not False
        or data["training_permission_included"] is not False
    ):
        raise ValueError("Dataset export cannot grant publication or model training")
    sources = data["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 4000:
        raise ValueError("Bounded nonempty sources required")
    measurement = data["measurement"]
    seen: dict[str, dict[str, str]] = {
        k: {} for k in ("source_id", "source_sha256", "player_id", "session_id")
    }
    for source in sources:
        split = source["split"]
        if split not in SPLITS:
            raise ValueError("Invalid dataset split")
        for key, group in seen.items():
            token = source[key]
            if token in group and (key in {"source_id", "source_sha256"} or group[token] != split):
                raise ValueError(f"Dataset duplicate or leaked {key}")
            group[token] = split
        batch = source["annotations"]
        if (
            batch["source_sha256"],
            batch["source_id"],
            batch["game_build"],
            batch["dataset_kind"],
        ) != (
            source["source_sha256"],
            source["source_id"],
            measurement["game_build"],
            data["dataset_kind"],
        ):
            raise ValueError("Dataset source/annotation measurement mismatch")
        if source["platform"] != measurement["platform"]:
            raise ValueError("Dataset platform mismatch")
        validate_annotations(batch, source["source_sha256"], situation=measurement["situation"])
        if source["qc"]["label"]["profile_valid"] is not True:
            raise ValueError("Invalid capture profile cannot be sealed")
        if source["qc"]["label"]["target_absent"] and any(
            t["label"]["eligibility"] == "ELIGIBLE" for t in source["tasks"]
        ):
            raise ValueError("Target-absent control contradicts reviewed opportunity")
        if {t["id"] for t in source["tasks"]} != {x["id"] for x in batch["examples"]}:
            raise ValueError("Annotation task membership mismatch")
        examples = {x["id"]: x for x in batch["examples"]}
        for task in [source["qc"], *source["tasks"]]:
            reviews = task["reviews"]
            if (
                len(reviews) not in {2, 3}
                or len({r["reviewer"] for r in reviews}) != len(reviews)
                or any(
                    type(r["seconds"]) is not int or not 1 <= r["seconds"] <= 28800 for r in reviews
                )
            ):
                raise ValueError("Independent bounded dataset reviews required")
            agreed = digest(reviews[0]["label"]) == digest(reviews[1]["label"])
            if (agreed and (task["state"] != "AGREED" or len(reviews) != 2)) or (
                not agreed and (task["state"] != "ADJUDICATED" or len(reviews) != 3)
            ):
                raise ValueError("Dataset disagreement needs independent adjudication")
            final = reviews[0 if agreed else 2]["label"]
            if final != task["label"]:
                raise ValueError("Dataset final label differs from independent review")
            if task["kind"] == "QC":
                if task["start_us"] != 0 or task["end_us"] != int(
                    source["duration_seconds"] * 1000000
                ):
                    raise ValueError("Dataset QC must cover the complete source")
                continue
            example = examples[task["id"]]
            if any(
                example[k] != task["label"][k] for k in ("conditions", "eligibility", "outcome")
            ) or (example["start_us"], example["end_us"]) != (task["start_us"], task["end_us"]):
                raise ValueError("Dataset labels differ from canonical annotations")
            for review in reviews:
                timing = review["label"].get("timing", {})
                if set(timing) != {"start_us", "end_us", "frame_duration_us"}:
                    raise ValueError("Explicit dataset timing audit required")
                start, end, frame = (timing[k] for k in ("start_us", "end_us", "frame_duration_us"))
                if (start is None) != (end is None) or (
                    start is not None
                    and (
                        type(start) is not int
                        or type(end) is not int
                        or not task["start_us"] <= start <= end <= task["end_us"]
                    )
                ):
                    raise ValueError("Dataset timing outside reviewed window")
                if frame is not None and (
                    start is None or type(frame) is not int or not 1 <= frame <= 1000000
                ):
                    raise ValueError("Dataset frame audit invalid")
    input_seen: dict[str, dict[str, str]] = {"player_id": {}, "session_id": {}}
    for study in data["inputs"]:
        for session in study["sessions"]:
            for key, allocations in input_seen.items():
                if session[key] in allocations and allocations[session[key]] != session["split"]:
                    raise ValueError("Dataset input split leakage")
                allocations[session[key]] = session["split"]
    if quality(sources, data["inputs"]) != data["qa"]:
        raise ValueError("Dataset QA receipt mismatch")
    return {
        "status": "VALID",
        "source_count": len(sources),
        "dataset_kind": data["dataset_kind"],
        "source_bytes_verified": False,
        "current_permissions_verified": False,
        "release_approval": False,
    }
