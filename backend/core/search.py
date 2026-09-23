"""Shared UTC calendar filters; current publications alone answer gameplay searches."""

from datetime import UTC, datetime, time, timedelta

from django.db.models import F, Q
from rest_framework import serializers

from backend.core.models import GameplayEvent


class SearchInput(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    character = serializers.CharField(max_length=50, required=False)
    situation = serializers.CharField(max_length=160, required=False)
    outcome = serializers.ChoiceField(choices=["SUCCESS", "FAILURE", "UNKNOWN"], required=False)
    mode = serializers.ChoiceField(
        choices=["unknown", "ranked", "quick", "player", "group", "practice", "takeover", "other"],
        required=False,
    )
    offset = serializers.IntegerField(default=0, min_value=0, max_value=100000)
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)

    def validate(self, values):
        if (
            values.get("date_from")
            and values.get("date_to")
            and values["date_from"] > values["date_to"]
        ):
            raise serializers.ValidationError("Start date must not follow end date")
        if values.get("date_to") and values["date_to"].year >= 9999:
            raise serializers.ValidationError("End date is outside the supported range")
        return values


def filter_matches(query, values):
    if "date_from" in values:
        query = query.filter(played_at__gte=datetime.combine(values["date_from"], time.min, UTC))
    if "date_to" in values:
        query = query.filter(
            played_at__lt=datetime.combine(values["date_to"] + timedelta(days=1), time.min, UTC)
        )
    if "mode" in values:
        query = query.filter(mode=values["mode"])
    if "character" in values:
        character = values["character"]
        query = query.filter(
            Q(participants__character=character)
            | Q(context=character)
            | Q(context__startswith=character + "/")
            | Q(context__endswith="/" + character)
        )
    return query.distinct()


def current_events(owner):
    return GameplayEvent.objects.filter(
        owner=owner,
        deleted_at=None,
        match__deleted_at=None,
        run__asset__deleted_at=None,
        run_id=F("match__analysispublication__run_id"),
        run__asset_id=F("match__asset_id"),
    )


def filter_events(query, values):
    for field in ("situation", "outcome"):
        if field in values:
            query = query.filter(**{field: values[field]})
    return query
