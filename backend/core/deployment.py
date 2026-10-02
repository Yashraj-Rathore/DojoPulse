"""Minimal readiness probe and a fail-closed restore boundary."""

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse


def health(request):
    if settings.RESTORE_QUARANTINE:
        return JsonResponse({"status": "QUARANTINED"}, status=503)
    try:
        executor = MigrationExecutor(connection)
        ready = not executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:
        ready = False
    return JsonResponse({"status": "READY" if ready else "NOT_READY"}, status=200 if ready else 503)


class RestoreQuarantineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.RESTORE_QUARANTINE:
            return JsonResponse({"status": "QUARANTINED"}, status=503)
        return self.get_response(request)
