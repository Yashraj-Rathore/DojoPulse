"""Operator-only review import and atomic active-contribution replacement."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from analysis.annotations import validate_annotations
from analysis.contracts import Eligibility, Opportunity, Outcome, digest
from analysis.statistics import summarize
from backend.core.models import (
    AnalysisPublication,
    AnalysisRun,
    GameplayEvent,
    Match,
    MatchContribution,
    ReplaySource,
)
from backend.core.ownership import lock_owner


def as_opportunity(event):
    match = event.match
    if not event.run_id:
        raise ValidationError("Metadata alone is not gameplay evidence")
    asset = event.run.asset
    deleted = bool(
        event.deleted_at or match.deleted_at or asset.deleted_at or match.asset_id != asset.pk
    )
    deleted = deleted or match.metadata_state == "REVIEW_REQUIRED"
    return Opportunity(
        id=str(event.pk),
        played_key=f"{match.pk}:{event.played_key}",
        source_sha256=asset.source_sha256,
        session_id=match.session_id,
        played_at=match.played_at.isoformat(),
        mode=match.mode,
        situation=event.situation,
        metric=event.metric,
        game_build=match.game_build,
        knowledge_revision=match.knowledge_revision,
        detector_version=event.detector_version,
        context=match.context,
        eligibility=Eligibility.UNKNOWN if deleted else Eligibility(event.eligibility),
        outcome=Outcome.UNKNOWN if deleted else Outcome(event.outcome),
        evidence=tuple(event.evidence),
        verified=event.verified,
        dataset_kind=match.dataset_kind,
        deleted=deleted,
    )


@transaction.atomic
def publish_annotations(operator, run_id, match_id, annotation):
    if not operator.is_staff or not operator.is_active:
        raise PermissionDenied("Independent review import requires an operator")
    owner_id = AnalysisRun.objects.values_list("owner_id", flat=True).get(pk=run_id)
    locked_owner = lock_owner(owner_id)
    run = AnalysisRun.objects.select_for_update(of=("self",)).select_related("asset").get(pk=run_id)
    if run.status == "PROCESSING":
        raise ValidationError("Wait for processing to finish before review import")
    match = (
        Match.objects.select_for_update(of=("self",))
        .select_related("asset", "owner")
        .get(pk=match_id)
    )
    if match.owner_id != run.owner_id or match.asset_id != run.asset_id:
        raise ValidationError("Run/match ownership mismatch")
    if (
        run.asset.metadata.get("attachment")
        and not ReplaySource.objects.filter(
            match=match, asset=run.asset, attribution_state="APPROVED"
        ).exists()
    ):
        raise ValidationError("Recording attribution must be reviewed before gameplay publication")
    if match.metadata_state == "REVIEW_REQUIRED":
        raise ValidationError("Resolve metadata correction before publishing gameplay evidence")
    if (
        run.asset.deleted_at
        or match.deleted_at
        or not locked_owner.is_active
        or run.status == "CANCELLED"
    ):
        raise ValidationError("Deleted/cancelled evidence cannot publish")
    validate_annotations(annotation, run.asset.source_sha256)
    if (
        annotation["game_build"] != match.game_build
        or annotation["session_id"] != match.session_id
        or annotation["source_kind"] != match.mode
        or annotation["dataset_kind"] != match.dataset_kind
    ):
        raise ValidationError("Annotation/match metadata mismatch")
    from analysis.contracts import aware_time

    if aware_time(annotation["played_at"]) != match.played_at:
        raise ValidationError("Played time differs")
    publication = AnalysisPublication.objects.filter(match=match).first()
    if (
        AnalysisPublication.objects.filter(
            match__owner=match.owner,
            match__asset__source_sha256=run.asset.source_sha256,
            match__deleted_at__isnull=True,
        )
        .exclude(match=match)
        .exists()
    ):
        raise ValidationError("Exact duplicate capture already contributes to this owner")
    if publication and publication.run_id == run.pk:
        if run.result.get("annotation_hash") != digest(annotation):
            raise ValidationError("Published run differs; create a new analysis revision")
        return publication
    if GameplayEvent.objects.filter(run=run, match=match).exists():
        raise ValidationError("Run already contains unpublished facts; use a new run")
    if publication and publication.run.created_at > run.created_at:
        raise ValidationError("Older analysis cannot replace a newer publication")
    duration = run.result.get("source", {}).get("duration_seconds")
    if duration is None:
        raise ValidationError("Validated source duration required")
    for item in annotation["examples"]:
        if item["end_us"] > duration * 1_000_000:
            raise ValidationError("Evidence outside source")
        GameplayEvent.objects.create(
            owner=match.owner,
            run=run,
            match=match,
            played_key=item["id"],
            situation=item["situation"],
            metric="punish-success/v1",
            detector_version="human-adjudication/1",
            start_us=item["start_us"],
            end_us=item["end_us"],
            eligibility=item["eligibility"],
            outcome=item["outcome"],
            verified=True,
            evidence=item["evidence"],
            review={
                "reviews": item["reviews"],
                "adjudication": item["adjudication"],
                "conditions": item["conditions"],
                "imported_by": operator.pk,
            },
        )
    events = list(GameplayEvent.objects.filter(run=run, match=match).select_related("match__asset"))
    stats = summarize([as_opportunity(e) for e in events])
    MatchContribution.objects.update_or_create(
        match=match, metric="punish-success/v1", defaults={"run": run, "summary": stats}
    )
    if publication:
        publication.run = run
        publication.revision += 1
        publication.save()
    else:
        publication = AnalysisPublication.objects.create(match=match, run=run)
    run.status = "PARTIAL"  # reviewed target only, never claim complete video understanding
    run.result["annotation_hash"] = digest(annotation)
    run.save(update_fields=["status", "result"])
    return publication
