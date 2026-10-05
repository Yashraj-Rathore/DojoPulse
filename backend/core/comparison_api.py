"""Private auditable comparison reports; no raw media, external identifiers or reviewer labels."""

import json

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analysis.contracts import digest
from backend.core.api import handled
from backend.core.comparisons import (
    availability,
    collection,
    delete_session,
    fingerprint,
    latest_sessions,
    phase_spec,
    record_session,
)
from backend.core.loops import require_active
from backend.core.match_api import private
from backend.core.models import EvaluationPlan


def result_view(owner, item):
    available, reasons = availability(owner, item)
    return {
        "id": item.pk,
        "phase": item.phase,
        "revision": item.revision,
        "created_at": item.created_at,
        "result_hash": digest(item.result),
        "available": available,
        "unavailable_reasons": reasons,
        "invalidated_at": item.invalidated_at,
        "result": item.result,
    }


def session_view(row):
    return {
        "id": row.pk,
        "phase": row.phase,
        "revision": row.revision,
        "code": row.code,
        "state": row.state,
        "played_at": row.played_at,
        "match_ids": row.match_ids,
        "content_hash": row.content_hash,
    }


@api_view(["GET"])
@private
@handled
@transaction.atomic
def detail(request, plan_id):
    require_active(request.user)
    plan = (
        EvaluationPlan.objects.select_for_update()
        .select_related("assignment")
        .get(owner=request.user, pk=plan_id)
    )
    if plan.evaluations.count() > 200:
        raise ValidationError("Comparison exceeds the bounded local report history")
    phases = {}
    for phase in ("FOLLOWUP", "RETENTION"):
        if phase == "RETENTION" and not plan.protocol.get("schedule", {}).get("retention"):
            continue
        spec = phase_spec(plan, phase)
        rows, info = collection(plan, phase, spec)
        phases[phase] = {
            "start": spec.followup_start,
            "end": spec.followup_end,
            "collection": info,
            "sessions": [session_view(row) for row in latest_sessions(plan, phase)],
            "evidence": [
                {
                    "id": str(e.pk),
                    "match_id": str(e.match_id),
                    "session_code": e.match.session_id,
                    "played_at": e.match.played_at,
                    "eligibility": e.eligibility,
                    "outcome": e.outcome,
                    "source": fingerprint(e),
                }
                for e in rows
            ],
        }
    report = {
        "version": "comparison-report/1",
        "plan_id": str(plan.pk),
        "plan_hash": plan.content_hash,
        "specification": plan.specification,
        "protocol": plan.protocol,
        "phases": phases,
        "revisions": [
            result_view(request.user, row) for row in plan.evaluations.order_by("-revision")
        ],
        "dataset_kind": plan.specification["dataset_kind"],
        "causal": False,
        "release_approved": False,
        "historical_unavailable_results_are_not_current_evidence": True,
    }
    # Normalize UUID/date objects before hashing/export so reload and download agree.
    from rest_framework.utils.encoders import JSONEncoder

    report = json.loads(json.dumps(report, cls=JSONEncoder))
    response = Response({**report, "report_hash": digest(report)})
    if request.query_params.get("download") == "1":
        response["Content-Disposition"] = 'attachment; filename="dojopulse-comparison.json"'
    return response


class SessionInput(serializers.Serializer):
    request_id = serializers.UUIDField()
    phase = serializers.ChoiceField(choices=["FOLLOWUP", "RETENTION"])
    code = serializers.CharField(max_length=100)
    state = serializers.ChoiceField(choices=["RECORDED", "MISSING", "SKIPPED"])
    played_at = serializers.DateTimeField(required=False)
    match_ids = serializers.ListField(child=serializers.UUIDField(), max_length=100, default=list)

    def validate(self, values):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError("Unsupported session report input")
        return values


@api_view(["POST"])
@private
@handled
def sessions(request, plan_id):
    data = SessionInput(data=request.data)
    data.is_valid(raise_exception=True)
    row = record_session(request.user, plan_id, data.validated_data)
    return Response(session_view(row), status=201 if row._created else 200)


@api_view(["DELETE"])
@private
@handled
def remove_session(request, session_id):
    delete_session(request.user, session_id)
    return Response({"status": "DELETED"})
