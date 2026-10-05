"""M08 synthetic end-to-end, leakage, timing and erasure contracts."""

import copy
import hashlib
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from analysis.contracts import digest
from analysis.datasets import quality, validate_snapshot
from backend.core import datasets, knowledge, pilot_api, pilots
from backend.core.consents import POLICY_VERSION, record_consent
from backend.core.evidence import as_opportunity, publish_annotations
from backend.core.models import (
    AnalysisRun,
    DatasetCollection,
    DatasetPartition,
    DatasetSnapshot,
    GameplayEvent,
    KnowledgeProposal,
    Match,
    MatchContribution,
    PilotCapture,
    ReplayAsset,
)
from backend.core.storage import delete_asset
from tests.test_knowledge_workflow import bundle, env  # noqa: F401
from tests.test_pilots import label

pytestmark = pytest.mark.django_db


def member(e, study, user, role):
    token = pilots.invite(e.owner, study.pk, role)
    return pilots.enroll(user, token, study.protocol_digest, adult=True, accepted=True, rights=True)


def source(
    e,
    study,
    participant,
    *,
    code="session-1",
    content=b"synthetic-dataset-capture",
    split="held-out",
    platform="synthetic",
):
    enrollment = member(e, study, participant, "PARTICIPANT")
    pilots.assign_split(e.owner, study.pk, enrollment.pk, split)
    played = timezone.now()
    session = pilots.add_session(
        participant,
        study.pk,
        code=code,
        phase="BASELINE",
        played_at=played,
        state="CAPTURED",
        playable_seconds=60,
        unaided=True,
        setup_seconds=120,
        useful=None,
        insight_seconds=None,
        request_id=uuid4(),
    )
    asset = ReplayAsset.objects.create(
        owner=participant,
        storage_key=f"{participant.pk}/{uuid4()}/source.mp4",
        source_sha256=hashlib.sha256(content).hexdigest(),
        bytes=len(content),
        retain_until=played + timedelta(days=1),
        metadata={"game_build": "fixture", "platform": platform, "dataset_kind": "synthetic"},
    )
    match = Match.objects.create(
        owner=participant,
        asset=asset,
        played_at=played,
        game_build="fixture",
        session_id=code,
        chronology_verified=True,
        mode="ranked",
        dataset_kind="synthetic",
        context="jin/jin",
        knowledge_revision="original-unverified-capture/1",
    )
    run = AnalysisRun.objects.create(
        owner=participant,
        asset=asset,
        request_key=uuid4().hex,
        status="REVIEW_REQUIRED",
        result={"source": {"source_sha256": asset.source_sha256, "duration_seconds": 60}},
    )
    capture = pilots.add_capture(participant, study.pk, session.pk, asset.pk)
    return SimpleNamespace(
        member=enrollment, session=session, asset=asset, match=match, run=run, capture=capture
    )


@pytest.fixture
def dataset_env(env, django_user_model):  # noqa: F811 - imported pytest fixture
    e = env
    definition, _ = bundle(e)
    e.dataset = datasets.create(
        e.owner, "Synthetic golden data", "synthetic", definition.pk, uuid4()
    )
    e.study = datasets.new_study(e.owner, e.dataset.pk, "Independent annotation", uuid4())
    e.participant = django_user_model.objects.create_user("dataset-player", is_staff=True)
    e.third = django_user_model.objects.create_user("dataset-adjudicator")
    e.reviewers = [
        member(e, e.study, e.one, "REVIEWER"),
        member(e, e.study, e.two, "REVIEWER"),
        member(e, e.study, e.third, "ADJUDICATOR"),
    ]
    e.capture = source(e, e.study, e.participant)
    return e


def task(e, kind="TARGET", *, start=0, end=1000000, prediction=None):
    return pilots.add_task(
        e.owner,
        e.study.pk,
        e.capture.capture.pk,
        kind=kind,
        start_us=start,
        end_us=60000000 if kind == "QC" else end,
        reviewer_one=e.reviewers[0].pk,
        reviewer_two=e.reviewers[1].pk,
        adjudicator=e.reviewers[2].pk,
        prediction=prediction,
        request_id=uuid4(),
    )


def timed(success=True, *, time=100, uncertainty=0):
    value = label(success)
    value["conditions"]["uncertainty_us"] = uncertainty
    if uncertainty > 16667:
        value["conditions"]["punish_confirmed"] = None
        value["conditions"]["failure_confirmed"] = None
        value["visibility"] = "UNCERTAIN"
    value["timing"] = {
        "start_us": time,
        "end_us": time + 100 if time is not None else None,
        "frame_duration_us": 16667 if time is not None else None,
    }
    return value


def reviewed(e, row, value):
    for user in (e.one, e.two):
        pilots.review_task(user, e.study.pk, row.pk, value, 30, uuid4())


def seal(e, *, absence=False, value=None):
    reviewed(
        e,
        task(e, "QC"),
        {"visibility": "RESOLVABLE", "profile_valid": True, "target_absent": absence},
    )
    if not absence:
        reviewed(e, task(e), value or timed())
    datasets.freeze(e.owner, e.dataset.pk)
    return datasets.seal(e.owner, e.dataset.pk, uuid4())


def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def test_pins_protocol_dependencies_and_idempotent_creation(dataset_env):
    e = dataset_env
    assert e.study.protocol["target"] == "test/situation/1"
    assert e.study.protocol["measurement"] == e.dataset.measurement
    assert "Keyed player/session/source split guards" in e.study.protocol["consent"]
    assert len(e.dataset.measurement["definitions"]) == 5
    assert (
        datasets.create(
            e.owner, e.dataset.title, "synthetic", e.dataset.knowledge_id, e.dataset.request_id
        ).pk
        == e.dataset.pk
    )
    with pytest.raises(ValidationError):
        datasets.create(
            e.owner, "Different", "synthetic", e.dataset.knowledge_id, e.dataset.request_id
        )
    with pytest.raises(ValidationError):
        datasets.create(e.owner, "Real data", "real", e.dataset.knowledge_id, uuid4())
    e.dataset.title = "Mutation"
    with pytest.raises(ValidationError, match="immutable"):
        e.dataset.save()


def test_holdout_blinding_freeze_and_pending_review_rejection(dataset_env):
    e = dataset_env
    row = task(e)
    reviewed(e, row, timed())
    with transaction.atomic():
        assert pilot_api.detail(e.owner, e.study.pk)["tasks"][0]["state"] == "BLINDED"
    with pytest.raises(ValidationError, match="Freeze"):
        datasets.seal(e.owner, e.dataset.pk, uuid4())
    datasets.freeze(e.owner, e.dataset.pk)
    with pytest.raises(ValidationError, match="QC"):
        datasets.seal(e.owner, e.dataset.pk, uuid4())
    with pytest.raises(ValidationError, match="frozen"):
        task(e, start=2000000, end=3000000)


def test_reviewed_sparse_snapshot_qa_and_idempotent_receipt(dataset_env):
    e = dataset_env
    row = seal(e)
    result = client(e.owner).get(f"/api/datasets/{e.dataset.pk}/snapshots/{row.pk}")
    assert result.status_code == 200
    data = result.json()
    assert validate_snapshot(data)["source_bytes_verified"] is False
    qa = data["data"]["qa"]
    assert qa["representative_coverage"] is False
    assert qa["scientific_gate"] == "NOT_RUN" and qa["release_approval"] is False
    held = qa["splits"]["held-out"]
    assert held["categories"]["SUCCESS"] == 1 and held["categories"]["FAILURE"] == 0
    assert held["timing"]["independently_audited"] == 1 and held["review_seconds"] == 120
    assert datasets.seal(e.owner, e.dataset.pk, row.request_id).pk == row.pk
    with pytest.raises(ValidationError, match="immutable"):
        row.save()
    bad = copy.deepcopy(data)
    bad["data"]["qa"]["release_approval"] = True
    bad["content_hash"] = digest(bad["data"])
    with pytest.raises(ValueError, match="QA"):
        validate_snapshot(bad)


def test_target_absent_sources_export_empty_canonical_batches(dataset_env):
    e = dataset_env
    row = seal(e, absence=True)
    source_data = row.data["sources"][0]
    assert source_data["annotations"]["examples"] == []
    assert row.data["qa"]["splits"]["held-out"]["categories"]["TARGET_ABSENT"] == 1
    assert (
        validate_snapshot({"data": row.data, "content_hash": row.content_hash})["status"] == "VALID"
    )


def test_absence_contradiction_cannot_seal(dataset_env):
    e = dataset_env
    reviewed(
        e, task(e, "QC"), {"visibility": "RESOLVABLE", "profile_valid": True, "target_absent": True}
    )
    reviewed(e, task(e), timed())
    datasets.freeze(e.owner, e.dataset.pk)
    with pytest.raises(ValueError, match="contradicts"):
        datasets.seal(e.owner, e.dataset.pk, uuid4())
    assert not DatasetSnapshot.objects.exists()


def test_timing_disagreement_needs_third_review_and_uses_reference(dataset_env):
    e = dataset_env
    reviewed(
        e,
        task(e, "QC"),
        {"visibility": "RESOLVABLE", "profile_valid": True, "target_absent": False},
    )
    row = task(
        e,
        prediction={
            "start_us": 1000,
            "eligibility": "ELIGIBLE",
            "outcome": "SUCCESS",
            "detector_version": "fixture/1",
        },
    )
    pilots.review_task(e.one, e.study.pk, row.pk, timed(time=100), 20, uuid4())
    pilots.review_task(e.two, e.study.pk, row.pk, timed(time=200), 25, uuid4())
    assert pilots.final_label(row)[0] == "DISAGREEMENT"
    datasets.freeze(e.owner, e.dataset.pk)
    with pytest.raises(ValidationError, match="independent"):
        datasets.seal(e.owner, e.dataset.pk, uuid4())
    pilots.review_task(e.third, e.study.pk, row.pk, timed(time=300), 40, uuid4())
    snapshot = datasets.seal(e.owner, e.dataset.pk, uuid4())
    qa = snapshot.data["qa"]["splits"]["held-out"]
    assert qa["timing"]["reviewer_start_gap_max_us"] == 100
    assert qa["recognition"]["timestamp_error_us"]["median"] == 700
    assert qa["adjudicated"] == 1


def test_missing_timing_never_becomes_accuracy_evidence(dataset_env):
    e = dataset_env
    row = task(e)
    with pytest.raises(ValidationError, match="timing audit"):
        pilots.review_task(e.one, e.study.pk, row.pk, label(), 30, uuid4())
    reviewed(e, row, timed(time=None, uncertainty=20000))
    reviewed(
        e,
        task(e, "QC"),
        {"visibility": "RESOLVABLE", "profile_valid": True, "target_absent": False},
    )
    datasets.freeze(e.owner, e.dataset.pk)
    snapshot = datasets.seal(e.owner, e.dataset.pk, uuid4())
    qa = snapshot.data["qa"]["splits"]["held-out"]
    assert qa["categories"]["UNCERTAIN"] == 1
    assert qa["timing"]["unaudited"] == 1 and qa["recognition"] is None


def test_cross_study_split_stays_locked_after_withdrawal(dataset_env):
    e = dataset_env
    second = datasets.new_study(e.owner, e.dataset.pk, "Second intake", uuid4())
    second_member = member(e, second, e.participant, "PARTICIPANT")
    with pytest.raises(ValidationError, match="split"):
        pilots.assign_split(e.owner, second.pk, second_member.pk, "development")
    pilots.withdraw(e.participant, e.study.pk)
    with pytest.raises(ValidationError, match="split"):
        pilots.assign_split(e.owner, second.pk, second_member.pk, "validation")
    assert DatasetPartition.objects.filter(dataset=e.dataset, kind="PLAYER").count() == 1
    assert not PilotCapture.objects.filter(asset=e.capture.asset).exists()


def test_duplicate_source_cannot_cross_linked_study_sessions(dataset_env):
    e = dataset_env
    second = datasets.new_study(e.owner, e.dataset.pk, "Second intake", uuid4())
    with pytest.raises(ValidationError, match="another dataset capture"):
        source(e, second, e.participant, code="session-2")


def test_wrong_platform_and_changed_provenance_block_snapshots(dataset_env, django_user_model):
    e = dataset_env
    player = django_user_model.objects.create_user("wrong-platform")
    with pytest.raises(ValidationError, match="build/platform"):
        source(e, e.study, player, content=b"wrong-platform", platform="steam")
    snapshot = seal(e)
    ReplayAsset.objects.filter(pk=e.capture.asset.pk).update(storage_generation="changed")
    response = client(e.owner).get(f"/api/datasets/{e.dataset.pk}/snapshots/{snapshot.pk}")
    assert response.status_code == 410
    snapshot.refresh_from_db()
    assert snapshot.data == {} and snapshot.invalidated_at


def test_source_and_reviewer_withdrawals_erase_receipts(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    pilots.withdraw(e.one, e.study.pk)
    snapshot.refresh_from_db()
    assert snapshot.data == {} and snapshot.invalidated_at
    assert (
        client(e.owner).get(f"/api/datasets/{e.dataset.pk}/snapshots/{snapshot.pk}").status_code
        == 410
    )
    assert not GameplayEvent.objects.exists()


def test_revoked_knowledge_erases_dataset_and_closure_still_works(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    proposal = KnowledgeProposal.objects.get(published_id=e.dataset.knowledge_id)
    knowledge.lifecycle(e.owner, proposal.pk, "WITHDRAW")
    snapshot.refresh_from_db()
    assert snapshot.data == {} and snapshot.invalidated_at
    detail = client(e.owner).get(f"/api/datasets/{e.dataset.pk}")
    assert detail.status_code == 200 and detail.data["measurement_available"] is False
    datasets.close(e.owner, e.dataset.pk)
    e.dataset.refresh_from_db()
    assert e.dataset.state == "CLOSED"


def test_owned_canonical_import_preserves_capture_and_invalidates_on_erasure(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    batch = snapshot.data["sources"][0]["annotations"]
    publication = publish_annotations(
        e.participant, e.capture.run.pk, e.capture.match.pk, batch, dataset_snapshot_id=snapshot.pk
    )
    assert publication.run_id == e.capture.run.pk
    event = GameplayEvent.objects.select_related("match", "run__asset").get()
    assert event.measurement["dataset_hash"] == snapshot.content_hash
    assert event.metric == "test/metric/1" and not as_opportunity(event).deleted
    e.capture.match.refresh_from_db()
    assert e.capture.match.knowledge_revision == "original-unverified-capture/1"
    assert MatchContribution.objects.get().summary["denominator"] == 1
    before = client(e.participant).get("/api/player-model?dataset_kind=synthetic")
    assert before.status_code == 200 and before.data["card_total"] == 1
    assert before.data["cards"][0]["scope"]["knowledge_revision"] == "test/knowledge/1"
    assert before.data["cards"][0]["summary"]["denominator"] == 1
    assert before.data["cards"][0]["drills"] == []  # Source grant is not a foreign drill grant.
    delete_asset(e.participant, e.capture.asset.pk)
    snapshot.refresh_from_db()
    event.refresh_from_db()
    assert snapshot.data == {} and event.deleted_at and not MatchContribution.objects.exists()
    after = client(e.participant).get("/api/player-model?dataset_kind=synthetic")
    assert after.status_code == 200 and after.data["cards"] == []


def test_no_foreign_export_or_unscoped_canonical_publication(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    url = f"/api/datasets/{e.dataset.pk}/snapshots/{snapshot.pk}"
    assert client(e.foreign).get(url).status_code == 404
    assert client(e.participant).get(url).status_code == 404
    batch = snapshot.data["sources"][0]["annotations"]
    with pytest.raises(PermissionDenied):
        publish_annotations(
            e.owner, e.capture.run.pk, e.capture.match.pk, batch, dataset_snapshot_id=snapshot.pk
        )
    changed = copy.deepcopy(batch)
    changed["examples"][0]["id"] = "substitute"
    with pytest.raises(ValidationError, match="exact reviewed"):
        publish_annotations(
            e.participant,
            e.capture.run.pk,
            e.capture.match.pk,
            changed,
            dataset_snapshot_id=snapshot.pk,
        )
    assert not GameplayEvent.objects.exists()


def test_processing_withdrawal_erases_owned_collection_without_foreign_labels(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    exported = client(e.owner).get("/api/account/export")
    assert exported.status_code == 200
    assert "dataset_snapshot_receipts" in str(exported.data)
    assert "dataset-player" not in str(exported.data)
    record_consent(e.owner, "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
    snapshot.refresh_from_db()
    e.dataset.refresh_from_db()
    assert snapshot.data == {} and e.dataset.measurement == {} and e.dataset.deleted_at


def test_portable_validator_detects_disjointness_and_qa_tampering(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    data = copy.deepcopy(snapshot.data)
    leaked = copy.deepcopy(data["sources"][0])
    leaked["source_id"] = str(uuid4())
    leaked["source_sha256"] = "b" * 64
    leaked["split"] = "validation"
    leaked["annotations"]["source_id"] = leaked["source_id"]
    leaked["annotations"]["source_sha256"] = leaked["source_sha256"]
    data["sources"].append(leaked)
    data["qa"] = quality(data["sources"])
    with pytest.raises(ValueError, match="leaked player_id"):
        validate_snapshot({"data": data, "content_hash": digest(data)})


def test_collection_close_erases_inputs_and_guard_receipts(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    datasets.close(e.owner, e.dataset.pk)
    snapshot.refresh_from_db()
    e.study.refresh_from_db()
    assert snapshot.data == {} and snapshot.content_hash
    assert not DatasetPartition.objects.exists() and e.study.protocol == {}
    assert not DatasetCollection.objects.filter(deleted_at=None).exists()


def test_source_binding_stays_locked_after_withdrawal(dataset_env, django_user_model):
    e = dataset_env
    pilots.withdraw(e.participant, e.study.pk)
    other = django_user_model.objects.create_user("duplicate-after-withdrawal")
    with pytest.raises(ValidationError, match="source leakage"):
        source(e, e.study, other, code="different-session")


def test_snapshot_timing_and_annotation_mismatch_are_rejected(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    data = copy.deepcopy(snapshot.data)
    task_data = data["sources"][0]["tasks"][0]
    task_data["label"]["timing"]["start_us"] = 500000000
    for review in task_data["reviews"]:
        review["label"]["timing"]["start_us"] = 500000000
    data["qa"] = quality(data["sources"], data["inputs"])
    with pytest.raises(ValueError, match="timing outside"):
        validate_snapshot({"data": data, "content_hash": digest(data)})


def test_retirement_preserves_frozen_dataset_but_stops_new_intake(dataset_env):
    e = dataset_env
    snapshot = seal(e)
    proposal = KnowledgeProposal.objects.get(published_id=e.dataset.knowledge_id)
    knowledge.lifecycle(e.owner, proposal.pk, "RETIRE")
    assert (
        client(e.owner).get(f"/api/datasets/{e.dataset.pk}/snapshots/{snapshot.pk}").status_code
        == 200
    )
    with pytest.raises(ValidationError):
        datasets.create(e.owner, "Post-retirement", "synthetic", e.dataset.knowledge_id, uuid4())


def test_adverse_and_target_absent_categories_stay_separate(dataset_env, django_user_model):
    e = dataset_env
    reviewed(
        e,
        task(e, "QC"),
        {"visibility": "RESOLVABLE", "profile_valid": True, "target_absent": False},
    )
    reviewed(e, task(e), timed())
    reviewed(e, task(e, start=2000000, end=3000000), timed(False, time=2000100))
    near = timed(time=4000100)
    near["conditions"]["standing"] = False
    near["conditions"]["punish_confirmed"] = None
    reviewed(e, task(e, start=4000000, end=5000000), near)
    reviewed(e, task(e, start=6000000, end=7000000), timed(time=None, uncertainty=20000))
    negative_player = django_user_model.objects.create_user("target-absent-control")
    e.capture = source(
        e, e.study, negative_player, code="absent-source", content=b"synthetic-negative"
    )
    reviewed(
        e, task(e, "QC"), {"visibility": "RESOLVABLE", "profile_valid": True, "target_absent": True}
    )
    datasets.freeze(e.owner, e.dataset.pk)
    snapshot = datasets.seal(e.owner, e.dataset.pk, uuid4())
    qa = snapshot.data["qa"]
    assert qa["splits"]["held-out"]["categories"] == dict.fromkeys(datasets.CATEGORIES, 1)
    assert qa["splits"]["held-out"]["missing_categories"] == []
    assert qa["representative_coverage"] is False
    assert qa["release_approval"] is False


def test_migration_reverse_refuses_dataset_history(dataset_env):
    import importlib

    from django.apps import apps
    from django.db import connection

    migration = importlib.import_module("backend.core.migrations.0018_dataset_operations")
    with pytest.raises(ValueError, match="dataset history"):
        migration.guard_reverse(apps, SimpleNamespace(connection=connection))


@pytest.mark.django_db(transaction=True)
def test_canonical_import_and_foreign_reviewer_withdrawal_serialize(dataset_env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("Actual PostgreSQL owner/capacity lock ordering required")
    e = dataset_env
    snapshot = seal(e)
    original = datasets.canonical_measurement
    entered, revoke_started = Event(), Event()

    def measured(*args, **kwargs):
        value = original(*args, **kwargs)
        entered.set()
        assert revoke_started.wait(10)
        return value

    monkeypatch.setattr(datasets, "canonical_measurement", measured)

    def importing():
        close_old_connections()
        try:
            publish_annotations(
                e.participant,
                e.capture.run.pk,
                e.capture.match.pk,
                snapshot.data["sources"][0]["annotations"],
                dataset_snapshot_id=snapshot.pk,
            )
        finally:
            close_old_connections()

    def revoking():
        close_old_connections()
        try:
            assert entered.wait(10)
            revoke_started.set()
            pilots.withdraw(e.one, e.study.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        imported = executor.submit(importing)
        revoked = executor.submit(revoking)
        imported.result(timeout=30)
        revoked.result(timeout=30)
    snapshot.refresh_from_db()
    assert snapshot.invalidated_at and snapshot.data == {}
    assert not GameplayEvent.objects.filter(deleted_at=None).exists()
    assert not MatchContribution.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_diagnosis_read_and_foreign_reviewer_withdrawal_serialize(dataset_env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import close_old_connections, connection

    from backend.core import player_model_api

    if connection.vendor != "postgresql":
        pytest.skip("Actual PostgreSQL withdrawal/read lock ordering required")
    e = dataset_env
    snapshot = seal(e)
    publish_annotations(
        e.participant,
        e.capture.run.pk,
        e.capture.match.pk,
        snapshot.data["sources"][0]["annotations"],
        dataset_snapshot_id=snapshot.pk,
    )
    original = player_model_api.projection
    entered, revoke_started = Event(), Event()

    def measured(*args, **kwargs):
        value = original(*args, **kwargs)
        entered.set()
        assert revoke_started.wait(10)
        return value

    monkeypatch.setattr(player_model_api, "projection", measured)

    def reading():
        close_old_connections()
        try:
            response = client(e.participant).get("/api/player-model?dataset_kind=synthetic")
            assert response.status_code == 200 and response.data["card_total"] == 1
        finally:
            close_old_connections()

    def revoking():
        close_old_connections()
        try:
            assert entered.wait(10)
            revoke_started.set()
            pilots.withdraw(e.one, e.study.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        read = executor.submit(reading)
        revoked = executor.submit(revoking)
        read.result(timeout=30)
        revoked.result(timeout=30)
    monkeypatch.setattr(player_model_api, "projection", original)
    after = client(e.participant).get("/api/player-model?dataset_kind=synthetic")
    assert after.status_code == 200 and after.data["cards"] == []
    snapshot.refresh_from_db()
    assert snapshot.invalidated_at and snapshot.data == {}
