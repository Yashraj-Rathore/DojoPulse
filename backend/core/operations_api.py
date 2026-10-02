"""Session/CSRF protected staff operations and owner usage; no free-text logs."""

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.budgets import totals
from backend.core.match_api import private
from backend.core.match_ingestion import active_owner
from backend.core.models import CostObservation, OperatorWork, ReplayAsset
from backend.core.operations import COMPONENTS, snapshot
from backend.core.ownership import lock_owner


def staff(user):
    active_owner(user)
    current = lock_owner(user.pk)
    if not current.is_staff:
        raise PermissionDenied("Operator access required")


class Window(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=30, default=1)


@api_view(["GET"])
@private
@handled
@transaction.atomic
def operations(request):
    staff(request.user)
    params = Window(data=request.query_params)
    params.is_valid(raise_exception=True)
    return Response(snapshot(params.validated_data["days"]))


@api_view(["GET"])
@private
@handled
@transaction.atomic
def usage(request):
    active_owner(request.user)
    from django.conf import settings

    return Response(
        {
            "seconds": totals(request.user),
            "storage_bytes": ReplayAsset.objects.filter(
                owner=request.user, purge_completed_at=None
            ).aggregate(value=Sum("bytes"))["value"]
            or 0,
            "limits": {
                "media_seconds": settings.OWNER_MEDIA_SECONDS_PER_DAY,
                "processing_seconds": settings.OWNER_PROCESSING_SECONDS_PER_DAY,
                "storage_bytes": settings.OWNER_STORAGE_BYTES,
                "analyses_per_asset_per_day": settings.ASSET_RUNS_PER_DAY,
            },
            "scope": "UTC day; open reservations cross midnight and settle only after physical stop.",
        }
    )


class WorkInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["REVIEW", "SUPPORT"])
    seconds = serializers.IntegerField(min_value=1, max_value=28800)
    scope = serializers.ChoiceField(choices=["SYNTHETIC", "OBSERVED"])
    request_id = serializers.UUIDField()


@api_view(["POST"])
@private
@handled
@transaction.atomic
def work(request):
    staff(request.user)
    params = WorkInput(data=request.data)
    params.is_valid(raise_exception=True)
    data = params.validated_data
    row, created = OperatorWork.objects.get_or_create(
        owner=request.user, request_id=data["request_id"], defaults=data
    )
    if any(getattr(row, key) != data[key] for key in ("kind", "seconds", "scope")):
        raise serializers.ValidationError("Request ID already records different work")
    return Response({"id": row.pk, "created": created}, status=201 if created else 200)


class CostInput(serializers.Serializer):
    component = serializers.ChoiceField(choices=COMPONENTS)
    scope = serializers.ChoiceField(choices=["SYNTHETIC", "OBSERVED"])
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    amount_usd = serializers.DecimalField(max_digits=12, decimal_places=6, min_value=0)
    reference = serializers.RegexField(r"^[A-Za-z0-9_-]{1,80}$")

    def validate(self, data):
        from django.utils import timezone

        if (
            not 0 <= (data["period_end"] - data["period_start"]).days < 30
            or data["period_end"] > timezone.localdate()
        ):
            raise serializers.ValidationError(
                "Use at most 30 whole UTC days ending no later than today"
            )
        return data


@api_view(["POST"])
@private
@handled
@transaction.atomic
def cost(request):
    staff(request.user)
    params = CostInput(data=request.data)
    params.is_valid(raise_exception=True)
    data = params.validated_data
    row, created = CostObservation.objects.get_or_create(
        component=data["component"],
        scope=data["scope"],
        period_start=data["period_start"],
        period_end=data["period_end"],
        defaults=data,
    )
    if row.amount_usd != data["amount_usd"] or row.reference != data["reference"]:
        raise serializers.ValidationError(
            "A different cost observation already exists for this component/window"
        )
    return Response({"id": row.pk, "created": created}, status=201 if created else 200)
