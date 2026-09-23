"""Minimal relational loop. Dense observations and immutable configuration stay in artifacts/JSON."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from analysis.contracts import digest


class Owned(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True)
    processing_consent_at = models.DateTimeField(null=True)
    training_consent_at = models.DateTimeField(null=True)


class Game(models.Model):
    key = models.CharField(primary_key=True, max_length=40)


class GameBuild(models.Model):
    key = models.CharField(primary_key=True, max_length=80)
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    platform = models.CharField(max_length=30)
    provenance = models.JSONField(default=dict)
    verified = models.BooleanField(default=False)


class Character(models.Model):
    key = models.CharField(primary_key=True, max_length=80)
    game = models.ForeignKey(Game, on_delete=models.PROTECT)


class Move(models.Model):
    key = models.CharField(primary_key=True, max_length=100)
    character = models.ForeignKey(Character, on_delete=models.PROTECT)


class DefinitionVersion(models.Model):
    """MoveVersion/FrameData, KnowledgeRevision, Situation/Metric/Drill definitions."""

    key = models.CharField(primary_key=True, max_length=160)
    kind = models.CharField(
        max_length=30,
        choices=[(x, x) for x in ("move", "knowledge", "situation", "metric", "drill", "capture")],
    )
    game_build = models.ForeignKey(GameBuild, on_delete=models.PROTECT, null=True)
    status = models.CharField(max_length=30, default="DRAFT")
    payload = models.JSONField()
    content_hash = models.CharField(max_length=64, editable=False)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Definitions are immutable; create a new version")
        self.content_hash = digest(
            {
                "key": self.key,
                "kind": self.kind,
                "status": self.status,
                "game_build": self.game_build_id,
                "payload": self.payload,
            }
        )
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)


class ReplayAsset(Owned):
    storage_key = models.CharField(max_length=250)
    source_sha256 = models.CharField(max_length=64, blank=True)
    bytes = models.PositiveBigIntegerField(default=0)
    metadata = models.JSONField(default=dict)
    deleted_at = models.DateTimeField(null=True)
    purge_completed_at = models.DateTimeField(null=True)
    upload_session = models.TextField(blank=True)  # secret; never serialized or logged
    upload_cancelled = models.BooleanField(default=False)
    retain_until = models.DateTimeField(null=True)


class Match(Owned):
    asset = models.ForeignKey(ReplayAsset, on_delete=models.PROTECT, null=True)
    game = models.ForeignKey(Game, on_delete=models.PROTECT, null=True)
    player_identity = models.ForeignKey("PlayerGameIdentity", on_delete=models.PROTECT, null=True)
    game_build = models.CharField(max_length=80, null=True)
    knowledge_revision = models.CharField(max_length=160, null=True)
    session_id = models.CharField(max_length=100, null=True)
    played_at = models.DateTimeField()
    chronology_verified = models.BooleanField(default=False)
    mode = models.CharField(
        max_length=20,
        default="unknown",
        choices=[
            (x, x)
            for x in (
                "unknown",
                "ranked",
                "quick",
                "player",
                "group",
                "practice",
                "takeover",
                "other",
            )
        ],
    )
    context = models.CharField(max_length=100, null=True)
    winner_slot = models.PositiveSmallIntegerField(null=True)
    metadata_revision = models.PositiveIntegerField(default=0)
    metadata_state = models.CharField(max_length=30, default="USER_UPLOAD")
    dataset_kind = models.CharField(max_length=20, default="real")
    deleted_at = models.DateTimeField(null=True)


class Participant(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="participants")
    slot = models.PositiveSmallIntegerField()
    character = models.CharField(max_length=50, null=True)
    snapshot = models.JSONField(default=dict)
    is_player = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["match", "slot"], name="unique_match_slot"),
            models.CheckConstraint(condition=Q(slot__in=[1, 2]), name="two_supported_slots"),
        ]


class PlayerGameIdentity(Owned):
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    namespace = models.CharField(max_length=100)
    value = models.CharField(max_length=200)
    display_label = models.CharField(max_length=200, null=True)
    state = models.CharField(max_length=20, default="CLAIMED")
    consent_scope = models.CharField(max_length=100)
    provenance = models.JSONField(default=dict)
    verification = models.JSONField(default=dict)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "game", "namespace", "value"], name="owner_game_identity"
            )
        ]


class MatchSourceRecord(Owned):
    """Append-only source assertions; deletion may explicitly redact their content."""

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="source_records")
    provider = models.CharField(max_length=100)
    policy_version = models.CharField(max_length=100)
    access_class = models.CharField(max_length=40)
    external_namespace = models.CharField(max_length=100)
    external_id = models.CharField(max_length=200)
    revision = models.PositiveIntegerField()
    retrieved_at = models.DateTimeField()
    raw_digest = models.CharField(max_length=64)
    normalized_digest = models.CharField(max_length=64)
    adapter_version = models.CharField(max_length=100)
    schema_version = models.CharField(max_length=100)
    assertion = models.JSONField()
    correction_state = models.CharField(max_length=30, default="ACCEPTED")

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Source assertions are immutable; append a revision")
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "provider", "external_namespace", "external_id", "revision"],
                name="source_record_revision",
            )
        ]


class ReplaySource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="replay_sources")
    source_record = models.ForeignKey(MatchSourceRecord, on_delete=models.CASCADE, null=True)
    asset = models.ForeignKey(ReplayAsset, on_delete=models.PROTECT, null=True)
    provider = models.CharField(max_length=100)
    access_class = models.CharField(max_length=40)
    representation = models.CharField(max_length=30)
    external_id = models.JSONField(null=True)
    availability = models.CharField(max_length=30, default="UNKNOWN")
    checked_at = models.DateTimeField(null=True)
    upstream_expires_at = models.DateTimeField(null=True)
    local_retain_until = models.DateTimeField(null=True)
    content_hash = models.CharField(max_length=64, blank=True)
    canonical_build = models.CharField(max_length=80, null=True)
    parser_version = models.CharField(max_length=100, null=True)
    attribution_state = models.CharField(max_length=30, default="NOT_REQUIRED")
    attribution = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["match", "asset"], name="one_upload_representation")
        ]


class MatchSync(Owned):
    identity = models.ForeignKey(PlayerGameIdentity, on_delete=models.CASCADE)
    provider = models.CharField(max_length=100)
    policy_version = models.CharField(max_length=100)
    query_start = models.DateTimeField()
    query_end = models.DateTimeField()
    checkpoint = models.TextField(null=True)
    coverage = models.JSONField(default=list)
    status = models.CharField(max_length=30, default="PENDING")
    fence = models.PositiveIntegerField(default=0)
    attempts = models.PositiveIntegerField(default=0)
    lease_until = models.DateTimeField(null=True)
    next_attempt_at = models.DateTimeField(null=True)
    last_succeeded_at = models.DateTimeField(null=True)
    stop_reason = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "identity", "provider", "query_start", "query_end"],
                name="sync_query_idempotency",
            )
        ]


class ReplaySegment(models.Model):
    asset = models.ForeignKey(ReplayAsset, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    start_us = models.PositiveBigIntegerField()
    end_us = models.PositiveBigIntegerField()
    mode = models.CharField(max_length=20)
    round_ordinal = models.PositiveSmallIntegerField(
        null=True
    )  # Round represented within segment now

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end_us__gte=F("start_us")), name="segment_time_order"
            )
        ]


class AnalysisRun(Owned):
    asset = models.ForeignKey(ReplayAsset, on_delete=models.CASCADE)
    pipeline_version = models.CharField(max_length=80, default="local-pipeline/1")
    request_key = models.CharField(max_length=100)
    status = models.CharField(max_length=30, default="QUEUED")
    attempts = models.PositiveSmallIntegerField(default=0)
    fence = models.PositiveIntegerField(default=0)
    lease_until = models.DateTimeField(null=True)
    result = models.JSONField(default=dict)
    error_code = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_key"], name="run_idempotency")
        ]


class ObservationArtifact(models.Model):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    storage_key = models.CharField(max_length=250)
    content_hash = models.CharField(max_length=64)
    schema_version = models.CharField(max_length=50)


class GameplayEvent(Owned):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    played_key = models.CharField(max_length=180)
    situation = models.CharField(max_length=160)
    metric = models.CharField(max_length=160)
    detector_version = models.CharField(max_length=100)
    start_us = models.PositiveBigIntegerField()
    end_us = models.PositiveBigIntegerField()
    eligibility = models.CharField(max_length=20)
    outcome = models.CharField(max_length=20)
    verified = models.BooleanField(default=False)
    evidence = models.JSONField(default=list)
    review = models.JSONField(default=dict)
    deleted_at = models.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Events are immutable; publish a new analysis revision")
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "match", "played_key"], name="unique_opportunity_revision"
            ),
            models.CheckConstraint(condition=Q(end_us__gte=F("start_us")), name="event_time_order"),
            models.CheckConstraint(
                condition=Q(eligibility__in=["ELIGIBLE", "INELIGIBLE", "UNKNOWN"]),
                name="valid_eligibility",
            ),
            models.CheckConstraint(
                condition=Q(outcome__in=["SUCCESS", "FAILURE", "UNKNOWN"]), name="valid_outcome"
            ),
            models.CheckConstraint(
                condition=Q(outcome="UNKNOWN") | (Q(eligibility="ELIGIBLE") & Q(verified=True)),
                name="known_outcome_requires_eligible_verified",
            ),
        ]
        indexes = [models.Index(fields=["owner", "match", "start_us"])]


class AnalysisPublication(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE)
    run = models.ForeignKey(AnalysisRun, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField(default=1)


class MatchContribution(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    metric = models.CharField(max_length=160)
    run = models.ForeignKey(AnalysisRun, on_delete=models.PROTECT)
    summary = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["match", "metric"], name="one_active_contribution")
        ]


class Recommendation(Owned):
    """DetectedWeakness and proposed action in one record; evidence snapshot stays explicit."""

    situation = models.CharField(max_length=160)
    metric = models.CharField(max_length=160)
    baseline_event_ids = models.JSONField()
    summary = models.JSONField()
    state = models.CharField(max_length=30, default="PROPOSED")


class DrillAssignment(Owned):
    recommendation = models.ForeignKey(Recommendation, on_delete=models.PROTECT, null=True)
    drill = models.ForeignKey(DefinitionVersion, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, default="ASSIGNED")


class TrainingSession(Owned):
    assignment = models.ForeignKey(DrillAssignment, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(null=True)
    mode = models.CharField(max_length=40, default="recorded_in_game")
    setup = models.JSONField(default=dict)


class DrillAttempt(models.Model):
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name="attempts")
    source_event = models.OneToOneField(GameplayEvent, on_delete=models.PROTECT)
    trial_index = models.PositiveIntegerField()
    played_key = models.CharField(max_length=240, unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "trial_index"], name="unique_trial")
        ]


class EvaluationPlan(Owned):
    assignment = models.OneToOneField(DrillAssignment, on_delete=models.PROTECT)
    specification = models.JSONField()
    content_hash = models.CharField(max_length=64, editable=False)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("EvaluationPlan is frozen")
        self.content_hash = digest(self.specification)
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)


class ImprovementEvaluation(Owned):
    plan = models.ForeignKey(EvaluationPlan, on_delete=models.CASCADE, related_name="evaluations")
    revision = models.PositiveIntegerField()
    result = models.JSONField()
    invalidated_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["plan", "revision"], name="unique_evaluation_revision")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Evaluation results are append-only")
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)
