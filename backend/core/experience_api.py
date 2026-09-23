"""Local player experience. No external notification delivery or provider access."""

from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.match_api import private
from backend.core.match_ingestion import active_owner
from backend.core.models import (
    AnalysisRun,
    DrillAssignment,
    EvaluationPlan,
    Feedback,
    GameplayEvent,
    ImprovementEvaluation,
    Match,
    MatchSourceRecord,
    NoticeReceipt,
    Participant,
    PlayerGameIdentity,
    Profile,
    ReplayAsset,
    TrainingSession,
)
from backend.core.search import SearchInput, current_events, filter_events, filter_matches
from backend.core.storage import delete_account

PREFERENCE_FIELDS = ("display_timezone", "analysis_notices", "practice_notices", "followup_notices")


class PreferencesInput(serializers.Serializer):
    display_timezone = serializers.ChoiceField(choices=["UTC", "browser"], required=False)
    analysis_notices = serializers.BooleanField(required=False)
    practice_notices = serializers.BooleanField(required=False)
    followup_notices = serializers.BooleanField(required=False)
    complete_onboarding = serializers.BooleanField(required=False)


@api_view(["GET", "PATCH"])
@private
@handled
@transaction.atomic
def preferences(request):
    active_owner(request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        data = PreferencesInput(data=request.data)
        data.is_valid(raise_exception=True)
        for field in PREFERENCE_FIELDS:
            if field in data.validated_data:
                setattr(profile, field, data.validated_data[field])
        if data.validated_data.get("complete_onboarding"):
            profile.onboarding_completed_at = timezone.now()
        profile.save()
    return Response(
        {
            **{field: getattr(profile, field) for field in PREFERENCE_FIELDS},
            "onboarding_completed_at": profile.onboarding_completed_at,
            "processing_consent_at": profile.processing_consent_at,
            "training_consent_at": profile.training_consent_at,
            "username": request.user.username,
            "delivery": "IN_APP_ONLY",
        }
    )


class EvidenceInput(SearchInput):
    match = serializers.UUIDField(required=False)
    eligibility = serializers.ChoiceField(
        choices=["ELIGIBLE", "INELIGIBLE", "UNKNOWN"], required=False
    )


@api_view(["GET"])
@private
@handled
def evidence(request):
    data = EvidenceInput(data=request.query_params)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    matches = filter_matches(Match.objects.filter(owner=request.user, deleted_at=None), values)
    query = filter_events(current_events(request.user).filter(match__in=matches), values)
    if "match" in values:
        Match.objects.get(pk=values["match"], owner=request.user, deleted_at=None)
        query = query.filter(match_id=values["match"])
    if "eligibility" in values:
        query = query.filter(eligibility=values["eligibility"])
    total, start, limit = query.count(), values["offset"], values["limit"]
    rows = query.select_related("match", "run__asset").order_by(
        "-match__played_at", "match_id", "start_us", "id"
    )[start : start + limit]
    return Response(
        {
            "total": total,
            "next_offset": start + limit if start + limit < total else None,
            "events": [
                {
                    "id": row.pk,
                    "match_id": row.match_id,
                    "played_at": row.match.played_at,
                    "mode": row.match.mode,
                    "start_us": row.start_us,
                    "end_us": row.end_us,
                    "eligibility": row.eligibility,
                    "outcome": row.outcome,
                    "situation": row.situation,
                    "game_build": row.match.game_build,
                    "knowledge_revision": row.match.knowledge_revision,
                    "detector_version": row.detector_version,
                    "dataset_kind": row.match.dataset_kind,
                    "source_hash": row.run.asset.source_sha256,
                    "source_asset_id": row.run.asset_id,
                    "metadata_state": row.match.metadata_state,
                    "reviewed": row.verified,
                    "review_count": len(row.review.get("reviews", [])),
                    "selectable": row.match.metadata_state != "REVIEW_REQUIRED" and row.verified,
                }
                for row in rows
            ],
        }
    )


class FeedbackInput(serializers.Serializer):
    request_id = serializers.UUIDField()
    category = serializers.ChoiceField(choices=["QUESTION", "PROBLEM", "CORRECTION", "SUGGESTION"])
    message = serializers.CharField(min_length=5, max_length=2000)
    event_id = serializers.UUIDField(required=False, allow_null=True)


@api_view(["GET", "POST"])
@private
@handled
@transaction.atomic
def feedback(request):
    active_owner(request.user)
    if request.method == "GET":
        return Response(
            {
                "feedback": list(
                    Feedback.objects.filter(owner=request.user)
                    .order_by("-created_at")
                    .values("id", "category", "message", "status", "event_id", "created_at")[:50]
                )
            }
        )
    data = FeedbackInput(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    event = None
    if values.get("event_id"):
        event = GameplayEvent.objects.get(
            pk=values["event_id"], owner=request.user, deleted_at=None, match__deleted_at=None
        )
    item, created = Feedback.objects.get_or_create(
        owner=request.user,
        request_id=values["request_id"],
        defaults={"category": values["category"], "message": values["message"], "event": event},
    )
    if (
        item.category != values["category"]
        or item.message != values["message"]
        or item.event_id != (event.pk if event else None)
    ):
        raise ValidationError("Request ID already belongs to different feedback")
    return Response(
        {"id": item.pk, "status": item.status, "delivery": "LOCAL_OPERATOR_QUEUE"},
        status=201 if created else 200,
    )


def notice_items(owner, profile):
    """Derived from durable state: poll/reload cannot lose a ready notice; receipts suppress it."""
    items = []
    if profile.analysis_notices:
        for run in (
            AnalysisRun.objects.filter(owner=owner, asset__deleted_at=None)
            .exclude(status__in=["QUEUED", "PROCESSING", "CANCELLED"])
            .order_by("-created_at")[:100]
        ):
            items.append(
                {
                    "key": f"run:{run.pk}:{run.status}",
                    "message": "Recording needs review"
                    if run.status == "REVIEW_REQUIRED"
                    else "Recording analysis: " + run.status.lower().replace("_", " "),
                    "href": "#evidence",
                    "category": "analysis",
                }
            )
    if profile.practice_notices:
        for assignment in (
            DrillAssignment.objects.filter(owner=owner, status="ASSIGNED")
            .exclude(recommendation__state="INVALIDATED")
            .order_by("-created_at")[:100]
        ):
            items.append(
                {
                    "key": f"practice:{assignment.pk}",
                    "message": "Your assigned drill is available. Check your frozen plan before recording practice.",
                    "href": "#practice",
                    "category": "practice",
                }
            )
    if profile.followup_notices:
        now = timezone.now()
        from analysis.contracts import aware_time

        for plan in (
            EvaluationPlan.objects.filter(owner=owner)
            .exclude(assignment__recommendation__state="INVALIDATED")
            .order_by("-created_at")[:100]
        ):
            spec = plan.specification
            if "followup_start" not in spec or "followup_end" not in spec:
                continue
            if now < aware_time(spec["followup_start"]):
                continue
            ended = now >= aware_time(spec["followup_end"])
            items.append(
                {
                    "key": f"plan:{plan.pk}:{'ended' if ended else 'open'}",
                    "message": "Follow-up window ended. Review coverage before comparing."
                    if ended
                    else "Follow-up window is open. Record comparable matches.",
                    "href": "#compare",
                    "category": "followup",
                }
            )
    dismissed = set(NoticeReceipt.objects.filter(owner=owner).values_list("key", flat=True))
    return [item for item in items if item["key"] not in dismissed]


class NoticeInput(serializers.Serializer):
    key = serializers.CharField(max_length=150)


@api_view(["GET", "POST"])
@private
@handled
@transaction.atomic
def notices(request):
    active_owner(request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    items = notice_items(request.user, profile)
    if request.method == "POST":
        data = NoticeInput(data=request.data)
        data.is_valid(raise_exception=True)
        key = data.validated_data["key"]
        if (
            not any(item["key"] == key for item in items)
            and not NoticeReceipt.objects.filter(owner=request.user, key=key).exists()
        ):
            raise ValidationError("Notice is no longer available")
        NoticeReceipt.objects.get_or_create(owner=request.user, key=key)
        items = [item for item in items if item["key"] != key]
    return Response(
        {
            "notices": items[:50],
            "remaining": max(0, len(items) - 50),
            "delivery": "IN_APP_ONLY",
            "scope": "Latest 100 records per category",
        }
    )


@api_view(["GET"])
@private
@handled
@transaction.atomic
def export_account(request):
    active_owner(request.user)
    user = request.user
    # Explicit field allowlists: no password hashes, upload-session tokens, storage paths,
    # raw provider payloads or reviewer/opponent identities enter this export.
    tables = {
        "identities": (
            PlayerGameIdentity.objects.filter(owner=user),
            ["id", "game_id", "namespace", "value", "state", "consent_scope"],
        ),
        "matches": (
            Match.objects.filter(owner=user, deleted_at=None),
            ["id", "played_at", "mode", "game_build", "context", "dataset_kind", "metadata_state"],
        ),
        "participants": (
            Participant.objects.filter(match__owner=user, match__deleted_at=None),
            ["match_id", "slot", "character", "is_player"],
        ),
        "sources": (
            MatchSourceRecord.objects.filter(owner=user, match__deleted_at=None),
            [
                "match_id",
                "provider",
                "access_class",
                "revision",
                "retrieved_at",
                "normalized_digest",
            ],
        ),
        "recordings": (
            ReplayAsset.objects.filter(owner=user, deleted_at=None),
            ["id", "source_sha256", "bytes", "retain_until"],
        ),
        "events": (
            GameplayEvent.objects.filter(owner=user, deleted_at=None, match__deleted_at=None),
            [
                "id",
                "match_id",
                "run_id",
                "played_key",
                "situation",
                "metric",
                "start_us",
                "end_us",
                "eligibility",
                "outcome",
                "verified",
            ],
        ),
        "assignments": (DrillAssignment.objects.filter(owner=user), ["id", "drill_id", "status"]),
        "practice": (
            TrainingSession.objects.filter(owner=user),
            ["id", "assignment_id", "completed_at", "mode"],
        ),
        "plans": (
            EvaluationPlan.objects.filter(owner=user),
            ["id", "assignment_id", "specification", "content_hash"],
        ),
        "evaluations": (
            ImprovementEvaluation.objects.filter(owner=user),
            ["id", "plan_id", "revision", "result", "invalidated_at"],
        ),
        "feedback": (
            Feedback.objects.filter(owner=user),
            ["id", "category", "message", "status", "event_id", "created_at"],
        ),
    }
    if sum(query.count() for query, _ in tables.values()) > 10000:
        return Response(
            {
                "error": "This workspace exceeds the local export limit. Ask the local operator for an offline export."
            },
            status=413,
        )
    profile, _ = Profile.objects.get_or_create(user=user)
    response = Response(
        {
            "schema": "dojopulse-export/1",
            "exported_at": timezone.now(),
            "username": user.username,
            "preferences": {field: getattr(profile, field) for field in PREFERENCE_FIELDS},
            "consent": {
                "processing": profile.processing_consent_at,
                "training": profile.training_consent_at,
            },
            "media_included": False,
            "scope": "Workspace records; private media downloads are separate. Source payloads and other people's identifiers are omitted.",
            **{name: list(query.values(*fields)) for name, (query, fields) in tables.items()},
        }
    )
    response["Content-Disposition"] = 'attachment; filename="dojopulse-workspace.json"'
    return response


class DeleteInput(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, max_length=256)
    confirmation = serializers.ChoiceField(choices=["DELETE MY WORKSPACE"])


@api_view(["DELETE"])
@private
@handled
def remove_account(request):
    data = DeleteInput(data=request.data)
    data.is_valid(raise_exception=True)
    if not request.user.check_password(data.validated_data["password"]):
        return Response({"error": "Current password is incorrect"}, status=400)
    pending = False
    try:
        delete_account(request.user)
    except OSError:
        # Tombstone committed before file IO; purge_expired retries physical cleanup.
        pending = True
    logout(request)
    return Response({"status": "DELETED", "purge_pending": pending}, status=202)
