"""Synthetic M07 contracts: real Tekken facts and experts are deliberately not fabricated."""

import copy
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from analysis.rules import REQUIRED
from backend.core import knowledge
from backend.core.consents import POLICY_VERSION, record_consent
from backend.core.evidence import as_opportunity, publish_annotations
from backend.core.jobs import claim_run, finish_run
from backend.core.loops import create_assignment, create_plan
from backend.core.models import (
    AnalysisPublication,
    AnalysisRun,
    DefinitionVersion,
    Game,
    GameBuild,
    GameplayEvent,
    KnowledgeProposal,
    KnowledgeReanalysis,
    KnowledgeReview,
    Match,
    MatchContribution,
    Profile,
    ReplayAsset,
)
from backend.core.storage import delete_account, delete_asset, private_path
from tests.test_backend import FakeStorage, reviewed_annotation

pytestmark = pytest.mark.django_db


@pytest.fixture
def env(django_user_model, settings, tmp_path):
    settings.DEBUG = True
    settings.LOCAL_OPERATOR_UPLOADS = True
    # Synthetic account setup only; the production password configuration is unchanged.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.PRIVATE_STORAGE_ROOT = tmp_path / "media"
    owner, one, two, foreign = [
        django_user_model.objects.create_user(name, password="test-knowledge", is_staff=True)
        for name in ("author", "review-one", "review-two", "foreign")
    ]
    game = Game.objects.create(key="tekken8")
    build = GameBuild.objects.create(key="fixture", game=game, platform="synthetic")
    content = b"synthetic-review-source"
    asset = ReplayAsset.objects.create(
        owner=owner,
        storage_key=f"{owner.pk}/{uuid4()}/source.mp4",
        bytes=len(content),
        source_sha256=hashlib.sha256(content).hexdigest(),
        metadata={"game_build": "fixture", "platform": "synthetic", "dataset_kind": "synthetic"},
        retain_until=timezone.now() + timedelta(days=20),
    )
    path = private_path(asset.storage_key)
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    AnalysisRun.objects.create(
        owner=owner,
        asset=asset,
        request_key="media",
        status="REVIEW_REQUIRED",
        result={"source": {"source_sha256": asset.source_sha256, "duration_seconds": 60}},
    )
    return SimpleNamespace(owner=owner, one=one, two=two, foreign=foreign, build=build, asset=asset)


def candidate(env, kind="build", key=None, payload=None, **kwargs):
    build_key = kwargs.pop("build_key", env.build.pk)
    body = (
        {
            "game_build": "fixture",
            "platform": "synthetic",
            "overlays": ["build", "frames", "inputs"],
        }
        if payload is None
        else payload
    )
    return knowledge.propose(
        env.owner,
        key=key or f"test/{kind}/{uuid4()}",
        kind=kind,
        build_key=build_key,
        dataset_kind=kwargs.pop("dataset_kind", "synthetic"),
        payload=body,
        provenance={
            "reference": "owned-fixture/1",
            "rights": "OWNED_RECORDING",
            "share_with_reviewers": True,
            "publish_game_facts": True,
        },
        asset_ids=[env.asset.pk],
        reviewer_one=kwargs.pop("reviewer_one", env.one.pk),
        reviewer_two=env.two.pk,
        request_id=kwargs.pop("request_id", uuid4()),
        **kwargs,
    )


def approve(env, proposal, *, decision="APPROVE"):
    for user in (env.one, env.two):
        knowledge.review(
            user,
            proposal.pk,
            proposal_hash=proposal.content_hash,
            decision=decision,
            note="Independently reviewed this synthetic fixture",
            confirm_reviewed=True,
            request_id=uuid4(),
        )


def release(env, kind, key, payload):
    proposal = candidate(env, kind, key, payload)
    approve(env, proposal)
    return knowledge.publish(env.owner, proposal.pk)


def bundle(env):
    release(
        env,
        "build",
        "test/build/1",
        {
            "game_build": "fixture",
            "platform": "synthetic",
            "overlays": ["build", "inputs", "frames"],
        },
    )
    common = {"game_build": "fixture", "build_definition": "test/build/1"}
    release(
        env,
        "move",
        "test/move/1",
        {
            **common,
            "move": "jin.uf4",
            "startup_frames": 17,
            "on_block_frames": -13,
            "reach_test": "synthetic-reach/1",
            "timing_test": "synthetic-timing/1",
        },
    )
    release(
        env,
        "situation",
        "test/situation/1",
        {
            **common,
            "supported_semantics": knowledge.SEMANTICS,
            "trigger": "opponent-jin-uf4-blocked",
            "required_observations": list(REQUIRED),
            "unknown_rules": ["unobservable"],
            "exclusions": ["wall", "axis", "resources", "stance"],
        },
    )
    release(
        env,
        "metric",
        "test/metric/1",
        {
            **common,
            "supported_semantics": knowledge.SEMANTICS,
            "numerator": "eligible-successes",
            "denominator": "eligible-known-outcomes",
            "unknown_policy": "exclude-and-report",
        },
    )
    definition = release(
        env,
        "knowledge",
        "test/knowledge/1",
        {
            **common,
            "situation_definition": "test/situation/1",
            "metric_definition": "test/metric/1",
            "move_versions": ["test/move/1"],
        },
    )
    drill = release(
        env,
        "drill",
        "test/drill/1",
        {
            **common,
            "situation_definition": "test/situation/1",
            "metric_definition": "test/metric/1",
            "knowledge_revision": definition.pk,
            "title": "Synthetic fixture only",
            "repetitions": 40,
            "setup": {"standing": True},
            "native_practice": {"candidate": "fixture-only"},
        },
    )
    return definition, drill


def capture(env, key="test/knowledge/1"):
    match = Match.objects.create(
        owner=env.owner,
        game=env.build.game,
        asset=env.asset,
        context="jin/jin",
        game_build="fixture",
        knowledge_revision=key,
        session_id="test-session",
        played_at=timezone.now() - timedelta(days=10),
        chronology_verified=True,
        mode="ranked",
        dataset_kind="synthetic",
    )
    run = AnalysisRun.objects.create(
        owner=env.owner,
        asset=env.asset,
        request_key=uuid4().hex,
        status="REVIEW_REQUIRED",
        result={"source": {"source_sha256": env.asset.source_sha256, "duration_seconds": 60}},
    )
    annotation = reviewed_annotation()
    annotation.update(
        source_sha256=env.asset.source_sha256,
        session_id=match.session_id,
        played_at=match.played_at.isoformat(),
    )
    annotation["examples"][0]["situation"] = "test/situation/1"
    publish_annotations(env.owner, run.pk, match.pk, annotation)
    return match, run, annotation


def mapping(env, disposition="REANALYSIS_REQUIRED", target_build="fixture"):
    body = copy.deepcopy(DefinitionVersion.objects.get(pk="test/knowledge/1").payload)
    body.pop("synthetic_only")
    target = release(env, "knowledge", "test/knowledge/2", body)
    return release(
        env,
        "compatibility",
        "test/compatibility/1",
        {
            "game_build": target_build,
            "build_definition": "test/build/1",
            "from_knowledge": "test/knowledge/1",
            "to_knowledge": target.pk,
            "disposition": disposition,
            "rationale": "synthetic-patch-review/1",
        },
    )


def test_independent_review_and_immutable_publication(env):
    draft = DefinitionVersion.objects.create(
        key="draft/build/1", kind="build", game_build=env.build, payload={"unverified": True}
    )
    with pytest.raises(ValidationError, match="new version"):
        candidate(env, key=draft.pk)
    proposal = candidate(env)
    with pytest.raises(ValidationError, match="Two independent"):
        knowledge.publish(env.owner, proposal.pk)
    with pytest.raises(PermissionDenied):
        knowledge.review(
            env.owner,
            proposal.pk,
            proposal_hash=proposal.content_hash,
            decision="APPROVE",
            note="Self-review",
            confirm_reviewed=True,
            request_id=uuid4(),
        )
    approve(env, proposal)
    definition = knowledge.publish(env.owner, proposal.pk)
    assert definition == knowledge.publish(env.owner, proposal.pk)
    assert definition.status == "APPROVED" and definition.payload["synthetic_only"]
    assert knowledge.effective(definition, "synthetic", env.owner.pk)
    assert not knowledge.effective(definition, "real", env.owner.pk)
    assert not knowledge.effective(definition, "synthetic", env.foreign.pk)
    env.build.refresh_from_db()
    draft.refresh_from_db()
    assert not env.build.verified and draft.status == "DRAFT"
    assert not GameplayEvent.objects.exists()
    with pytest.raises(ValidationError):
        definition.save()


def test_unverified_build_registration_and_session_csrf(env):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(env.owner)
    body = {"version": "synthetic-patch-2", "platform": "synthetic"}
    assert client.post("/api/knowledge/builds", body, format="json").status_code == 403
    csrf = client.get("/api/session").json()["csrf"]
    response = client.post("/api/knowledge/builds", body, format="json", HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code == 201 and response.json()["verified"] is False
    assert (
        client.post("/api/knowledge/builds", body, format="json", HTTP_X_CSRFTOKEN=csrf).json()
        == response.json()
    )
    assert not KnowledgeProposal.objects.exists()


def test_payload_semantics_and_tampering_fail_closed(env):
    proposal = candidate(env)
    KnowledgeProposal.objects.filter(pk=proposal.pk).update(payload={"tampered": True})
    with pytest.raises(PermissionDenied):
        knowledge.review(
            env.one,
            proposal.pk,
            proposal_hash=proposal.content_hash,
            decision="APPROVE",
            note="Synthetic",
            confirm_reviewed=True,
            request_id=uuid4(),
        )
    with pytest.raises(ValidationError):
        candidate(
            env, payload={"game_build": "fixture", "platform": "wrong", "overlays": ["build"]}
        )
    bundle(env)
    definition = DefinitionVersion.objects.get(pk="test/metric/1")
    DefinitionVersion.objects.filter(pk=definition.pk).update(
        payload={**definition.payload, "unknown_policy": "discard-quietly"}
    )
    definition.refresh_from_db()
    assert not knowledge.effective(definition, "synthetic", env.owner.pk)
    assert not knowledge.effective(
        DefinitionVersion.objects.get(pk="test/drill/1"), "synthetic", env.owner.pk
    )


def test_rejection_hash_and_idempotent_sealed_reviews(env):
    request = uuid4()
    proposal = candidate(env, key="test/build/1", request_id=request)
    assert candidate(env, key="test/build/1", request_id=request).pk == proposal.pk
    with pytest.raises(ValidationError, match="Request ID"):
        candidate(env, key="test/build/other", request_id=request)
    with pytest.raises(ValidationError):
        knowledge.review(
            env.one,
            proposal.pk,
            proposal_hash="0" * 64,
            decision="APPROVE",
            note="Reviewed",
            confirm_reviewed=True,
            request_id=uuid4(),
        )
    review_id = uuid4()
    kwargs = dict(
        proposal_hash=proposal.content_hash,
        decision="REJECT",
        note="Insufficient source evidence",
        confirm_reviewed=True,
        request_id=review_id,
    )
    first = knowledge.review(env.one, proposal.pk, **kwargs)
    assert knowledge.review(env.one, proposal.pk, **kwargs).pk == first.pk
    with pytest.raises(ValidationError, match="sealed"):
        knowledge.review(env.one, proposal.pk, **{**kwargs, "decision": "APPROVE"})
    with pytest.raises(ValidationError):
        knowledge.publish(env.owner, proposal.pk)


@pytest.mark.parametrize(
    "case",
    [
        "author",
        "same-reviewer",
        "foreign-source",
        "unfinished",
        "unvalidated",
        "wrong-platform",
        "wrong-scope",
        "expired",
        "withdrawn-reviewer",
    ],
)
def test_proposal_evidence_and_independence_guards(env, case):
    kwargs = {}
    if case == "author":
        kwargs["reviewer_one"] = env.owner.pk
    elif case == "same-reviewer":
        kwargs["reviewer_one"] = env.two.pk
    elif case == "foreign-source":
        ReplayAsset.objects.filter(pk=env.asset.pk).update(owner=env.foreign)
    elif case == "unfinished":
        from backend.core.models import UploadSession

        UploadSession.objects.create(
            owner=env.owner,
            asset=env.asset,
            request_id=uuid4(),
            expires_at=timezone.now() + timedelta(hours=1),
            state="VERIFYING",
        )
    elif case == "unvalidated":
        AnalysisRun.objects.all().delete()
    elif case == "wrong-platform":
        ReplayAsset.objects.filter(pk=env.asset.pk).update(
            metadata={**env.asset.metadata, "platform": "steam"}
        )
    elif case == "wrong-scope":
        kwargs["dataset_kind"] = "real"
    elif case == "expired":
        ReplayAsset.objects.filter(pk=env.asset.pk).update(
            retain_until=timezone.now() - timedelta(seconds=1)
        )
    elif case == "withdrawn-reviewer":
        Profile.objects.create(user=env.one, processing_withdrawn_at=timezone.now())
    with pytest.raises((ValidationError, PermissionDenied)):
        candidate(env, **kwargs)
    assert not KnowledgeProposal.objects.exists()


def test_real_publication_is_separately_gated(env):
    ReplayAsset.objects.filter(pk=env.asset.pk).update(
        metadata={**env.asset.metadata, "dataset_kind": "real"}
    )
    proposal = candidate(env, dataset_kind="real")
    approve(env, proposal)
    with pytest.raises(ValidationError, match="Real publication"):
        knowledge.publish(env.owner, proposal.pk)
    assert not DefinitionVersion.objects.exists()


def test_full_synthetic_release_reanalysis_and_frozen_history(env):
    _, drill = bundle(env)
    match, original, annotation = capture(env)
    old_event = GameplayEvent.objects.get(run=original)
    old_hash = as_opportunity(old_event).content_hash
    assignment = create_assignment(env.owner, drill.pk)
    plan = create_plan(
        env.owner,
        assignment.pk,
        [old_event.pk],
        (match.played_at + timedelta(hours=1)).isoformat(),
        (timezone.now() + timedelta(days=1)).isoformat(),
        (timezone.now() + timedelta(days=10)).isoformat(),
    )
    plan.refresh_from_db()
    frozen = copy.deepcopy(plan.specification)
    definition = mapping(env)
    preview = knowledge.impact(env.owner, definition.pk)
    assert preview["matches"][0]["state"] == "READY"
    request = uuid4()
    result = knowledge.reanalyse(
        env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=request
    )
    assert (
        knowledge.reanalyse(
            env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=request
        ).pk
        == result.pk
    )
    assert result.run.status == "QUEUED"
    assert AnalysisPublication.objects.get(match=match).run == original
    assert GameplayEvent.objects.count() == 1
    with pytest.raises(ValidationError, match="active analysis"):
        knowledge.reanalyse(
            env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=uuid4()
        )
    claimed = claim_run(result.run_id)
    assert claimed is not None
    assert finish_run(
        result.run_id,
        claimed,
        {
            "status": "REVIEW_REQUIRED",
            "source": {"source_sha256": env.asset.source_sha256, "duration_seconds": 60},
        },
    )
    publish_annotations(env.owner, result.run_id, match.pk, annotation)
    publish_annotations(env.owner, result.run_id, match.pk, annotation)
    new = GameplayEvent.objects.get(run=result.run)
    assert as_opportunity(new).knowledge_revision == "test/knowledge/2"
    assert as_opportunity(old_event).content_hash == old_hash
    match.refresh_from_db()
    plan.refresh_from_db()
    assert match.game_build == "fixture" and match.knowledge_revision == "test/knowledge/1"
    assert plan.specification == frozen
    assert AnalysisPublication.objects.get(match=match).revision == 2
    assert MatchContribution.objects.get(match=match).run == result.run


@pytest.mark.parametrize("disposition", ["SAME_MEASUREMENT", "INCOMPATIBLE"])
def test_compatibility_does_not_rewrite_capture_or_queue_without_review(env, disposition):
    bundle(env)
    match, _, _ = capture(env)
    definition = mapping(env, disposition)
    assert knowledge.impact(env.owner, definition.pk)["matches"][0]["state"] == disposition
    with pytest.raises(ValidationError, match=disposition):
        knowledge.reanalyse(
            env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=uuid4()
        )
    assert not KnowledgeReanalysis.objects.exists()


def test_cross_build_capture_requires_new_baseline(env):
    bundle(env)
    match, _, _ = capture(env)
    definition = mapping(env)
    Match.objects.filter(pk=match.pk).update(game_build="older-capture-build")
    assert (
        knowledge.impact(env.owner, definition.pk)["matches"][0]["state"]
        == "CAPTURE_BUILD_INCOMPATIBLE"
    )
    with pytest.raises(ValidationError, match="CAPTURE_BUILD_INCOMPATIBLE"):
        knowledge.reanalyse(
            env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=uuid4()
        )
    assert not KnowledgeReanalysis.objects.exists()


def test_retirement_preserves_history_withdrawal_invalidates_and_cancels(env):
    _, drill = bundle(env)
    match, original, _ = capture(env)
    definition = mapping(env)
    old = GameplayEvent.objects.get(run=original)
    before = as_opportunity(old).content_hash
    result = knowledge.reanalyse(
        env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=uuid4()
    )
    proposal = KnowledgeProposal.objects.get(published_id="test/knowledge/1")
    knowledge.lifecycle(env.owner, proposal.pk, "RETIRE")
    assert not knowledge.effective(proposal.published, "synthetic", env.owner.pk)
    assert knowledge.effective(proposal.published, "synthetic", env.owner.pk, historical=True)
    assert as_opportunity(old).content_hash == before
    with pytest.raises(ValidationError):
        create_assignment(env.owner, drill.pk)
    knowledge.lifecycle(env.owner, proposal.pk, "WITHDRAW")
    assert as_opportunity(old).deleted
    assert not MatchContribution.objects.exists()
    assert not GameplayEvent.objects.filter(deleted_at=None).exists()
    result.run.refresh_from_db()
    assert result.run.status == "CANCELLED" and result.run.fence > 0
    assert KnowledgeProposal.objects.get(published=definition).state == "WITHDRAWN"


@pytest.mark.parametrize("action", ["source", "consent", "reviewer-delete", "restore"])
def test_privacy_revokes_shared_sources_notes_and_releases(env, action):
    bundle(env)
    if action == "source":
        delete_asset(env.owner, env.asset.pk, storage=FakeStorage())
    elif action == "consent":
        record_consent(env.one, "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
    elif action == "reviewer-delete":
        delete_account(env.two, storage=FakeStorage())
    else:
        with transaction.atomic():
            knowledge.restore_revoke()
    assert not KnowledgeProposal.objects.exclude(state="WITHDRAWN").exists()
    assert not KnowledgeProposal.objects.exclude(payload={}, provenance={}).exists()
    assert not KnowledgeReview.objects.exclude(note="").exists()
    assert not KnowledgeProposal.objects.filter(sources__isnull=False).exists()
    assert not knowledge.effective(
        DefinitionVersion.objects.get(pk="test/drill/1"), "synthetic", env.owner.pk
    )


def test_migration_reverse_refuses_governed_history(env):
    from importlib import import_module

    from django.apps import apps

    candidate(env)
    migration = import_module("backend.core.migrations.0017_knowledge_governance")
    with pytest.raises(ValueError, match="version pins"):
        migration.guard_reverse(apps, SimpleNamespace(connection=connection))


def test_private_api_blind_review_media_and_export(env):
    proposal = candidate(env)
    client = APIClient()
    assert client.get("/api/knowledge").status_code == 403
    client.force_authenticate(env.foreign)
    assert client.get("/api/knowledge").json()["proposals"] == []
    assert client.get(f"/api/knowledge/{proposal.pk}/media/{env.asset.pk}").status_code == 403
    kwargs = dict(
        proposal_hash=proposal.content_hash,
        decision="APPROVE",
        note="Private first reviewer note",
        confirm_reviewed=True,
        request_id=uuid4(),
    )
    knowledge.review(env.one, proposal.pk, **kwargs)
    client.force_authenticate(env.two)
    body = client.get("/api/knowledge").json()
    assert body["proposals"][0]["reviews"] == [] and body["sources"] == []
    assert "Private first reviewer note" not in str(body)
    media = client.get(f"/api/knowledge/{proposal.pk}/media/{env.asset.pk}", HTTP_RANGE="bytes=0-3")
    assert media.status_code == 206 and b"".join(media.streaming_content) == b"synt"
    assert media["Cache-Control"] == "private, no-store"
    export = client.get("/api/account/export").json()
    assert export["knowledge_proposals"] == [] and export["knowledge_own_reviews"] == []
    assert "Private first reviewer note" not in str(export)
    client.force_authenticate(env.one)
    own = client.get("/api/account/export").json()
    assert own["knowledge_own_reviews"][0]["note"] == kwargs["note"]


def test_streaming_grant_rechecks_withdrawal(env, monkeypatch):
    proposal = candidate(env)
    client = APIClient()
    client.force_authenticate(env.one)
    # Force the next chunk to perform authorization again, after the response was opened.
    clock = [100.0]
    monkeypatch.setattr("backend.core.private_media.time.monotonic", lambda: clock[0])
    path = private_path(env.asset.storage_key)
    path.write_bytes(b"x" * 140000)
    response = client.get(f"/api/knowledge/{proposal.pk}/media/{env.asset.pk}")
    stream = iter(response.streaming_content)
    assert len(next(stream)) == 65536
    knowledge.lifecycle(env.owner, proposal.pk, "WITHDRAW")
    clock[0] += 1
    with pytest.raises(ValueError, match="GRANT_REVOKED"):
        next(stream)
    response.close()


def test_reanalysis_rejects_stale_metadata_and_foreign_matches(env):
    bundle(env)
    match, _, annotation = capture(env)
    definition = mapping(env)
    with pytest.raises((Match.DoesNotExist, ValidationError)):
        knowledge.reanalyse(
            env.foreign, match_id=match.pk, mapping_key=definition.pk, request_id=uuid4()
        )
    result = knowledge.reanalyse(
        env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=uuid4()
    )
    AnalysisRun.objects.filter(pk=result.run_id).update(
        status="REVIEW_REQUIRED",
        result={"source": {"source_sha256": env.asset.source_sha256, "duration_seconds": 60}},
    )
    Match.objects.filter(pk=match.pk).update(metadata_revision=F("metadata_revision") + 1)
    with pytest.raises(ValidationError, match="changed"):
        publish_annotations(env.owner, result.run_id, match.pk, annotation)
    assert GameplayEvent.objects.count() == 1


@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_concurrent_publish_is_single_immutable_release(env):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    proposal = candidate(env)
    approve(env, proposal)

    def worker():
        close_old_connections()
        try:
            return knowledge.publish(env.owner, proposal.pk).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _: worker(), range(2)))
    assert result == [proposal.key] * 2
    assert DefinitionVersion.objects.count() == 1


@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_review_races_with_source_withdrawal(env):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    proposal = candidate(env)

    def worker(action):
        close_old_connections()
        try:
            if action == "review":
                try:
                    knowledge.review(
                        env.one,
                        proposal.pk,
                        proposal_hash=proposal.content_hash,
                        decision="APPROVE",
                        note="Synthetic source reviewed",
                        confirm_reviewed=True,
                        request_id=uuid4(),
                    )
                except PermissionDenied:
                    pass
            else:
                delete_asset(env.owner, env.asset.pk, storage=FakeStorage())
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(worker, ["review", "delete"]))
    proposal.refresh_from_db()
    assert proposal.state == "WITHDRAWN" and proposal.payload == {}
    assert not proposal.sources.exists()
    assert not proposal.reviews.exclude(note="").exists()


@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_worker_claim_and_foreign_reviewer_revocation_share_lock_order(env, monkeypatch):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    bundle(env)
    match, _, _ = capture(env)
    definition = mapping(env)
    result = knowledge.reanalyse(
        env.owner, match_id=match.pk, mapping_key=definition.pk, request_id=uuid4()
    )
    at_capacity, revoking = Event(), Event()
    from backend.core import jobs
    from backend.core.security import capacity_lock

    def worker_capacity():
        at_capacity.set()
        assert revoking.wait(10)
        capacity_lock()

    def revocation_capacity():
        capacity_lock()
        revoking.set()
        assert at_capacity.wait(10)

    monkeypatch.setattr(jobs, "capacity_lock", worker_capacity)
    monkeypatch.setattr(knowledge, "capacity_lock", revocation_capacity)

    def work(action):
        close_old_connections()
        try:
            if action == "claim":
                return jobs.claim_run(result.run_id)
            assert at_capacity.wait(10)
            record_consent(env.one, "PROCESSING", "WITHDRAW", POLICY_VERSION, uuid4())
            return None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(work, ["claim", "revoke"])) == [None, None]
    result.run.refresh_from_db()
    assert result.run.status == "CANCELLED"
    assert result.run.rundispatch.status == "CANCELLED"


def test_priority_assessment_requires_exact_independent_drill_release(env):
    _, drill = bundle(env)
    payload = {k: v for k, v in drill.payload.items() if k != "synthetic_only"}
    payload["priority_assessment"] = {
        "version": "priority-assessment/1",
        "value": 0.7,
        "trainability": 0.8,
        "rationale": "Synthetic relative assessment; no actual player benefit claim.",
    }
    proposal = candidate(env, "drill", "test/priority-drill/1", payload)
    with pytest.raises(ValidationError, match="Two independent"):
        knowledge.publish(env.owner, proposal.pk)
    approve(env, proposal)
    published = knowledge.publish(env.owner, proposal.pk)
    assert knowledge.effective(published, "synthetic", env.owner.pk)
    assert published.payload["priority_assessment"] == payload["priority_assessment"]
    bad = copy.deepcopy(payload)
    bad["priority_assessment"]["value"] = True
    with pytest.raises(ValueError, match="finite fractions"):
        candidate(env, "drill", "test/invalid-priority/1", bad)
    assert not knowledge.effective(published, "synthetic", env.foreign.pk)
    knowledge.revoke(proposal, "ASSESSMENT_WITHDRAWN")
    assert not knowledge.effective(published, "synthetic", env.owner.pk)


def test_m11_workflow_requires_new_version_and_both_independent_reviews(env):
    from tests.test_practice_workflow import WORKFLOW

    _, old = bundle(env)
    payload = {**old.payload, "practice_workflow": WORKFLOW}
    payload.pop("synthetic_only", None)
    proposal = candidate(env, "drill", "test/drill/2", payload)
    with pytest.raises(ValidationError):
        knowledge.publish(env.owner, proposal.pk)
    approve(env, proposal)
    item = knowledge.publish(env.owner, proposal.pk)
    assert item.payload["practice_workflow"] == WORKFLOW
    old.refresh_from_db()
    assert "practice_workflow" not in old.payload and item.content_hash != old.content_hash
    bad = copy.deepcopy(payload)
    bad["practice_workflow"]["progression"]["minimum_known"] = 1
    with pytest.raises((ValidationError, ValueError)):
        candidate(env, "drill", "test/drill/3", bad)
