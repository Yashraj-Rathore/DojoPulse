"""Owned practice transactions; reports never become measured gameplay exposure."""

import math
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from analysis.contracts import EvaluationSpec, aware_time, digest
from analysis.practice import progression, workflow
from analysis.statistics import summarize
from backend.core.evidence import as_opportunity
from backend.core.knowledge import effective
from backend.core.models import DrillAssignment, DrillAttempt, EvaluationPlan, PracticeLog
from backend.core.player_model import projection, review_status, scope_of
from backend.core.search import current_events

OBSTACLES = {"NONE", "SETUP", "TIME", "CAPTURE", "UNCLEAR", "OTHER"}


def assignment_diagnosis(owner, drill, value):
    from backend.core.player_model_api import ModelInput

    if not isinstance(value, dict) or set(value) != {
        "card_id",
        "policy_hash",
        "evidence_hash",
        "filters",
    }:
        raise ValidationError("Supply the current diagnosis identity, hashes and filters")
    if not isinstance(value["filters"], dict):
        raise ValidationError("Diagnosis filters must be an object")
    data = ModelInput(data=value["filters"])
    data.is_valid(raise_exception=True)
    filters = {**data.validated_data, "offset": 0, "limit": 100}
    model = projection(owner, filters, include_membership=True)
    card = next((c for c in model["cards"] if c["id"] == value["card_id"]), None)
    if (
        not card
        or model["policy_hash"] != value["policy_hash"]
        or card["evidence_hash"] != value["evidence_hash"]
        or card["state"] != "OBSERVED_FAILURE_PATTERN"
        or drill.pk not in {d["key"] for d in card["drills"]}
    ):
        raise ValidationError("Diagnosis changed or is unqualified; refresh before assignment")
    if len(card["membership"]) > 2000:
        raise ValidationError("Assignment diagnosis exceeds 2000 windows; narrow its scope")
    return {
        "version": "assignment-diagnosis/1",
        "card_id": card["id"],
        "scope": card["scope"],
        "summary": card["summary"],
        "review": card["review"],
        "membership": card["membership"],
        "policy_hash": model["policy_hash"],
        "evidence_hash": card["evidence_hash"],
        "filters": {k: str(v) for k, v in filters.items()},
        "release_approved": False,
    }


def capture_end(event):
    duration = event.run.result.get("source", {}).get("duration_seconds")
    if (
        type(duration) not in (int, float)
        or not math.isfinite(duration)
        or not 0 < duration <= 14400
    ):
        raise ValidationError("Practice requires a bounded validated source duration")
    return event.match.played_at + timedelta(seconds=duration)


def frozen_baseline(owner, assignment):
    from backend.core.loops import owned_events

    plan = EvaluationPlan.objects.get(owner=owner, assignment=assignment)
    spec = EvaluationSpec.from_dict(plan.specification)
    events = owned_events(owner, [key for key, _ in spec.baseline_membership])
    observations = [as_opportunity(e) for e in events]
    if (
        any(o.deleted for o in observations)
        or sorted((o.id, o.content_hash) for o in observations) != sorted(spec.baseline_membership)
        or len({digest(scope_of(e)) for e in events}) != 1
    ):
        raise ValidationError("Frozen baseline evidence is unavailable or incompatible")
    return plan, spec, events, observations


def compatible(event, scope, plan, spec):
    if (
        scope_of(event) != scope
        or event.match.mode != "practice"
        or not event.match.chronology_verified
    ):
        return False
    if event.match.metadata_state == "REVIEW_REQUIRED" or not event.verified:
        return False
    if event.match.played_at < aware_time(spec.baseline_end) or capture_end(event) > aware_time(
        spec.followup_start
    ):
        return False
    if spec.dataset_kind == "real" and event.match.played_at < plan.created_at:
        return False
    return not as_opportunity(event).deleted


def validate_link(owner, assignment, events):
    from backend.core.loops import require_complete_captures

    require_complete_captures(events)
    if assignment.drill_hash != assignment.drill.content_hash:
        raise ValidationError("Assignment drill version pin requires review")
    try:
        plan, spec, baseline, _ = frozen_baseline(owner, assignment)
    except EvaluationPlan.DoesNotExist as error:
        raise ValidationError("Freeze a baseline plan before linking practice") from error
    current = set(
        current_events(owner).filter(pk__in=[e.pk for e in events]).values_list("pk", flat=True)
    )
    if current != {e.pk for e in events}:
        raise ValidationError("Practice must use the complete current analysis publication")
    scope = scope_of(baseline[0])
    if any(not compatible(e, scope, plan, spec) or not review_status(e)[0] for e in events):
        raise ValidationError(
            "Practice needs independent review, exact baseline scope and source end within frozen practice dates"
        )


def current_practice(owner, assignment, *, plan=None, spec=None, scope=None):
    """Preserve frozen links, but count only current authorized compatible sources."""
    if plan is None:
        plan, spec, baseline, _ = frozen_baseline(owner, assignment)
        scope = scope_of(baseline[0])
    attempts = DrillAttempt.objects.filter(session__owner=owner, session__assignment=assignment)
    if attempts.count() > 2000:
        raise ValidationError(
            "Practice exceeds 2000 linked trials; start a separately reviewed assignment"
        )
    events = [
        a.source_event
        for a in attempts.select_related("source_event__match", "source_event__run__asset")
    ]
    current = set(
        current_events(owner).filter(pk__in=[e.pk for e in events]).values_list("pk", flat=True)
    )
    available = []
    for event in events:
        try:
            valid = (
                event.pk in current
                and compatible(event, scope, plan, spec)
                and review_status(event)[0]
            )
        except (ValueError, ValidationError):
            valid = False
        if valid:
            available.append(event)
    return available, len(events) - len(available)


def assignment_detail(owner, assignment):
    data = {
        "id": str(assignment.pk),
        "status": assignment.status,
        "drill_id": assignment.drill_id,
        "drill_hash": assignment.drill_hash,
        "diagnosis": assignment.diagnosis,
        "workflow": None,
        "progression": None,
        "evidence": [],
        "blockers": [],
        "reports_count_as_verified_trials": False,
        "release_approved": False,
    }
    data["logs"] = list(
        PracticeLog.objects.filter(owner=owner, assignment=assignment)
        .exclude(state="DELETED")
        .order_by("-created_at")
        .values("id", "state", "started_at", "ended_at", "reported_attempts", "obstacle")[:50]
    )
    kind = "synthetic" if assignment.drill.payload.get("synthetic_only") else "real"
    if (
        assignment.drill_hash != assignment.drill.content_hash
        or assignment.status in {"CANCELLED", "WITHDRAWN"}
        or not effective(assignment.drill, kind, owner.pk)
    ):
        data["blockers"].append("ASSIGNMENT_OR_DRILL_UNAVAILABLE")
        return data
    value = assignment.drill.payload.get("practice_workflow")
    if not value:
        data["blockers"].append("REVIEWED_WORKFLOW_REQUIRED")
        return data
    data["workflow"] = workflow(value)
    try:
        plan, spec, baseline, observations = frozen_baseline(owner, assignment)
    except (EvaluationPlan.DoesNotExist, ValidationError, ValueError):
        data["blockers"].append("FROZEN_BASELINE_REQUIRED")
        return data
    summary = summarize(observations)
    reviews = [review_status(e) for e in baseline]
    baseline_ready = (
        summary["denominator"] >= spec.minimum_sample
        and summary["sessions"] >= spec.minimum_sessions
        and (summary["coverage"] or 0) >= spec.minimum_coverage
        and (summary["eligibility_coverage"] or 0) >= spec.minimum_coverage
        and all(r[0] for r in reviews)
        and sum(r[1] for r in reviews) / len(reviews) >= 0.8
    )
    events, unavailable = current_practice(
        owner, assignment, plan=plan, spec=spec, scope=scope_of(baseline[0])
    )
    reviews = [review_status(e) for e in events]
    reviewed = sum(r[0] for r in reviews)
    data["progression"] = progression(
        [as_opportunity(e) for e in events],
        value["progression"],
        reviewed=reviewed,
        agreement=sum(r[1] for r in reviews) / reviewed if reviewed else None,
        minimum_plan_practice=spec.minimum_practice,
        dataset_kind=spec.dataset_kind,
        baseline_available=baseline_ready,
        unavailable=unavailable,
    )
    data["plan"] = {
        "id": str(plan.pk),
        "content_hash": plan.content_hash,
        "baseline_end": spec.baseline_end,
        "followup_start": spec.followup_start,
        "followup_end": spec.followup_end,
    }
    data["unavailable_trials"] = unavailable
    data["evidence"] = [
        {
            "id": str(e.pk),
            "match_id": str(e.match_id),
            "asset_id": str(e.run.asset_id),
            "start_us": e.start_us,
            "end_us": e.end_us,
        }
        for e in events[:5]
    ]
    return data


@transaction.atomic
def log_practice(owner, assignment_id, values):
    from backend.core.loops import require_active

    require_active(owner)
    assignment = (
        DrillAssignment.objects.select_for_update()
        .select_related("drill")
        .get(owner=owner, pk=assignment_id)
    )
    if assignment.status in {"CANCELLED", "WITHDRAWN"}:
        raise ValidationError("Assignment is cancelled or withdrawn")
    kind = "synthetic" if assignment.drill.payload.get("synthetic_only") else "real"
    if assignment.drill_hash != assignment.drill.content_hash or not effective(
        assignment.drill, kind, owner.pk
    ):
        raise ValidationError("Reviewed drill is unavailable")
    workflow(assignment.drill.payload.get("practice_workflow"))
    start, end = values["started_at"], values["ended_at"]
    if (
        start > end
        or end - start > timedelta(hours=8)
        or end > timezone.now() + timedelta(minutes=5)
    ):
        raise ValidationError("Use ordered times, up to eight hours, without future sessions")
    count, state = values["reported_attempts"], values["state"]
    if values["obstacle"] not in OBSTACLES or state not in {"COMPLETED", "INTERRUPTED", "SKIPPED"}:
        raise ValidationError("Invalid session state or obstacle")
    if (
        type(count) is not int
        or not 0 <= count <= 2000
        or (state == "SKIPPED" and count)
        or (state == "COMPLETED" and not count)
    ):
        raise ValidationError(
            "Skipped sessions have zero attempts; completed sessions require 1-2000"
        )
    input_hash = digest(
        {k: str(v) if k in {"started_at", "ended_at"} else v for k, v in values.items()}
    )
    prior = PracticeLog.objects.filter(owner=owner, request_id=values["request_id"]).first()
    if prior:
        if (
            prior.state == "DELETED"
            or prior.assignment_id != assignment.pk
            or prior.pins.get("input_hash") != input_hash
        ):
            raise ValidationError("Report request belongs to deleted or different work")
        prior._created = False
        return prior
    if PracticeLog.objects.filter(owner=owner, assignment=assignment).count() >= 1000:
        raise ValidationError("Assignment already has 1000 self-report receipts")
    plan = EvaluationPlan.objects.filter(assignment=assignment, owner=owner).first()
    item = PracticeLog.objects.create(
        owner=owner,
        assignment=assignment,
        **values,
        pins={
            "version": "practice-log/1",
            "input_hash": input_hash,
            "drill_hash": assignment.drill.content_hash,
            "workflow_hash": digest(assignment.drill.payload["practice_workflow"]),
            "plan_hash": plan.content_hash if plan else None,
        },
    )
    item._created = True
    return item


@transaction.atomic
def delete_log(owner, log_id):
    from backend.core.ownership import lock_owner
    from backend.core.security import capacity_lock

    lock_owner(owner.pk)
    capacity_lock()
    item = PracticeLog.objects.select_for_update().get(owner=owner, pk=log_id)
    PracticeLog.objects.filter(pk=item.pk).update(
        state="DELETED",
        started_at=None,
        ended_at=None,
        reported_attempts=None,
        obstacle="NONE",
        pins={},
    )


@transaction.atomic
def cancel_assignment(owner, assignment_id):
    from backend.core.loops import require_active

    require_active(owner)
    item = DrillAssignment.objects.select_for_update().get(owner=owner, pk=assignment_id)
    item.status = "CANCELLED"
    item.save(update_fields=["status"])
    return item
