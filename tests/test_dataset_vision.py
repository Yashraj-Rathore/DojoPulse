import json
from datetime import date, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest

from analysis.annotations import validate_annotations
from analysis.perception_metrics import score_predictions
from analysis.vision import reconcile, template_candidates
from tests.factories import conditions
from tools.validate_dataset import confined, validate_manifest


def annotation():
    return {
        "schema_version": "annotation/1",
        "source_id": "a",
        "source_sha256": "a" * 64,
        "dataset_kind": "synthetic",
        "game_build": "fixture",
        "session_id": "s",
        "source_kind": "synthetic",
        "played_at": "2026-09-18T00:00:00Z",
        "examples": [
            {
                "id": "e",
                "start_us": 0,
                "end_us": 1,
                "situation": "tekken8.jin-vs-jin.blocked-uf4/v1",
                "characters": ["jin", "jin"],
                "eligibility": "ELIGIBLE",
                "outcome": "SUCCESS",
                "evidence": ["frame1"],
                "conditions": conditions(punish_confirmed=True),
                "reviews": [
                    {
                        "reviewer": r,
                        "eligibility": "ELIGIBLE",
                        "outcome": "SUCCESS",
                        "confidence": "high",
                        "seconds": 10,
                    }
                    for r in ("r1", "r2")
                ],
                "adjudication": None,
            }
        ],
    }


def test_independent_review_and_disagreement():
    value = annotation()
    validate_annotations(value, "a" * 64)
    value["examples"][0]["reviews"][1]["outcome"] = "FAILURE"
    with pytest.raises(ValueError):
        validate_annotations(value)
    value["examples"][0]["adjudication"] = {
        "reviewer": "r3",
        "reason": "contact verified",
        "seconds": 9,
    }
    validate_annotations(value)


def test_labels_cannot_override_missing_evidence():
    value = annotation()
    value["examples"][0]["conditions"]["reach_validated"] = None
    with pytest.raises(ValueError):
        validate_annotations(value)


def test_private_path_and_split_leakage(tmp_path):
    with pytest.raises(ValueError):
        confined(tmp_path, "../escape.mp4")
    manifest = json.loads(Path("datasets/dataset-manifest.example.json").read_text())
    manifest["sources"][0]["consent"]["retention_until"] = (
        date.today() + timedelta(days=30)
    ).isoformat()
    duplicate = dict(manifest["sources"][0], source_id="b", sha256="b" * 64, split="held-out")
    manifest["sources"].append(duplicate)
    with pytest.raises(ValueError, match="player_id"):
        validate_manifest(manifest, tmp_path, metadata_only=True)


def test_cv_synthetic_template_and_temporal_dedup(tmp_path):
    rng = np.random.default_rng(7)
    target = rng.integers(0, 255, (12, 20), dtype=np.uint8)
    frame = np.zeros((100, 100), dtype=np.uint8)
    frame[30:42, 40:60] = target
    cv2.imwrite(str(tmp_path / "frame.png"), frame)
    cv2.imwrite(str(tmp_path / "template.png"), target)
    match = template_candidates(
        tmp_path / "frame.png", tmp_path / "template.png", (0, 0, 100, 100), 0.99
    )
    assert match["x"] == 40 and match["confidence"] is None
    groups = reconcile([{"label": "PUNISH", "timestamp_us": t} for t in (0, 1000, 100000)], 2000)
    assert len(groups) == 2 and groups[0]["sample_count"] == 2


def test_outcome_specific_metrics_and_duplicate_predictions():
    truth = [
        {
            "source_id": "a",
            "id": "t",
            "start_us": 100,
            "eligibility": "ELIGIBLE",
            "outcome": "FAILURE",
        }
    ]
    predictions = [
        {
            "source_id": "a",
            "id": f"p{i}",
            "start_us": 100,
            "eligibility": "ELIGIBLE",
            "outcome": "SUCCESS",
        }
        for i in range(2)
    ]
    metrics = score_predictions(truth, predictions)
    assert metrics["slices"]["FAILURE"]["recall"] == 0
    assert metrics["slices"]["SUCCESS"]["fp"] == 2
    assert metrics["slices"]["eligible"]["precision"] == 0.5
