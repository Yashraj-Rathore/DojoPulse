"""Application transactions for assignments, verified practice and frozen evaluation."""

from dataclasses import asdict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from analysis.contracts import EvaluationSpec, digest
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
    from backend.core.consents import require_processing

    require_processing(current)
    if (
        not current.is_active
        or Profile.objects.filter(user=owner, deleted_at__isnull=False).exists()
    ):
        raise ValidationError("Account is inactive")
    from backend.core.security import capacity_lock

    # Every loop write reads shared release grants before locking its domain rows.
    capacity_lock()


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
def create_assignment(owner, drill_key, *, request_id=None, diagnosis=None):
    require_active(owner)
    drill = DefinitionVersion.objects.get(pk=drill_key, kind="drill")
    from backend.core.knowledge import require_definition

    require_definition(
        drill_key,
        "synthetic" if drill.payload.get("synthetic_only") else "real",
        owner.pk,
        kind="drill",
    )
    from backend.core.practice import assignment_diagnosis

    input_hash = digest({"drill": drill_key, "diagnosis": diagnosis})
    if request_id:
        prior = DrillAssignment.objects.filter(owner=owner, request_id=request_id).first()
        if prior:
            if prior.diagnosis.get("input_hash") != input_hash or prior.status in {
                "WITHDRAWN",
                "CANCELLED",
            }:
                raise ValidationError("Assignment request belongs to different or withdrawn work")
            prior._created = False
            return prior
    snapshot = assignment_diagnosis(owner, drill, diagnosis) if diagnosis is not None else {}
    if request_id:
        snapshot["input_hash"] = input_hash
    item = DrillAssignment.objects.create(
        owner=owner,
        drill=drill,
        drill_hash=drill.content_hash,
        request_id=request_id,
        diagnosis=snapshot,
    )
    item._created = True
    return item


@transaction.atomic
def create_plan(
    owner,
    assignment_id,
    baseline_ids,
    baseline_end,
    followup_start,
    followup_end,
    *,
    schedule=None,
    request_id=None,
):
    require_active(owner)
    assignment = DrillAssignment.objects.select_for_update().get(pk=assignment_id, owner=owner)
    if assignment.status in {"WITHDRAWN", "CANCELLED"}:
        raise ValidationError("Assignment is withdrawn or cancelled")
    input_hash = digest(
        {
            "assignment": str(assignment_id),
            "baseline": sorted(map(str, baseline_ids)),
            "baseline_end": baseline_end,
            "followup_start": followup_start,
            "followup_end": followup_end,
            "schedule": schedule,
        }
    )
    if request_id:
        prior = EvaluationPlan.objects.filter(owner=owner, request_id=request_id).first()
        if prior:
            if prior.input_hash != input_hash:
                raise ValidationError("Plan request belongs to different frozen work")
            prior._created = False
            return prior
    events = owned_events(owner, baseline_ids)
    require_complete_captures(events)
    if not events:
        raise ValidationError("Baseline cannot be empty")
    from backend.core.search import current_events

    if set(
        current_events(owner).filter(pk__in=[e.pk for e in events]).values_list("pk", flat=True)
    ) != {e.pk for e in events}:
        raise ValidationError("Baseline must use the current analysis publication")
    evidence = [as_opportunity(e) for e in events]
    if any(e.deleted or e.mode != "ranked" for e in evidence):
        raise ValidationError("Baseline must be undeleted real-match evidence")
    if any(not e.match.chronology_verified for e in events):
        raise ValidationError("Chronology requires review")
    first = evidence[0]
    from backend.core.player_model import scope_of

    if len({digest(scope_of(e)) for e in events}) != 1:
        raise ValidationError("Baseline measurement hashes or platforms are mixed")
    for field, value in (
        ("metric_definition", first.metric),
        ("knowledge_revision", first.knowledge_revision),
    ):
        if field in assignment.drill.payload and assignment.drill.payload[field] != value:
            raise ValidationError("Drill does not match baseline measurement")
    reviewed_workflow = assignment.drill.payload.get("practice_workflow")
    if reviewed_workflow and reviewed_workflow["context"] != first.context:
        raise ValidationError("Drill context does not match baseline")
    if assignment.diagnosis.get("membership"):
        pinned = dict(assignment.diagnosis["membership"])
        if any(pinned.get(e.id) != e.content_hash for e in evidence):
            raise ValidationError("Baseline must belong to the pinned assignment diagnosis")
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
    from backend.core.knowledge import effective

    approved = effective(assignment.drill, first.dataset_kind, owner.pk) and all(
        (definition := DefinitionVersion.objects.filter(pk=key).first())
        and effective(definition, first.dataset_kind, owner.pk)
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
    from backend.core.comparisons import make_protocol

    if specification.dataset_kind == "real" and schedule is None:
        raise ValidationError("Real comparison requires a prospective collection schedule")
    protocol = make_protocol(schedule, specification, events) if schedule is not None else {}
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
    item = EvaluationPlan.objects.create(
        owner=owner,
        assignment=assignment,
        specification=asdict(specification),
        protocol=protocol,
        request_id=request_id,
        input_hash=input_hash,
    )
    item._created = True
    return item


@transaction.atomic
def record_practice(owner, assignment_id, event_ids, *, request_id=None):
    require_active(owner)
    assignment = DrillAssignment.objects.select_for_update().get(pk=assignment_id, owner=owner)
    if assignment.status in {"WITHDRAWN", "CANCELLED"}:
        raise ValidationError("Assignment is withdrawn or cancelled")
    from backend.core.knowledge import require_definition

    require_definition(
        assignment.drill_id,
        "synthetic" if assignment.drill.payload.get("synthetic_only") else "real",
        owner.pk,
        kind="drill",
    )
    events = owned_events(owner, event_ids)
    if not events:
        raise ValidationError("No practice evidence")
    from backend.core.practice import capture_end, validate_link

    validate_link(owner, assignment, events)
    if request_id:
        prior = TrainingSession.objects.filter(owner=owner, request_id=request_id).first()
        if prior:
            if prior.assignment_id != assignment.pk or sorted(
                prior.setup.get("event_ids", [])
            ) != sorted(map(str, event_ids)):
                raise ValidationError("Practice request belongs to different evidence")
            prior._created = False
            return prior
    if DrillAttempt.objects.filter(session__assignment=assignment).count() + len(events) > 2000:
        raise ValidationError(
            "Practice exceeds 2000 linked trials; create a new reviewed assignment"
        )
    situation = assignment.drill.payload["situation_definition"]
    if any(
        e.match.mode != "practice"
        or not e.verified
        or e.deleted_at
        or e.match.deleted_at
        or not e.match.asset_id
        or e.match.asset.deleted_at
        or (e.match.asset.retain_until and e.match.asset.retain_until <= timezone.now())
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
    completed_at = max(capture_end(e) for e in events)
    session = TrainingSession.objects.create(
        owner=owner,
        assignment=assignment,
        completed_at=completed_at,
        request_id=request_id,
        setup={
            "verification": "human-adjudication/1",
            "event_ids": sorted(str(e.pk) for e in events),
            "drill_hash": assignment.drill.content_hash,
            "workflow_hash": digest(assignment.drill.payload.get("practice_workflow")),
        },
    )
    for i, event in enumerate(events):
        DrillAttempt.objects.create(
            session=session, source_event=event, trial_index=i, played_key=played_keys[i]
        )
    assignment.status = "PRACTICED"
    assignment.save(update_fields=["status"])
    session._created = True
    return session


@transaction.atomic
def evaluate_plan(owner, plan_id, followup_ids=None, *, phase="FOLLOWUP"):
    require_active(owner)
    plan = EvaluationPlan.objects.select_for_update().get(pk=plan_id, owner=owner)
    from backend.core.comparisons import evaluate_comparison

    return evaluate_comparison(owner, plan, followup_ids, phase)


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
        selected += result.result.get("practice_membership", []) + result.result.get(
            "reference_membership", []
        )
        if ids.intersection(str(x[0]) for x in selected):
            ImprovementEvaluation.objects.filter(pk=result.pk).update(invalidated_at=timezone.now())
