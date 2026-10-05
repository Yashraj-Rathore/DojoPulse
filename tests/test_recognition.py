# ruff: noqa: F811
"""M09 synthetic candidates, independent release controls and evidence revocation."""

from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from rest_framework.test import APIClient

from analysis.contracts import digest
from analysis.recognition import artifact_hash, benchmark, candidates
from analysis.rules import REQUIRED
from backend.core import datasets, recognition
from backend.core.models import DetectorVersion, GameplayEvent, RecognitionRun
from tests.test_datasets import dataset_env, seal  # noqa: F401
from tests.test_knowledge_workflow import env  # noqa: F401

pytestmark = pytest.mark.django_db


def configuration(e, version="fixture-detector/1"):
    return {
        "schema_version": "detector-manifest/1",
        "version": version,
        "engine": "observation-rules/1",
        "artifact_hash": artifact_hash(),
        "dataset_kind": "synthetic",
        "measurement": e.dataset.measurement,
        "capture_profile": "synthetic-observations/1",
        "max_uncertainty_us": 16667,
        "max_unknown_rate": 0.2,
        "observation_artifacts": {},
    }


def batch(e, config, *, value=True, start=100):
    observations = [
        {
            "condition": key,
            "value": True,
            "support": "HIGH",
            "start_us": start,
            "end_us": start + 100,
            "uncertainty_us": 0,
            "evidence": f"fixture/{key}/1",
        }
        for key in REQUIRED
    ]
    observations.append(
        {
            "condition": "punish_confirmed" if value else "failure_confirmed",
            "value": True,
            "support": "HIGH",
            "start_us": start,
            "end_us": start + 100,
            "uncertainty_us": 0,
            "evidence": "fixture/contact/1",
        }
    )
    return {
        "schema_version": "observation-batch/1",
        "manifest_hash": digest(config),
        "observation_artifacts": config["observation_artifacts"],
        "sources": [
            {
                "source_id": str(e.capture.asset.pk),
                "source_sha256": e.capture.asset.source_sha256,
                "game_build": "fixture",
                "platform": "synthetic",
                "capture_profile": config["capture_profile"],
                "duration_us": 60_000_000,
                "provenance": "SYNTHETIC_FIXTURE",
                "windows": [
                    {
                        "id": "window-1",
                        "start_us": start,
                        "end_us": start + 100,
                        "observations": observations,
                    }
                ],
            }
        ],
    }


def register(e, config=None):
    return recognition.register(
        e.owner, e.dataset.pk, config or configuration(e), e.one.pk, e.two.pk, uuid4()
    )


def qualify(e):
    config = configuration(e)
    version = register(e, config)
    snapshot = seal(e)
    receipt = recognition.run(e.owner, version.pk, snapshot.pk, batch(e, config), uuid4())
    return config, version, snapshot, receipt


def approvals(e, version, receipt):
    for reviewer in (e.one, e.two):
        recognition.review(
            reviewer, version.pk, receipt.pk, receipt.content_hash, "APPROVE", uuid4()
        )


def client(user):
    result = APIClient()
    result.force_authenticate(user)
    return result


def test_synthetic_candidates_are_not_canonical_and_benchmark_is_reproducible(
    dataset_env, tmp_path, monkeypatch
):
    e = dataset_env
    config, version, snapshot, receipt = qualify(e)
    result = receipt.report
    assert result["software_pass"] and result["metrics"]["slices"]["SUCCESS"]["tp"] == 1
    assert result["scientific_gate"] == "NOT_RUN" and not result["real_release_approval"]
    assert result["predictions"][0]["verified"] is False
    assert result["predictions"][0]["evidence"][0]["start_us"] == 100
    assert GameplayEvent.objects.count() == 0
    bundle = {"content_hash": snapshot.content_hash, "data": snapshot.data}
    assert benchmark(config, bundle, receipt.inputs) == result
    assert (
        recognition.run(e.owner, version.pk, snapshot.pk, receipt.inputs, receipt.request_id).pk
        == receipt.pk
    )
    assert artifact_hash() == config["artifact_hash"]
    import json

    from tools.recognize_observations import main

    reproduction = client(e.owner).get(f"/api/recognition/{version.pk}/runs/{receipt.pk}")
    assert reproduction.status_code == 200
    exported = tmp_path / "receipt.json"
    output = tmp_path / "reproduced.json"
    exported.write_text(json.dumps(reproduction.json()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv", ["recognize", "--receipt", str(exported), "--output", str(output)]
    )
    main()
    assert json.loads(output.read_text(encoding="utf-8")) == receipt.report


@pytest.mark.parametrize(
    "mutation", ["missing", "low", "conflict", "uncertainty", "unsupported", "template", "real"]
)
def test_unknown_is_explicit_and_never_infers_failure(dataset_env, mutation):
    e = dataset_env
    config = configuration(e)
    value = batch(e, config)
    src = value["sources"][0]
    obs = src["windows"][0]["observations"]
    if mutation == "missing":
        obs.pop()
    elif mutation == "low":
        obs[-1]["support"] = "LOW"
    elif mutation == "conflict":
        obs.append(dict(obs[-1], condition="failure_confirmed"))
    elif mutation == "uncertainty":
        obs[-1]["uncertainty_us"] = 16668
    elif mutation == "unsupported":
        src["game_build"] = "next-build"
    elif mutation == "template":
        src["provenance"] = "UNCALIBRATED_TEMPLATE"
    else:
        config["dataset_kind"] = "real"
        value["manifest_hash"] = digest(config)
    result = candidates(config, value)["predictions"][0]
    assert result["outcome"] == "UNKNOWN" and result["reasons"]
    assert result["confidence"] is None and not result["verified"]


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "path", "boolean_time", "outside", "hash", "nonfinite", "overcapacity"],
)
def test_untrusted_observation_bounds(dataset_env, mutation):
    e = dataset_env
    config = configuration(e)
    value = batch(e, config)
    if mutation == "duplicate":
        value["sources"] *= 2
    elif mutation == "path":
        value["sources"][0]["windows"][0]["observations"][0]["evidence"] = "../private file"
    elif mutation == "boolean_time":
        value["sources"][0]["duration_us"] = True
    elif mutation == "outside":
        value["sources"][0]["windows"][0]["observations"][0]["start_us"] = 60_000_001
    elif mutation == "hash":
        value["manifest_hash"] = "a" * 64
    elif mutation == "nonfinite":
        config["max_unknown_rate"] = float("nan")
    else:
        value["sources"] *= 1001
    with pytest.raises(ValueError):
        candidates(config, value)


def test_version_scope_artifact_idempotency_and_real_gate(dataset_env):
    e = dataset_env
    version = register(e)
    assert (
        recognition.register(
            e.owner, e.dataset.pk, version.manifest, e.one.pk, e.two.pk, version.request_id
        ).pk
        == version.pk
    )
    with pytest.raises(ValidationError):
        register(e, dict(configuration(e, "fixture/2"), artifact_hash="0" * 64))
    with pytest.raises(ValidationError):
        register(e, dict(configuration(e, "fixture/2"), dataset_kind="real"))
    with pytest.raises(ValidationError):
        recognition.register(e.owner, e.dataset.pk, version.manifest, e.owner.pk, e.two.pk, uuid4())
    with pytest.raises(ValidationError):
        version.save()
    with pytest.raises(DetectorVersion.DoesNotExist):
        with transaction.atomic():
            recognition.current(e.foreign, version.pk)


def test_activation_needs_exact_independent_reviews_and_latest_report(dataset_env):
    e = dataset_env
    _, version, _, receipt = qualify(e)
    with pytest.raises(ValidationError, match="Two independent"):
        recognition.activate(e.owner, version.pk, receipt.pk)
    with pytest.raises(PermissionDenied):
        recognition.review(
            e.owner, version.pk, receipt.pk, receipt.content_hash, "APPROVE", uuid4()
        )
    with pytest.raises(ValidationError, match="Exact"):
        recognition.review(e.one, version.pk, receipt.pk, "0" * 64, "APPROVE", uuid4())
    approvals(e, version, receipt)
    recognition.activate(e.owner, version.pk, receipt.pk)
    version.refresh_from_db()
    assert version.state == "ACTIVE"
    recognition.disable(e.owner, version.pk)
    version.refresh_from_db()
    assert version.state == "DISABLED" and version.disabled_reason == "OPERATOR_STOP"


def test_drift_kills_active_version_and_old_pass_cannot_override(dataset_env):
    e = dataset_env
    config, version, snapshot, receipt = qualify(e)
    approvals(e, version, receipt)
    recognition.activate(e.owner, version.pk, receipt.pk)
    changed = batch(e, config)
    changed["sources"][0]["windows"][0]["observations"].pop()
    failed = recognition.run(e.owner, version.pk, snapshot.pk, changed, uuid4())
    assert not failed.report["software_pass"] and "ABSTENTION_STOP" in failed.report["stop_reasons"]
    version.refresh_from_db()
    assert version.state == "DISABLED" and version.disabled_reason == "DRIFT_STOP"
    with pytest.raises(ValidationError, match="latest"):
        recognition.activate(e.owner, version.pk, receipt.pk)


def test_replacement_and_rollback_select_only_approved_version(dataset_env):
    e = dataset_env
    _, one, snapshot, receipt = qualify(e)
    approvals(e, one, receipt)
    recognition.activate(e.owner, one.pk, receipt.pk)
    config = configuration(e, "fixture-detector/2")
    two = register(e, config)
    next_receipt = recognition.run(e.owner, two.pk, snapshot.pk, batch(e, config), uuid4())
    approvals(e, two, next_receipt)
    recognition.activate(e.owner, two.pk, next_receipt.pk)
    one.refresh_from_db()
    assert one.state == "DISABLED"
    recognition.activate(e.owner, one.pk, receipt.pk)
    two.refresh_from_db()
    assert two.state == "DISABLED"
    assert DetectorVersion.objects.filter(state="ACTIVE").count() == 1
    assert GameplayEvent.objects.count() == 0


def test_negative_controls_cannot_be_omitted_or_treated_as_true_targets(dataset_env):
    e = dataset_env
    config = configuration(e)
    version = register(e, config)
    snapshot = seal(e, absence=True)
    receipt = recognition.run(e.owner, version.pk, snapshot.pk, batch(e, config), uuid4())
    assert receipt.report["negative_controls"] == {"sources": 1, "false_positives": 1}
    assert not receipt.report["software_pass"]
    omitted = batch(e, config)
    omitted["sources"][0]["source_id"] = str(uuid4())
    with pytest.raises(ValidationError, match="every held-out"):
        recognition.run(e.owner, version.pk, snapshot.pk, omitted, uuid4())


@pytest.mark.parametrize("cause", ["dataset", "reviewer", "restore", "expiry", "tamper"])
def test_erasure_and_stale_reads_withhold_private_evidence(dataset_env, cause):
    e = dataset_env
    _, version, snapshot, receipt = qualify(e)
    if cause == "dataset":
        datasets.close(e.owner, e.dataset.pk)
    elif cause == "reviewer":
        recognition.erase_account(e.one.pk)
    elif cause == "restore":
        recognition.restore_revoke()
    elif cause == "expiry":
        from django.utils import timezone

        from backend.core.models import ReplayAsset

        ReplayAsset.objects.filter(pk=e.capture.asset.pk).update(retain_until=timezone.now())
    else:
        RecognitionRun.objects.filter(pk=receipt.pk).update(report={"tampered": True})
    response = client(e.owner).get(f"/api/recognition/{version.pk}")
    assert response.status_code == 200
    assert response.json()["manifest"] is None and response.json()["runs"] == []
    receipt.refresh_from_db()
    version.refresh_from_db()
    assert receipt.inputs == {} and receipt.report == {} and receipt.invalidated_at
    assert version.state == "INVALIDATED" and version.manifest == {}


def test_api_reviewer_metrics_do_not_disclose_source_ids_or_observations(dataset_env):
    e = dataset_env
    _, version, _, receipt = qualify(e)
    owner = client(e.owner).get(f"/api/recognition/{version.pk}")
    assert owner["Cache-Control"] == "private, no-store"
    assert owner.json()["runs"][0]["report"]["predictions"]
    reviewed = client(e.one).get(f"/api/recognition/{version.pk}")
    text = str(reviewed.json())
    assert str(e.capture.asset.pk) not in text and "predictions" not in text
    assert reviewed.json()["runs"][0]["report"]["metrics"]
    assert client(e.foreign).get(f"/api/recognition/{version.pk}").status_code == 404
    assert client(e.one).get(f"/api/recognition/{version.pk}/runs/{receipt.pk}").status_code == 404
    assert (
        client(e.one).post(f"/api/recognition/{version.pk}/disable", {}, format="json").status_code
        == 404
    )
    exported = client(e.owner).get("/api/account/export").json()
    assert "detector_versions" in exported and "recognition_receipts" in exported
    assert str(e.one.pk) not in str(exported["detector_versions"][0].get("reviewer_one", ""))


def test_migration_reverse_refuses_detector_history(dataset_env):
    import importlib

    from django.apps import apps
    from django.db.migrations.exceptions import IrreversibleError

    register(dataset_env)
    guard = importlib.import_module(
        "backend.core.migrations.0021_recognition_lifecycle"
    ).guard_history
    with pytest.raises(IrreversibleError):
        guard(apps, None)


def test_offline_template_bridge_abstains_and_host_discards_candidates(
    dataset_env, tmp_path, monkeypatch
):
    import hashlib
    import json

    import cv2
    import numpy as np

    from analysis.media import profile
    from backend.core.parser import validate_report
    from tools import analyze_capture

    e = dataset_env
    config = configuration(e)
    config["capture_profile"] = profile()["id"]
    pixels = np.random.default_rng(7).integers(0, 255, (12, 20), dtype=np.uint8)
    target = tmp_path / "template.png"
    cv2.imwrite(str(target), pixels)
    templates = {
        "templates": [
            {
                "label": "punish_confirmed",
                "file": "template.png",
                "region": [0, 0, 100, 100],
                "threshold": 0.99,
            }
        ]
    }
    config["observation_artifacts"] = {
        "template-config": digest(templates),
        "punish_confirmed": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    config_file = tmp_path / "manifest.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")
    template_file = tmp_path / "templates.json"
    template_file.write_text(json.dumps(templates), encoding="utf-8")
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            {"game_build": "fixture", "platform": "synthetic", "source_id": str(e.capture.asset.pk)}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        analyze_capture,
        "probe",
        lambda source: {
            "source_sha256": e.capture.asset.source_sha256,
            "duration_seconds": 60,
            "probe_cpu_seconds": 0,
            "probe_peak_rss_bytes": 0,
            "bytes": 10,
        },
    )

    def extract(source, directory, info):
        directory.mkdir()
        image = np.zeros((100, 100), dtype=np.uint8)
        image[30:42, 40:60] = pixels
        cv2.imwrite(str(directory / "frame.png"), image)
        return {
            "samples": [{"file": "frame.png", "timestamp_us": 100}],
            "cpu_seconds": 0,
            "peak_rss_bytes": 0,
            "stored_bytes": 100,
        }

    monkeypatch.setattr(analyze_capture, "extract_samples", extract)
    report = analyze_capture.analyze(
        tmp_path / "fixture.mp4",
        tmp_path / "report.json",
        metadata,
        templates_path=template_file,
        detector_manifest_path=config_file,
    )
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["recognition_candidates"]["predictions"][0]["outcome"] == "UNKNOWN"
    assert report["observation_batch"]["observation_artifacts"] == config["observation_artifacts"]
    safe = validate_report(report)
    assert "recognition_candidates" not in safe and safe["opportunities"] == []


@pytest.mark.django_db(transaction=True)
def test_assigned_review_does_not_lock_another_account_row(dataset_env):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    from backend.core.ownership import lock_owner

    if connection.vendor != "postgresql":
        pytest.skip("Actual PostgreSQL ownership/lock regression")
    e = dataset_env
    _, version, _, _ = qualify(e)

    def read_review():
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '4s'")
            return client(e.one).get(f"/api/recognition/{version.pk}").status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            lock_owner(e.owner.pk)
            assert pool.submit(read_review).result(timeout=8) == 200
