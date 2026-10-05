"""Session/CSRF-protected local recognition console; private reports are owner-only."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core import datasets, knowledge, recognition
from backend.core.api import handled
from backend.core.match_api import private
from backend.core.models import DetectorVersion, RecognitionRun


class Register(serializers.Serializer):
    dataset_id = serializers.UUIDField()
    configuration = serializers.JSONField()
    reviewer_one = serializers.IntegerField(min_value=1)
    reviewer_two = serializers.IntegerField(min_value=1)
    request_id = serializers.UUIDField()


class Run(serializers.Serializer):
    snapshot_id = serializers.UUIDField()
    observations = serializers.JSONField()
    request_id = serializers.UUIDField()


class Review(serializers.Serializer):
    run_id = serializers.UUIDField()
    report_hash = serializers.RegexField(r"^[a-f0-9]{64}$")
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    request_id = serializers.UUIDField()


class Activate(serializers.Serializer):
    run_id = serializers.UUIDField()


def checked(serializer, value):
    data = serializer(data=value)
    data.is_valid(raise_exception=True)
    return data.validated_data


def brief(row, owner):
    return {
        "id": str(row.pk),
        "version": row.version,
        "dataset_id": str(row.dataset_id),
        "state": row.state,
        "content_hash": row.content_hash,
        "role": "OWNER" if row.owner_id == owner.pk else "REVIEWER",
        "disabled_reason": row.disabled_reason,
    }


@api_view(["GET", "POST"])
@private
@handled
@transaction.atomic
def versions(request):
    owner = knowledge.actor(request.user)
    if request.method == "POST":
        row = recognition.register(owner, **checked(Register, request.data))
        return Response(brief(row, owner), status=201)
    rows = DetectorVersion.objects.filter(
        Q(owner=owner) | Q(reviewer_one=owner) | Q(reviewer_two=owner)
    ).order_by("-created_at")[:100]
    return Response({"versions": [brief(r, owner) for r in rows], **recognition.engine_contract()})


def view(request, detector_id):
    owner = knowledge.actor(request.user)
    row = (
        DetectorVersion.objects.select_related("dataset")
        .filter(Q(owner=owner) | Q(reviewer_one=owner) | Q(reviewer_two=owner))
        .get(pk=detector_id)
    )
    data = brief(row, owner)
    data.update(manifest=None, runs=[], real_release_enabled=False, automatic_publication=False)
    if row.state == "INVALIDATED":
        return data
    try:
        with transaction.atomic():
            recognition.current(owner, row.pk, reviewer=True)
    except (ValidationError, PermissionDenied):
        recognition.invalidate_dataset(row.dataset_id, "AUTHORIZATION_OR_ENGINE_CHANGED")
        data.update(state="INVALIDATED", disabled_reason="AUTHORIZATION_OR_ENGINE_CHANGED")
        return data
    data["manifest"] = row.manifest
    for receipt in row.runs.select_related("detector__dataset", "snapshot").order_by("-created_at")[
        :100
    ]:
        info = {
            "id": str(receipt.pk),
            "snapshot_id": str(receipt.snapshot_id),
            "content_hash": receipt.content_hash,
            "input_hash": receipt.input_hash,
            "valid": False,
            "reason": receipt.reason,
            "report": None,
            "reviewed": receipt.reviews.filter(owner=owner).exists(),
            "approval_count": receipt.reviews.filter(decision="APPROVE").count(),
        }
        if not receipt.invalidated_at:
            try:
                with transaction.atomic():
                    recognition.live_run(receipt)
            except ValidationError:
                recognition.invalidate_dataset(row.dataset_id, "STALE_PERMISSION_OR_INPUT")
                return {
                    **data,
                    "state": "INVALIDATED",
                    "manifest": None,
                    "runs": [],
                    "disabled_reason": "STALE_PERMISSION_OR_INPUT",
                }
            report = (
                receipt.report
                if data["role"] == "OWNER"
                else {
                    key: receipt.report[key]
                    for key in (
                        "schema_version",
                        "metrics",
                        "negative_controls",
                        "stop_reasons",
                        "software_pass",
                        "scientific_gate",
                        "benchmark_design",
                        "interpretation",
                        "real_release_approval",
                        "automatic_publication",
                    )
                }
            )
            info.update(valid=True, report=report)
        data["runs"].append(info)
    return data


@api_view(["GET"])
@private
@handled
@transaction.atomic
def detail(request, detector_id):
    return Response(view(request, detector_id))


@api_view(["GET"])
@private
@handled
@transaction.atomic
def download(request, detector_id, run_id):
    row = recognition.current(request.user, detector_id)
    receipt = recognition.live_run(
        RecognitionRun.objects.select_related("detector__dataset", "snapshot").get(
            pk=run_id, detector=row
        )
    )
    bundle = datasets.current_snapshot(row.owner, row.dataset, receipt.snapshot)
    return Response(
        {
            "schema_version": "recognition-reproduction/1",
            "manifest": row.manifest,
            "snapshot": bundle,
            "observations": receipt.inputs,
            "report": receipt.report,
            "content_hash": receipt.content_hash,
            "input_hash": receipt.input_hash,
        }
    )


@api_view(["POST"])
@private
@handled
@transaction.atomic
def command(request, detector_id, operation):
    if operation == "run":
        receipt = recognition.run(request.user, detector_id, **checked(Run, request.data))
        return Response({"id": str(receipt.pk), "content_hash": receipt.content_hash}, status=201)
    if operation == "review":
        recognition.review(request.user, detector_id, **checked(Review, request.data))
    elif operation == "activate":
        recognition.activate(request.user, detector_id, **checked(Activate, request.data))
    elif operation == "disable":
        recognition.disable(request.user, detector_id)
    else:
        raise ValidationError("Unknown recognition operation")
    return Response(view(request, detector_id))
