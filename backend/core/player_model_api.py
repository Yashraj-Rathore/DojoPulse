"""Authenticated, consent-aware diagnosis reads serialized against evidence withdrawals."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from backend.core.api import handled
from backend.core.loops import require_active
from backend.core.match_api import private
from backend.core.player_model import projection
from backend.core.search import SearchInput


class ModelInput(SearchInput):
    dataset_kind = serializers.ChoiceField(choices=["real", "synthetic"], default="real")
    context = serializers.CharField(max_length=100, required=False)
    game_build = serializers.CharField(max_length=80, required=False)
    knowledge_revision = serializers.CharField(max_length=160, required=False)
    detector_version = serializers.CharField(max_length=100, required=False)
    platform = serializers.CharField(max_length=50, required=False)

    def validate(self, values):
        # Favorable outcome/eligibility subsets cannot become a diagnosis denominator.
        permitted = {
            "date_from",
            "date_to",
            "character",
            "situation",
            "offset",
            "limit",
            "dataset_kind",
            "context",
            "game_build",
            "knowledge_revision",
            "detector_version",
            "platform",
        }
        if set(self.initial_data) - permitted:
            raise serializers.ValidationError("Unsupported diagnosis filter")
        today = timezone.now().date()
        values.setdefault("date_to", today)
        if not 2 <= values["date_to"].year <= 9998:
            raise serializers.ValidationError("Date is outside the supported range")
        if hasattr(self.initial_data, "getlist") and any(
            len(self.initial_data.getlist(key)) != 1 for key in self.initial_data
        ):
            raise serializers.ValidationError("Use each diagnosis filter once")
        values.setdefault("date_from", values["date_to"] - timedelta(days=89))
        values = super().validate(values)
        if (values["date_to"] - values["date_from"]).days > 365:
            raise serializers.ValidationError("Choose at most 366 UTC dates")
        return values


@api_view(["GET"])
@private
@handled
@transaction.atomic
def player_model(request):
    require_active(request.user)
    data = ModelInput(data=request.query_params)
    data.is_valid(raise_exception=True)
    return Response(projection(request.user, data.validated_data))
