"""Portable, bounded observation rules. Candidates never confer gameplay verification."""

import hashlib
import math
import re
from pathlib import Path
from typing import Any

from analysis.contracts import digest
from analysis.datasets import validate_snapshot
from analysis.perception_metrics import score_predictions
from analysis.rules import REQUIRED, judge

ENGINE = "observation-rules/1"
CONDITIONS = (*REQUIRED, "punish_confirmed", "failure_confirmed")
CODE = re.compile(r"^[A-Za-z0-9_.:/-]{1,160}$")
SHA = re.compile(r"^[a-f0-9]{64}$")


def artifact_hash() -> str:
    root = Path(__file__).parent
    return digest(
        {
            name: hashlib.sha256((root / name).read_text(encoding="utf-8").encode()).hexdigest()
            for name in (
                "recognition.py",
                "rules.py",
                "perception_metrics.py",
                "contracts.py",
                "vision.py",
            )
        }
    )


def shape(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Invalid recognition object fields")
    return value


def integer(value: Any, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError("Recognition timestamp/count outside bounds")
    return value


def code(value: Any) -> str:
    if not isinstance(value, str) or not CODE.fullmatch(value):
        raise ValueError("Invalid bounded recognition code")
    return value


def manifest(value: Any) -> dict[str, Any]:
    data = shape(
        value,
        {
            "schema_version",
            "version",
            "engine",
            "artifact_hash",
            "dataset_kind",
            "measurement",
            "capture_profile",
            "max_uncertainty_us",
            "max_unknown_rate",
            "observation_artifacts",
        },
    )
    if data["schema_version"] != "detector-manifest/1" or data["engine"] != ENGINE:
        raise ValueError("Unsupported detector contract/engine")
    code(data["version"])
    code(data["capture_profile"])
    if data["dataset_kind"] not in {"synthetic", "real"}:
        raise ValueError("Invalid detector data scope")
    if data["artifact_hash"] != artifact_hash():
        raise ValueError("Detector engine artifact differs from this installation")
    pin = shape(
        data["measurement"],
        {"game_build", "platform", "knowledge", "situation", "metric", "definitions"},
    )
    for key in ("game_build", "platform", "knowledge", "situation", "metric"):
        code(pin[key])
    if not isinstance(pin["definitions"], dict) or not 1 <= len(pin["definitions"]) <= 10:
        raise ValueError("Explicit measurement pins required")
    for name, ref in pin["definitions"].items():
        code(name)
        shape(ref, {"key", "hash"})
        code(ref["key"])
        if not isinstance(ref["hash"], str) or not SHA.fullmatch(ref["hash"]):
            raise ValueError("Invalid measurement content hash")
    integer(data["max_uncertainty_us"], 0, 16667)
    artifacts = data["observation_artifacts"]
    if not isinstance(artifacts, dict) or len(artifacts) > 21:
        raise ValueError("Bounded observation artifact hashes required")
    for name, sha in artifacts.items():
        code(name)
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("Invalid observation artifact hash")
    limit = data["max_unknown_rate"]
    if type(limit) not in (float, int) or not math.isfinite(limit) or not 0 <= limit <= 0.2:
        raise ValueError("Abstention stop limit must be between zero and 0.2")
    return data


def candidates(config: dict[str, Any], batch: Any) -> dict[str, Any]:
    config = manifest(config)
    data = shape(batch, {"schema_version", "manifest_hash", "observation_artifacts", "sources"})
    if data["schema_version"] != "observation-batch/1" or data["manifest_hash"] != digest(config):
        raise ValueError("Observation batch must pin the exact detector manifest")
    if data["observation_artifacts"] != config["observation_artifacts"]:
        raise ValueError("Observation configuration/template artifacts differ")
    sources = data["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 1000:
        raise ValueError("Bounded observation sources required")
    predictions: list[dict[str, Any]] = []
    seen = set()
    unsupported = []
    for source in sources:
        shape(
            source,
            {
                "source_id",
                "source_sha256",
                "game_build",
                "platform",
                "capture_profile",
                "duration_us",
                "provenance",
                "windows",
            },
        )
        sid = code(source["source_id"])
        if (
            sid in seen
            or not isinstance(source["source_sha256"], str)
            or not SHA.fullmatch(source["source_sha256"])
        ):
            raise ValueError("Duplicate source or invalid byte hash")
        seen.add(sid)
        for key in ("game_build", "platform", "capture_profile"):
            code(source[key])
        duration = integer(source["duration_us"], 1, 600_000_000)
        if source["provenance"] not in {
            "SYNTHETIC_FIXTURE",
            "OPERATOR_OBSERVATIONS",
            "UNCALIBRATED_TEMPLATE",
        }:
            raise ValueError("Unknown observation provenance")
        supported = (
            source["game_build"] == config["measurement"]["game_build"]
            and source["platform"] == config["measurement"]["platform"]
            and source["capture_profile"] == config["capture_profile"]
        )
        if not supported:
            unsupported.append(sid)
        windows = source["windows"]
        if not isinstance(windows, list) or len(windows) > 100:
            raise ValueError("Too many candidate windows")
        ids = set()
        for window in windows:
            shape(window, {"id", "start_us", "end_us", "observations"})
            wid = code(window["id"])
            if wid in ids or len(predictions) >= 1000:
                raise ValueError("Duplicate window or candidate capacity exceeded")
            ids.add(wid)
            start = integer(window["start_us"], 0, duration)
            end = integer(window["end_us"], start, duration)
            observations = window["observations"]
            if not isinstance(observations, list) or len(observations) > 64:
                raise ValueError("Too many observations")
            evidence = []
            values: dict[str, list[Any]] = {}
            uncertainties = []
            for obs in observations:
                shape(
                    obs,
                    {
                        "condition",
                        "value",
                        "support",
                        "start_us",
                        "end_us",
                        "uncertainty_us",
                        "evidence",
                    },
                )
                if obs["condition"] not in CONDITIONS or (
                    obs["value"] is not None and type(obs["value"]) is not bool
                ):
                    raise ValueError("Invalid observation condition/value")
                if obs["support"] not in {"HIGH", "LOW", "UNKNOWN"}:
                    raise ValueError("Support is ordinal, not a calibrated probability")
                left = integer(obs["start_us"], start, end)
                integer(obs["end_us"], left, end)
                uncertainties.append(integer(obs["uncertainty_us"], 0, duration))
                code(obs["evidence"])
                values.setdefault(obs["condition"], []).append(
                    obs["value"] if obs["support"] == "HIGH" else None
                )
                evidence.append(obs)
            conditions = {
                key: parts[0] if all(p == parts[0] for p in parts) else None
                for key, parts in values.items()
            }
            conditions["uncertainty_us"] = max(uncertainties) if uncertainties else None
            # Only synthetic fixture rules can produce known candidates. Real calibration is absent.
            trusted_fixture = (
                config["dataset_kind"] == "synthetic"
                and source["provenance"] == "SYNTHETIC_FIXTURE"
                and supported
            )
            result = judge(
                conditions,
                reviewed=trusted_fixture,
                max_uncertainty_us=config["max_uncertainty_us"],
            )
            reasons = list(result.reasons)
            if not supported:
                reasons.append("UNSUPPORTED_BUILD_OR_PROFILE")
            if not trusted_fixture:
                reasons.append("DETECTOR_NOT_REAL_VALIDATED")
            predictions.append(
                {
                    "source_id": sid,
                    "id": wid,
                    "start_us": start,
                    "end_us": end,
                    "eligibility": result.eligibility.value,
                    "outcome": result.outcome.value,
                    "reasons": reasons,
                    "evidence": evidence,
                    "confidence": None,
                    "status": "CANDIDATE",
                    "verified": False,
                    "detector_version": config["version"],
                }
            )
    return {
        "schema_version": "recognition-candidates/1",
        "manifest_hash": digest(config),
        "predictions": predictions,
        "unsupported_sources": unsupported,
        "automatic_publication": False,
        "real_release_approval": False,
    }


def benchmark(config: dict[str, Any], bundle: Any, batch: Any) -> dict[str, Any]:
    validate_snapshot(bundle)
    config = manifest(config)
    data = bundle["data"]
    if (
        config["measurement"] != data["measurement"]
        or config["dataset_kind"] != data["dataset_kind"]
    ):
        raise ValueError("Snapshot and detector measurement must match exactly")
    report = candidates(config, batch)
    sources = [s for s in data["sources"] if s["split"] == "held-out"]
    supplied = {s["source_id"]: s for s in batch["sources"]}
    if not sources or set(supplied) != {s["source_id"] for s in sources}:
        raise ValueError("Benchmark must cover every held-out source, including negative controls")
    truth = []
    absent = set()
    for source in sources:
        observed = supplied[source["source_id"]]
        if observed["source_sha256"] != source["source_sha256"] or observed["duration_us"] != round(
            source["duration_seconds"] * 1_000_000
        ):
            raise ValueError("Observation source hash/duration differs from the reviewed snapshot")
        if source["qc"]["label"]["target_absent"]:
            absent.add(source["source_id"])
        for task in source["tasks"]:
            label = task["label"]
            if task["kind"] == "QC" and label.get("target_absent"):
                absent.add(source["source_id"])
            if task["kind"] != "TARGET":
                continue
            timing = label.get("timing") or {}
            if timing.get("start_us") is None:
                raise ValueError("Held-out target needs independently audited timing")
            truth.append(
                {
                    "source_id": source["source_id"],
                    "id": task["id"],
                    "start_us": timing["start_us"],
                    "eligibility": label["eligibility"],
                    "outcome": label["outcome"],
                }
            )
    metrics = score_predictions(truth, report["predictions"], config["max_uncertainty_us"])
    negative_fp = sum(
        p["source_id"] in absent and p["eligibility"] == "ELIGIBLE" for p in report["predictions"]
    )
    reasons = []
    if report["unsupported_sources"]:
        reasons.append("UNSUPPORTED_BUILD_OR_PROFILE")
    if not metrics["prediction_count"] or metrics["abstention_rate"] > config["max_unknown_rate"]:
        reasons.append("ABSTENTION_STOP")
    if not metrics["observable_outcome_coverage"] or metrics["observable_outcome_coverage"] < 0.8:
        reasons.append("INSUFFICIENT_OBSERVABLE_COVERAGE")
    if any(s["fp"] or s["fn"] for s in metrics["slices"].values()) or negative_fp:
        reasons.append("PREDICTION_ERRORS")
    return {
        **report,
        "schema_version": "recognition-benchmark/1",
        "snapshot_hash": bundle["content_hash"],
        "input_hash": digest(batch),
        "metrics": metrics,
        "negative_controls": {"sources": len(absent), "false_positives": negative_fp},
        "stop_reasons": reasons,
        "software_pass": not reasons and config["dataset_kind"] == "synthetic",
        "scientific_gate": "NOT_RUN",
        "benchmark_design": "RETROSPECTIVE_SOFTWARE_CHECK",
        "source_bytes_verified": False,
        "interpretation": "Operator observation receipts do not establish detector accuracy on real video; repeated held-out use cannot qualify G2.",
    }
