"""Offline evidence checks for replay acquisition; never an adapter or runtime approval."""

from __future__ import annotations

import hashlib
import math
import stat
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from analysis.contracts import aware_time, digest
from ingestion.contracts import ProviderClass

VERSION = "replay-acquisition/1"
GATES = (
    "BROWSER_REQUEST",
    "IDENTITY_MAPPING",
    "MATCH_LOOKUP",
    "REPLAY_ACQUISITION",
    "COMPATIBLE_PLAYBACK",
    "AUTOMATIC_CAPTURE",
    "PRIVATE_DELIVERY",
    "MATCH_ATTRIBUTION",
)
CONTROLS = (
    "EXPIRED_REPLAY",
    "INCOMPATIBLE_BUILD",
    "WRONG_PLAYER",
    "DUPLICATE_RETRY",
    "RATE_LIMIT",
    "TIMEOUT",
    "CANCELLATION",
    "CONSENT_WITHDRAWAL",
)
MAX_ARTIFACT_BYTES = 536_870_912
MAX_EVIDENCE_BYTES = 629_145_600


def obj(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def choice(*values: str) -> dict[str, Any]:
    return {"enum": list(values)}


def array(items: dict[str, Any], maximum: int) -> dict[str, Any]:
    return {"type": "array", "items": items, "maxItems": maximum}


TOKEN = {"type": "string", "pattern": "^[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,79}$"}
HASH = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
BUILD = {"type": ["string", "null"], "minLength": 1, "maxLength": 80}
TIME = {"type": ["string", "null"], "maxLength": 40}
REFERENCES = {**array(TOKEN, 16), "uniqueItems": True}
CHECK = obj(
    {
        "status": choice("NOT_RUN", "OBSERVED", "FAILED", "EXPIRED", "NOT_FOUND", "INCOMPATIBLE"),
        "execution": choice("AUTOMATIC", "MANUAL", "UNKNOWN"),
        "attempts": {"type": "integer", "minimum": 0, "maximum": 8},
        "seconds": {"type": ["number", "null"], "minimum": 0, "maximum": 1200},
        "evidence": REFERENCES,
    }
)
REVIEW = obj(
    {
        "status": choice("PENDING", "RECORDED_ACCEPTANCE", "BLOCKED"),
        "purpose": choice("LOCAL_FEASIBILITY", "MANAGED_SERVICE"),
        "valid_until": TIME,
        "evidence": REFERENCES,
    }
)
SCHEMA = obj(
    {
        "schema_version": {"const": VERSION},
        "purpose": choice("LOCAL_FEASIBILITY", "MANAGED_SERVICE"),
        "provider": obj(
            {
                "key": TOKEN,
                "version": TOKEN,
                "access_class": choice(*(item.value for item in ProviderClass)),
                "upstream_class": choice(*(item.value for item in ProviderClass)),
                "route": choice(
                    "CLIENT_PLAYBACK_CAPTURE", "VIDEO_EXPORT", "NATIVE_REPLAY_RENDERER"
                ),
            }
        ),
        "native_control": choice("AVAILABLE", "UNAVAILABLE", "UNVERIFIED", "NOT_APPLICABLE"),
        "reviews": obj({"technical": REVIEW, "usage": REVIEW}),
        "limits": obj(
            {
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1200},
                "maximum_attempts": {"type": "integer", "minimum": 1, "maximum": 8},
                "maximum_video_bytes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_ARTIFACT_BYTES,
                },
                "requests_per_hour": {"type": ["integer", "null"], "minimum": 1, "maximum": 10000},
                "retention_days": {"type": "integer", "minimum": 1, "maximum": 90},
                "cost_budget_usd": {"type": ["number", "null"], "minimum": 0, "maximum": 1000},
            }
        ),
        "artifacts": array(
            obj(
                {
                    "id": TOKEN,
                    "kind": choice("LOG", "SCREENSHOT", "REVIEW", "VIDEO", "DELIVERY_RECEIPT"),
                    "file": {"type": "string", "minLength": 1, "maxLength": 240},
                    "sha256": HASH,
                    "bytes": {"type": "integer", "minimum": 1, "maximum": MAX_ARTIFACT_BYTES},
                }
            ),
            64,
        ),
        "trials": array(
            obj(
                {
                    "id": TOKEN,
                    "dataset_kind": choice("real", "synthetic"),
                    "player_platform": choice("PC", "PS5", "XBOX_SERIES", "UNKNOWN"),
                    "replay_origin": choice("PUBLIC_ONLINE_REPLAY", "LOCAL_REPLAY", "UNKNOWN"),
                    "source_build": BUILD,
                    "playback_build": BUILD,
                    "observed_at": {"type": "string", "maxLength": 40},
                    "upstream_expires_at": TIME,
                    "customer_external_actions": {"type": "integer", "minimum": 0, "maximum": 100},
                    "operator_manual_actions": {"type": "integer", "minimum": 0, "maximum": 100},
                    "steps": obj(dict.fromkeys(GATES, CHECK)),
                    "video_artifact": {"type": ["string", "null"], "maxLength": 80},
                    "delivered_sha256": {"anyOf": [HASH, {"type": "null"}]},
                    "cost_usd": {"type": ["number", "null"], "minimum": 0, "maximum": 1000},
                }
            ),
            50,
        ),
        "controls": obj(dict.fromkeys(CONTROLS, CHECK)),
    }
)


def empty_check() -> dict[str, Any]:
    return {
        "status": "NOT_RUN",
        "execution": "UNKNOWN",
        "attempts": 0,
        "seconds": None,
        "evidence": [],
    }


def new_plan(*, native_control: str = "UNVERIFIED") -> dict[str, Any]:
    """No evidence, review, customer action or game result is invented by initialization."""
    return {
        "schema_version": VERSION,
        "purpose": "LOCAL_FEASIBILITY",
        "provider": {
            "key": "tekken-client-capture-candidate",
            "version": "unqualified-1",
            "access_class": "REVERSE_ENGINEERED",
            "upstream_class": "OFFICIAL",
            "route": "CLIENT_PLAYBACK_CAPTURE",
        },
        "native_control": native_control,
        "reviews": {
            name: {
                "status": "PENDING",
                "purpose": "LOCAL_FEASIBILITY",
                "valid_until": None,
                "evidence": [],
            }
            for name in ("technical", "usage")
        },
        "limits": {
            "timeout_seconds": 1200,
            "maximum_attempts": 3,
            "maximum_video_bytes": MAX_ARTIFACT_BYTES,
            "requests_per_hour": None,
            "retention_days": 7,
            "cost_budget_usd": None,
        },
        "artifacts": [],
        "trials": [],
        "controls": {name: empty_check() for name in CONTROLS},
    }


def validate_plan(plan: dict[str, Any]) -> None:
    def finite(value: Any) -> bool:
        if isinstance(value, float):
            return math.isfinite(value)
        if isinstance(value, dict):
            return all(finite(item) for item in value.values())
        if isinstance(value, list):
            return all(finite(item) for item in value)
        return True

    if not finite(plan) or not Draft202012Validator(SCHEMA).is_valid(plan):
        # Schema error details may contain private input; do not echo them to logs.
        raise ValueError("Invalid replay acquisition plan")
    artifacts = plan["artifacts"]
    ids = {artifact["id"] for artifact in artifacts}
    if len(ids) != len(artifacts) or len({trial["id"] for trial in plan["trials"]}) != len(
        plan["trials"]
    ):
        raise ValueError("Duplicate evidence or trial reference")
    if sum(artifact["bytes"] for artifact in artifacts) > MAX_EVIDENCE_BYTES:
        raise ValueError("Evidence exceeds aggregate byte limit")
    checks = list(plan["controls"].values()) + list(plan["reviews"].values())
    for trial in plan["trials"]:
        aware_time(trial["observed_at"])
        if trial["upstream_expires_at"] is not None:
            aware_time(trial["upstream_expires_at"])
        checks.extend(trial["steps"].values())
        if trial["video_artifact"] is not None and trial["video_artifact"] not in ids:
            raise ValueError("Video references missing evidence")
    for review in plan["reviews"].values():
        if review["valid_until"] is not None:
            aware_time(review["valid_until"])
    if any(not set(check["evidence"]) <= ids for check in checks):
        raise ValueError("Check references missing evidence")


def checked_artifact(root: Path, artifact: dict[str, Any]) -> None:
    name = artifact["file"]
    relative = PurePosixPath(name)
    if (
        relative.is_absolute()
        or "\\" in name
        or ":" in name
        or any(part in {".", "..", ""} for part in name.split("/"))
    ):
        raise ValueError("Evidence must use a confined relative file")
    path = root
    for part in relative.parts:
        path /= part
        info = path.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError("Linked evidence is not permitted")
    if not path.resolve(strict=True).is_relative_to(root):
        raise ValueError("Evidence escapes the selected directory")
    before = path.stat()
    limit = MAX_ARTIFACT_BYTES if artifact["kind"] == "VIDEO" else 8_388_608
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_size != artifact["bytes"]
        or before.st_size > limit
    ):
        raise ValueError("Evidence file has an invalid type or byte count")
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        remaining = before.st_size
        while remaining:
            block = source.read(min(1_048_576, remaining))
            if not block:
                raise ValueError("Evidence changed while reading")
            checksum.update(block)
            remaining -= len(block)
        if source.read(1):
            raise ValueError("Evidence changed while reading")
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("Evidence changed while reading")
    if checksum.hexdigest() != artifact["sha256"]:
        raise ValueError("Evidence checksum mismatch")


def observed(check: dict[str, Any], limits: dict[str, Any]) -> bool:
    return (
        check["status"] == "OBSERVED"
        and check["execution"] == "AUTOMATIC"
        and bool(check["evidence"])
        and 0 < check["attempts"] <= limits["maximum_attempts"]
        and check["seconds"] is not None
        and check["seconds"] <= limits["timeout_seconds"]
    )


def assess(plan: dict[str, Any], evidence_root: Path, *, now: datetime) -> dict[str, Any]:
    """Check declared evidence and bytes. Human/game/backend facts remain unverified."""
    validate_plan(plan)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Assessment time must be timezone-aware")
    for parent in (evidence_root.absolute(), *evidence_root.absolute().parents):
        info = parent.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError("Linked evidence directory is not permitted")
    root_info = evidence_root.lstat()
    if (
        not stat.S_ISDIR(root_info.st_mode)
        or evidence_root.is_symlink()
        or getattr(root_info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise ValueError("Select a real evidence directory")
    root = evidence_root.resolve(strict=True)
    for artifact in plan["artifacts"]:
        checked_artifact(root, artifact)
    artifacts = {artifact["id"]: artifact for artifact in plan["artifacts"]}
    limits = plan["limits"]
    gaps: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    candidates = []
    review_gaps = []
    for name, review in plan["reviews"].items():
        if (
            review["status"] != "RECORDED_ACCEPTANCE"
            or review["purpose"] != plan["purpose"]
            or not review["evidence"]
            or any(artifacts[ref]["kind"] != "REVIEW" for ref in review["evidence"])
            or review["valid_until"] is None
            or aware_time(review["valid_until"]) <= now
        ):
            review_gaps.append(f"{name.upper()}_REVIEW_MISSING_OR_OUT_OF_SCOPE")
    for trial in plan["trials"]:
        missing = []
        for gate, check in trial["steps"].items():
            outcomes[check["status"]] += 1
            if not observed(check, limits):
                missing.append(gate)
        if trial["dataset_kind"] != "real":
            missing.append("SYNTHETIC_TRIAL")
        if plan["provider"]["access_class"] == "USER_UPLOAD":
            missing.append("USER_UPLOAD_IS_FALLBACK")
        if trial["replay_origin"] != "PUBLIC_ONLINE_REPLAY":
            missing.append("PUBLIC_REPLAY_ORIGIN_UNVERIFIED")
        if trial["player_platform"] == "UNKNOWN":
            missing.append("PLAYER_PLATFORM_UNVERIFIED")
        if trial["customer_external_actions"] or trial["operator_manual_actions"]:
            missing.append("MANUAL_EXTERNAL_ACTIONS")
        if not trial["source_build"] or trial["source_build"] != trial["playback_build"]:
            missing.append("BUILD_COMPATIBILITY_UNVERIFIED")
        observed_at = aware_time(trial["observed_at"])
        if observed_at > now:
            missing.append("FUTURE_OBSERVATION")
        if trial["upstream_expires_at"] and aware_time(trial["upstream_expires_at"]) <= observed_at:
            missing.append("REPLAY_EXPIRED_AT_OBSERVATION")
        video = artifacts.get(trial["video_artifact"])
        delivery = trial["steps"]["PRIVATE_DELIVERY"]["evidence"]
        if (
            not video
            or video["kind"] != "VIDEO"
            or video["bytes"] > limits["maximum_video_bytes"]
            or video["sha256"] != trial["delivered_sha256"]
            or video["id"] not in trial["steps"]["AUTOMATIC_CAPTURE"]["evidence"]
            or not any(artifacts[ref]["kind"] == "DELIVERY_RECEIPT" for ref in delivery)
        ):
            missing.append("SAME_VIDEO_DELIVERY_EVIDENCE_MISSING")
        if (
            sum(check["seconds"] or 0 for check in trial["steps"].values())
            > limits["timeout_seconds"]
        ):
            missing.append("TOTAL_TIMEOUT_EXCEEDED")
        gaps.update(set(missing))
        if not missing:
            candidates.append(trial)
    console_candidates = sum(
        trial["player_platform"] in {"PS5", "XBOX_SERIES"} for trial in candidates
    )
    control_gaps = [name for name, check in plan["controls"].items() if not observed(check, limits)]
    service_gaps = list(review_gaps)
    if plan["purpose"] != "MANAGED_SERVICE":
        service_gaps.append("MANAGED_SERVICE_USAGE_NOT_RECORDED")
    if not console_candidates:
        service_gaps.append("PC_PLAYBACK_OF_CONSOLE_PUBLIC_REPLAY_NOT_DEMONSTRATED")
    if not candidates:
        service_gaps.append("NO_REAL_BROWSER_ONLY_REPLAY_CANDIDATE")
    if plan["provider"]["access_class"] == "USER_UPLOAD":
        service_gaps.append("USER_UPLOAD_IS_FALLBACK")
    if (
        plan["provider"]["route"] == "CLIENT_PLAYBACK_CAPTURE"
        and plan["native_control"] != "AVAILABLE"
    ):
        service_gaps.append("NATIVE_CONTROL_UNAVAILABLE_OR_UNVERIFIED")
    if limits["requests_per_hour"] is None:
        service_gaps.append("RATE_POLICY_UNREVIEWED")
    if limits["cost_budget_usd"] is None or any(trial["cost_usd"] is None for trial in candidates):
        service_gaps.append("COST_NOT_MEASURED_OR_BUDGETED")
    elif any(trial["cost_usd"] > limits["cost_budget_usd"] for trial in candidates):
        service_gaps.append("COST_BUDGET_EXCEEDED")
    data = {
        "schema_version": VERSION,
        "plan_sha256": digest(plan),
        "assessed_at": now.isoformat(),
        "provider": plan["provider"],
        "purpose": plan["purpose"],
        "artifact_count": len(artifacts),
        "artifact_bytes_checked": sum(artifact["bytes"] for artifact in artifacts.values()),
        "trial_count": len(plan["trials"]),
        "real_trial_count": sum(trial["dataset_kind"] == "real" for trial in plan["trials"]),
        "synthetic_trial_count": sum(
            trial["dataset_kind"] == "synthetic" for trial in plan["trials"]
        ),
        "first_replay_evidence_status": "EVIDENCE_SUBMITTED_FOR_REVIEW"
        if candidates
        else ("INCOMPLETE" if plan["trials"] else "NOT_RUN"),
        "candidate_count": len(candidates),
        "console_candidate_count": console_candidates,
        "declared_step_outcomes": dict(sorted(outcomes.items())),
        "trial_evidence_gaps": dict(sorted(gaps.items())),
        "review_evidence_gaps": review_gaps,
        "control_evidence_gaps": control_gaps,
        "service_evidence_gaps": sorted(set(service_gaps)),
        "runtime_enabled": False,
        "current_permissions_verified": False,
        "real_game_semantics_verified": False,
        "media_profile_verified": False,
        "current_backend_delivery_verified": False,
        "scientific_gates": "NOT_RUN",
        "release_approval": False,
        "next_action": "COMPLETE_TECHNICAL_AND_USAGE_REVIEW"
        if review_gaps
        else "REVIEW_ACTUAL_GAME_AND_PRIVATE_DELIVERY_EVIDENCE",
    }
    return {"content_hash": digest(data), "data": data}
