"""Private guided practice reads and explicit self-report lifecycle."""

from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.loops import require_active
from backend.core.match_api import private
from backend.core.models import DrillAssignment
from backend.core.practice import (
    OBSTACLES,
    assignment_detail,
    cancel_assignment,
    delete_log,
    log_practice,
)


class LogInput(serializers.Serializer):
    request_id = serializers.UUIDField()
    state = serializers.ChoiceField(choices=["COMPLETED", "INTERRUPTED", "SKIPPED"])
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField()
    reported_attempts = serializers.IntegerField(min_value=0, max_value=2000)
    obstacle = serializers.ChoiceField(choices=sorted(OBSTACLES), default="NONE")

    def validate(self, values):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError("Unsupported report field")
        return values


@api_view(["GET"])
@private
@handled
@transaction.atomic
def training(request, assignment_id):
    require_active(request.user)
    item = DrillAssignment.objects.get(owner=request.user, pk=assignment_id)
    return Response(assignment_detail(request.user, item))


@api_view(["POST"])
@private
@handled
def report(request, assignment_id):
    data = LogInput(data=request.data)
    data.is_valid(raise_exception=True)
    item = log_practice(request.user, assignment_id, data.validated_data)
    return Response(
        {"id": item.pk, "state": item.state, "verified_trials": 0},
        status=201 if item._created else 200,
    )


@api_view(["DELETE"])
@private
@handled
def remove_report(request, log_id):
    delete_log(request.user, log_id)
    return Response({"status": "DELETED"})


@api_view(["POST"])
@private
@handled
def cancel(request, assignment_id):
    item = cancel_assignment(request.user, assignment_id)
    return Response({"id": item.pk, "status": item.status})
