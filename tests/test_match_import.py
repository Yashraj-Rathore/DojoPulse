from dataclasses import replace
from datetime import timedelta
from importlib import import_module

import pytest
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from backend.core.evidence import as_opportunity
from backend.core.match_ingestion import (
    claim_local_sync,
    commit_local_page,
    fail_local_sync,
    link_local_identity,
    mark_replay_unavailable,
    register_upload_source,
    start_local_sync,
)
from backend.core.models import (
    AnalysisRun,
    GameplayEvent,
    Match,
    MatchContribution,
    MatchSourceRecord,
    MatchSync,
    PlayerGameIdentity,
    Recommendation,
    ReplayAsset,
    ReplaySource,
)
from backend.core.storage import delete_account, delete_metadata_match
from ingestion.contracts import ExternalId, Operation, ProviderClass
from ingestion.synthetic import END, PLAYER, START, SyntheticProvider
from tests.test_backend import FakeStorage

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user("import-owner", is_staff=True)


def setup_sync(owner, provider="synthetic-a"):
    adapter = SyntheticProvider(provider)
    identity = link_local_identity(
        owner,
        "tekken8",
        adapter.resolve_player(PLAYER.value, Operation.RESOLVE_ID),
        PLAYER,
        processing_consent=True,
    )
    job = start_local_sync(owner, identity.pk, adapter.key, START, END)
    token = claim_local_sync(owner, job.pk)
    return adapter, identity, job, token


def import_one(owner, provider="synthetic-a"):
    adapter, identity, job, token = setup_sync(owner, provider)
    page = replace(adapter.discover_matches(PLAYER, None, START, END), next_cursor=None)
    assert commit_local_page(owner, job.pk, token, None, page)
    match = Match.objects.get(owner=owner, source_records__provider=provider)
    return adapter, identity, job, page, match


def recommit(owner, identity, job, page):
    start_local_sync(owner, identity.pk, job.provider, START, END)
    token = claim_local_sync(owner, job.pk)
    return commit_local_page(owner, job.pk, token, None, page)


def corrected(page, **fields):
    item = page.matches[0]
    return replace(
        page,
        matches=(
            replace(
                item,
                **fields,
                provenance=replace(
                    item.provenance, retrieved_at=END + timedelta(hours=1), record_digest="b" * 64
                ),
            ),
        ),
    )


def test_metadata_import_has_no_invented_evidence_or_context(owner):
    _, identity, _, _, match = import_one(owner)
    assert identity.state == "CLAIMED" and not identity.verification
    assert match.asset_id is None
    assert match.game_build is match.context is match.session_id is match.knowledge_revision is None
    assert match.mode == "unknown" and not match.chronology_verified
    assert match.winner_slot == 1
    assert match.participants.count() == 2
    assert all(p.character is None for p in match.participants.all())
    assert (
        ReplayAsset.objects.count()
        == AnalysisRun.objects.count()
        == GameplayEvent.objects.count()
        == 0
    )
    record = match.source_records.get()
    assert record.assertion["raw_game_version"] == "unmapped-999"
    assert record.policy_version == "synthetic-local/1"


def test_replayed_page_and_refreshed_timestamp_are_idempotent(owner):
    _, identity, job, page, match = import_one(owner)
    refreshed = replace(
        page,
        matches=(
            replace(
                page.matches[0],
                provenance=replace(
                    page.matches[0].provenance, retrieved_at=END + timedelta(days=1)
                ),
            ),
        ),
    )
    assert recommit(owner, identity, job, refreshed)
    assert Match.objects.count() == MatchSourceRecord.objects.count() == 1
    assert Match.objects.get().pk == match.pk


def test_two_providers_do_not_merge_coincident_ids(owner):
    first = import_one(owner, "synthetic-a")[-1]
    second = import_one(owner, "synthetic-b")[-1]
    assert first.pk != second.pk
    assert first.game_id == second.game_id and first.winner_slot == second.winner_slot
    assert PlayerGameIdentity.objects.count() == 1


def test_corrections_append_preserve_uuid_and_reject_old_snapshot(owner):
    _, identity, job, page, match = import_one(owner)
    assert recommit(owner, identity, job, corrected(page, winner_slot=2, raw_winner="2"))
    match.refresh_from_db()
    assert match.winner_slot == 2 and match.metadata_revision == 2
    assert list(
        match.source_records.order_by("revision").values_list("assertion__winner_slot", flat=True)
    ) == [1, 2]
    with pytest.raises(ValidationError, match="Out-of-order"):
        recommit(owner, identity, job, page)
    assert match.source_records.count() == 2
    with pytest.raises(ValidationError, match="immutable"):
        match.source_records.first().save()


def test_page_validation_rolls_back_earlier_rows_and_checkpoint(owner):
    adapter, _, job, token = setup_sync(owner)
    page = adapter.discover_matches(PLAYER, None, START, END)
    bad = replace(
        page.matches[0], game="wrong-game", external_id=ExternalId("synthetic:battle", "bad")
    )
    with pytest.raises(ValidationError):
        commit_local_page(owner, job.pk, token, None, replace(page, matches=(page.matches[0], bad)))
    job.refresh_from_db()
    assert job.checkpoint is None and job.coverage == []
    assert not Match.objects.exists() and not MatchSourceRecord.objects.exists()


def test_stale_worker_and_cursor_cannot_commit(owner):
    adapter, _, job, token = setup_sync(owner)
    page = adapter.discover_matches(PLAYER, None, START, END)
    assert not commit_local_page(owner, job.pk, token + 1, None, page)
    assert not commit_local_page(owner, job.pk, token, "wrong", page)
    MatchSync.objects.filter(pk=job.pk).update(lease_until=timezone.now() - timedelta(seconds=1))
    next_token = claim_local_sync(owner, job.pk)
    assert next_token == token + 1
    assert not commit_local_page(owner, job.pk, token, None, page)
    assert commit_local_page(owner, job.pk, next_token, None, page)
    job.refresh_from_db()
    assert job.checkpoint == "second"


def test_failed_acquisition_keeps_checkpoint_and_applies_retry_budget(owner):
    _, _, job, token = setup_sync(owner)
    assert fail_local_sync(owner, job.pk, token)
    job.refresh_from_db()
    assert job.checkpoint is None and job.coverage == []
    assert job.next_attempt_at > timezone.now() and claim_local_sync(owner, job.pk) is None
    MatchSync.objects.filter(pk=job.pk).update(attempts=4, next_attempt_at=None)
    token = claim_local_sync(owner, job.pk)
    assert fail_local_sync(owner, job.pk, token)
    assert claim_local_sync(owner, job.pk) is None


def test_partial_and_empty_pages_record_coverage(owner):
    adapter, _, job, token = setup_sync(owner)
    page = replace(
        adapter.discover_matches(PLAYER, None, START, END),
        matches=(),
        next_cursor=None,
        coverage="PARTIAL",
        gaps=("older history unavailable",),
        truncated=True,
    )
    assert commit_local_page(owner, job.pk, token, None, page)
    job.refresh_from_db()
    assert job.status == "COMPLETE" and job.coverage[0]["truncated"]
    assert job.coverage[0]["gaps"] and not Match.objects.exists()


def test_cross_owner_access_and_shared_public_identity(owner, django_user_model):
    _, identity, job, _, match = import_one(owner)
    other = django_user_model.objects.create_user("second-importer")
    with pytest.raises(ObjectDoesNotExist):
        start_local_sync(other, identity.pk, "synthetic-a", START, END)
    with pytest.raises(ObjectDoesNotExist):
        claim_local_sync(other, job.pk)
    with pytest.raises(ObjectDoesNotExist):
        delete_metadata_match(other, match.pk)
    other_match = import_one(other)[-1]
    assert other_match.pk != match.pk and PlayerGameIdentity.objects.count() == 2


def test_delete_revokes_identity_fences_late_work_and_removes_metadata(owner):
    _, identity, job, page, match = import_one(owner)
    start_local_sync(owner, identity.pk, job.provider, START, END)
    token = claim_local_sync(owner, job.pk)
    delete_metadata_match(owner, match.pk)
    delete_metadata_match(owner, match.pk)
    assert not MatchSourceRecord.objects.exists() and not match.participants.exists()
    job.refresh_from_db()
    assert job.status == "CANCELLED" and job.fence > token and job.coverage == []
    with pytest.raises(ValidationError, match="revoked"):
        commit_local_page(owner, job.pk, token, None, page)
    with pytest.raises(ValidationError, match="revoked"):
        setup_sync(owner)


def test_account_deletion_purges_identity_and_blocks_stale_owner_object(owner):
    import_one(owner)
    stale_owner = type(owner).objects.get(pk=owner.pk)
    delete_account(owner, FakeStorage())
    assert not PlayerGameIdentity.objects.exists() and not MatchSync.objects.exists()
    assert not MatchSourceRecord.objects.exists()
    assert Match.objects.get().deleted_at
    with pytest.raises(ValidationError, match="Deleted account"):
        setup_sync(stale_owner)


def test_expired_or_incompatible_replay_keeps_match_metadata(owner):
    _, _, _, _, match = import_one(owner)
    source = ReplaySource.objects.create(
        match=match,
        source_record=match.source_records.get(),
        provider="synthetic-a",
        access_class="USER_UPLOAD",
        representation="NATIVE_REPLAY",
    )
    mark_replay_unavailable(owner, source.pk, "EXPIRED")
    assert MatchSourceRecord.objects.count() == 1 and Match.objects.get().deleted_at is None
    mark_replay_unavailable(owner, source.pk, "VERSION_UNSUPPORTED")
    source.refresh_from_db()
    assert source.availability == "VERSION_UNSUPPORTED"
    assert not GameplayEvent.objects.exists()


def test_production_or_real_data_cannot_use_local_path(owner):
    adapter, identity, job, token = setup_sync(owner)
    with pytest.raises(ValidationError):
        start_local_sync(owner, identity.pk, "wavu", START, END)
    page = adapter.discover_matches(PLAYER, None, START, END)
    for provenance in (
        replace(page.matches[0].provenance, dataset_kind="real"),
        replace(page.matches[0].provenance, access_class=ProviderClass.REVERSE_ENGINEERED),
        replace(page.matches[0].provenance, provider="wavu"),
    ):
        with pytest.raises(ValidationError):
            commit_local_page(
                owner,
                job.pk,
                token,
                None,
                replace(page, matches=(replace(page.matches[0], provenance=provenance),)),
            )
    assert not Match.objects.exists()


def test_upload_backfill_preserves_match_and_existing_evidence_fields(owner):
    asset = ReplayAsset.objects.create(
        owner=owner, storage_key="fake/source.mp4", source_sha256="a" * 64
    )
    match = Match.objects.create(
        owner=owner,
        asset=asset,
        played_at=START,
        game_build="fixture",
        session_id="old-session",
        context="jin/jin",
        knowledge_revision="old/1",
    )
    before = Match.objects.values().get(pk=match.pk)
    migration = import_module("backend.core.migrations.0004_backfill_upload_sources")
    with connection.schema_editor(atomic=False) as editor:
        migration.backfill(apps, editor)
        migration.backfill(apps, editor)
    assert before == Match.objects.values().get(pk=match.pk)
    source = register_upload_source(match)
    assert ReplaySource.objects.count() == 1 and source.content_hash == "a" * 64
    assert source.provider == "user-video" and source.access_class == "USER_UPLOAD"


def test_metadata_only_event_is_rejected_explicitly(owner):
    match = import_one(owner)[-1]
    with pytest.raises(ValidationError, match="Metadata alone"):
        as_opportunity(GameplayEvent(match=match))


def test_synthetic_command_is_repeatable(owner):
    for _ in range(2):
        call_command(
            "import_synthetic_matches", operator=owner.username, confirm_synthetic_consent=True
        )
    assert Match.objects.count() == MatchSourceRecord.objects.count() == 2
    assert GameplayEvent.objects.count() == ReplayAsset.objects.count() == 0


def test_corrected_source_cannot_rewrite_reviewed_gameplay(owner):
    _, identity, job, page, match = import_one(owner)
    asset = ReplayAsset.objects.create(
        owner=owner, storage_key="fake/review.mp4", source_sha256="a" * 64
    )
    match.asset = asset
    match.context = "jin/jin"
    match.session_id = "reviewed-session"
    match.mode = "ranked"
    match.game_build = "reviewed-build"
    match.knowledge_revision = "reviewed-knowledge"
    match.save()
    run = AnalysisRun.objects.create(owner=owner, asset=asset, request_key="reviewed")
    event = GameplayEvent.objects.create(
        owner=owner,
        match=match,
        run=run,
        played_key="1",
        situation="s",
        metric="m",
        detector_version="review/1",
        start_us=0,
        end_us=100,
        eligibility="ELIGIBLE",
        outcome="SUCCESS",
        verified=True,
        evidence=["span/1"],
    )
    MatchContribution.objects.create(match=match, run=run, metric="m", summary={"numerator": 1})
    recommendation = Recommendation.objects.create(
        owner=owner, situation="s", metric="m", baseline_event_ids=[str(event.pk)], summary={}
    )
    before = GameplayEvent.objects.values().get(pk=event.pk)
    assert recommit(owner, identity, job, corrected(page, winner_slot=2, raw_winner="2"))
    match.refresh_from_db()
    recommendation.refresh_from_db()
    assert match.game_build == "reviewed-build" and match.winner_slot == 1
    assert match.metadata_state == "REVIEW_REQUIRED"
    assert before == GameplayEvent.objects.values().get(pk=event.pk)
    assert not MatchContribution.objects.exists() and recommendation.state == "INVALIDATED"
    event.refresh_from_db()
    assert as_opportunity(event).deleted


def test_local_identity_requires_explicit_selection_and_consent(owner):
    candidates = SyntheticProvider().resolve_player(PLAYER.value, Operation.RESOLVE_ID)
    with pytest.raises(ValidationError, match="consent"):
        link_local_identity(owner, "tekken8", candidates, PLAYER, processing_consent=False)
    with pytest.raises(ValueError, match="selection"):
        link_local_identity(owner, "tekken8", candidates, None, processing_consent=True)
    with pytest.raises(ValueError, match="ambiguous"):
        link_local_identity(
            owner, "tekken8", candidates + candidates, PLAYER, processing_consent=True
        )
    assert not PlayerGameIdentity.objects.exists()
