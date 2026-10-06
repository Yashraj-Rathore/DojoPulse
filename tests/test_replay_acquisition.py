"""Controlled evidence fixtures are never proof of actual Tekken acquisition or permission."""

import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest

from analysis.contracts import digest
from ingestion.acquisition import CONTROLS, GATES, assess, new_plan

NOW = datetime(2026, 10, 6, 18, tzinfo=UTC)


def artifact(root, reference, kind, value):
    content = value.encode()
    filename = reference + ".fixture"
    (root / filename).write_bytes(content)
    return {
        "id": reference,
        "kind": kind,
        "file": filename,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def pack(root):
    """Intentionally self-declared real data exercises non-promotion, not actual game facts."""
    plan = new_plan(native_control="AVAILABLE")
    plan["artifacts"] = [
        artifact(root, "private-log", "LOG", "PRIVATE_PLAYER_ID NEVER_EXPORT_TOKEN"),
        artifact(
            root,
            "private-video",
            "VIDEO",
            "controlled synthetic bytes, not a playable Tekken match",
        ),
        artifact(
            root,
            "private-receipt",
            "DELIVERY_RECEIPT",
            "controlled receipt, not a backend observation",
        ),
        artifact(
            root, "private-review", "REVIEW", "controlled declaration, not an actual usage approval"
        ),
    ]
    steps = {
        gate: {
            "status": "OBSERVED",
            "execution": "AUTOMATIC",
            "attempts": 1,
            "seconds": 1,
            "evidence": ["private-log"],
        }
        for gate in GATES
    }
    steps["AUTOMATIC_CAPTURE"]["evidence"] = ["private-video"]
    steps["PRIVATE_DELIVERY"]["evidence"] = ["private-receipt"]
    plan["trials"] = [
        {
            "id": "trial-1",
            "dataset_kind": "real",
            "player_platform": "PC",
            "replay_origin": "PUBLIC_ONLINE_REPLAY",
            "source_build": "fixture-build",
            "playback_build": "fixture-build",
            "observed_at": "2026-10-06T17:00:00Z",
            "upstream_expires_at": None,
            "customer_external_actions": 0,
            "operator_manual_actions": 0,
            "steps": steps,
            "video_artifact": "private-video",
            "delivered_sha256": plan["artifacts"][1]["sha256"],
            "cost_usd": None,
        }
    ]
    return plan


def test_empty_plan_reports_real_blockers_without_inventing_attempts(tmp_path):
    report = assess(new_plan(native_control="UNAVAILABLE"), tmp_path, now=NOW)
    data = report["data"]
    assert data["trial_count"] == data["candidate_count"] == data["real_trial_count"] == 0
    assert data["first_replay_evidence_status"] == "NOT_RUN"
    assert set(data["control_evidence_gaps"]) == set(CONTROLS)
    assert {
        "NATIVE_CONTROL_UNAVAILABLE_OR_UNVERIFIED",
        "NO_REAL_BROWSER_ONLY_REPLAY_CANDIDATE",
        "RATE_POLICY_UNREVIEWED",
    } <= set(data["service_evidence_gaps"])
    assert report["content_hash"] == digest(data)


def test_complete_declarations_and_matching_bytes_cannot_activate_anything(tmp_path):
    plan = pack(tmp_path)
    plan["purpose"] = "MANAGED_SERVICE"
    plan["reviews"] = {
        name: {
            "status": "RECORDED_ACCEPTANCE",
            "purpose": "MANAGED_SERVICE",
            "valid_until": "2026-10-07T00:00:00Z",
            "evidence": ["private-review"],
        }
        for name in ("technical", "usage")
    }
    plan["limits"].update(requests_per_hour=10, cost_budget_usd=1)
    plan["trials"][0].update(player_platform="PS5", cost_usd=0.1)
    plan["controls"] = {
        control: copy.deepcopy(plan["trials"][0]["steps"]["MATCH_LOOKUP"]) for control in CONTROLS
    }
    data = assess(plan, tmp_path, now=NOW)["data"]
    assert data["candidate_count"] == data["console_candidate_count"] == 1
    assert data["first_replay_evidence_status"] == "EVIDENCE_SUBMITTED_FOR_REVIEW"
    assert data["service_evidence_gaps"] == data["control_evidence_gaps"] == []
    for flag in (
        "runtime_enabled",
        "current_permissions_verified",
        "real_game_semantics_verified",
        "media_profile_verified",
        "current_backend_delivery_verified",
        "release_approval",
    ):
        assert data[flag] is False
    assert data["scientific_gates"] == "NOT_RUN"
    rendered = json.dumps(data)
    assert "PRIVATE_PLAYER_ID" not in rendered and "NEVER_EXPORT_TOKEN" not in rendered
    assert str(tmp_path) not in rendered and "private-video.fixture" not in rendered


@pytest.mark.parametrize(
    ("key", "value", "gap"),
    [
        ("dataset_kind", "synthetic", "SYNTHETIC_TRIAL"),
        ("customer_external_actions", 1, "MANUAL_EXTERNAL_ACTIONS"),
        ("operator_manual_actions", 1, "MANUAL_EXTERNAL_ACTIONS"),
        ("replay_origin", "LOCAL_REPLAY", "PUBLIC_REPLAY_ORIGIN_UNVERIFIED"),
        ("player_platform", "UNKNOWN", "PLAYER_PLATFORM_UNVERIFIED"),
        ("playback_build", "older-fixture-build", "BUILD_COMPATIBILITY_UNVERIFIED"),
        ("observed_at", "2026-10-07T00:00:00Z", "FUTURE_OBSERVATION"),
        ("upstream_expires_at", "2026-10-06T16:00:00Z", "REPLAY_EXPIRED_AT_OBSERVATION"),
        ("delivered_sha256", "0" * 64, "SAME_VIDEO_DELIVERY_EVIDENCE_MISSING"),
    ],
)
def test_incomplete_or_manual_trials_cannot_supply_browser_only_evidence(tmp_path, key, value, gap):
    plan = pack(tmp_path)
    plan["trials"][0][key] = value
    data = assess(plan, tmp_path, now=NOW)["data"]
    assert data["candidate_count"] == 0
    assert data["trial_evidence_gaps"][gap] == 1


def test_failed_expired_and_synthetic_trials_remain_in_denominator(tmp_path):
    plan = pack(tmp_path)
    for index, status in enumerate(("FAILED", "EXPIRED", "NOT_FOUND", "INCOMPATIBLE"), start=2):
        trial = copy.deepcopy(plan["trials"][0])
        trial.update(id=f"trial-{index}", dataset_kind="synthetic")
        trial["steps"]["REPLAY_ACQUISITION"]["status"] = status
        plan["trials"].append(trial)
    data = assess(plan, tmp_path, now=NOW)["data"]
    assert data["trial_count"] == 5 and data["synthetic_trial_count"] == 4
    assert data["candidate_count"] == 1 and data["trial_evidence_gaps"]["REPLAY_ACQUISITION"] == 4
    assert all(
        data["declared_step_outcomes"][status] == 1
        for status in ("FAILED", "EXPIRED", "NOT_FOUND", "INCOMPATIBLE")
    )
    assert data["console_candidate_count"] == 0


@pytest.mark.parametrize("change", ["manual", "no-evidence", "no-timing", "retries", "timeout"])
def test_missing_download_stage_is_not_rescued_by_a_working_recorder(tmp_path, change):
    plan = pack(tmp_path)
    check = plan["trials"][0]["steps"]["REPLAY_ACQUISITION"]
    if change == "manual":
        check["execution"] = "MANUAL"
    elif change == "no-evidence":
        check["evidence"] = []
    elif change == "no-timing":
        check["seconds"] = None
    elif change == "retries":
        check["attempts"] = 4
    else:
        plan["limits"]["timeout_seconds"] = 7
    data = assess(plan, tmp_path, now=NOW)["data"]
    assert data["candidate_count"] == 0
    assert data["trial_evidence_gaps"].get("REPLAY_ACQUISITION") or data["trial_evidence_gaps"].get(
        "TOTAL_TIMEOUT_EXCEEDED"
    )


def test_reviews_cannot_cross_purpose_or_expiry_and_upload_stays_fallback(tmp_path):
    plan = pack(tmp_path)
    plan["purpose"] = "MANAGED_SERVICE"
    plan["provider"]["access_class"] = "USER_UPLOAD"
    for review in plan["reviews"].values():
        review.update(
            status="RECORDED_ACCEPTANCE",
            valid_until="2026-10-06T18:00:00Z",
            evidence=["private-review"],
        )
    data = assess(plan, tmp_path, now=NOW)["data"]
    assert len(data["review_evidence_gaps"]) == 2
    assert "USER_UPLOAD_IS_FALLBACK" in data["service_evidence_gaps"]
    assert data["candidate_count"] == 0


@pytest.mark.parametrize(
    "file",
    [
        "../secret",
        "/secret",
        "C:/secret",
        "nested/../secret",
        "file:secret",
        "nested\\secret",
        "./private-video.fixture",
    ],
)
def test_evidence_cannot_read_outside_selected_directory(tmp_path, file):
    plan = pack(tmp_path)
    plan["artifacts"][1]["file"] = file
    with pytest.raises(ValueError, match="confined relative file"):
        assess(plan, tmp_path, now=NOW)


def test_checksum_corruption_missing_refs_and_unbounded_inputs_are_rejected(tmp_path):
    plan = pack(tmp_path)
    (tmp_path / "private-log.fixture").write_bytes(b"changed")
    with pytest.raises(ValueError):
        assess(plan, tmp_path, now=NOW)
    plan = pack(tmp_path)
    plan["trials"][0]["steps"]["MATCH_LOOKUP"]["evidence"] = ["missing"]
    with pytest.raises(ValueError, match="missing evidence"):
        assess(plan, tmp_path, now=NOW)
    plan = pack(tmp_path)
    plan["limits"]["maximum_attempts"] = 100
    with pytest.raises(ValueError, match="Invalid"):
        assess(plan, tmp_path, now=NOW)
    plan = pack(tmp_path)
    plan["trials"][0]["cost_usd"] = float("nan")
    with pytest.raises(ValueError, match="Invalid"):
        assess(plan, tmp_path, now=NOW)


def test_linked_evidence_file_and_ancestor_directory_are_rejected(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    plan = pack(evidence)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(evidence, target_is_directory=True)
    except OSError:
        pytest.skip("OS does not grant symlink creation; Linux CI covers actual links")
    with pytest.raises(ValueError, match="Linked evidence directory"):
        assess(plan, alias, now=NOW)
    nested = evidence / "nested"
    nested.mkdir()
    with pytest.raises(ValueError, match="Linked evidence directory"):
        assess(plan, alias / "nested", now=NOW)
    video = evidence / "private-video.fixture"
    video.rename(evidence / "original.fixture")
    video.symlink_to(evidence / "original.fixture")
    with pytest.raises(ValueError, match="Linked evidence"):
        assess(plan, evidence, now=NOW)


def test_cli_produces_non_promoting_report_and_never_overwrites_inputs(tmp_path):
    plan_path, output = tmp_path / "plan.json", tmp_path / "report.json"
    command = [sys.executable, "-m", "tools.qualify_replay_acquisition", str(plan_path)]
    env = {**os.environ, "ALLOW_SQLITE": "1"}
    init = subprocess.run(
        [*command, "--init", "--native-control", "UNAVAILABLE"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert init.returncode == 0 and json.loads(init.stdout)["trial_count"] == 0
    content = plan_path.read_bytes()
    assert (
        subprocess.run([*command, "--init"], capture_output=True, env=env, timeout=15).returncode
        == 2
    )
    result = subprocess.run(
        [*command, "--evidence-dir", str(tmp_path), "--output", str(output)],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0 and json.loads(result.stdout)["release_approval"] is False
    assert json.loads(output.read_text())["data"]["first_replay_evidence_status"] == "NOT_RUN"
    overwrite = subprocess.run(
        [*command, "--evidence-dir", str(tmp_path), "--output", str(plan_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert overwrite.returncode == 2 and plan_path.read_bytes() == content
    assert str(tmp_path) not in overwrite.stderr
