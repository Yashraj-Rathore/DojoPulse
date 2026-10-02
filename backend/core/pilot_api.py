"""Session/CSRF-protected local pilot tools with role and evidence-level visibility."""

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from backend.core import pilot_reports, pilots
from backend.core.api import handled
from backend.core.match_api import private
from backend.core.models import (
    Match,
    PilotCapture,
    PilotEnrollment,
    PilotGateReport,
    PilotSession,
    PilotStudy,
    PilotTask,
    Profile,
)


class Create(serializers.Serializer):
    title = serializers.RegexField(r"^[A-Za-z0-9 _.-]{1,80}$")
    dataset_kind = serializers.ChoiceField(choices=["synthetic", "real"])
    request_id = serializers.UUIDField()


class Role(serializers.Serializer):
    role = serializers.ChoiceField(choices=pilots.ROLES)


class Invitation(serializers.Serializer):
    token = serializers.CharField(max_length=2000)


class Join(Invitation):
    protocol_digest = serializers.RegexField(r"^[a-f0-9]{64}$")
    adult = serializers.BooleanField()
    accepted = serializers.BooleanField()
    rights = serializers.BooleanField()


class Split(serializers.Serializer):
    enrollment_id = serializers.UUIDField()
    split = serializers.ChoiceField(choices=["development", "validation", "held-out"])
    comparison_order = serializers.ChoiceField(
        choices=["UNASSIGNED", "STRUCTURED_FIRST", "NATIVE_FIRST", "USUAL_FIRST"],
        default="UNASSIGNED",
    )


class Session(serializers.Serializer):
    code = serializers.RegexField(r"^[A-Za-z0-9_-]{1,60}$")
    phase = serializers.ChoiceField(choices=["BASELINE", "PRACTICE", "FOLLOWUP", "NATIVE", "USUAL"])
    played_at = serializers.DateTimeField()
    playable_seconds = serializers.IntegerField(min_value=0, max_value=86400, allow_null=True)
    state = serializers.ChoiceField(
        choices=["CAPTURED", "MISSING", "ZERO_OPPORTUNITIES", "INVALID"]
    )
    unaided = serializers.BooleanField()
    setup_seconds = serializers.IntegerField(min_value=0, max_value=86400, allow_null=True)
    useful = serializers.BooleanField(allow_null=True)
    insight_seconds = serializers.IntegerField(min_value=0, max_value=86400, allow_null=True)
    request_id = serializers.UUIDField()


class Capture(serializers.Serializer):
    session_id = serializers.UUIDField()
    asset_id = serializers.UUIDField()


class Prediction(serializers.Serializer):
    start_us = serializers.IntegerField(min_value=0, max_value=600000000)
    eligibility = serializers.ChoiceField(choices=["ELIGIBLE", "INELIGIBLE", "UNKNOWN"])
    outcome = serializers.ChoiceField(choices=["SUCCESS", "FAILURE", "UNKNOWN"])
    detector_version = serializers.RegexField(r"^[A-Za-z0-9_.:/-]{1,100}$")

    def validate(self, data):
        if data["eligibility"] != "ELIGIBLE" and data["outcome"] != "UNKNOWN":
            raise serializers.ValidationError(
                "Ineligible/unknown predictions must abstain on outcome"
            )
        return data


class Task(serializers.Serializer):
    capture_id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["QC", "TARGET", "TRIAL"])
    start_us = serializers.IntegerField(min_value=0, max_value=600000000)
    end_us = serializers.IntegerField(min_value=0, max_value=600000000)
    reviewer_one = serializers.UUIDField()
    reviewer_two = serializers.UUIDField()
    adjudicator = serializers.UUIDField()
    prediction = Prediction(allow_null=True)
    request_id = serializers.UUIDField()


class Review(serializers.Serializer):
    task_id = serializers.UUIDField()
    label = serializers.JSONField()
    seconds = serializers.IntegerField(min_value=1, max_value=28800)
    request_id = serializers.UUIDField()

    def validate_label(self, value):
        if not isinstance(value, dict) or len(str(value)) > 4000:
            raise serializers.ValidationError("A bounded structured label is required")
        return value


class Evaluation(serializers.Serializer):
    evaluation_id = serializers.UUIDField()


class Decision(serializers.Serializer):
    report_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=["WAIT", "CONTINUE", "NARROW", "STOP"])
    reason = serializers.ChoiceField(
        choices=[
            "INSUFFICIENT_SAMPLE",
            "UNOBSERVABLE",
            "RECOGNITION",
            "INGESTION",
            "PRACTICE",
            "EXPOSURE",
            "COMPARABILITY",
            "UTILITY",
            "CRITERIA_MET",
        ]
    )
    reference = serializers.RegexField(r"^[A-Za-z0-9_-]{1,80}$")


def checked(serializer, data):
    params = serializer(data=data)
    params.is_valid(raise_exception=True)
    return params.validated_data


def brief(study, role):
    return {
        "id": str(study.pk),
        "title": study.title,
        "dataset_kind": study.dataset_kind,
        "state": study.state,
        "role": role,
        "revision": study.revision,
        "protocol_digest": study.protocol_digest,
        "protocol": study.protocol,
    }


@api_view(["GET", "POST"])
@private
@handled
@transaction.atomic
def studies(request):
    user = pilots.actor(request.user)
    if request.method == "POST":
        row = pilots.create_study(user, **checked(Create, request.data))
        return Response(brief(row, "MANAGER"), status=201)
    members = {
        m.study_id: m.role
        for m in PilotEnrollment.objects.filter(
            owner=user, state="ACTIVE", expires_at__gt=timezone.now()
        )
    }
    rows = PilotStudy.objects.filter(deleted_at=None, owner__is_active=True)
    own = rows.filter(owner=user) if user.is_staff else rows.none()
    rows = (own | rows.filter(pk__in=members)).distinct().order_by("-created_at")[:100]
    return Response(
        {
            "studies": [
                brief(row, "MANAGER" if row.owner_id == user.pk else members[row.pk])
                for row in rows
            ],
            "real_intake_enabled": settings.PILOT_REAL_DATA_APPROVED,
            "local_tools_enabled": settings.DEBUG,
        }
    )


@api_view(["POST"])
@private
@handled
@transaction.atomic
def inspect_invitation(request):
    pilots.actor(request.user)
    row, role = pilots.invitation(**checked(Invitation, request.data))
    return Response(brief(row, role))


@api_view(["POST"])
@private
@handled
def join(request):
    row = pilots.enroll(request.user, **checked(Join, request.data))
    return Response(
        {"study_id": row.study_id, "pseudonym": row.pseudonym, "role": row.role}, status=201
    )


def detail(user, study_id):
    _, study, member = pilots.study_for(user, study_id)
    manager = study.owner_id == user.pk
    role = "MANAGER" if manager else member.role
    data = brief(study, role)
    data["pseudonym"] = str(member.pseudonym) if member else None
    enrollment = PilotEnrollment.objects.filter(
        study=study, state="ACTIVE", expires_at__gt=timezone.now()
    )
    data["members"] = (
        list(enrollment.values("id", "pseudonym", "role", "split", "comparison_order"))
        if manager
        else []
    )
    sessions = PilotSession.objects.filter(enrollment__study=study)
    if not manager:
        sessions = sessions.filter(enrollment=member)
    data["sessions"] = list(
        sessions.order_by("played_at").values(
            "id",
            "enrollment__pseudonym",
            "code",
            "phase",
            "played_at",
            "state",
            "playable_seconds",
            "unaided",
            "setup_seconds",
            "useful",
            "insight_seconds",
        )[: settings.PILOT_MAX_SESSIONS]
    )
    captures = PilotCapture.objects.filter(session__enrollment__study=study, withdrawn_at=None)
    if not manager:
        captures = captures.filter(session__enrollment=member)
    data["captures"] = list(
        captures.values("id", "session_id", "game_build", "duration_seconds", "source_sha256")
    )
    tasks = (
        PilotTask.objects.filter(
            capture__session__enrollment__study=study, capture__withdrawn_at=None
        )
        .select_related("capture__asset", "capture__session__enrollment__owner")
        .prefetch_related("pilotreview_set")
    )
    if not manager:
        from django.db.models import Q

        tasks = tasks.filter(
            Q(reviewer_one=member) | Q(reviewer_two=member) | Q(adjudicator=member)
        )
    data["tasks"] = []
    for task in tasks[: settings.PILOT_MAX_TASKS]:
        if not pilots.live_capture(task.capture):
            continue
        if member and member.role != (
            "ADJUDICATOR" if member.pk == task.adjudicator_id else "REVIEWER"
        ):
            continue
        state, label = pilots.final_label(task)
        submitted = list(task.pilotreview_set.all())
        own = next((r for r in submitted if member and r.reviewer_id == member.pk), None)
        dual = state != "PENDING" and {task.reviewer_one_id, task.reviewer_two_id} <= {
            r.reviewer_id for r in submitted
        }
        hidden = (
            manager
            and task.capture.session.enrollment.split == "held-out"
            and study.state != "FROZEN"
        )
        # Independent reviewers cannot inspect predictions or their colleague's labels before dual submission.
        data["tasks"].append(
            {
                "id": task.pk,
                "capture_id": task.capture_id,
                "kind": task.kind,
                "start_us": task.start_us,
                "end_us": task.end_us,
                "state": "BLINDED" if hidden else state,
                "submitted": bool(own),
                "final_label": label if dual and not hidden else None,
                "reviews": [
                    {"label": r.label, "adjudication": r.reviewer_id == task.adjudicator_id}
                    for r in submitted
                ]
                if dual and not hidden
                else [],
                "own_label": own.label if own else None,
                "can_review": bool(
                    member
                    and not own
                    and (member.pk != task.adjudicator_id or state == "DISAGREEMENT")
                ),
                "media_url": f"/api/pilots/{study.pk}/tasks/{task.pk}/media",
            }
        )
    reports = PilotGateReport.objects.filter(
        study=study, invalidated_at=None, revision=study.revision
    ).select_related("pilotdecision")
    if not manager and role != "EXPERT":
        reports = reports.none()
    # Dynamic retention, account revocation and canonical invalidation must invalidate stale exports too.
    current = pilot_reports.metrics(study) if reports.exists() else {}
    data["reports"] = [
        {
            "id": r.pk,
            "gate": r.gate,
            "content_hash": r.content_hash,
            "data": r.data,
            "decision": {
                "action": r.pilotdecision.action,
                "reason": r.pilotdecision.reason,
                "reference": r.pilotdecision.reference,
            }
            if hasattr(r, "pilotdecision")
            else None,
        }
        for r in reports
        if current.get(r.gate) == r.data
    ]
    data["available_sources"] = (
        list(
            Match.objects.filter(
                owner=user,
                deleted_at=None,
                asset__deleted_at=None,
                asset__isnull=False,
                dataset_kind=study.dataset_kind,
            ).values("asset_id", "played_at", "game_build", "session_id")[:100]
        )
        if role == "PARTICIPANT"
        else []
    )
    return data


@api_view(["GET", "DELETE"])
@private
@handled
@transaction.atomic
def study_detail(request, study_id):
    if request.method == "DELETE":
        if PilotStudy.objects.filter(pk=study_id, owner=request.user, deleted_at=None).exists():
            pilots.close_study(request.user, study_id)
        else:
            pilots.withdraw(request.user, study_id)
        return Response({"withdrawn": True})
    return Response(detail(request.user, study_id))


COMMANDS = {
    "invite": (Role, pilots.invite),
    "split": (Split, pilots.assign_split),
    "session": (Session, pilots.add_session),
    "capture": (Capture, pilots.add_capture),
    "task": (Task, pilots.add_task),
    "review": (Review, pilots.review_task),
    "evaluation": (Evaluation, pilots.link_evaluation),
    "decision": (Decision, pilot_reports.decide),
}


@api_view(["POST"])
@private
@handled
def command(request, study_id, operation):
    if operation == "annotations":
        return Response(pilot_reports.annotations(request.user, study_id))
    if operation == "freeze":
        pilots.freeze(request.user, study_id)
        return Response({"frozen": True})
    if operation == "reports":
        rows = pilot_reports.generate(request.user, study_id)
        return Response({"reports": [str(row.pk) for row in rows]})
    if operation not in COMMANDS:
        return Response({"error": "Unknown pilot operation"}, status=404)
    serializer, fn = COMMANDS[operation]
    result = fn(request.user, study_id, **checked(serializer, request.data))
    return Response({"token": result} if operation == "invite" else {"recorded": True})


@api_view(["GET"])
@private
@handled
@transaction.atomic
def media(request, study_id, task_id):
    user, study, member = pilots.study_for(request.user, study_id)
    task = PilotTask.objects.select_related(
        "capture__asset", "capture__session__enrollment__owner"
    ).get(pk=task_id, capture__session__enrollment__study=study)
    if user.pk != study.owner_id and (
        not member
        or member.pk not in {task.reviewer_one_id, task.reviewer_two_id, task.adjudicator_id}
    ):
        raise PermissionDenied("Assigned reviewer access required")
    if not pilots.live_capture(task.capture) or task.capture.asset.storage_provider != "LOCAL":
        return HttpResponse(status=410)
    from backend.core.media_response import video_response
    from backend.core.storage import private_path

    response = video_response(
        private_path(task.capture.asset.storage_key), request.headers.get("Range")
    )
    if response.streaming:
        response.block_size = 65536
        stream = response.streaming_content

        def chunks():
            try:
                for block in stream:
                    cap = (
                        PilotCapture.objects.select_related("asset", "session__enrollment__owner")
                        .filter(pk=task.capture_id)
                        .first()
                    )
                    if not cap:
                        break
                    current = PilotStudy.objects.filter(
                        pk=study.pk, deleted_at=None, owner__is_active=True
                    ).exists()
                    permitted = (
                        PilotEnrollment.objects.filter(
                            pk=member.pk,
                            role="ADJUDICATOR" if member.pk == task.adjudicator_id else "REVIEWER",
                            state="ACTIVE",
                            expires_at__gt=timezone.now(),
                            owner__is_active=True,
                        ).exists()
                        if member
                        else PilotStudy.objects.filter(pk=study.pk, owner__is_staff=True).exists()
                    )
                    consent = not Profile.objects.filter(
                        user=user, processing_withdrawn_at__isnull=False
                    ).exists()
                    if not current or not permitted or not consent or not pilots.live_capture(cap):
                        break
                    yield block
            finally:
                if hasattr(stream, "close"):
                    stream.close()

        response.streaming_content = chunks()
    return response
