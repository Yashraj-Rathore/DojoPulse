"""Application transactions for assignments, verified practice and frozen evaluation."""

from dataclasses import asdict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from analysis.contracts import EvaluationSpec, digest
from analysis.evaluation import evaluate
from backend.core.evidence import as_opportunity
from backend.core.models import (
    DefinitionVersion,
    DrillAssignment,
    DrillAttempt,
    EvaluationPlan,
    GameplayEvent,
    ImprovementEvaluation,
    Profile,
    Recommendation,
    TrainingSession,
)
from backend.core.ownership import lock_owner


def owned_events(owner, ids):
    strings = [str(x) for x in ids]
    if len(strings) != len(set(strings)):
        raise ValidationError("Duplicate event IDs")
    events = list(
        GameplayEvent.objects.filter(owner=owner, pk__in=strings).select_related("match__asset")
    )
    if len(events) != len(strings):
        raise ValidationError("Missing or unauthorized evidence")
    selected_runs = {}
    for event in events:
        if event.match_id in selected_runs and selected_runs[event.match_id] != event.run_id:
            raise ValidationError("Select one analysis revision per match")
        selected_runs[event.match_id] = event.run_id
    return events


def require_active(owner):
    current = lock_owner(owner.pk)
    if (
        not current.is_active
        or Profile.objects.filter(user=owner, deleted_at__isnull=False).exists()
    ):
        raise ValidationError("Account is inactive")


def require_complete_captures(events):
    """Selection cannot silently drop unfavorable/unknown rows inside a reviewed capture."""
    selected = {e.pk for e in events}
    for match_id, run_id in {(e.match_id, e.run_id) for e in events}:
        expected = set(
            GameplayEvent.objects.filter(match_id=match_id, run_id=run_id).values_list(
                "pk", flat=True
            )
        )
        if not expected.issubset(selected):
            raise ValidationError("Select every reviewed opportunity in each chosen capture")


@transaction.atomic
def create_assignment(owner, drill_key):
    require_active(owner)
    drill = DefinitionVersion.objects.get(pk=drill_key, kind="drill")
    if drill.status != "APPROVED":
        raise ValidationError("Drill awaits expert review; assignment is gated")
    return DrillAssignment.objects.create(owner=owner, drill=drill)


@transaction.atomic
def create_plan(owner, assignment_id, baseline_ids, baseline_end, followup_start, followup_end):
    require_active(owner)
    assignment = DrillAssignment.objects.select_for_update().get(pk=assignment_id, owner=owner)
    events = owned_events(owner, baseline_ids)
    require_complete_captures(events)
    if not events:
        raise ValidationError("Baseline cannot be empty")
    evidence = [as_opportunity(e) for e in events]
    if any(e.deleted or e.mode != "ranked" for e in evidence):
        raise ValidationError("Baseline must be undeleted real-match evidence")
    if any(not e.match.chronology_verified for e in events):
        raise ValidationError("Chronology requires review")
    first = evidence[0]
    if (
        assignment.drill.payload.get("situation_definition") != first.situation
        or assignment.drill.payload.get("game_build") != first.game_build
    ):
        raise ValidationError("Drill does not match baseline situation/build")
    for e in evidence:
        if (
            e.situation,
            e.metric,
            e.context,
            e.game_build,
            e.knowledge_revision,
            e.detector_version,
            e.dataset_kind,
        ) != (
            first.situation,
            first.metric,
            first.context,
            first.game_build,
            first.knowledge_revision,
            first.detector_version,
            first.dataset_kind,
        ):
            raise ValidationError("Baseline definitions are mixed")
    approved = assignment.drill.status == "APPROVED" and all(
        DefinitionVersion.objects.filter(pk=key, status="APPROVED").exists()
        for key in (first.situation, first.metric, first.knowledge_revision)
    )
    specification = EvaluationSpec(
        situation=first.situation,
        metric=first.metric,
        context=first.context,
        baseline_membership=tuple((e.id, e.content_hash) for e in evidence),
        compatible_builds=(first.game_build,),
        compatible_detectors=(first.detector_version,),
        compatible_knowledge=(first.knowledge_revision,),
        baseline_end=baseline_end,
        followup_start=followup_start,
        followup_end=followup_end,
        measurement_approved=approved,
        dataset_kind=first.dataset_kind,
    )
    from analysis.contracts import aware_time

    if first.dataset_kind == "real" and aware_time(followup_start) <= timezone.now():
        raise ValidationError("Real follow-up must be prospective; freeze before practice")

    if any(aware_time(e.played_at) > aware_time(baseline_end) for e in evidence):
        raise ValidationError("Baseline extends beyond cutoff")
    from analysis.statistics import summarize

    summary = summarize(evidence)
    recommendation = Recommendation.objects.create(
        owner=owner,
        situation=first.situation,
        metric=first.metric,
        baseline_event_ids=[e.id for e in evidence],
        summary=summary,
        state="MEASURED_BASELINE"
        if summary["denominator"] >= specification.minimum_sample
        else "INSUFFICIENT_BASELINE",
    )
    assignment.recommendation = recommendation
    assignment.save(update_fields=["recommendation"])
    return EvaluationPlan.objects.create(
        owner=owner, assignment=assignment, specification=asdict(specification)
    )


@transaction.atomic
def record_practice(owner, assignment_id, event_ids):
    require_active(owner)
    assignment = DrillAssignment.objects.select_for_update().get(pk=assignment_id, owner=owner)
    if assignment.drill.status != "APPROVED":
        raise ValidationError("Unreviewed drill")
    events = owned_events(owner, event_ids)
    if not events:
        raise ValidationError("No practice evidence")
    situation = assignment.drill.payload["situation_definition"]
    if any(
        e.match.mode != "practice"
        or not e.verified
        or e.deleted_at
        or e.match.deleted_at
        or not e.match.asset_id
        or e.match.asset.deleted_at
        or e.match.metadata_state == "REVIEW_REQUIRED"
        or e.situation != situation
        or not e.match.chronology_verified
        for e in events
    ):
        raise ValidationError("Verified compatible practice footage required")
    if any(e.match.game_build != assignment.drill.payload["game_build"] for e in events):
        raise ValidationError("Practice build incompatible with drill")
    if DrillAttempt.objects.filter(source_event__in=events).exists():
        raise ValidationError("Practice already assigned; cannot count twice")
    played_keys = [f"{e.match_id}:{e.played_key}" for e in events]
    if DrillAttempt.objects.filter(played_key__in=played_keys).exists():
        raise ValidationError("Reprocessed practice cannot count twice")
    completed_at = max(e.match.played_at for e in events)
    session = TrainingSession.objects.create(
        owner=owner,
        assignment=assignment,
        completed_at=completed_at,
        setup={"verification": "human-adjudication/1", "event_ids": [str(e.pk) for e in events]},
    )
    for i, event in enumerate(events):
        DrillAttempt.objects.create(
            session=session, source_event=event, trial_index=i, played_key=played_keys[i]
        )
    assignment.status = "PRACTICED"
    assignment.save(update_fields=["status"])
    return session


@transaction.atomic
def evaluate_plan(owner, plan_id, followup_ids):
    require_active(owner)
    plan = EvaluationPlan.objects.select_for_update().get(pk=plan_id, owner=owner)
    spec = EvaluationSpec.from_dict(plan.specification)
    from analysis.contracts import aware_time

    if spec.dataset_kind == "real" and timezone.now() < aware_time(spec.followup_end):
        raise ValidationError("Fixed follow-up window has not ended; no repeated peeking")
    baseline_ids = [key for key, _ in spec.baseline_membership]
    baseline = owned_events(owner, baseline_ids)
    followup = owned_events(owner, followup_ids)
    require_complete_captures(followup)
    if spec.dataset_kind == "real":
        from django.db.models import F

        expected = set(
            GameplayEvent.objects.filter(
                owner=owner,
                situation=spec.situation,
                metric=spec.metric,
                match__context=spec.context,
                match__mode="ranked",
                match__dataset_kind="real",
                match__played_at__gte=aware_time(spec.followup_start),
                match__played_at__lte=aware_time(spec.followup_end),
                run_id=F("match__analysispublication__run_id"),
            ).values_list("pk", flat=True)
        )
        if expected != {e.pk for e in followup}:
            raise ValidationError(
                "Follow-up must include every recorded target opportunity in the frozen window"
            )
    if any(not e.match.chronology_verified for e in baseline + followup):
        raise ValidationError("Chronology requires review")
    sessions = TrainingSession.objects.filter(
        assignment=plan.assignment, owner=owner, completed_at__isnull=False
    )
    from analysis.contracts import aware_time

    sessions = sessions.filter(
        completed_at__gte=aware_time(spec.baseline_end),
        completed_at__lte=aware_time(spec.followup_start),
    )
    attempts = DrillAttempt.objects.filter(
        session__in=sessions,
        source_event__deleted_at__isnull=True,
        source_event__match__deleted_at__isnull=True,
        source_event__match__asset__deleted_at__isnull=True,
        source_event__match__asset__isnull=False,
        source_event__eligibility="ELIGIBLE",
        source_event__outcome__in=["SUCCESS", "FAILURE"],
        source_event__verified=True,
        source_event__match__played_at__gte=aware_time(spec.baseline_end),
        source_event__match__played_at__lte=aware_time(spec.followup_start),
    ).exclude(source_event__match__metadata_state="REVIEW_REQUIRED")
    if spec.dataset_kind == "real":
        attempts = attempts.filter(source_event__match__played_at__gte=plan.created_at)
    completed = sessions.order_by("-completed_at").first()
    result = evaluate(
        spec,
        [as_opportunity(e) for e in baseline],
        [as_opportunity(e) for e in followup],
        verified_practice=attempts.count(),
        practice_completed_at=completed.completed_at.isoformat() if completed else None,
    )
    result["practice_membership"] = sorted(
        (str(a.source_event_id), as_opportunity(a.source_event).content_hash)
        for a in attempts.select_related("source_event__match__asset")
    )
    previous = plan.evaluations.order_by("-revision").first()
    if previous and digest(previous.result) == digest(result) and not previous.invalidated_at:
        return previous
    return ImprovementEvaluation.objects.create(
        owner=owner, plan=plan, revision=previous.revision + 1 if previous else 1, result=result
    )


def invalidate_for_events(event_ids):
    """Controlled lifecycle mutation; immutable result payload and memberships remain unchanged."""
    ids = set(map(str, event_ids))
    for recommendation in Recommendation.objects.exclude(state="INVALIDATED"):
        if ids.intersection(map(str, recommendation.baseline_event_ids)):
            Recommendation.objects.filter(pk=recommendation.pk).update(state="INVALIDATED")
    for result in ImprovementEvaluation.objects.select_related("plan").filter(
        invalidated_at__isnull=True
    ):
        selected = result.plan.specification["baseline_membership"] + result.result.get(
            "followup_membership", []
        )
        selected += result.result.get("practice_membership", [])
        if ids.intersection(str(x[0]) for x in selected):
            ImprovementEvaluation.objects.filter(pk=result.pk).update(invalidated_at=timezone.now())
