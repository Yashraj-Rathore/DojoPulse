"""Local extraction: python -m tools.analyze_capture capture.mp4 --output report.json."""

import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

from jsonschema import ValidationError

from analysis.annotations import review_metrics, validate_annotations
from analysis.contracts import digest
from analysis.media import extract_samples, probe, profile
from analysis.recognition import CONDITIONS, candidates, manifest
from analysis.vision import reconcile, template_candidates


def analyze(
    source: Path,
    output: Path,
    metadata_path: Path | None = None,
    annotations_path: Path | None = None,
    templates_path: Path | None = None,
    detector_manifest_path: Path | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    report: dict[str, Any] = {
        "schema_version": "capture-report/1",
        "analysis_version": "local-pipeline/1",
        "capture_profile": profile()["id"],
        "game_build": None,
        "status": "VALIDATING",
        "opportunities": [],
        "observations": [],
        "issues": [],
        "automatic_gameplay_validated": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path else {}
        report["game_build"] = metadata.get("game_build")
        info = probe(source)
        report["source"] = info
        directory = output.parent / ("observations-" + uuid.uuid4().hex)
        samples = extract_samples(source, directory, info)
        report["artifacts"] = {"directory": directory.name, **samples}
        if templates_path:
            config = json.loads(templates_path.read_text(encoding="utf-8"))
            if (
                not isinstance(config.get("templates"), list)
                or not 1 <= len(config["templates"]) <= 20
            ):
                raise ValueError("BOUNDED_TEMPLATE_CONFIGURATION_REQUIRED")
            artifact_pins = {"template-config": digest(config)}
            raw: list[dict[str, Any]] = []
            for entry in config["templates"]:
                template = (templates_path.parent / entry["file"]).resolve()
                if not template.is_relative_to(templates_path.parent.resolve()):
                    raise ValueError("TEMPLATE_PATH_ESCAPE")
                if entry["label"] in artifact_pins or template.stat().st_size > 1_048_576:
                    raise ValueError("INVALID_TEMPLATE_ARTIFACT")
                artifact_pins[entry["label"]] = hashlib.sha256(template.read_bytes()).hexdigest()
                for sample in samples["samples"]:
                    candidate = template_candidates(
                        directory / sample["file"],
                        template,
                        tuple(entry["region"]),
                        entry["threshold"],
                    )
                    if candidate:
                        raw.append(
                            {
                                "label": entry["label"],
                                "timestamp_us": sample["timestamp_us"],
                                "sample": sample["file"],
                                **candidate,
                            }
                        )
            report["observations"] = reconcile(raw, config.get("max_gap_us", 100000))
            report["observation_artifacts"] = artifact_pins
        if detector_manifest_path:
            detector = manifest(json.loads(detector_manifest_path.read_text(encoding="utf-8")))
            duration = round(info["duration_seconds"] * 1_000_000)
            windows = []
            for index, observation in enumerate(report["observations"]):
                if observation["label"] not in CONDITIONS:
                    continue
                start, end = observation["start_us"], observation["end_us"]
                windows.append(
                    {
                        "id": f"template-window-{index}",
                        "start_us": start,
                        "end_us": end,
                        "observations": [
                            {
                                "condition": observation["label"],
                                "value": True,
                                "support": "LOW",
                                "start_us": start,
                                "end_us": end,
                                "uncertainty_us": 16667,
                                "evidence": f"template/{observation['label']}",
                            }
                        ],
                    }
                )
            observation_batch = {
                "schema_version": "observation-batch/1",
                "manifest_hash": digest(detector),
                "observation_artifacts": report.get("observation_artifacts", {}),
                "sources": [
                    {
                        "source_id": metadata.get("source_id", info["source_sha256"]),
                        "source_sha256": info["source_sha256"],
                        "duration_us": duration,
                        "game_build": metadata.get("game_build", "unknown"),
                        "platform": metadata.get("platform", "unknown"),
                        "capture_profile": report["capture_profile"],
                        "provenance": "UNCALIBRATED_TEMPLATE",
                        "windows": windows,
                    }
                ],
            }
            report["recognition_candidates"] = candidates(detector, observation_batch)
            report["observation_batch"] = observation_batch
        report["status"] = "REVIEW_REQUIRED"
        report["issues"] = ["GAMEPLAY_PROFILE_UNVALIDATED", "MOVE_KNOWLEDGE_UNVERIFIED"]
        if not metadata.get("build_confirmed"):
            report["issues"].append("BUILD_UNCONFIRMED")
        if not metadata.get("overlays_confirmed"):
            report["issues"].append("OVERLAYS_UNCONFIRMED")
        if annotations_path:
            annotations = json.loads(annotations_path.read_text(encoding="utf-8"))
            validate_annotations(annotations, info["source_sha256"])
            if metadata.get("game_build") != annotations["game_build"]:
                raise ValueError("ANNOTATION_BUILD_MISMATCH")
            if any(
                x["end_us"] > info["duration_seconds"] * 1_000_000 for x in annotations["examples"]
            ):
                raise ValueError("ANNOTATION_OUTSIDE_SOURCE")
            report["dataset_kind"] = annotations["dataset_kind"]
            report["opportunities"] = annotations["examples"]
            report["review"] = review_metrics(annotations)
            report["measurement_source"] = "operator-imported-human-adjudication"
            report["status"] = "PARTIAL"
            report["issues"].append("HUMAN_LABELS_DO_NOT_VALIDATE_AUTOMATION")
        report["cost"] = {
            "processing_seconds": time.monotonic() - started,
            "decoder_cpu_seconds": info["probe_cpu_seconds"] + samples["cpu_seconds"],
            "decoder_peak_rss_bytes": max(info["probe_peak_rss_bytes"], samples["peak_rss_bytes"]),
            "source_bytes": info["bytes"],
            "derived_bytes": samples["stored_bytes"],
            "cloud_bytes_transferred": None,
            "cloud_cost_usd": None,
            "human_review_seconds": report.get("review", {}).get("review_seconds", 0),
            "failed": False,
        }
    except (ValueError, KeyError, OSError, ValidationError) as error:
        report.update(status="FAILED", issues=[str(error)], opportunities=[])
        report["cost"] = {"processing_seconds": time.monotonic() - started, "failed": True}
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/capture.json"))
    parser.add_argument("--metadata", type=Path)
    parser.add_argument(
        "--annotations", type=Path, help="Operator-reviewed sidecar; never client truth"
    )
    parser.add_argument("--templates", type=Path, help="Optional uncalibrated candidate templates")
    parser.add_argument(
        "--detector-manifest",
        type=Path,
        help="Pinned offline template-to-UNKNOWN candidate receipt",
    )
    args = parser.parse_args()
    report = analyze(
        args.capture,
        args.output,
        args.metadata,
        args.annotations,
        args.templates,
        args.detector_manifest,
    )
    print(
        json.dumps(
            {"status": report["status"], "issues": report["issues"], "report": str(args.output)}
        )
    )
    raise SystemExit(2 if report["status"] == "FAILED" else 0)


if __name__ == "__main__":
    main()
