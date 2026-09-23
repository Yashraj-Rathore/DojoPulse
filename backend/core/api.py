"""Thin authenticated API. No CV or AI runs in a request."""

import json
import uuid
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import FileResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analysis.contracts import aware_time
from analysis.statistics import summarize
from backend.core.evidence import as_opportunity
from backend.core.jobs import cancel_run
from backend.core.loops import create_assignment, create_plan, evaluate_plan, record_practice
from backend.core.match_ingestion import register_upload_source
from backend.core.models import (
    AnalysisRun,
    DefinitionVersion,
    DrillAssignment,
    EvaluationPlan,
    GameplayEvent,
    ImprovementEvaluation,
    Match,
    Profile,
    ReplayAsset,
    TrainingSession,
)
from backend.core.ownership import lock_owner
from backend.core.storage import delete_asset, private_path


def handled(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ObjectDoesNotExist:
            return Response({"error": "Not found"}, status=404)
        except IntegrityError:
            return Response({"error": "Conflicting or duplicate operation"}, status=409)
        except (ValidationError, ValueError, KeyError) as error:
            return Response({"error": str(error)}, status=400)

    return wrapped


@require_http_methods(["GET", "POST", "DELETE"])
@csrf_protect
def session(request):
    token = get_token(request)
    if request.method == "DELETE":
        logout(request)
        return JsonResponse({"authenticated": False})
    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not isinstance(body, dict):
            return JsonResponse({"error": "JSON object required"}, status=400)
        user = authenticate(request, username=body.get("username"), password=body.get("password"))
        if user is None:
            return JsonResponse({"error": "Invalid credentials"}, status=401)
        login(request, user)
        token = get_token(request)
    return JsonResponse(
        {
            "authenticated": request.user.is_authenticated,
            "csrf": token,
            "username": request.user.get_username() if request.user.is_authenticated else None,
            "local_uploads": settings.LOCAL_OPERATOR_UPLOADS and request.user.is_staff
            if request.user.is_authenticated
            else False,
        }
    )


@api_view(["GET"])
def overview(request):
    user = request.user
    events = (
        GameplayEvent.objects.filter(
            owner=user,
            deleted_at__isnull=True,
            match__deleted_at__isnull=True,
            match__asset__isnull=False,
            run_id=F("match__analysispublication__run_id"),
        )
        .exclude(match__metadata_state="REVIEW_REQUIRED")
        .select_related("match__asset")
    )
    return Response(
        {
            "stage": "LOCAL_VALIDATION",
            "gameplay_validated": False,
            "runs": list(
                AnalysisRun.objects.filter(owner=user, asset__deleted_at__isnull=True)
                .order_by("-created_at")
                .values("id", "asset_id", "status", "error_code")[:50]
            ),
            "events": [
                {
                    "id": e.pk,
                    "match_id": e.match_id,
                    "mode": e.match.mode,
                    "start_us": e.start_us,
                    "eligibility": e.eligibility,
                    "outcome": e.outcome,
                    "situation": e.situation,
                    "played_at": e.match.played_at,
                    "source_asset_id": e.match.asset_id,
                }
                for e in events.order_by("-created_at")[:500]
            ],
            "drills": list(
                DefinitionVersion.objects.filter(kind="drill").values("key", "status", "payload")
            ),
            "assignments": list(
                DrillAssignment.objects.filter(owner=user).values("id", "drill_id", "status")
            ),
            "plans": list(
                EvaluationPlan.objects.filter(owner=user).values(
                    "id", "assignment_id", "specification"
                )
            ),
            "evaluations": list(
                ImprovementEvaluation.objects.filter(owner=user)
                .order_by("-created_at")
                .values("id", "plan_id", "revision", "result", "invalidated_at")[:50]
            ),
            "practice": [
                {
                    "id": s.pk,
                    "assignment_id": s.assignment_id,
                    "attempts": s.attempts.count(),
                    "summary": summarize(
                        [
                            as_opportunity(a.source_event)
                            for a in s.attempts.select_related("source_event__match__asset")
                        ]
                    ),
                    "completed_at": s.completed_at,
                }
                for s in TrainingSession.objects.filter(owner=user)[:50]
            ],
        }
    )


@api_view(["POST"])
@handled
def upload(request):
    if not settings.LOCAL_OPERATOR_UPLOADS or not request.user.is_staff:
        return Response(
            {"error": "External uploads gated. Local operator ingestion must be enabled."},
            status=503,
        )
    if request.data.get("processing_consent") != "true":
        return Response({"error": "Explicit service-processing consent required"}, status=400)
    source = request.FILES.get("file")
    if source is None or source.size > 536870912 or not source.name.lower().endswith(".mp4"):
        return Response({"error": "An MP4 up to 512 MiB is required"}, status=400)
    metadata = json.loads(request.data.get("metadata", "{}"))
    if not isinstance(metadata, dict):
        return Response({"error": "Metadata must be a JSON object"}, status=400)
    required = {"game_build", "session_id", "played_at", "source_kind"}
    if not required.issubset(metadata) or metadata["source_kind"] not in {
        "ranked",
        "practice",
        "takeover",
    }:
        return Response({"error": "Build, session, played-at and mode are required"}, status=400)
    played = aware_time(metadata["played_at"])
    asset_id = uuid.uuid4()
    key = f"{request.user.pk}/{asset_id}/source.mp4"
    path = private_path(key)
    path.parent.mkdir(parents=True, exist_ok=False)
    written = 0
    try:
        with path.open("xb") as stream:
            for chunk in source.chunks():
                written += len(chunk)
                if written > 536870912:
                    raise ValueError("File exceeded limit")
                stream.write(chunk)
        with transaction.atomic():
            current = lock_owner(request.user.pk)
            if not current.is_active:
                raise ValidationError("Deleted account cannot ingest media")
            profile, _ = Profile.objects.select_for_update().get_or_create(user=request.user)
            if profile.deleted_at:
                raise ValidationError("Deleted account cannot ingest media")
            asset = ReplayAsset.objects.create(
                id=asset_id,
                owner=request.user,
                storage_key=key,
                bytes=written,
                metadata=metadata,
                retain_until=timezone.now() + timedelta(days=60),
            )
            profile.processing_consent_at = timezone.now()
            profile.save(update_fields=["processing_consent_at"])
            match = Match.objects.create(
                owner=request.user,
                asset=asset,
                game_build=metadata["game_build"],
                knowledge_revision="tekken8-3.02.01-pilot-draft/1",
                session_id=metadata["session_id"],
                played_at=played,
                mode=metadata["source_kind"],
                context="jin/jin",
            )
            register_upload_source(match)
            run = AnalysisRun.objects.create(
                owner=request.user, asset=asset, request_key=str(asset_id)
            )
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return Response({"asset_id": asset.pk, "run_id": run.pk, "status": run.status}, status=202)


@api_view(["GET", "DELETE"])
@handled
def run_detail(request, run_id):
    if request.method == "DELETE":
        run = cancel_run(request.user, run_id)
    else:
        run = AnalysisRun.objects.get(pk=run_id, owner=request.user, asset__deleted_at__isnull=True)
    return Response(
        {"id": run.pk, "status": run.status, "error_code": run.error_code, "result": run.result}
    )


@api_view(["DELETE"])
@handled
def asset_delete(request, asset_id):
    delete_asset(request.user, asset_id)
    return Response({"status": "DELETED"}, status=202)


@api_view(["GET"])
@handled
def media(request, asset_id):
    asset = ReplayAsset.objects.get(pk=asset_id, owner=request.user, deleted_at__isnull=True)
    path = private_path(asset.storage_key)
    if not path.is_file():
        return Response({"error": "Media is unavailable"}, status=404)
    response = FileResponse(path.open("rb"), content_type="video/mp4")
    response["Cache-Control"] = "private, no-store"
    return response


class AssignmentInput(serializers.Serializer):
    drill_key = serializers.CharField(max_length=160)


class PlanInput(serializers.Serializer):
    assignment_id = serializers.UUIDField()
    baseline_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=2000
    )
    baseline_end = serializers.DateTimeField()
    followup_start = serializers.DateTimeField()
    followup_end = serializers.DateTimeField()


class MembershipInput(serializers.Serializer):
    event_ids = serializers.ListField(child=serializers.UUIDField(), max_length=2000)


@api_view(["POST"])
@handled
def assignments(request):
    data = AssignmentInput(data=request.data)
    data.is_valid(raise_exception=True)
    item = create_assignment(request.user, data.validated_data["drill_key"])
    return Response({"id": item.pk, "status": item.status}, status=201)


@api_view(["POST"])
@handled
def plans(request):
    data = PlanInput(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    for key in ("baseline_end", "followup_start", "followup_end"):
        values[key] = values[key].isoformat()
    plan = create_plan(request.user, **values)
    return Response({"id": plan.pk, "specification": plan.specification}, status=201)


@api_view(["POST"])
@handled
def practice(request, assignment_id):
    data = MembershipInput(data=request.data)
    data.is_valid(raise_exception=True)
    item = record_practice(request.user, assignment_id, data.validated_data["event_ids"])
    return Response({"id": item.pk, "attempts": item.attempts.count()}, status=201)


@api_view(["POST"])
@handled
def evaluations(request, plan_id):
    data = MembershipInput(data=request.data)
    data.is_valid(raise_exception=True)
    item = evaluate_plan(request.user, plan_id, data.validated_data["event_ids"])
    return Response(
        {
            "id": item.pk,
            "revision": item.revision,
            "result": item.result,
            "invalidated_at": item.invalidated_at,
        },
        status=201,
    )
