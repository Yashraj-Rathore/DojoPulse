"""M08 collections reuse consented pilot review; all grants remain revocable."""

import hashlib
import hmac
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from analysis.contracts import digest
from analysis.datasets import CATEGORIES, quality, validate_snapshot
from backend.core import knowledge, pilots
from backend.core.models import (
    DatasetCollection,
    DatasetPartition,
    DatasetSnapshot,
    DatasetStudy,
    DefinitionVersion,
    KnowledgeProposal,
    Match,
    PilotCapture,
    PilotEnrollment,
)

SAMPLING = {
    "version": "bounded-jin/1",
    "categories": list(CATEGORIES),
    "splits": ["development", "validation", "held-out"],
    "timing_tolerance_us": 16667,
    "minimum_per_category_per_split": 1,
    "interpretation": "Local coverage checklist, not a scientific sample-size approval.",
}
CONSENT = " This dataset pins an exact reviewed build and measurement. Keyed player/session/source split guards remain through collection closure to prevent leakage after withdrawal; labels, manifests and source grants are erased or invalidated. Dataset export does not include model-training permission."


def study_dataset(study):
    link = DatasetStudy.objects.select_related("dataset__knowledge").filter(study=study).first()
    return link.dataset if link else None


def measurement_for(owner, key, scope):
    definition = knowledge.require_definition(key, scope, owner.pk, kind="knowledge")
    if not KnowledgeProposal.objects.filter(published=definition, owner=owner).exists():
        raise ValidationError("M08 requires a governed M07 release, not a legacy fixture")
    payload = definition.payload
    refs = {
        "knowledge": definition.pk,
        "build": payload["build_definition"],
        "situation": payload["situation_definition"],
        "metric": payload["metric_definition"],
        **{f"move-{i}": k for i, k in enumerate(payload["move_versions"])},
    }
    definitions = {
        name: knowledge.require_definition(key, scope, owner.pk) for name, key in refs.items()
    }
    return {
        "knowledge": definition.pk,
        "situation": refs["situation"],
        "metric": refs["metric"],
        "game_build": payload["game_build"],
        "platform": definition.game_build.platform,
        "definitions": {
            name: {"key": d.pk, "hash": d.content_hash} for name, d in definitions.items()
        },
    }


def live_measurement(dataset, *, historical=False):
    if dataset.deleted_at or dataset.state == "CLOSED":
        return False
    for pin in dataset.measurement.get("definitions", {}).values():
        definition = DefinitionVersion.objects.filter(pk=pin["key"]).first()
        if (
            not definition
            or definition.content_hash != pin["hash"]
            or not knowledge.effective(
                definition, dataset.dataset_kind, dataset.owner_id, historical=historical
            )
        ):
            return False
    return bool(dataset.measurement.get("definitions"))


def collection_for(user, dataset_id, *, require_live=True):
    current = knowledge.actor(user)
    row = DatasetCollection.objects.select_for_update().get(
        pk=dataset_id, owner=current, deleted_at=None
    )
    if require_live and not live_measurement(row, historical=row.state == "FROZEN"):
        invalidate(row.pk, "MEASUREMENT_UNAVAILABLE")
        raise ValidationError("Pinned measurement is withdrawn, expired or unavailable")
    return current, row


@transaction.atomic
def create(user, title, dataset_kind, knowledge_key, request_id):
    owner = knowledge.actor(user)
    prior = DatasetCollection.objects.filter(owner=owner, request_id=request_id).first()
    if prior:
        if (prior.title, prior.dataset_kind, prior.knowledge_id) != (
            title,
            dataset_kind,
            knowledge_key,
        ) or prior.deleted_at:
            raise ValidationError("Dataset request ID already used")
        return prior
    if dataset_kind not in {"synthetic", "real"} or (
        dataset_kind == "real" and not settings.PILOT_REAL_DATA_APPROVED
    ):
        raise ValidationError("Real dataset intake requires explicit protocol/rights review")
    if DatasetCollection.objects.filter(owner=owner, deleted_at=None).count() >= 20:
        raise ValidationError("Local collection capacity reached")
    measurement = measurement_for(owner, knowledge_key, dataset_kind)
    return DatasetCollection.objects.create(
        owner=owner,
        title=title,
        dataset_kind=dataset_kind,
        knowledge_id=knowledge_key,
        measurement=measurement,
        sampling=SAMPLING,
        request_id=request_id,
    )


@transaction.atomic
def new_study(user, dataset_id, title, request_id):
    owner, dataset = collection_for(user, dataset_id)
    if dataset.state != "COLLECTING":
        raise ValidationError("Dataset inputs are frozen")
    prior = DatasetStudy.objects.filter(dataset=dataset, study__request_id=request_id).first()
    if prior:
        if prior.study.title != title:
            raise ValidationError("Study request ID already used")
        return prior.study
    if dataset.studies.count() >= 10:
        raise ValidationError("Local dataset study capacity reached")
    study = pilots.create_study(owner, title, dataset.dataset_kind, request_id, dataset=dataset)
    return study


def token(dataset, kind, value):
    material = json.dumps([str(dataset.pk), kind, value], separators=(",", ":"))
    return hmac.new(
        settings.DATA_SUPPRESSION_KEY.encode(), material.encode(), hashlib.sha256
    ).hexdigest()


def reserve(dataset, kind, value, split, *, binding=""):
    keyed = token(dataset, kind, value)
    row, _ = DatasetPartition.objects.get_or_create(
        dataset=dataset, kind=kind, token=keyed, defaults={"split": split, "binding": binding}
    )
    if row.split != split or row.binding != binding:
        raise ValidationError(f"Dataset-wide {kind.lower()} leakage: original split is immutable")
    return keyed


def check_split(study, member, split):
    dataset = study_dataset(study)
    if dataset:
        other = PilotEnrollment.objects.filter(
            study__datasetstudy__dataset=dataset, owner=member.owner, role="PARTICIPANT"
        ).exclude(pk=member.pk)
        if other.filter(pilotsession__isnull=False).exclude(split=split).exists():
            raise ValidationError("Player split must agree across every linked study")
        guard = DatasetPartition.objects.filter(
            dataset=dataset, kind="PLAYER", token=token(dataset, "PLAYER", str(member.owner_id))
        ).first()
        if guard and guard.split != split:
            raise ValidationError("Dataset player split is already locked")


def session_guard(study, member, code, played_at):
    dataset = study_dataset(study)
    if dataset:
        if dataset.state != "COLLECTING" or not live_measurement(dataset):
            raise ValidationError("Dataset is frozen or measurement is unavailable")
        reserve(dataset, "PLAYER", str(member.owner_id), member.split)
        reserve(
            dataset,
            "SESSION",
            [str(member.owner_id), code],
            member.split,
            binding=token(dataset, "PLAYED_AT", played_at.isoformat()),
        )
        from backend.core.models import PilotSession

        if (
            PilotSession.objects.filter(enrollment__study__datasetstudy__dataset=dataset).count()
            >= 4000
        ):
            raise ValidationError("Dataset session capacity reached")


def capture_pin(study, member, session, asset, match, duration):
    dataset = study_dataset(study)
    if not dataset:
        return {}
    measurement = dataset.measurement
    if (
        match.game_build,
        asset.metadata.get("platform"),
        asset.metadata.get("game_build"),
        asset.metadata.get("dataset_kind"),
    ) != (
        measurement["game_build"],
        measurement["platform"],
        measurement["game_build"],
        dataset.dataset_kind,
    ):
        raise ValidationError("Capture must match the pinned exact build/platform/scope")
    if (
        PilotCapture.objects.filter(
            session__enrollment__study__datasetstudy__dataset=dataset,
            source_sha256=asset.source_sha256,
        )
        .exclude(session=session, asset=asset)
        .exists()
    ):
        raise ValidationError("Source bytes already belong to another dataset capture")
    if match.context != "jin/jin":
        raise ValidationError("Dataset capture must use the declared bounded Jin/Jin context")
    reserve(
        dataset,
        "SOURCE",
        asset.source_sha256,
        member.split,
        binding=token(
            dataset,
            "SOURCE_ASSIGNMENT",
            [str(member.owner_id), session.code, session.played_at.isoformat()],
        ),
    )
    return {
        "metadata_hash": digest(asset.metadata),
        "generation": asset.storage_generation,
        "bytes": asset.bytes,
        "duration_seconds": duration,
        "measurement_hash": digest(measurement),
    }


def live_pin(capture):
    if not capture.provenance:
        return not study_dataset(capture.session.enrollment.study)
    dataset = study_dataset(capture.session.enrollment.study)
    asset = capture.asset
    return bool(
        dataset
        and asset
        and live_measurement(dataset, historical=dataset.state == "FROZEN")
        and capture.provenance
        == {
            "metadata_hash": digest(asset.metadata),
            "generation": asset.storage_generation,
            "bytes": asset.bytes,
            "duration_seconds": capture.duration_seconds,
            "measurement_hash": digest(dataset.measurement),
        }
    )


def invalidate(dataset_id, reason):
    from backend.core.loops import invalidate_for_events
    from backend.core.models import GameplayEvent, MatchContribution

    ids = list(
        DatasetSnapshot.objects.filter(dataset_id=dataset_id, invalidated_at=None).values_list(
            "pk", flat=True
        )
    )
    events = list(
        GameplayEvent.objects.filter(
            measurement__dataset_snapshot__in=[str(i) for i in ids], deleted_at=None
        )
    )
    if events:
        invalidate_for_events([str(e.pk) for e in events])
        GameplayEvent.objects.filter(pk__in=[e.pk for e in events]).update(
            deleted_at=timezone.now()
        )
        MatchContribution.objects.filter(match_id__in=[e.match_id for e in events]).delete()
    DatasetSnapshot.objects.filter(dataset_id=dataset_id, invalidated_at=None).update(
        data={}, invalidated_at=timezone.now(), reason=reason
    )


def invalidate_study(study_id):
    link = DatasetStudy.objects.filter(study_id=study_id).first()
    if link:
        invalidate(link.dataset_id, "STUDY_CHANGED_OR_WITHDRAWN")


def invalidate_definitions(keys):
    for dataset in DatasetCollection.objects.filter(deleted_at=None):
        if any(p["key"] in keys for p in dataset.measurement.get("definitions", {}).values()):
            invalidate(dataset.pk, "MEASUREMENT_WITHDRAWN")


def erase_account(owner_id):
    for dataset in DatasetCollection.objects.filter(owner_id=owner_id, deleted_at=None):
        invalidate(dataset.pk, "ACCOUNT_WITHDRAWN")
        DatasetPartition.objects.filter(dataset=dataset).delete()
        DatasetCollection.objects.filter(pk=dataset.pk).update(
            title="Withdrawn dataset",
            sampling={},
            measurement={},
            state="CLOSED",
            deleted_at=timezone.now(),
        )


def restore_revoke():
    for dataset_id in (
        DatasetSnapshot.objects.filter(invalidated_at=None)
        .values_list("dataset_id", flat=True)
        .distinct()
    ):
        invalidate(dataset_id, "RESTORE_QUARANTINE")
    DatasetPartition.objects.all().delete()
    DatasetCollection.objects.filter(deleted_at=None).update(
        state="CLOSED",
        title="Restored revoked dataset",
        measurement={},
        sampling={},
        deleted_at=timezone.now(),
    )


@transaction.atomic
def freeze(user, dataset_id):
    _, dataset = collection_for(user, dataset_id)
    links = list(dataset.studies.select_related("study"))
    if not links or any(link.study.state == "CLOSED" or link.study.deleted_at for link in links):
        raise ValidationError("Active linked study inputs are required")
    for link in links:
        pilots.freeze(user, link.study_id)
    DatasetCollection.objects.filter(pk=dataset.pk).update(state="FROZEN")


def material(user, dataset):
    from backend.core import pilot_reports

    if dataset.state != "FROZEN":
        raise ValidationError("Freeze dataset inputs before accessing held-out labels")
    sources, inputs = [], []
    for link in dataset.studies.select_related("study").order_by("study_id"):
        study = link.study
        if study.deleted_at or study.state != "FROZEN":
            raise ValidationError("Every linked study must remain frozen and active")
        _, sessions, captures, tasks, _, input_hash = pilot_reports.snapshot(study)
        registered = PilotCapture.objects.filter(
            session__enrollment__study=study, withdrawn_at=None
        ).count()
        if registered != len(captures):
            raise ValidationError("Dataset contains expired, revoked or changed source evidence")
        inputs.append(
            {
                "study_id": str(study.pk),
                "protocol_hash": study.protocol_digest,
                "revision": study.revision,
                "input_hash": input_hash,
                "sessions": [
                    {
                        "id": str(s.pk),
                        "state": s.state,
                        "phase": s.phase,
                        "player_id": token(dataset, "PLAYER", str(s.enrollment.owner_id)),
                        "session_id": token(
                            dataset, "SESSION", [str(s.enrollment.owner_id), s.code]
                        ),
                        "split": s.enrollment.split,
                        "played_at": s.played_at.isoformat(),
                        "playable_seconds": s.playable_seconds,
                    }
                    for s in sessions
                ],
            }
        )
        batches = {b["source_id"]: b for b in pilot_reports.annotation_batches(study)["batches"]}
        for capture in captures:
            selected = [t for t in tasks if t.capture_id == capture.pk]
            reviews = []
            for task in selected:
                state, label = pilots.final_label(task)
                if not label:
                    raise ValidationError(
                        "Every dataset task requires dual review or independent adjudication"
                    )
                pair = [
                    r
                    for r in task.pilotreview_set.all()
                    if r.reviewer_id in {task.reviewer_one_id, task.reviewer_two_id}
                ]
                third = [
                    r for r in task.pilotreview_set.all() if r.reviewer_id == task.adjudicator_id
                ]
                reviews.append(
                    {
                        "id": str(task.pk),
                        "kind": task.kind,
                        "start_us": task.start_us,
                        "end_us": task.end_us,
                        "state": state,
                        "label": label,
                        "prediction": task.prediction,
                        "reviews": [
                            {
                                "reviewer": str(r.reviewer.pseudonym),
                                "label": r.label,
                                "seconds": r.seconds,
                            }
                            for r in sorted(pair, key=lambda r: str(r.reviewer_id)) + third
                        ],
                    }
                )
            qc = [t for t in reviews if t["kind"] == "QC"]
            if len(qc) != 1 or not qc[0]["label"]["profile_valid"]:
                raise ValidationError(
                    "Every source needs complete independently reviewed capture QC"
                )
            match = Match.objects.get(asset=capture.asset, deleted_at=None)
            batch = batches.get(str(capture.asset_id)) or {
                "schema_version": "annotation/1",
                "source_id": str(capture.asset_id),
                "source_sha256": capture.source_sha256,
                "dataset_kind": dataset.dataset_kind,
                "game_build": capture.game_build,
                "session_id": match.session_id,
                "source_kind": match.mode,
                "played_at": match.played_at.isoformat(),
                "examples": [],
            }
            member = capture.session.enrollment
            sources.append(
                {
                    "source_id": str(capture.asset_id),
                    "source_sha256": capture.source_sha256,
                    "player_id": token(dataset, "PLAYER", str(member.owner_id)),
                    "session_id": token(
                        dataset, "SESSION", [str(member.owner_id), capture.session.code]
                    ),
                    "split": member.split,
                    "platform": dataset.measurement["platform"],
                    "duration_seconds": capture.duration_seconds,
                    "provenance": capture.provenance,
                    "retain_until": capture.asset.retain_until.isoformat(),
                    "consent_hash": member.consent_digest,
                    "qc": qc[0],
                    "tasks": [t for t in reviews if t["kind"] != "QC"],
                    "annotations": batch,
                }
            )
    if len(sources) > 4000 or sum(len(s["tasks"]) + 1 for s in sources) > 10000:
        raise ValidationError("Dataset snapshot capacity exceeded")
    return {
        "schema_version": "dataset-snapshot/1",
        "dataset_id": str(dataset.pk),
        "dataset_kind": dataset.dataset_kind,
        "measurement": dataset.measurement,
        "sampling": dataset.sampling,
        "inputs": inputs,
        "sources": sources,
        "qa": quality(sources, inputs),
        "automatic_publication": False,
        "training_permission_included": False,
    }


@transaction.atomic
def seal(user, dataset_id, request_id):
    _, dataset = collection_for(user, dataset_id)
    prior = DatasetSnapshot.objects.filter(dataset=dataset, request_id=request_id).first()
    if prior:
        current_snapshot(user, dataset, prior)
        return prior
    if dataset.snapshots.count() >= 100:
        raise ValidationError("Dataset snapshot capacity reached")
    data = material(user, dataset)
    validate_snapshot({"content_hash": digest(data), "data": data})
    sequence = (dataset.snapshots.aggregate(value=Max("sequence"))["value"] or 0) + 1
    return DatasetSnapshot.objects.create(
        dataset=dataset, sequence=sequence, request_id=request_id, data=data
    )


def current_snapshot(user, dataset, row):
    if row.invalidated_at:
        raise ValidationError("Snapshot has been invalidated and its private data erased")
    try:
        if digest(row.data) != row.content_hash:
            raise ValidationError("Stored snapshot content hash mismatch")
        current = material(user, dataset)
        if digest(current) != row.content_hash:
            raise ValidationError("Snapshot no longer matches current permissions or source inputs")
    except (ValidationError, ValueError):
        invalidate(dataset.pk, "STALE_PERMISSION_OR_INPUT")
        raise
    return {"content_hash": row.content_hash, "data": row.data}


@transaction.atomic
def close(user, dataset_id):
    _, dataset = collection_for(user, dataset_id, require_live=False)
    for link in dataset.studies.filter(study__deleted_at=None):
        pilots.close_study(user, link.study_id)
    invalidate(dataset.pk, "COLLECTION_CLOSED")
    DatasetPartition.objects.filter(dataset=dataset).delete()
    DatasetCollection.objects.filter(pk=dataset.pk).update(
        state="CLOSED",
        title="Closed dataset",
        sampling={},
        measurement={},
        deleted_at=timezone.now(),
    )


def canonical_measurement(run, match, snapshot_id, annotation):
    """Explicit source-specific grant; never makes another workspace's definitions global."""
    row = DatasetSnapshot.objects.select_related("dataset__owner").get(
        pk=snapshot_id, invalidated_at=None
    )
    dataset = row.dataset
    if (
        not knowledge.live_user(dataset.owner_id)
        or not dataset.owner.is_staff
        or not live_measurement(dataset, historical=True)
    ):
        raise ValidationError("Dataset measurement grant is unavailable")
    current_snapshot(dataset.owner, dataset, row)
    source = next((s for s in row.data["sources"] if s["source_id"] == str(run.asset_id)), None)
    if (
        not source
        or digest(source["annotations"]) != digest(annotation)
        or match.dataset_kind != dataset.dataset_kind
    ):
        raise ValidationError(
            "Canonical import must equal this snapshot's exact reviewed source batch"
        )
    measurement = dataset.measurement
    if (match.game_build, run.asset.metadata.get("platform")) != (
        measurement["game_build"],
        measurement["platform"],
    ):
        raise ValidationError("Canonical capture differs from dataset measurement")
    return {
        "knowledge_revision": measurement["knowledge"],
        "knowledge_hash": dataset.knowledge.content_hash,
        "situation": measurement["situation"],
        "metric": measurement["metric"],
        "dataset_snapshot": str(row.pk),
        "dataset_hash": row.content_hash,
    }


def event_available(event):
    row = (
        DatasetSnapshot.objects.select_related("dataset__owner")
        .filter(pk=event.measurement["dataset_snapshot"], invalidated_at=None)
        .first()
    )
    if not row or row.content_hash != event.measurement.get("dataset_hash"):
        return False
    dataset = row.dataset
    if (
        not knowledge.live_user(dataset.owner_id)
        or not dataset.owner.is_staff
        or not live_measurement(dataset, historical=True)
    ):
        return False
    capture = (
        PilotCapture.objects.select_related("asset", "session__enrollment__owner")
        .filter(
            session__enrollment__study__datasetstudy__dataset=dataset,
            asset_id=event.run.asset_id,
            session__enrollment__owner_id=event.owner_id,
            withdrawn_at=None,
        )
        .first()
    )
    if not capture or not pilots.live_capture(capture):
        return False
    return all(
        pilots.final_label(t)[1] for t in capture.pilottask_set.prefetch_related("pilotreview_set")
    )
