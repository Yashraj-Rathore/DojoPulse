# ruff: noqa: F811
"""G1 proposal boundaries, adverse denominators, privacy and reproducible exports."""

import copy
import json
import subprocess
import sys
from uuid import uuid4

import pytest

from analysis.contracts import digest
from analysis.datasets import quality
from analysis.observability import assess
from analysis.rules import judge
from backend.core import pilots
from backend.core.models import GameplayEvent
from tests.test_datasets import client, dataset_env, seal  # noqa: F401
from tests.test_knowledge_workflow import env  # noqa: F401

pytestmark = pytest.mark.django_db


def receipt(data):
    data["qa"] = quality(data["sources"], data["inputs"])
    return {"content_hash": digest(data), "data": data}


def relabel(source, *, resolved=True, outcome=True, condition=None, timing=True):
    task = source["tasks"][0]
    label = task["label"]
    if outcome is False:
        label["conditions"]["punish_confirmed"] = None
        label["conditions"]["failure_confirmed"] = True
    if not resolved:
        label["visibility"] = "UNOBSERVABLE"
        label["conditions"]["punish_confirmed"] = None
        label["conditions"]["failure_confirmed"] = None
    if condition:
        label["conditions"][condition] = None
    result = judge(label["conditions"], reviewed=True)
    label["eligibility"], label["outcome"] = result.eligibility.value, result.outcome.value
    if not timing:
        label["timing"] = {"start_us": None, "end_us": None, "frame_duration_us": None}
    for review in task["reviews"]:
        review["label"] = copy.deepcopy(label)
    example = source["annotations"]["examples"][0]
    for key in ("eligibility", "outcome", "conditions"):
        example[key] = copy.deepcopy(label[key])
    for review in example["reviews"]:
        review["eligibility"], review["outcome"] = label["eligibility"], label["outcome"]
        review["confidence"] = "unobservable" if not resolved else "high"


def sample(base, captures=20, resolved=20, *, real=False):
    data = copy.deepcopy(base.data)
    original = data["sources"][0]
    session = data["inputs"][0]["sessions"][0]
    data["sources"], data["inputs"][0]["sessions"] = [], []
    if real:
        data["dataset_kind"] = "real"
    for index in range(captures):
        source = copy.deepcopy(original)
        source["source_id"] = str(uuid4())
        source["source_sha256"] = digest(["synthetic-observability-fixture", index])
        source["player_id"] = digest(["fixture-player", index % 2])
        source["session_id"] = digest(["fixture-session", index])
        source["qc"]["id"] = str(uuid4())
        source["tasks"][0]["id"] = str(uuid4())
        annotation = source["annotations"]
        annotation["dataset_kind"] = data["dataset_kind"]
        annotation["source_id"], annotation["source_sha256"] = (
            source["source_id"],
            source["source_sha256"],
        )
        annotation["examples"][0]["id"] = source["tasks"][0]["id"]
        relabel(source, resolved=index < resolved, outcome=index % 2 == 0)
        data["sources"].append(source)
        item = copy.deepcopy(session)
        item.update(id=str(uuid4()), player_id=source["player_id"], session_id=source["session_id"])
        data["inputs"][0]["sessions"].append(item)
    return data


@pytest.mark.parametrize(
    ("resolved", "expected"),
    [
        (18, "MEETS_PROPOSED_THRESHOLD"),
        (17, "REVIEW_REQUIRED"),
        (16, "REVIEW_REQUIRED"),
        (15, "NARROW_REQUIRED"),
    ],
)
def test_exact_proposed_thresholds_preserve_unresolved_denominator(dataset_env, resolved, expected):
    data = sample(seal(dataset_env), resolved=resolved)
    report = assess(receipt(data))["data"]
    assert report["proposed_threshold_result"] == expected
    assert report["totals"]["critical_windows"] == 20
    assert report["totals"]["resolvable_windows"] == resolved
    assert report["totals"]["unresolved_windows"] == 20 - resolved
    assert report["scientific_gate"] == "NOT_RUN" and report["release_approval"] is False
    assert "SYNTHETIC_DATA" in report["blockers"]


def test_real_labelled_receipt_and_perfect_rate_do_not_grant_permissions(dataset_env):
    report = assess(receipt(sample(seal(dataset_env), real=True)))["data"]
    assert report["proposed_threshold_result"] == "MEETS_PROPOSED_THRESHOLD"
    assert report["dataset_kind"] == "real" and "SYNTHETIC_DATA" not in report["blockers"]
    assert report["scientific_gate"] == "NOT_RUN" and report["release_approval"] is False
    assert report["source_bytes_verified"] is report["current_permissions_verified"] is False
    assert {
        "CURRENT_PERMISSIONS_NOT_VERIFIED",
        "EXPERT_QUALIFICATION_NOT_VERIFIED",
        "PROSPECTIVE_PROTOCOL_NOT_APPROVED",
    } <= set(report["blockers"])


def test_missing_captures_and_timing_are_not_hidden_by_perfect_rate(dataset_env):
    data = sample(seal(dataset_env), captures=19)
    relabel(data["sources"][0], timing=False)
    report = assess(receipt(data))["data"]
    assert report["proposed_threshold_result"] == "INSUFFICIENT_EVIDENCE"
    assert report["totals"]["resolvable_rate"] == 1
    assert report["totals"]["timing_unaudited_windows"] == 1
    assert {"INSUFFICIENT_CAPTURES", "INCOMPLETE_TIMING_AUDIT"} <= set(report["blockers"])


def test_target_absent_controls_cannot_supply_resolvable_windows(dataset_env):
    data = sample(seal(dataset_env))
    for source in data["sources"]:
        source["tasks"], source["annotations"]["examples"] = [], []
        source["qc"]["label"]["target_absent"] = True
        for review in source["qc"]["reviews"]:
            review["label"]["target_absent"] = True
    report = assess(receipt(data))["data"]
    assert report["totals"]["captures"] == 20
    assert report["totals"]["critical_windows"] == 0 and report["totals"]["resolvable_rate"] is None
    assert report["totals"]["categories"]["TARGET_ABSENT"] == 20
    assert report["proposed_threshold_result"] == "INSUFFICIENT_EVIDENCE"


def test_practice_cannot_inflate_initial_ranked_capture_count(dataset_env):
    data = sample(seal(dataset_env))
    for source in data["sources"]:
        source["annotations"]["source_kind"] = "practice"
        source["tasks"][0]["kind"] = "TRIAL"
    for session in data["inputs"][0]["sessions"]:
        session["phase"] = "PRACTICE"
    report = assess(receipt(data))["data"]
    assert report["totals"]["captures"] == report["totals"]["critical_windows"] == 0
    assert report["totals"]["excluded_non_ranked_captures"] == 20


def test_exclusion_does_not_rescue_unknown_actor_or_incomplete_window(dataset_env):
    data = sample(seal(dataset_env))
    relabel(data["sources"][0], condition="actor_verified")
    source = data["sources"][1]
    source["tasks"][0]["label"]["conditions"]["wall_clear"] = False
    relabel(source, condition="window_complete")
    report = assess(receipt(data))["data"]
    assert report["totals"]["resolvable_windows"] == 18
    assert report["totals"]["unresolved_reasons"]["MISSING_CRITICAL_CONDITIONS"] == 2


def test_all_splits_and_capture_concentration_remain_visible(dataset_env):
    data = sample(seal(dataset_env))
    for index, (source, session) in enumerate(
        zip(data["sources"], data["inputs"][0]["sessions"], strict=True)
    ):
        split = "development" if index % 2 else "held-out"
        source["split"] = session["split"] = split
    report = assess(receipt(data))["data"]
    assert report["splits"]["development"]["critical_windows"] == 10
    assert report["splits"]["held-out"]["critical_windows"] == 10
    assert report["splits"]["validation"]["resolvable_rate"] is None
    assert report["totals"]["source_resolvable_rate_minimum"] == 1


@pytest.mark.parametrize("mutation", ["duplicate", "mixed", "visibility", "inventory"])
def test_malformed_snapshots_cannot_create_assessments(dataset_env, mutation):
    data = sample(seal(dataset_env))
    source = data["sources"][0]
    if mutation == "duplicate":
        source["tasks"].append(copy.deepcopy(source["tasks"][0]))
    elif mutation == "mixed":
        source["tasks"][0]["kind"] = "TRIAL"
    elif mutation == "visibility":
        source["qc"]["label"]["visibility"] = "APPROVED"
        for review in source["qc"]["reviews"]:
            review["label"]["visibility"] = "APPROVED"
    else:
        data["inputs"][0]["sessions"] = []
    with pytest.raises(ValueError):
        assess(receipt(data))


def test_missing_captured_session_and_target_inventory_are_explicit(dataset_env):
    data = sample(seal(dataset_env))
    data["sources"][0]["tasks"], data["sources"][0]["annotations"]["examples"] = [], []
    extra = copy.deepcopy(data["inputs"][0]["sessions"][0])
    extra["session_id"] = digest("unsubmitted-fixture-capture")
    data["inputs"][0]["sessions"].append(extra)
    report = assess(receipt(data))["data"]
    assert report["captured_sessions_without_sources"] == 1
    assert {"INCOMPLETE_TARGET_INVENTORY", "CAPTURED_SESSIONS_WITHOUT_SOURCES"} <= set(
        report["blockers"]
    )


def test_owned_api_matches_offline_hash_and_discloses_no_private_labels(dataset_env):
    e = dataset_env
    row = seal(e)
    path = f"/api/datasets/{e.dataset.pk}/snapshots/{row.pk}/observability"
    result = client(e.owner).get(path)
    assert result.status_code == 200 and result["Cache-Control"] == "private, no-store"
    assert result.json() == assess({"content_hash": row.content_hash, "data": row.data})
    text = json.dumps(result.json())
    assert str(e.capture.asset.pk) not in text and str(e.reviewers[0].pseudonym) not in text
    assert client(e.one).get(path).status_code == 404
    assert client(e.foreign).get(path).status_code == 404
    assert not GameplayEvent.objects.exists()


@pytest.mark.parametrize("withdrawal", ["reviewer", "expiry"])
def test_revoked_evidence_withholds_reports_and_erases_snapshot(dataset_env, withdrawal):
    e = dataset_env
    row = seal(e)
    if withdrawal == "reviewer":
        pilots.withdraw(e.one, e.study.pk)
    else:
        from datetime import timedelta

        from django.utils import timezone

        e.capture.asset.retain_until = timezone.now() - timedelta(seconds=1)
        e.capture.asset.save(update_fields=["retain_until"])
    assert (
        client(e.owner)
        .get(f"/api/datasets/{e.dataset.pk}/snapshots/{row.pk}/observability")
        .status_code
        == 410
    )
    row.refresh_from_db()
    assert row.data == {} and row.invalidated_at


def test_cli_reproduces_report_and_rejects_input_overwrite(dataset_env, tmp_path):
    row = seal(dataset_env)
    bundle = {"content_hash": row.content_hash, "data": row.data}
    source, output = tmp_path / "snapshot.json", tmp_path / "assessment.json"
    source.write_text(json.dumps(bundle), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "tools.assess_observability", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == assess(bundle)
    result = subprocess.run(
        [sys.executable, "-m", "tools.assess_observability", str(source), "--output", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2 and "cannot overwrite" in result.stderr
    assert json.loads(source.read_text(encoding="utf-8")) == bundle


def test_invalid_annotation_contract_has_no_private_error_payload(dataset_env):
    row = seal(dataset_env)
    data = copy.deepcopy(row.data)
    data["sources"][0]["annotations"]["private_note"] = "private-review-details"
    with pytest.raises(ValueError, match="^Invalid annotation contract in observability snapshot$"):
        assess(receipt(data))
