"""Minimal relational loop. Dense observations and immutable configuration stay in artifacts/JSON."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

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
    onboarding_completed_at = models.DateTimeField(null=True)
    display_timezone = models.CharField(max_length=20, default="UTC")
    analysis_notices = models.BooleanField(default=True)
    practice_notices = models.BooleanField(default=True)
    followup_notices = models.BooleanField(default=True)
    session_epoch = models.PositiveIntegerField(default=0)
    processing_withdrawn_at = models.DateTimeField(null=True)


class AccountEmail(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    normalized = models.EmailField(unique=True)
    verified_at = models.DateTimeField(null=True)


class AccountChallenge(Owned):
    activates_account = models.BooleanField(default=False)
    purpose = models.CharField(max_length=20)
    token_digest = models.CharField(max_length=64, unique=True)
    email = models.EmailField()
    auth_state = models.CharField(max_length=64)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True)


class AccountSession(Owned):
    key_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)


class ConsentReceipt(Owned):
    scope = models.CharField(max_length=20)
    action = models.CharField(max_length=12)
    policy_version = models.CharField(max_length=60)
    policy_digest = models.CharField(max_length=64)
    source = models.CharField(max_length=30)
    request_id = models.UUIDField(default=uuid.uuid4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="consent_request")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Consent receipts are append-only")
        super().save(*args, **kwargs)


class MatchSuppression(Owned):
    provider = models.CharField(max_length=100)
    key_digest = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "provider", "key_digest"], name="suppressed_source"
            )
        ]


class Feedback(Owned):
    category = models.CharField(max_length=20)
    message = models.TextField(max_length=2000)
    event = models.ForeignKey("GameplayEvent", on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, default="OPEN")
    request_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="feedback_request")
        ]


class NoticeReceipt(Owned):
    key = models.CharField(max_length=150)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "key"], name="notice_receipt")]


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
        choices=[
            (x, x)
            for x in (
                "build",
                "move",
                "knowledge",
                "situation",
                "metric",
                "drill",
                "capture",
                "compatibility",
            )
        ],
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
    storage_provider = models.CharField(max_length=12, default="LOCAL")
    storage_generation = models.CharField(max_length=30, blank=True)
    source_sha256 = models.CharField(max_length=64, blank=True)
    bytes = models.PositiveBigIntegerField(default=0)
    metadata = models.JSONField(default=dict)
    deleted_at = models.DateTimeField(null=True)
    purge_completed_at = models.DateTimeField(null=True)
    upload_session = models.TextField(
        blank=True
    )  # Secret: scoped transfer only; no logs/exports/controls.
    upload_cancelled = models.BooleanField(default=False)
    upload_expires_at = models.DateTimeField(null=True)  # Non-secret upstream capability deadline.
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

    class Meta:
        indexes = [models.Index(fields=["owner", "-played_at", "-id"], name="history_owner_played")]


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
    heartbeat_at = models.DateTimeField(null=True)
    deadline_at = models.DateTimeField(null=True)
    progress = models.PositiveSmallIntegerField(default=0)
    phase = models.CharField(max_length=30, default="QUEUED")
    result = models.JSONField(default=dict)
    error_code = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_key"], name="run_idempotency")
        ]


class RunDispatch(models.Model):
    """Transactional intent; transport retries cannot create a second execution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.OneToOneField(AnalysisRun, on_delete=models.CASCADE)
    generation = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, default="PENDING", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    lease_until = models.DateTimeField(null=True)
    task_name = models.CharField(max_length=500, blank=True)
    operation_name = models.CharField(max_length=500, blank=True)
    error_code = models.CharField(max_length=60, blank=True)


class ExecutionSlot(models.Model):
    """Physical capacity remains reserved until the runtime confirms it has stopped."""

    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    fence = models.PositiveIntegerField()
    runtime = models.CharField(max_length=20, default="LOCAL")
    execution_name = models.CharField(max_length=500, blank=True)
    stop_requested_at = models.DateTimeField(null=True)
    released_at = models.DateTimeField(null=True, db_index=True)
    started_at = models.DateTimeField(null=True)
    claimed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["run", "fence"], name="execution_attempt")]


class RunBudget(models.Model):
    run = models.OneToOneField(AnalysisRun, on_delete=models.CASCADE)
    day = models.DateField(default=timezone.localdate, db_index=True)
    state = models.CharField(max_length=10, default="OPEN")
    reserved_media_seconds = models.PositiveIntegerField(default=600)
    reserved_processing_seconds = models.PositiveIntegerField()
    charged_media_seconds = models.PositiveIntegerField(default=0)
    charged_processing_seconds = models.PositiveIntegerField(default=0)
    settled_at = models.DateTimeField(null=True)
    measurement_complete = models.BooleanField(default=False)
    attempt_seconds = models.PositiveIntegerField(default=420)
    max_attempts = models.PositiveSmallIntegerField(default=3)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(state__in=["OPEN", "CLOSED"]), name="run_budget_state"
            )
        ]


class AttemptMetric(models.Model):
    slot = models.OneToOneField(ExecutionSlot, on_delete=models.CASCADE)
    attempt_number = models.PositiveSmallIntegerField(default=1)
    queued_seconds = models.FloatField(null=True)
    elapsed_seconds = models.FloatField(null=True)
    coordinator_cpu_seconds = models.FloatField(null=True)
    coordinator_peak_rss_bytes = models.PositiveBigIntegerField(null=True)
    decoder_cpu_seconds = models.FloatField(null=True)
    decoder_peak_rss_bytes = models.PositiveBigIntegerField(null=True)
    source_bytes = models.PositiveBigIntegerField(null=True)
    media_seconds = models.FloatField(null=True)
    derived_bytes = models.PositiveBigIntegerField(null=True)
    outcome = models.CharField(max_length=30, default="PROCESSING")


class RequestMetric(models.Model):
    minute = models.DateTimeField(db_index=True)
    route = models.CharField(max_length=20)
    count = models.PositiveIntegerField(default=0)
    server_errors = models.PositiveIntegerField(default=0)
    throttled = models.PositiveIntegerField(default=0)
    seconds = models.FloatField(default=0)
    max_seconds = models.FloatField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["minute", "route"], name="request_metric_bucket")
        ]


class OperatorWork(Owned):
    kind = models.CharField(max_length=12)
    seconds = models.PositiveIntegerField()
    scope = models.CharField(max_length=12, default="SYNTHETIC")
    request_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="operator_work_request"),
            models.CheckConstraint(
                condition=Q(scope__in=["SYNTHETIC", "OBSERVED"])
                & Q(kind__in=["REVIEW", "SUPPORT"])
                & Q(seconds__gt=0, seconds__lte=28800),
                name="operator_work_valid",
            ),
        ]


class CostObservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    component = models.CharField(max_length=20)
    period_start = models.DateField()
    period_end = models.DateField()
    scope = models.CharField(max_length=12)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=6)
    reference = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["component", "period_start", "period_end", "scope"],
                name="cost_observation_period",
            ),
            models.CheckConstraint(
                condition=Q(amount_usd__gte=0)
                & Q(period_end__gte=F("period_start"))
                & Q(scope__in=["SYNTHETIC", "OBSERVED"])
                & Q(component__in=["INFRASTRUCTURE", "PROVIDER", "REVIEW", "SUPPORT"]),
                name="cost_observation_valid",
            ),
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
    # Knowledge revisions vary by analysis, never by rewriting original capture facts.
    measurement = models.JSONField(default=dict)
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
    request_id = models.UUIDField(null=True)
    drill_hash = models.CharField(max_length=64, default="")
    diagnosis = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "request_id"], name="unique_assignment_request"
            )
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if any(
                getattr(old, field) != getattr(self, field)
                for field in ("owner_id", "drill_id", "drill_hash", "diagnosis", "request_id")
            ):
                raise ValidationError("Assignment source and version pins are immutable")
        return super().save(*args, **kwargs)


class TrainingSession(Owned):
    assignment = models.ForeignKey(DrillAssignment, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(null=True)
    mode = models.CharField(max_length=40, default="recorded_in_game")
    setup = models.JSONField(default=dict)
    request_id = models.UUIDField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="unique_practice_request")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Recorded practice sessions and source pins are immutable")
        return super().save(*args, **kwargs)


class PracticeLog(Owned):
    """Adherence self-report only; never a verified DrillAttempt or evaluation exposure."""

    assignment = models.ForeignKey(DrillAssignment, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    state = models.CharField(max_length=16)
    started_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)
    reported_attempts = models.PositiveIntegerField(null=True)
    obstacle = models.CharField(max_length=24, default="NONE")
    pins = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "Practice self-reports are immutable; withdraw and create a new receipt"
            )
        kwargs["force_insert"] = True
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "request_id"], name="unique_practice_log_request"
            ),
            models.CheckConstraint(
                condition=Q(state__in=["COMPLETED", "INTERRUPTED", "SKIPPED", "DELETED"]),
                name="valid_practice_log_state",
            ),
            models.CheckConstraint(
                condition=Q(state="DELETED")
                | (
                    Q(
                        started_at__isnull=False,
                        ended_at__isnull=False,
                        reported_attempts__isnull=False,
                    )
                    & Q(ended_at__gte=F("started_at"))
                    & Q(reported_attempts__lte=2000)
                ),
                name="practice_log_bounded_times",
            ),
        ]


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
    protocol = models.JSONField(default=dict)
    request_id = models.UUIDField(null=True)
    input_hash = models.CharField(max_length=64, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="unique_plan_request")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("EvaluationPlan is frozen")
        self.content_hash = (
            digest({"specification": self.specification, "protocol": self.protocol})
            if self.protocol
            else digest(self.specification)
        )
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)


class ImprovementEvaluation(Owned):
    plan = models.ForeignKey(EvaluationPlan, on_delete=models.CASCADE, related_name="evaluations")
    revision = models.PositiveIntegerField()
    result = models.JSONField()
    invalidated_at = models.DateTimeField(null=True)
    phase = models.CharField(max_length=16, default="FOLLOWUP")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["plan", "revision"], name="unique_evaluation_revision")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Evaluation results are append-only")
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)


class ComparisonSession(Owned):
    """Append-only owned play ledger; reported gaps never become gameplay observations."""

    plan = models.ForeignKey(EvaluationPlan, on_delete=models.CASCADE)
    phase = models.CharField(max_length=16)
    session_key = models.CharField(max_length=64)
    code = models.CharField(max_length=100, default="")
    revision = models.PositiveIntegerField()
    request_id = models.UUIDField()
    state = models.CharField(max_length=16)
    played_at = models.DateTimeField(null=True)
    match_ids = models.JSONField(default=list)
    content_hash = models.CharField(max_length=64)
    input_hash = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Comparison session receipts are append-only")
        kwargs["force_insert"] = True
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "request_id"], name="unique_comparison_session_request"
            ),
            models.UniqueConstraint(
                fields=["plan", "phase", "session_key", "revision"],
                name="unique_comparison_session_revision",
            ),
            models.CheckConstraint(
                condition=Q(phase__in=["FOLLOWUP", "RETENTION"]), name="valid_comparison_phase"
            ),
            models.CheckConstraint(
                condition=Q(state__in=["RECORDED", "MISSING", "SKIPPED", "DELETED"]),
                name="valid_comparison_session_state",
            ),
        ]


class SecurityMutex(models.Model):
    """Serializes admission across owners; always acquire after the owner lock."""

    key = models.CharField(max_length=40, primary_key=True)


class RequestBudget(models.Model):
    """Short-lived keyed digests, never raw addresses or credentials."""

    key = models.CharField(max_length=64, primary_key=True)
    expires_at = models.DateTimeField(db_index=True)
    count = models.PositiveIntegerField(default=0)


class UploadAdmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(db_index=True)
    reserved_bytes = models.PositiveBigIntegerField()


class UploadSession(Owned):
    asset = models.OneToOneField(ReplayAsset, on_delete=models.PROTECT)
    match = models.ForeignKey(Match, on_delete=models.PROTECT, null=True)
    request_id = models.UUIDField()
    claim_digest = models.CharField(max_length=64)
    expected_sha256 = models.CharField(max_length=64)
    expected_md5 = models.CharField(max_length=24)
    received_bytes = models.PositiveBigIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
    state = models.CharField(max_length=20, default="INITIALIZING")
    fence = models.PositiveIntegerField(default=0)
    verification_lease = models.DateTimeField(null=True)
    verification_attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True)
    error_code = models.CharField(max_length=60, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="upload_session_request"),
            models.CheckConstraint(
                condition=Q(
                    state__in=[
                        "INITIALIZING",
                        "UPLOADING",
                        "VERIFYING",
                        "COMPLETE",
                        "PURGING",
                        "CANCELLED",
                    ]
                ),
                name="upload_session_state",
            ),
        ]


class RecordingDevice(Owned):
    label = models.CharField(max_length=60)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)
    last_seen_at = models.DateTimeField(null=True)


class DevicePairing(Owned):
    label = models.CharField(max_length=60)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True)


class RecordingReceipt(Owned):
    device = models.ForeignKey(RecordingDevice, on_delete=models.PROTECT)
    # Keyed byte identity remains as a suppression receipt after remote deletion.
    key_digest = models.CharField(max_length=64)
    suppressed = models.BooleanField(default=False)
    request_id = models.UUIDField(default=uuid.uuid4)
    session = models.OneToOneField(UploadSession, on_delete=models.PROTECT, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "key_digest"], name="recording_byte_receipt")
        ]


class PilotStudy(Owned):
    title = models.CharField(max_length=80)
    dataset_kind = models.CharField(max_length=12)
    protocol = models.JSONField()
    protocol_digest = models.CharField(max_length=64)
    state = models.CharField(max_length=12, default="COLLECTING")
    revision = models.PositiveIntegerField(default=1)
    request_id = models.UUIDField()
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="pilot_study_request"),
            models.CheckConstraint(
                condition=Q(dataset_kind__in=["synthetic", "real"])
                & Q(state__in=["COLLECTING", "FROZEN", "CLOSED"]),
                name="pilot_study_valid",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Study protocol is immutable; use a new study revision")
        self.protocol_digest = digest(self.protocol)
        super().save(*args, **kwargs)


class PilotEnrollment(Owned):
    study = models.ForeignKey(PilotStudy, on_delete=models.CASCADE)
    role = models.CharField(max_length=16)
    pseudonym = models.UUIDField(default=uuid.uuid4, editable=False)
    split = models.CharField(max_length=16, default="development")
    comparison_order = models.CharField(max_length=20, default="UNASSIGNED")
    state = models.CharField(max_length=12, default="ACTIVE")
    consent_digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    evaluation = models.ForeignKey(ImprovementEvaluation, on_delete=models.SET_NULL, null=True)
    evaluation_digest = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["study", "owner"], name="pilot_one_role"),
            models.CheckConstraint(
                condition=Q(role__in=["PARTICIPANT", "REVIEWER", "ADJUDICATOR", "EXPERT"])
                & Q(state__in=["ACTIVE", "WITHDRAWN"])
                & Q(split__in=["development", "validation", "held-out"]),
                name="pilot_enrollment_valid",
            ),
        ]


class PilotSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(PilotEnrollment, on_delete=models.CASCADE)
    code = models.CharField(max_length=60)
    phase = models.CharField(max_length=16)
    played_at = models.DateTimeField()
    playable_seconds = models.PositiveIntegerField(null=True)
    state = models.CharField(max_length=20)
    unaided = models.BooleanField(default=False)
    setup_seconds = models.PositiveIntegerField(null=True)
    useful = models.BooleanField(null=True)
    insight_seconds = models.PositiveIntegerField(null=True)
    request_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "code"], name="pilot_session_code"),
            models.UniqueConstraint(
                fields=["enrollment", "request_id"], name="pilot_session_request"
            ),
        ]


class PilotCapture(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(PilotSession, on_delete=models.CASCADE)
    asset = models.ForeignKey(ReplayAsset, on_delete=models.SET_NULL, null=True)
    source_sha256 = models.CharField(max_length=64, blank=True)
    game_build = models.CharField(max_length=80, blank=True)
    duration_seconds = models.FloatField()
    original_retain_until = models.DateTimeField(null=True)
    provenance = models.JSONField(default=dict)
    withdrawn_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "asset"], name="pilot_capture_source")
        ]


class PilotTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    capture = models.ForeignKey(PilotCapture, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12)
    start_us = models.PositiveBigIntegerField()
    end_us = models.PositiveBigIntegerField()
    reviewer_one = models.ForeignKey(PilotEnrollment, on_delete=models.PROTECT, related_name="+")
    reviewer_two = models.ForeignKey(PilotEnrollment, on_delete=models.PROTECT, related_name="+")
    adjudicator = models.ForeignKey(PilotEnrollment, on_delete=models.PROTECT, related_name="+")
    prediction = models.JSONField(null=True)
    request_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["capture", "request_id"], name="pilot_task_request"),
            models.CheckConstraint(
                condition=Q(end_us__gte=F("start_us")) & Q(kind__in=["QC", "TARGET", "TRIAL"]),
                name="pilot_task_valid",
            ),
        ]


class PilotReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(PilotTask, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(PilotEnrollment, on_delete=models.PROTECT)
    label = models.JSONField()
    label_digest = models.CharField(max_length=64)
    seconds = models.PositiveIntegerField()
    request_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "reviewer"], name="pilot_independent_review")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Pilot reviews are immutable")
        super().save(*args, **kwargs)


class PilotGateReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    study = models.ForeignKey(PilotStudy, on_delete=models.CASCADE)
    gate = models.CharField(max_length=2)
    revision = models.PositiveIntegerField()
    data = models.JSONField()
    content_hash = models.CharField(max_length=64)
    invalidated_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["study", "gate", "revision"], name="pilot_gate_revision"
            )
        ]


class PilotDecision(models.Model):
    report = models.OneToOneField(PilotGateReport, on_delete=models.CASCADE)
    actor = models.ForeignKey(PilotEnrollment, on_delete=models.PROTECT)
    action = models.CharField(max_length=12)
    reason = models.CharField(max_length=30)
    reference = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)


class KnowledgeProposal(Owned):
    """Sealed candidate and explicitly shared sources; state is a revocable release grant."""

    key = models.CharField(max_length=160, unique=True)
    kind = models.CharField(max_length=30)
    game_build = models.ForeignKey(GameBuild, on_delete=models.PROTECT)
    dataset_kind = models.CharField(max_length=12)
    payload = models.JSONField()
    provenance = models.JSONField()
    content_hash = models.CharField(max_length=64)
    reviewer_one = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    reviewer_two = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    published = models.OneToOneField(DefinitionVersion, on_delete=models.PROTECT, null=True)
    state = models.CharField(max_length=12, default="OPEN")
    reason = models.CharField(max_length=30, blank=True)
    request_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "request_id"], name="knowledge_proposal_request"
            ),
            models.CheckConstraint(
                condition=~Q(reviewer_one=F("reviewer_two"))
                & ~Q(owner=F("reviewer_one"))
                & ~Q(owner=F("reviewer_two")),
                name="knowledge_independent_reviewers",
            ),
        ]


class KnowledgeEvidence(models.Model):
    proposal = models.ForeignKey(
        KnowledgeProposal, on_delete=models.CASCADE, related_name="sources"
    )
    asset = models.ForeignKey(ReplayAsset, on_delete=models.PROTECT)
    snapshot = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proposal", "asset"], name="knowledge_source")
        ]


class KnowledgeReview(Owned):
    proposal = models.ForeignKey(
        KnowledgeProposal, on_delete=models.CASCADE, related_name="reviews"
    )
    decision = models.CharField(max_length=12)
    note = models.TextField(max_length=2000)
    proposal_hash = models.CharField(max_length=64)
    request_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proposal", "owner"], name="knowledge_review_once")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Knowledge reviews are immutable")
        super().save(*args, **kwargs)


class KnowledgeReanalysis(Owned):
    match = models.ForeignKey(Match, on_delete=models.PROTECT)
    mapping = models.ForeignKey(DefinitionVersion, on_delete=models.PROTECT, related_name="+")
    target = models.ForeignKey(DefinitionVersion, on_delete=models.PROTECT, related_name="+")
    run = models.OneToOneField(AnalysisRun, on_delete=models.PROTECT)
    snapshot = models.JSONField()
    request_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "request_id"], name="knowledge_reanalysis_request"
            )
        ]


class DatasetCollection(Owned):
    title = models.CharField(max_length=80)
    dataset_kind = models.CharField(max_length=12)
    knowledge = models.ForeignKey(DefinitionVersion, on_delete=models.PROTECT)
    measurement = models.JSONField()
    sampling = models.JSONField()
    state = models.CharField(max_length=12, default="COLLECTING")
    request_id = models.UUIDField()
    deleted_at = models.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Dataset specification is immutable; create a new collection")
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="dataset_request"),
            models.CheckConstraint(
                condition=Q(dataset_kind__in=["synthetic", "real"])
                & Q(state__in=["COLLECTING", "FROZEN", "CLOSED"]),
                name="dataset_collection_valid",
            ),
        ]


class DatasetStudy(models.Model):
    dataset = models.ForeignKey(DatasetCollection, on_delete=models.CASCADE, related_name="studies")
    study = models.OneToOneField(PilotStudy, on_delete=models.PROTECT)


class DatasetPartition(models.Model):
    """Keyed leakage guards; no raw identity, source hash or session code."""

    dataset = models.ForeignKey(DatasetCollection, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12)
    token = models.CharField(max_length=64)
    binding = models.CharField(max_length=64, blank=True)
    split = models.CharField(max_length=16)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dataset", "kind", "token"], name="dataset_partition"),
            models.CheckConstraint(
                condition=Q(kind__in=["PLAYER", "SESSION", "SOURCE"])
                & Q(split__in=["development", "validation", "held-out"]),
                name="dataset_partition_valid",
            ),
        ]


class DatasetSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        DatasetCollection, on_delete=models.CASCADE, related_name="snapshots"
    )
    sequence = models.PositiveIntegerField()
    request_id = models.UUIDField()
    data = models.JSONField()
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    invalidated_at = models.DateTimeField(null=True)
    reason = models.CharField(max_length=30, blank=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "Dataset snapshots are immutable; invalidation may erase private data"
            )
        self.content_hash = digest(self.data)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dataset", "sequence"], name="dataset_sequence"),
            models.UniqueConstraint(
                fields=["dataset", "request_id"], name="dataset_snapshot_request"
            ),
        ]


class DetectorVersion(Owned):
    dataset = models.ForeignKey(DatasetCollection, on_delete=models.PROTECT)
    version = models.CharField(max_length=160)
    manifest = models.JSONField()
    content_hash = models.CharField(max_length=64)
    state = models.CharField(max_length=16, default="REGISTERED")
    request_id = models.UUIDField()
    reviewer_one = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="detector_review_one"
    )
    reviewer_two = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="detector_review_two"
    )
    activated_at = models.DateTimeField(null=True)
    disabled_reason = models.CharField(max_length=40, blank=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Detector configuration is immutable; register a new version")
        self.content_hash = digest(self.manifest)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "version"], name="detector_owner_version"),
            models.UniqueConstraint(fields=["owner", "request_id"], name="detector_request"),
            models.UniqueConstraint(
                fields=["dataset"], condition=Q(state="ACTIVE"), name="detector_active_dataset"
            ),
            models.CheckConstraint(
                condition=Q(state__in=["REGISTERED", "ACTIVE", "DISABLED", "INVALIDATED"]),
                name="detector_state_valid",
            ),
        ]


class RecognitionRun(Owned):
    detector = models.ForeignKey(DetectorVersion, on_delete=models.CASCADE, related_name="runs")
    snapshot = models.ForeignKey(DatasetSnapshot, on_delete=models.PROTECT)
    request_id = models.UUIDField()
    inputs = models.JSONField()
    report = models.JSONField()
    input_hash = models.CharField(max_length=64)
    content_hash = models.CharField(max_length=64)
    invalidated_at = models.DateTimeField(null=True)
    reason = models.CharField(max_length=40, blank=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "Recognition receipts are immutable; invalidation erases private inputs"
            )
        self.input_hash = digest(self.inputs)
        self.content_hash = digest(self.report)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "request_id"], name="recognition_run_request")
        ]


class DetectorReview(Owned):
    run = models.ForeignKey(RecognitionRun, on_delete=models.CASCADE, related_name="reviews")
    decision = models.CharField(max_length=10)
    report_hash = models.CharField(max_length=64)
    request_id = models.UUIDField()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Detector reviews are immutable")
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "owner"], name="detector_independent_review"),
            models.UniqueConstraint(fields=["owner", "request_id"], name="detector_review_request"),
            models.CheckConstraint(
                condition=Q(decision__in=["APPROVE", "REJECT"]), name="detector_review_valid"
            ),
        ]
