"""IAM-authenticated Cloud Tasks entry point, disabled with unqualified media runtime."""

import json
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from backend.core.cloud import CloudFailure, GoogleControl, authorized_session
from backend.core.dispatch import launch_dispatch
from backend.core.models import RunDispatch


def configured_control():
    return GoogleControl(
        authorized_session(),
        settings.GOOGLE_TASK_QUEUE,
        settings.GOOGLE_ANALYSIS_JOB,
        settings.GOOGLE_TASK_TARGET,
        settings.GOOGLE_TASK_SERVICE_ACCOUNT,
    )


def verify_task_identity(token):
    from google.auth.transport.requests import Request
    from google.oauth2.id_token import verify_oauth2_token

    class BoundedRequest(Request):
        def __call__(self, *args, **kwargs):
            kwargs["timeout"] = 5
            return super().__call__(*args, **kwargs)

    claims = verify_oauth2_token(token, BoundedRequest(), audience=settings.GOOGLE_TASK_TARGET)
    if (
        claims.get("email") != settings.GOOGLE_TASK_SERVICE_ACCOUNT
        or claims.get("email_verified") is not True
    ):
        raise ValueError("TASK_IDENTITY_REJECTED")


@csrf_exempt
def dispatch_task(request):
    if not settings.CLOUD_MEDIA_RUNTIME_QUALIFIED or settings.RESTORE_QUARANTINE:
        return JsonResponse({"error": "DISPATCH_DISABLED"}, status=503)
    if request.method != "POST":
        return JsonResponse({"error": "METHOD_NOT_ALLOWED"}, status=405)
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer ") or len(authorization) > 8192:
        return JsonResponse({"error": "TASK_IDENTITY_REJECTED"}, status=401)
    try:
        verify_task_identity(authorization[7:])
    except Exception:
        return JsonResponse({"error": "TASK_IDENTITY_REJECTED"}, status=401)
    try:
        if int(request.headers.get("Content-Length", "0")) > 1024 or len(request.body) > 1024:
            raise ValueError("TASK_TOO_LARGE")
        body = json.loads(request.body)
        dispatch_id = uuid.UUID(body["dispatch_id"])
        generation = body["generation"]
        if (
            set(body) != {"dispatch_id", "generation"}
            or type(generation) is not int
            or not 1 <= generation <= 1000
        ):
            raise ValueError("INVALID_TASK")
    except (ValueError, TypeError, KeyError):
        return JsonResponse({"error": "INVALID_TASK"}, status=400)
    try:
        result = launch_dispatch(configured_control(), dispatch_id, generation)
    except RunDispatch.DoesNotExist:
        return JsonResponse({"status": "IGNORED"})  # Purged obsolete intent.
    except CloudFailure:
        return JsonResponse({"error": "DISPATCH_UNAVAILABLE"}, status=503)
    return JsonResponse({"status": result}, status=503 if result == "CAPACITY" else 200)
