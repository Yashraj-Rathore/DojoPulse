"""Typed evidence contracts shared by CLI, persistence and evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class Eligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


class Outcome(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def aware_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timestamp must include timezone")
    return result


@dataclass(frozen=True)
class Opportunity:
    id: str
    played_key: str
    source_sha256: str
    session_id: str
    played_at: str
    mode: str
    situation: str
    metric: str
    game_build: str
    knowledge_revision: str
    detector_version: str
    context: str
    eligibility: Eligibility
    outcome: Outcome
    evidence: tuple[str, ...]
    verified: bool = False
    dataset_kind: str = "real"
    deleted: bool = False

    def __post_init__(self) -> None:
        aware_time(self.played_at)
        if not all((self.id, self.played_key, self.session_id, self.context)):
            raise ValueError("Missing identity/context")
        if len(self.source_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.source_sha256
        ):
            raise ValueError("Invalid source hash")
        if self.mode not in {"ranked", "practice", "takeover", "synthetic"}:
            raise ValueError("Invalid source mode")
        if self.dataset_kind not in {"real", "synthetic"}:
            raise ValueError("Invalid dataset kind")
        if self.eligibility not in Eligibility or self.outcome not in Outcome:
            raise ValueError("Invalid eligibility/outcome")
        if self.outcome != Outcome.UNKNOWN and (
            self.eligibility != Eligibility.ELIGIBLE or not self.verified or not self.evidence
        ):
            raise ValueError("Known outcomes require eligible, verified evidence")

    @property
    def content_hash(self) -> str:
        return digest(asdict(self))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Opportunity:
        data = dict(value)
        data["eligibility"] = Eligibility(data["eligibility"])
        data["outcome"] = Outcome(data["outcome"])
        data["evidence"] = tuple(data["evidence"])
        return cls(**data)


@dataclass(frozen=True)
class EvaluationSpec:
    situation: str
    metric: str
    context: str
    baseline_membership: tuple[tuple[str, str], ...]
    compatible_builds: tuple[str, ...]
    compatible_detectors: tuple[str, ...]
    compatible_knowledge: tuple[str, ...]
    baseline_end: str
    followup_start: str
    followup_end: str
    minimum_sample: int = 40
    minimum_sessions: int = 5
    minimum_practice: int = 40
    minimum_coverage: float = 0.9
    max_coverage_difference: float = 0.05
    meaningful_change: float = 0.1
    bootstrap_samples: int = 2000
    seed: int = 19
    measurement_approved: bool = False
    dataset_kind: str = "real"
    capture_profile: str = "tekken8-steam-en-1080p60/v1"
    policy_version: str = "comparison-policy/1"
    exclusions: tuple[str, ...] = (
        "wall",
        "off-axis",
        "unreachable",
        "resource-variant",
        "unverified-timing",
    )
    stop_rules: tuple[str, ...] = (
        "fixed-followup-window",
        "no-early-positive-stop",
        "deleted-evidence-invalidates",
        "build-change-requires-review",
    )

    def __post_init__(self) -> None:
        if not (
            aware_time(self.baseline_end)
            <= aware_time(self.followup_start)
            < aware_time(self.followup_end)
        ):
            raise ValueError("Invalid temporal windows")
        if min(self.minimum_sample, self.minimum_sessions, self.minimum_practice) < 1:
            raise ValueError("Minimum evidence must be positive")
        if not 100 <= self.bootstrap_samples <= 10000:
            raise ValueError("Bootstrap count outside bounded range")
        if not 0 < self.meaningful_change < 1:
            raise ValueError("Meaningful change must be a fraction")
        if not 0 <= self.minimum_coverage <= 1 or not 0 <= self.max_coverage_difference <= 1:
            raise ValueError("Coverage bounds invalid")
        ids = [x[0] for x in self.baseline_membership]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Baseline membership must be nonempty and unique")
        if not all((self.compatible_builds, self.compatible_detectors, self.compatible_knowledge)):
            raise ValueError("Compatibility must be explicit")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EvaluationSpec:
        data = dict(value)
        for key in (
            "compatible_builds",
            "compatible_detectors",
            "compatible_knowledge",
            "exclusions",
            "stop_rules",
        ):
            if key not in data:
                continue
            data[key] = tuple(data[key])
        data["baseline_membership"] = tuple(tuple(x) for x in data["baseline_membership"])
        return cls(**data)
