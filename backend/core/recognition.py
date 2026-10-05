"""Owned local detector lifecycle. No credentials, video decode or automatic publication."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from analysis.contracts import digest
from analysis.recognition import artifact_hash, benchmark, manifest
from backend.core import datasets, knowledge
from backend.core.models import DatasetSnapshot, DetectorReview, DetectorVersion, RecognitionRun


def invalidate_dataset(dataset_id, reason):
    now = timezone.now()
    RecognitionRun.objects.filter(detector__dataset_id=dataset_id, invalidated_at=None).update(
        inputs={}, report={}, invalidated_at=now, reason=reason[:40]
    )
    versions = DetectorVersion.objects.filter(dataset_id=dataset_id).exclude(state="INVALIDATED")
    # Blind labels/inputs can advance after a configuration is fixed. Only versions
    # that have consumed a snapshot are invalidated by those changes; withdrawal
    # still makes the subsequent snapshot authorization check fail.
    if reason == "STUDY_CHANGED_OR_WITHDRAWN":
        versions = versions.filter(runs__isnull=False)
    versions.update(manifest={}, state="INVALIDATED", disabled_reason=reason[:40])


def erase_account(owner_id):
    for dataset_id in (
        DetectorVersion.objects.filter(owner_id=owner_id)
        .values_list("dataset_id", flat=True)
        .distinct()
    ):
        invalidate_dataset(dataset_id, "ACCOUNT_WITHDRAWN")
    # A withdrawn independent reviewer cannot leave an active approval behind.
    affected = DetectorVersion.objects.filter(
        Q(reviewer_one_id=owner_id) | Q(reviewer_two_id=owner_id)
    )
    for dataset_id in affected.values_list("dataset_id", flat=True).distinct():
        invalidate_dataset(dataset_id, "REVIEWER_WITHDRAWN")
    DetectorReview.objects.filter(owner_id=owner_id).delete()


def restore_revoke():
    for dataset_id in DetectorVersion.objects.values_list("dataset_id", flat=True).distinct():
        invalidate_dataset(dataset_id, "RESTORE_QUARANTINE")
    DetectorReview.objects.all().delete()


def current(user, detector_id, *, reviewer=False):
    owner = knowledge.actor(user)
    query = DetectorVersion.objects.select_for_update(of=("self",)).select_related(
        "dataset", "dataset__owner"
    )
    if reviewer:
        query = query.filter(Q(owner=owner) | Q(reviewer_one=owner) | Q(reviewer_two=owner))
    else:
        query = query.filter(owner=owner)
    row = query.get(pk=detector_id)
    if row.state == "INVALIDATED" or not datasets.live_measurement(row.dataset, historical=True):
        raise ValidationError("Detector measurement or source authorization is unavailable")
    if digest(row.manifest) != row.content_hash:
        raise ValidationError("Detector manifest content hash differs")
    try:
        manifest(row.manifest)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    for person in (row.owner_id, row.reviewer_one_id, row.reviewer_two_id):
        if (
            not knowledge.live_user(person)
            or not get_user_model().objects.filter(pk=person, is_staff=True).exists()
        ):
            raise PermissionDenied("Detector operator or assigned reviewer is unavailable")
    return row


@transaction.atomic
def register(user, dataset_id, configuration, reviewer_one, reviewer_two, request_id):
    owner, dataset = datasets.collection_for(user, dataset_id)
    try:
        config = manifest(configuration)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    if (
        dataset.measurement != config["measurement"]
        or dataset.dataset_kind != config["dataset_kind"]
    ):
        raise ValidationError("Detector must pin the collection's exact measurement")
    if dataset.dataset_kind != "synthetic":
        raise ValidationError(
            "Real detector registration/release needs explicit G1/G2 technical review"
        )
    if len({owner.pk, reviewer_one, reviewer_two}) != 3:
        raise ValidationError("Two distinct independent operators required")
    for person in (reviewer_one, reviewer_two):
        if (
            not knowledge.live_user(person)
            or not get_user_model().objects.filter(pk=person, is_staff=True).exists()
        ):
            raise ValidationError("Assigned independent operator unavailable")
    prior = DetectorVersion.objects.filter(owner=owner, request_id=request_id).first()
    if prior:
        if (prior.dataset_id, prior.content_hash, prior.reviewer_one_id, prior.reviewer_two_id) != (
            dataset.pk,
            digest(config),
            reviewer_one,
            reviewer_two,
        ) or prior.state == "INVALIDATED":
            raise ValidationError("Detector request ID already used")
        return prior
    if DetectorVersion.objects.filter(owner=owner).count() >= 100:
        raise ValidationError("Local detector version capacity reached")
    return DetectorVersion.objects.create(
        owner=owner,
        dataset=dataset,
        version=config["version"],
        manifest=config,
        reviewer_one_id=reviewer_one,
        reviewer_two_id=reviewer_two,
        request_id=request_id,
    )


def live_run(row):
    if (
        row.invalidated_at
        or digest(row.inputs) != row.input_hash
        or digest(row.report) != row.content_hash
    ):
        raise ValidationError("Recognition receipt is invalidated or differs from its content hash")
    with transaction.atomic():
        bundle = datasets.current_snapshot(row.detector.owner, row.detector.dataset, row.snapshot)
    if (
        row.report.get("manifest_hash") != row.detector.content_hash
        or row.report.get("snapshot_hash") != bundle["content_hash"]
    ):
        raise ValidationError("Recognition receipt pins differ from current inputs")
    return row


@transaction.atomic
def run(user, detector_id, snapshot_id, observations, request_id):
    row = current(user, detector_id)
    snapshot = DatasetSnapshot.objects.get(pk=snapshot_id, dataset=row.dataset)
    with transaction.atomic():
        bundle = datasets.current_snapshot(row.owner, row.dataset, snapshot)
    prior = RecognitionRun.objects.filter(owner=row.owner, request_id=request_id).first()
    if prior:
        if (prior.detector_id, prior.snapshot_id, prior.input_hash) != (
            row.pk,
            snapshot.pk,
            digest(observations),
        ):
            raise ValidationError("Recognition request ID already used")
        return live_run(prior)
    if row.runs.count() >= 100:
        raise ValidationError("Local recognition receipt capacity reached")
    try:
        report = benchmark(row.manifest, bundle, observations)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    result = RecognitionRun.objects.create(
        owner=row.owner,
        detector=row,
        snapshot=snapshot,
        inputs=observations,
        report=report,
        request_id=request_id,
    )
    if row.state == "ACTIVE" and not report["software_pass"]:
        DetectorVersion.objects.filter(pk=row.pk).update(
            state="DISABLED", disabled_reason="DRIFT_STOP"
        )
    return result


@transaction.atomic
def review(user, detector_id, run_id, report_hash, decision, request_id):
    row = current(user, detector_id, reviewer=True)
    owner = knowledge.actor(user)
    if owner.pk not in (row.reviewer_one_id, row.reviewer_two_id):
        raise PermissionDenied("Only assigned independent operators can review this receipt")
    receipt = live_run(
        RecognitionRun.objects.select_related("detector__dataset", "snapshot").get(
            pk=run_id, detector=row
        )
    )
    if report_hash != receipt.content_hash or decision not in {"APPROVE", "REJECT"}:
        raise ValidationError("Exact current report hash and explicit decision required")
    prior = DetectorReview.objects.filter(run=receipt, owner=owner).first()
    if prior:
        if (prior.report_hash, prior.decision, prior.request_id) != (
            report_hash,
            decision,
            request_id,
        ):
            raise ValidationError("Independent receipt already reviewed")
        return prior
    return DetectorReview.objects.create(
        owner=owner, run=receipt, report_hash=report_hash, decision=decision, request_id=request_id
    )


@transaction.atomic
def activate(user, detector_id, run_id):
    row = current(user, detector_id)
    receipt = live_run(
        RecognitionRun.objects.select_related("detector__dataset", "snapshot").get(
            pk=run_id, detector=row
        )
    )
    if row.manifest["dataset_kind"] != "synthetic" or not receipt.report.get("software_pass"):
        raise ValidationError("Only passing synthetic software candidates can be activated locally")
    approvals = set(
        receipt.reviews.filter(decision="APPROVE", report_hash=receipt.content_hash).values_list(
            "owner_id", flat=True
        )
    )
    if approvals != {row.reviewer_one_id, row.reviewer_two_id}:
        raise ValidationError("Two independent approvals of the exact report required")
    # Current observation drift cannot be overridden with an older passing receipt.
    latest = row.runs.filter(invalidated_at=None).order_by("-created_at", "-id").first()
    if latest.pk != receipt.pk:
        raise ValidationError(
            "Activate only the latest receipt; rerun after drift or changed inputs"
        )
    DetectorVersion.objects.filter(dataset=row.dataset, state="ACTIVE").exclude(pk=row.pk).update(
        state="DISABLED", disabled_reason="REPLACED_BY_REVIEWED_VERSION"
    )
    DetectorVersion.objects.filter(pk=row.pk).update(
        state="ACTIVE", activated_at=timezone.now(), disabled_reason=""
    )
    return row


@transaction.atomic
def disable(user, detector_id):
    row = current(user, detector_id)
    DetectorVersion.objects.filter(pk=row.pk).update(
        state="DISABLED", disabled_reason="OPERATOR_STOP"
    )


def engine_contract():
    return {
        "engine": "observation-rules/1",
        "artifact_hash": artifact_hash(),
        "real_release_enabled": False,
        "automatic_publication": False,
    }
