"""Provider-independent frozen comparisons, prospective retention and owned collection ledgers."""

import re
from dataclasses import asdict, replace

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from analysis.comparison import diagnostics, schedule
from analysis.contracts import EvaluationSpec, aware_time, digest
from analysis.evaluation import NEXT_ACTION, evaluate
from backend.core.evidence import as_opportunity
from backend.core.models import (
    ComparisonSession,
    EvaluationPlan,
    GameplayEvent,
    ImprovementEvaluation,
    Match,
    ReplaySource,
)
from backend.core.player_model import review_status, scope_of
from backend.core.practice import capture_end, current_practice
from backend.core.search import current_events

PHASES = {"FOLLOWUP", "RETENTION"}


def source_available(event):
    source = ReplaySource.objects.filter(match=event.match, asset=event.run.asset).first()
    if source is None:
        return event.match.dataset_kind == "synthetic"
    return (
        source.availability == "AVAILABLE"
        and source.attribution_state in {"APPROVED", "NOT_REQUIRED"}
        and (source.local_retain_until is None or source.local_retain_until > timezone.now())
    )


def unavailable_sources(events):
    sources = {}
    for event in events:
        sources.setdefault((event.match_id, event.run_id), event)
    return {e.match_id for e in sources.values() if not source_available(e)}


def fingerprint(event):
    source = ReplaySource.objects.filter(match=event.match, asset=event.run.asset).first()
    decoder = event.run.result.get("decoder_identity")
    if decoder is not None and (
        not isinstance(decoder, dict)
        or set(decoder) != {"contract", "image_sha256"}
        or decoder["contract"] != "isolated-media/1"
        or not isinstance(decoder["image_sha256"], str)
        or not re.fullmatch(r"sha256:[a-f0-9]{64}", decoder["image_sha256"])
    ):
        raise ValidationError("Unqualified decoder provenance")
    media = event.run.result.get("source", {})
    return {
        "version": "comparison-source/1",
        "representation": source.representation if source else "UNKNOWN",
        "source_namespace": source.provider if source else "UNKNOWN",
        "access_class": source.access_class if source else "UNKNOWN",
        "source_parser": source.parser_version if source else None,
        "pipeline": event.run.pipeline_version,
        "decoder": decoder,
        "width": media.get("width"),
        "height": media.get("height"),
    }


def manifest(events):
    cache = {}
    rows = []
    for event in events:
        key = (event.match_id, event.run_id)
        if key not in cache:
            cache[key] = fingerprint(event)
        rows.append(
            {
                "id": str(event.pk),
                "hash": as_opportunity(event).content_hash,
                "scope": scope_of(event),
                "source": cache[key],
                "review_hash": digest(event.review),
            }
        )
    return sorted(rows, key=lambda r: r["id"])


def make_protocol(value, spec, baseline):
    value = schedule(value, spec)
    rows = manifest(baseline)
    if unavailable_sources(baseline):
        raise ValidationError("Baseline sources require current availability and attribution")
    sources = {digest(r["source"]) for r in rows}
    if len(sources) != 1:
        raise ValidationError("Baseline sources or decoder pipelines are mixed; review a new plan")
    if any(capture_end(e) > aware_time(spec.baseline_end) for e in baseline):
        raise ValidationError("The entire baseline recording must end before its cutoff")
    if spec.dataset_kind == "real" and (
        rows[0]["source"]["decoder"] is None or rows[0]["source"]["representation"] == "UNKNOWN"
    ):
        raise ValidationError("Real comparison needs reviewed source and pinned decoder provenance")
    return {
        "version": "comparison-protocol/1",
        "schedule": value,
        "scope": scope_of(baseline[0]),
        "baseline_manifest": rows,
        "source_policy": {
            "version": "exact-source-pipeline/1",
            "fingerprint": rows[0]["source"],
            "changes_require_new_reviewed_plan": True,
        },
        "baseline_planning": diagnostics([as_opportunity(e) for e in baseline], spec),
        "collection_is_prospective": spec.dataset_kind == "real",
        "release_approved": False,
    }


def phase_spec(plan, phase):
    if phase not in PHASES:
        raise ValidationError("Unsupported comparison phase")
    spec = EvaluationSpec.from_dict(plan.specification)
    if phase == "RETENTION":
        retention = plan.protocol.get("schedule", {}).get("retention")
        if not retention:
            raise ValidationError("Retention must be declared when freezing the original plan")
        spec = replace(spec, followup_start=retention["start"], followup_end=retention["end"])
    return spec


def latest_sessions(plan, phase):
    query = ComparisonSession.objects.filter(plan=plan, phase=phase)
    if query.count() > 3000:
        raise ValidationError("Session ledger exceeds the bounded local history")
    latest = {}
    for row in query.order_by("revision", "created_at", "id"):
        latest[row.session_key] = row
    return sorted(latest.values(), key=lambda r: r.session_key)


def collection(plan, phase, spec):
    matches = Match.objects.filter(
        owner=plan.owner,
        context=spec.context,
        dataset_kind=spec.dataset_kind,
        mode="ranked",
        played_at__gte=aware_time(spec.followup_start),
        played_at__lte=aware_time(spec.followup_end),
    )
    if matches.count() > 1000:
        raise ValidationError("Window exceeds 1000 recorded matches; use a narrower new plan")
    events = current_events(plan.owner).filter(
        match__in=matches, situation=spec.situation, metric=spec.metric
    )
    if events.count() > 2000:
        raise ValidationError("Window exceeds 2000 opportunities; use a narrower new plan")
    rows = list(
        events.select_related("match", "run__asset").order_by("match__played_at", "start_us", "id")
    )
    observed = {e.match_id for e in rows}
    receipts = latest_sessions(plan, phase)
    missing = sum(r.state == "MISSING" for r in receipts)
    deleted = sum(r.state == "DELETED" for r in receipts)
    unsupported_captures = matches.exclude(pk__in=observed).count()
    unavailable_source_count = len(unavailable_sources(rows))
    recorded_keys = {e.match.session_id for e in rows}
    unresolved = sum(
        r.state == "RECORDED"
        and (
            r.code not in recorded_keys
            or not set(r.match_ids).issubset({str(e.match_id) for e in rows})
        )
        for r in receipts
    )
    expected = None
    if plan.protocol:
        declared = plan.protocol["schedule"]
        expected = (
            declared["expected_followup_sessions"]
            if phase == "FOLLOWUP"
            else declared["retention"]["expected_sessions"]
        )
    info = {
        "version": "comparison-collection/1",
        "expected_sessions": expected,
        "observed_sessions": len(recorded_keys),
        "missing_reported_sessions": missing,
        "skipped_reported_sessions": sum(r.state == "SKIPPED" for r in receipts),
        "withdrawn_reported_sessions": deleted,
        "unresolved_recorded_sessions": unresolved,
        "matches_without_current_target_publication": unsupported_captures,
        "matches_with_unavailable_local_sources": unavailable_source_count,
        "recorded_matches": matches.count(),
        "self_reports_add_verified_outcomes": False,
        "unsubmitted_recordings_detectable": False,
        "membership": sorted((str(r.pk), r.content_hash) for r in receipts),
        "complete": not (
            missing or deleted or unresolved or unsupported_captures or unavailable_source_count
        )
        and (expected is None or len(recorded_keys) >= expected),
    }
    return rows, info


def availability(owner, item):
    """Check present authorization/publication without changing the historical result JSON."""
    if item.invalidated_at:
        return False, ["EVIDENCE_WITHDRAWN"]
    from backend.core.knowledge import require_definition

    try:
        require_definition(
            item.plan.assignment.drill_id,
            item.plan.specification["dataset_kind"],
            owner.pk,
            kind="drill",
            historical=True,
        )
    except (ValidationError, ValueError):
        return False, ["DRILL_AUTHORIZATION_CHANGED"]
    memberships = list(item.plan.specification["baseline_membership"])
    for field in ("followup_membership", "practice_membership", "reference_membership"):
        memberships += item.result.get(field, [])
    if len(memberships) > 10000:
        return False, ["REPORT_EXCEEDS_LOCAL_BOUND"]
    expected = dict(memberships)
    events = list(
        GameplayEvent.objects.filter(owner=owner, pk__in=expected).select_related(
            "match", "run__asset"
        )
    )
    if len(events) != len(expected):
        return False, ["MISSING_OR_UNAUTHORIZED_EVIDENCE"]
    current = set(current_events(owner).filter(pk__in=expected).values_list("pk", flat=True))
    if current != {e.pk for e in events}:
        return False, ["PUBLICATION_OR_SOURCE_CHANGED"]
    if any(
        (o := as_opportunity(e)).deleted or expected[str(e.pk)] != o.content_hash for e in events
    ) or unavailable_sources(events):
        return False, ["SOURCE_EXPIRED_WITHDRAWN_OR_CHANGED"]
    pinned = {r["id"]: r for r in item.result.get("measurement_manifest", [])}
    if pinned:
        try:
            if pinned != {r["id"]: r for r in manifest(events) if r["id"] in pinned}:
                return False, ["MEASUREMENT_OR_DECODER_CHANGED"]
        except (ValueError, ValidationError):
            return False, ["MEASUREMENT_OR_DECODER_CHANGED"]
    if item.plan.protocol:
        spec = phase_spec(item.plan, item.phase)
        try:
            rows, info = collection(item.plan, item.phase, spec)
        except ValidationError:
            return False, ["COLLECTION_EXCEEDS_LOCAL_BOUND"]
        if sorted((str(e.pk), as_opportunity(e).content_hash) for e in rows) != sorted(
            map(tuple, item.result["followup_membership"])
        ) or digest(info) != digest(item.result.get("collection")):
            return False, ["COLLECTION_CHANGED_REEVALUATE"]
    if item.phase == "RETENTION" and item.result.get("retention", {}).get("reference_result_hash"):
        initial = item.plan.evaluations.filter(phase="FOLLOWUP").order_by("-revision").first()
        if (
            not initial
            or digest(initial.result) != item.result["retention"]["reference_result_hash"]
            or not availability(owner, initial)[0]
        ):
            return False, ["INITIAL_COMPARISON_CHANGED_REEVALUATE"]
    return True, []


def evaluate_comparison(owner, plan, followup_ids, phase):
    from backend.core.knowledge import require_definition
    from backend.core.loops import owned_events, require_complete_captures

    spec = phase_spec(plan, phase)
    require_definition(
        plan.assignment.drill_id, spec.dataset_kind, owner.pk, kind="drill", historical=True
    )
    if spec.dataset_kind == "real" and timezone.now() < aware_time(spec.followup_end):
        raise ValidationError("Fixed collection window has not ended; no repeated peeking")
    baseline = owned_events(owner, [key for key, _ in spec.baseline_membership])
    automatic, collected = collection(plan, phase, spec)
    followup = automatic if followup_ids is None else owned_events(owner, followup_ids)
    require_complete_captures(followup)
    if (plan.protocol or spec.dataset_kind == "real") and {e.pk for e in followup} != {
        e.pk for e in automatic
    }:
        raise ValidationError("Include every current target opportunity in the frozen window")
    if any(not e.match.chronology_verified for e in baseline + followup):
        raise ValidationError("Chronology requires review")
    original_spec = EvaluationSpec.from_dict(plan.specification)
    scope = scope_of(baseline[0])
    practice, unavailable = current_practice(
        owner, plan.assignment, plan=plan, spec=original_spec, scope=scope
    )
    observations = [as_opportunity(e) for e in practice]
    completed = max((capture_end(e) for e in practice), default=None)
    result = evaluate(
        spec,
        [as_opportunity(e) for e in baseline],
        [as_opportunity(e) for e in followup],
        verified_practice=0
        if unavailable
        else sum(
            o.eligibility == "ELIGIBLE" and o.outcome in {"SUCCESS", "FAILURE"}
            for o in observations
        ),
        practice_completed_at=completed.isoformat() if completed else None,
    )
    result.update(
        phase=phase,
        plan_hash=plan.content_hash,
        phase_spec_hash=digest(asdict(spec)),
        practice_membership=sorted((o.id, o.content_hash) for o in observations),
        unavailable_practice_trials=unavailable,
        release_approved=False,
        diagnostics={
            "baseline": diagnostics([as_opportunity(e) for e in baseline], spec),
            "followup": diagnostics([as_opportunity(e) for e in followup], spec),
        },
    )
    measurement = manifest(baseline + followup + practice)
    measured = {r["id"]: r for r in measurement}
    reasons = []
    if unavailable_sources(baseline + followup + practice):
        reasons.append("LOCAL_SOURCE_EXPIRED_UNAVAILABLE_OR_ATTRIBUTION_CHANGED")
    if plan.protocol and digest(
        sorted((measured[str(e.pk)] for e in baseline), key=lambda r: r["id"])
    ) != digest(plan.protocol["baseline_manifest"]):
        reasons.append("FROZEN_BASELINE_MEASUREMENT_CHANGED")
    baseline_source = measured[str(baseline[0].pk)]["source"]
    target_scope = plan.protocol.get("scope", scope)
    target_source = plan.protocol.get("source_policy", {}).get("fingerprint", baseline_source)
    if any(r["scope"] != target_scope or r["source"] != target_source for r in measurement):
        reasons.append("EXACT_MEASUREMENT_OR_SOURCE_PIPELINE_CHANGED")
    current = set(
        current_events(owner)
        .filter(pk__in=[e.pk for e in baseline + followup])
        .values_list("pk", flat=True)
    )
    if current != {e.pk for e in baseline + followup}:
        reasons.append("PUBLICATION_CHANGED")
    if any(not review_status(e)[0] for e in baseline + followup):
        reasons.append("INDEPENDENT_REVIEW_REQUIRED")
    if plan.protocol and any(capture_end(e) > aware_time(spec.followup_end) for e in followup):
        reasons.append("SOURCE_END_OUTSIDE_COLLECTION_WINDOW")
    if reasons:
        result.update(status="NOT_COMPARABLE", change_interval=None)
        result["reasons"] = sorted(set(result["reasons"] + reasons))
    elif plan.protocol and not collected["complete"]:
        result.update(status="INSUFFICIENT_EXPOSURE", change_interval=None)
        result["reasons"] = sorted(
            set(result["reasons"] + ["COLLECTION_GAPS_OR_EXPECTED_SESSIONS_MISSING"])
        )
    result["next_action"] = NEXT_ACTION[result["status"]]
    result["collection"] = collected if plan.protocol else None
    result["measurement_manifest"] = measurement
    if phase == "RETENTION":
        initial = plan.evaluations.filter(phase="FOLLOWUP").order_by("-revision").first()
        valid = bool(initial and availability(owner, initial)[0])
        result["retention"] = {
            "reference_result_hash": digest(initial.result) if valid else None,
            "reference_status": initial.result["status"] if valid else None,
            "state": "INITIAL_COMPARISON_UNAVAILABLE"
            if not valid
            else "OBSERVED_CHANGE_PERSISTS"
            if initial.result["status"] == result["status"] == "OBSERVED_IMPROVEMENT"
            else "RETENTION_NOT_ESTABLISHED",
            "causal": False,
        }
        result["reference_membership"] = initial.result["followup_membership"] if valid else []
        if valid:
            referenced = owned_events(owner, [key for key, _ in result["reference_membership"]])
            result["measurement_manifest"] = manifest(baseline + followup + practice + referenced)
    previous = plan.evaluations.filter(phase=phase).order_by("-revision").first()
    if previous and digest(previous.result) == digest(result) and not previous.invalidated_at:
        previous._created = False
        return previous
    if plan.evaluations.count() >= 200:
        raise ValidationError("Local comparison revision capacity reached")
    maximum = plan.evaluations.aggregate(value=Max("revision"))["value"] or 0
    item = ImprovementEvaluation.objects.create(
        owner=owner, plan=plan, phase=phase, revision=maximum + 1, result=result
    )
    item._created = True
    return item


@transaction.atomic
def record_session(owner, plan_id, values):
    from backend.core.loops import require_active

    require_active(owner)
    plan = EvaluationPlan.objects.select_for_update().get(owner=owner, pk=plan_id)
    if not plan.protocol:
        raise ValidationError("Declare a collection schedule in a new frozen plan first")
    spec = phase_spec(plan, values["phase"])
    if plan.assignment.status in {"CANCELLED", "WITHDRAWN"}:
        raise ValidationError("Assignment is cancelled or withdrawn")
    from backend.core.knowledge import require_definition

    require_definition(
        plan.assignment.drill_id, spec.dataset_kind, owner.pk, kind="drill", historical=True
    )
    code = values["code"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}", code):
        raise ValidationError("Use the canonical session code, up to 100 characters")
    input_hash = digest(values)
    prior = ComparisonSession.objects.filter(owner=owner, request_id=values["request_id"]).first()
    if prior:
        if prior.state == "DELETED" or prior.plan_id != plan.pk or prior.input_hash != input_hash:
            raise ValidationError("Session request belongs to deleted or different work")
        prior._created = False
        return prior
    match_ids = list(map(str, values.get("match_ids", [])))
    state = values["state"]
    played = values.get("played_at")
    if state == "RECORDED":
        matches = list(Match.objects.filter(owner=owner, pk__in=match_ids))
        if (
            not matches
            or len(matches) != len(match_ids)
            or any(
                m.session_id != code
                or m.mode != "ranked"
                or m.context != spec.context
                or m.dataset_kind != spec.dataset_kind
                or m.deleted_at
                or not m.chronology_verified
                for m in matches
            )
        ):
            raise ValidationError(
                "Link owned ranked matches with this exact canonical session code and context"
            )
        played = min(m.played_at for m in matches)
        if any(
            not aware_time(spec.followup_start) <= m.played_at <= aware_time(spec.followup_end)
            for m in matches
        ):
            raise ValidationError("Linked matches fall outside the frozen phase")
    elif state not in {"MISSING", "SKIPPED"} or match_ids:
        raise ValidationError("Only recorded sessions link matches; other states report a gap")
    if (
        played is None
        or not aware_time(spec.followup_start) <= played <= aware_time(spec.followup_end)
        or played > timezone.now()
    ):
        raise ValidationError("Use an observed session time inside the frozen phase")
    key = digest({"owner": owner.pk, "plan": str(plan.pk), "phase": values["phase"], "code": code})
    previous = (
        ComparisonSession.objects.filter(plan=plan, phase=values["phase"], session_key=key)
        .order_by("-revision")
        .first()
    )
    if previous and previous.state == "DELETED":
        raise ValidationError("Withdrawn session cannot be recreated by a retry")
    if ComparisonSession.objects.filter(plan=plan).count() >= 3000 or (
        not previous and len(latest_sessions(plan, values["phase"])) >= 200
    ):
        raise ValidationError("Local session history capacity reached")
    data = {
        "phase": values["phase"],
        "code": code,
        "state": state,
        "played_at": played.isoformat(),
        "match_ids": sorted(match_ids),
        "plan_hash": plan.content_hash,
    }
    item = ComparisonSession.objects.create(
        owner=owner,
        plan=plan,
        phase=values["phase"],
        session_key=key,
        code=code,
        state=state,
        played_at=played,
        match_ids=sorted(match_ids),
        revision=previous.revision + 1 if previous else 1,
        request_id=values["request_id"],
        input_hash=input_hash,
        content_hash=digest(data),
    )
    item._created = True
    return item


@transaction.atomic
def delete_session(owner, session_id):
    from backend.core.ownership import lock_owner
    from backend.core.security import capacity_lock

    lock_owner(owner.pk)
    capacity_lock()
    row = ComparisonSession.objects.get(owner=owner, pk=session_id)
    EvaluationPlan.objects.select_for_update().get(pk=row.plan_id, owner=owner)
    ComparisonSession.objects.filter(
        plan=row.plan, phase=row.phase, session_key=row.session_key
    ).update(state="DELETED", code="", played_at=None, match_ids=[], input_hash="")
    ImprovementEvaluation.objects.filter(
        plan=row.plan, phase=row.phase, invalidated_at=None
    ).update(invalidated_at=timezone.now())
