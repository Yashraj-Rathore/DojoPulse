"""Local research workflow; no automatic gameplay publication or real-study approval."""

import math
import re
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from analysis.contracts import aware_time, digest
from analysis.rules import REQUIRED, judge
from backend.core.consents import require_processing
from backend.core.models import (
    AnalysisRun,
    GameplayEvent,
    ImprovementEvaluation,
    Match,
    PilotCapture,
    PilotDecision,
    PilotEnrollment,
    PilotGateReport,
    PilotReview,
    PilotSession,
    PilotStudy,
    PilotTask,
    Profile,
    ReplayAsset,
)
from backend.core.ownership import lock_owner
from backend.core.security import capacity_lock

CONSENT_VERSION = "local-pilot/1"
CONSENT = "Join this specified adult-only study using a pseudonym. Assigned independent reviewers may view the captures you explicitly register. Study data is retained through the observation window plus seven audit days, at most 60 days. Participation, review and model-training permissions are separate. Withdrawal erases study evidence and invalidates dependent reports; your private workspace recordings remain unless you delete them. This local protocol is not approved for real participant intake."
ROLES = ("PARTICIPANT", "REVIEWER", "ADJUDICATOR", "EXPERT")
SALT = "pilot-invitation/1"


def actor(user):
    current = lock_owner(user.pk)
    if (
        not current.is_active
        or Profile.objects.filter(user=current, deleted_at__isnull=False).exists()
    ):
        raise PermissionDenied("Active account required")
    capacity_lock()  # No other account locks after this point, including in privacy hooks.
    return current


def study_for(user, study_id, *, manager=False, privacy=False):
    current = actor(user)
    require_processing(current)
    study = (
        PilotStudy.objects.select_for_update()
        .select_related("owner")
        .get(pk=study_id, deleted_at=None)
    )
    if not study.owner.is_active:
        raise PermissionDenied("Study is unavailable")
    if study.dataset_kind == "real" and not settings.PILOT_REAL_DATA_APPROVED:
        raise PermissionDenied(
            "Real pilot intake requires reviewed protocol, rights and retention approval"
        )
    if study.dataset_kind == "synthetic" and not settings.DEBUG:
        raise PermissionDenied("Synthetic pilot tools are local development only")
    from backend.core.datasets import live_measurement, study_dataset

    dataset = study_dataset(study)
    if (
        not privacy
        and dataset
        and not live_measurement(dataset, historical=dataset.state == "FROZEN")
    ):
        raise PermissionDenied("This dataset's reviewed measurement is unavailable")
    member = PilotEnrollment.objects.filter(
        study=study, owner=current, state="ACTIVE", expires_at__gt=timezone.now()
    ).first()
    if study.owner_id == current.pk:
        if not current.is_staff:
            raise PermissionDenied("Current operator permission required")
    elif manager or not member:
        raise PermissionDenied("Study membership required")
    if member:
        require_processing(current)
    return current, study, member


def collecting(study):
    if study.state != "COLLECTING":
        raise ValidationError("The dataset is frozen; create a new study for changed inputs")


def bump(study):
    from backend.core.datasets import invalidate_study

    invalidate_study(study.pk)
    PilotStudy.objects.filter(pk=study.pk).update(revision=F("revision") + 1)
    PilotGateReport.objects.filter(study=study, invalidated_at=None).update(
        invalidated_at=timezone.now(), data={}
    )


@transaction.atomic
def create_study(user, title, dataset_kind, request_id, *, dataset=None):
    current = actor(user)
    require_processing(current)
    if not current.is_staff:
        raise PermissionDenied("Operator access required")
    if dataset_kind not in {"synthetic", "real"} or (
        dataset_kind == "real" and not settings.PILOT_REAL_DATA_APPROVED
    ):
        raise PermissionDenied("Real study approval is not configured")
    if not settings.DEBUG and dataset_kind == "synthetic":
        raise PermissionDenied("Synthetic studies require local development")
    prior = PilotStudy.objects.filter(owner=current, request_id=request_id).first()
    if prior:
        from backend.core.datasets import study_dataset

        if (prior.title, prior.dataset_kind) != (title, dataset_kind) or study_dataset(
            prior
        ) != dataset:
            raise ValidationError("Study request ID already used")
        return prior
    if PilotStudy.objects.filter(owner=current, deleted_at=None).count() >= 20:
        raise ValidationError("Local study capacity reached")
    now = timezone.now().replace(second=0, microsecond=0)
    protocol = {
        "version": CONSENT_VERSION,
        "consent": CONSENT,
        "target": "tekken8.jin-vs-jin.blocked-uf4/v1",
        "started_at": now.isoformat(),
        "baseline_end": (now + timedelta(days=7)).isoformat(),
        "followup_start": (now + timedelta(days=9)).isoformat(),
        "ends_at": (now + timedelta(days=37)).isoformat(),
        "audit_ends_at": (now + timedelta(days=44)).isoformat(),
        "training_permission_included": False,
        "gates": {
            "G1": "20 captures, >=90% resolvable; >20% unobservable narrows",
            "G2": ">=300 held-out accepted predictions, precision >=.98, exact lower >=.95, recall >=.60 in each outcome slice",
            "G3": "15-20 unaided users, >=80% valid, median setup <=600s; <50% changes ingestion",
            "G4": "10 users x >=40 trials, >=90% coverage and >=95% prediction/truth agreement",
            "G5": "20 prospective histories, 28 follow-up days, >=60% exposure; <30% changes target",
            "G6": ">=60% comparable plus native/usual comparison; <30% or no added utility revises scope",
        },
    }
    if dataset:
        from backend.core.datasets import CONSENT as DATASET_CONSENT
        from backend.core.models import DatasetStudy

        protocol.update(
            target=dataset.measurement["situation"],
            measurement=dataset.measurement,
            dataset_id=str(dataset.pk),
            sampling=dataset.sampling,
        )
        protocol["consent"] += DATASET_CONSENT
    row = PilotStudy.objects.create(
        owner=current,
        title=title,
        dataset_kind=dataset_kind,
        protocol=protocol,
        request_id=request_id,
    )
    if dataset:
        DatasetStudy.objects.create(dataset=dataset, study=row)
    return row


@transaction.atomic
def invite(user, study_id, role):
    _, study, _ = study_for(user, study_id, manager=True)
    collecting(study)
    if role not in ROLES:
        raise ValidationError("Invalid study role")
    return signing.dumps(
        {"study": str(study.pk), "role": role, "protocol": study.protocol_digest}, salt=SALT
    )


def invitation(token):
    try:
        data = signing.loads(token, salt=SALT, max_age=86400)
        study = PilotStudy.objects.get(
            pk=data["study"], deleted_at=None, state="COLLECTING", owner__is_active=True
        )
    except (signing.BadSignature, PilotStudy.DoesNotExist, KeyError, ValueError) as error:
        raise ValidationError("Invitation is invalid or expired") from error
    if data["protocol"] != study.protocol_digest or data["role"] not in ROLES:
        raise ValidationError("Invitation protocol changed")
    if aware_time(study.protocol["audit_ends_at"]) <= timezone.now():
        raise ValidationError("Study consent window has expired")
    if study.dataset_kind == "synthetic" and not settings.DEBUG:
        raise PermissionDenied("Synthetic studies are local only")
    if study.dataset_kind == "real" and not settings.PILOT_REAL_DATA_APPROVED:
        raise PermissionDenied("Real pilot intake is gated")
    return study, data["role"]


@transaction.atomic
def enroll(user, token, protocol_digest, *, adult, accepted, rights):
    current = actor(user)
    require_processing(current)
    study, role = invitation(token)
    if not settings.DEBUG and study.dataset_kind == "synthetic":
        raise PermissionDenied("Synthetic studies are local only")
    if current.pk == study.owner_id:
        raise ValidationError("The manager cannot serve as an independent study member")
    if (
        not adult
        or not accepted
        or (role == "PARTICIPANT" and not rights)
        or protocol_digest != study.protocol_digest
    ):
        raise ValidationError(
            "Review and explicitly accept the current adult study consent and recording rights"
        )
    prior = PilotEnrollment.objects.filter(study=study, owner=current).first()
    if prior:
        if prior.role != role or prior.state != "ACTIVE" or prior.consent_digest != protocol_digest:
            raise ValidationError("Membership is withdrawn or conflicts with the invitation")
        return prior
    if PilotEnrollment.objects.filter(study=study).count() >= settings.PILOT_MAX_MEMBERS:
        raise ValidationError("Local cohort capacity reached")
    row = PilotEnrollment.objects.create(
        owner=current,
        study=study,
        role=role,
        consent_digest=protocol_digest,
        expires_at=aware_time(study.protocol["audit_ends_at"]),
    )
    bump(study)
    return row


@transaction.atomic
def assign_split(user, study_id, enrollment_id, split, comparison_order="UNASSIGNED"):
    _, study, _ = study_for(user, study_id, manager=True)
    collecting(study)
    row = PilotEnrollment.objects.get(
        pk=enrollment_id, study=study, role="PARTICIPANT", state="ACTIVE"
    )
    if (
        split not in {"development", "validation", "held-out"}
        or PilotSession.objects.filter(enrollment=row).exists()
    ):
        raise ValidationError("Assign a player-disjoint split before their first session")
    if comparison_order not in {"UNASSIGNED", "STRUCTURED_FIRST", "NATIVE_FIRST", "USUAL_FIRST"}:
        raise ValidationError("Invalid prospective comparison allocation")
    from backend.core.datasets import check_split

    check_split(study, row, split)
    PilotEnrollment.objects.filter(pk=row.pk).update(split=split, comparison_order=comparison_order)
    bump(study)


@transaction.atomic
def add_session(user, study_id, **data):
    _, study, member = study_for(user, study_id)
    collecting(study)
    if not member or member.role != "PARTICIPANT":
        raise PermissionDenied("Participant membership required")
    if data["played_at"] > timezone.now():
        raise ValidationError("Future play cannot be recorded as observed evidence")
    if data["played_at"] < member.created_at:
        raise ValidationError("Prospective sessions must follow this participant's study consent")
    if (
        not aware_time(study.protocol["started_at"])
        <= data["played_at"]
        <= aware_time(study.protocol["ends_at"])
    ):
        raise ValidationError("Session time must fall inside the prospective study window")
    limits = {
        "BASELINE": ("started_at", "baseline_end"),
        "PRACTICE": ("baseline_end", "followup_start"),
        "FOLLOWUP": ("followup_start", "ends_at"),
        "NATIVE": ("followup_start", "ends_at"),
        "USUAL": ("followup_start", "ends_at"),
    }
    lower, upper = limits[data["phase"]]
    if (
        not aware_time(study.protocol[lower])
        <= data["played_at"]
        <= aware_time(study.protocol[upper])
    ):
        raise ValidationError("Original play time must fall inside the frozen phase window")
    prior = PilotSession.objects.filter(enrollment=member, request_id=data["request_id"]).first()
    if prior:
        if any(getattr(prior, key) != value for key, value in data.items()):
            raise ValidationError("Session request ID already used")
        return prior
    if PilotSession.objects.filter(enrollment__study=study).count() >= settings.PILOT_MAX_SESSIONS:
        raise ValidationError("Local session capacity reached")
    from backend.core.datasets import session_guard

    session_guard(study, member, data["code"], data["played_at"])
    row = PilotSession.objects.create(enrollment=member, **data)
    bump(study)
    return row


@transaction.atomic
def add_capture(user, study_id, session_id, asset_id):
    current, study, member = study_for(user, study_id)
    collecting(study)
    if not member or member.role != "PARTICIPANT":
        raise PermissionDenied("Participant membership required")
    session = PilotSession.objects.get(pk=session_id, enrollment=member, state="CAPTURED")
    asset = ReplayAsset.objects.get(pk=asset_id, owner=current, deleted_at=None)
    if asset.retain_until and asset.retain_until <= timezone.now():
        raise ValidationError("Expired media cannot join a study")
    match = Match.objects.get(asset=asset, owner=current, deleted_at=None)
    if (
        match.dataset_kind != study.dataset_kind
        or not match.game_build
        or not match.chronology_verified
        or not match.session_id
        or match.mode != ("practice" if session.phase == "PRACTICE" else "ranked")
        or not re.fullmatch(r"[a-f0-9]{64}", asset.source_sha256 or "")
    ):
        raise ValidationError(
            "Validated source hash, exact build and matching dataset scope required"
        )
    run = (
        AnalysisRun.objects.filter(
            asset=asset,
            status__in=["REVIEW_REQUIRED", "PARTIAL", "COMPLETED"],
            result__source__source_sha256=asset.source_sha256,
        )
        .order_by("-created_at")
        .first()
    )
    duration = run.result.get("source", {}).get("duration_seconds") if run else None
    if type(duration) not in {int, float} or not math.isfinite(duration) or not 0 < duration <= 600:
        raise ValidationError("A validated media report is required")
    prior = PilotCapture.objects.filter(
        session__enrollment__study=study, source_sha256=asset.source_sha256
    ).first()
    if prior:
        if prior.session_id != session.pk or prior.asset_id != asset.pk:
            raise ValidationError("A source cannot cross players/sessions/splits within this study")
        return prior
    if match.played_at != session.played_at or match.session_id != session.code:
        raise ValidationError(
            "Session code and play time must equal the source's original chronology"
        )
    from backend.core.datasets import capture_pin

    provenance = capture_pin(study, member, session, asset, match, duration)
    row = PilotCapture.objects.create(
        session=session,
        asset=asset,
        source_sha256=asset.source_sha256,
        game_build=match.game_build,
        duration_seconds=duration,
        provenance=provenance,
        original_retain_until=(
            PilotCapture.objects.filter(asset=asset, withdrawn_at=None)
            .order_by("session__played_at")
            .first()
            .original_retain_until
            if PilotCapture.objects.filter(asset=asset, withdrawn_at=None).exists()
            else asset.retain_until
        ),
    )
    ReplayAsset.objects.filter(pk=asset.pk).update(
        retain_until=max(asset.retain_until or timezone.now(), member.expires_at)
    )
    bump(study)
    return row


def live_capture(capture):
    from backend.core.datasets import live_pin

    member = capture.session.enrollment
    asset = capture.asset
    return bool(
        not capture.withdrawn_at
        and asset
        and not asset.deleted_at
        and asset.source_sha256 == capture.source_sha256
        and live_pin(capture)
        and (not asset.retain_until or asset.retain_until > timezone.now())
        and member.state == "ACTIVE"
        and member.expires_at > timezone.now()
        and member.owner.is_active
        and Match.objects.filter(
            asset=asset,
            owner=member.owner,
            deleted_at=None,
            game_build=capture.game_build,
            played_at=capture.session.played_at,
            session_id=capture.session.code,
            chronology_verified=True,
            mode="practice" if capture.session.phase == "PRACTICE" else "ranked",
        ).count()
        == 1
        and not Profile.objects.filter(
            user=member.owner, processing_withdrawn_at__isnull=False
        ).exists()
    )


def label_for(kind, data):
    visibility = data["visibility"]
    if visibility not in {"RESOLVABLE", "UNCERTAIN", "UNOBSERVABLE"}:
        raise ValidationError("Invalid visibility label")
    if kind == "QC":
        if (
            type(data.get("profile_valid")) is not bool
            or type(data.get("target_absent")) is not bool
        ):
            raise ValidationError("Capture QC needs explicit profile/absence judgments")
        return {
            "visibility": visibility,
            "profile_valid": data["profile_valid"],
            "target_absent": data["target_absent"],
        }
    conditions = data.get("conditions", {})
    allowed = {*REQUIRED, "uncertainty_us", "punish_confirmed", "failure_confirmed"}
    if not isinstance(conditions, dict) or set(conditions) != allowed:
        raise ValidationError("Every required evidence condition must be explicit")
    if any(
        value is not None and type(value) is not bool
        for key, value in conditions.items()
        if key != "uncertainty_us"
    ):
        raise ValidationError("Conditions are true, false or unknown")
    uncertainty = conditions["uncertainty_us"]
    if type(uncertainty) is not int or not 0 <= uncertainty <= 1000000:
        raise ValidationError("Timestamp uncertainty must be a bounded integer")
    result = judge(conditions, reviewed=True)
    if visibility != "RESOLVABLE" and result.outcome.value != "UNKNOWN":
        raise ValidationError("Unobservable/uncertain outcomes must abstain")
    return {
        "visibility": visibility,
        "conditions": conditions,
        "eligibility": result.eligibility.value,
        "outcome": result.outcome.value,
    }


@transaction.atomic
def add_task(user, study_id, capture_id, **data):
    _, study, _ = study_for(user, study_id, manager=True)
    collecting(study)
    capture = PilotCapture.objects.select_related("asset", "session__enrollment__owner").get(
        pk=capture_id, session__enrollment__study=study
    )
    if (
        not live_capture(capture)
        or not 0 <= data["start_us"] <= data["end_us"] <= capture.duration_seconds * 1000000
    ):
        raise ValidationError("Evidence must be retained and inside validated source time")
    if (
        data["kind"] == "TRIAL"
        and capture.session.phase != "PRACTICE"
        or data["kind"] == "TARGET"
        and capture.session.phase not in {"BASELINE", "FOLLOWUP"}
    ):
        raise ValidationError("Trial/target review must use the correct prospective phase")
    if (
        data.get("prediction")
        and not 0 <= data["prediction"]["start_us"] <= capture.duration_seconds * 1000000
    ):
        raise ValidationError("Prediction time must be inside the source")
    members = [
        PilotEnrollment.objects.get(
            pk=data[key],
            study=study,
            state="ACTIVE",
            expires_at__gt=timezone.now(),
            owner__is_active=True,
        )
        for key in ("reviewer_one", "reviewer_two", "adjudicator")
    ]
    if len({m.pk for m in members}) != 3 or [m.role for m in members] != [
        "REVIEWER",
        "REVIEWER",
        "ADJUDICATOR",
    ]:
        raise ValidationError("Two independent reviewers and a distinct adjudicator required")
    for key, member in zip(("reviewer_one", "reviewer_two", "adjudicator"), members, strict=True):
        data[key] = member
    prior = PilotTask.objects.filter(capture=capture, request_id=data["request_id"]).first()
    if prior:
        if any(getattr(prior, key) != value for key, value in data.items()):
            raise ValidationError("Task request ID already used")
        return prior
    if data["kind"] == "QC":
        if (
            data["start_us"] != 0
            or data["end_us"] != int(capture.duration_seconds * 1000000)
            or data.get("prediction") is not None
        ):
            raise ValidationError(
                "QC covers the complete source and cannot carry outcome predictions"
            )
        if PilotTask.objects.filter(capture=capture, kind="QC").exists():
            raise ValidationError("One complete-capture QC task per source")
    elif PilotTask.objects.filter(
        capture=capture,
        kind__in=["TARGET", "TRIAL"],
        start_us__lte=data["end_us"],
        end_us__gte=data["start_us"],
    ).exists():
        raise ValidationError("Target/trial windows must not overlap")
    if (
        PilotTask.objects.filter(capture__session__enrollment__study=study).count()
        >= settings.PILOT_MAX_TASKS
    ):
        raise ValidationError("Local review capacity reached")
    row = PilotTask.objects.create(capture=capture, **data)
    bump(study)
    return row


def final_label(task):
    assigned = list(
        PilotEnrollment.objects.filter(
            pk__in=[task.reviewer_one_id, task.reviewer_two_id, task.adjudicator_id],
            state="ACTIVE",
            expires_at__gt=timezone.now(),
            owner__is_active=True,
        ).exclude(owner__profile__processing_withdrawn_at__isnull=False)
    )
    roles = {row.pk: row.role for row in assigned}
    if (
        roles.get(task.reviewer_one_id) != "REVIEWER"
        or roles.get(task.reviewer_two_id) != "REVIEWER"
        or roles.get(task.adjudicator_id) != "ADJUDICATOR"
    ):
        return "PENDING", None
    reviews = {item.reviewer_id: item for item in task.pilotreview_set.all()}
    one, two = reviews.get(task.reviewer_one_id), reviews.get(task.reviewer_two_id)
    if not one or not two:
        return "PENDING", None
    if one.label_digest == two.label_digest:
        return "AGREED", one.label
    adjudication = reviews.get(task.adjudicator_id)
    return ("ADJUDICATED", adjudication.label) if adjudication else ("DISAGREEMENT", None)


@transaction.atomic
def review_task(user, study_id, task_id, label, seconds, request_id):
    _, study, member = study_for(user, study_id)
    if not member or study.state == "CLOSED":
        raise PermissionDenied("Assigned reviewer membership required")
    task = PilotTask.objects.select_related(
        "capture__asset", "capture__session__enrollment__owner"
    ).get(pk=task_id, capture__session__enrollment__study=study)
    if not live_capture(task.capture) or member.pk not in {
        task.reviewer_one_id,
        task.reviewer_two_id,
        task.adjudicator_id,
    }:
        raise PermissionDenied("Assigned retained evidence required")
    if member.role != ("ADJUDICATOR" if member.pk == task.adjudicator_id else "REVIEWER"):
        raise PermissionDenied("Current assigned role required")
    checked = label_for(task.kind, label)
    from backend.core.datasets import study_dataset

    if study_dataset(study) and task.kind != "QC":
        timing = label.get("timing")
        if not isinstance(timing, dict) or set(timing) != {
            "start_us",
            "end_us",
            "frame_duration_us",
        }:
            raise ValidationError(
                "Dataset labels require an explicit timing audit, including unknowns"
            )
        start, end, frame = (timing[k] for k in ("start_us", "end_us", "frame_duration_us"))
        if (start is None) != (end is None) or (
            start is not None
            and (
                type(start) is not int
                or type(end) is not int
                or not task.start_us <= start <= end <= task.end_us
            )
        ):
            raise ValidationError(
                "Reviewed timing must be inside the assigned window or both unknown"
            )
        if frame is not None and (type(frame) is not int or not 1 <= frame <= 1000000):
            raise ValidationError("Frame duration is a bounded measured integer or unknown")
        if frame is not None and start is None:
            raise ValidationError("Frame audit requires observed timestamps")
        checked["timing"] = timing
    prior = PilotReview.objects.filter(task=task, reviewer=member).first()
    if prior:
        if prior.label != checked or prior.seconds != seconds or prior.request_id != request_id:
            raise ValidationError("Review is immutable; request conflicts with submitted label")
        return prior
    if member.pk == task.adjudicator_id and final_label(task)[0] != "DISAGREEMENT":
        raise ValidationError("Adjudication requires two completed disagreeing reviews")
    row = PilotReview.objects.create(
        task=task,
        reviewer=member,
        label=checked,
        label_digest=digest(checked),
        seconds=seconds,
        request_id=request_id,
    )
    bump(study)
    return row


@transaction.atomic
def freeze(user, study_id):
    _, study, _ = study_for(user, study_id, manager=True)
    if study.state == "CLOSED":
        raise ValidationError("Study is closed")
    PilotStudy.objects.filter(pk=study.pk).update(state="FROZEN")


def invalidate_captures(query):
    ids = list(query.values_list("pk", flat=True))
    studies = set(query.values_list("session__enrollment__study_id", flat=True))
    for capture in query:
        if capture.asset_id:
            others = list(
                PilotCapture.objects.filter(asset_id=capture.asset_id, withdrawn_at=None)
                .exclude(pk__in=ids)
                .filter(
                    session__enrollment__state="ACTIVE",
                    session__enrollment__expires_at__gt=timezone.now(),
                )
                .values_list("session__enrollment__expires_at", flat=True)
            )
            restored = (
                max([capture.original_retain_until, *others])
                if capture.original_retain_until
                else (max(others) if others else None)
            )
            ReplayAsset.objects.filter(pk=capture.asset_id).update(retain_until=restored)
    PilotReview.objects.filter(task__capture_id__in=ids).delete()
    PilotTask.objects.filter(capture_id__in=ids).update(prediction=None)
    query.update(
        asset=None, source_sha256="", game_build="", provenance={}, withdrawn_at=timezone.now()
    )
    for study_id in studies:
        bump(PilotStudy.objects.get(pk=study_id))


def invalidate_asset(asset_id):
    capacity_lock()
    invalidate_captures(PilotCapture.objects.filter(asset_id=asset_id))


def erase_enrollment(member):
    invalidate_captures(PilotCapture.objects.filter(session__enrollment=member))
    reviewed = set(
        PilotReview.objects.filter(reviewer=member).values_list(
            "task__capture__session__enrollment__study_id", flat=True
        )
    )
    PilotReview.objects.filter(reviewer=member).delete()
    PilotDecision.objects.filter(actor=member).delete()
    PilotSession.objects.filter(enrollment=member).delete()
    PilotEnrollment.objects.filter(pk=member.pk).update(
        state="WITHDRAWN",
        consent_digest="",
        pseudonym=uuid4(),
        evaluation=None,
        evaluation_digest="",
    )
    for study_id in reviewed | {member.study_id}:
        bump(PilotStudy.objects.get(pk=study_id))


@transaction.atomic
def withdraw(user, study_id):
    current = actor(user)
    member = PilotEnrollment.objects.get(owner=current, study_id=study_id)
    if member.state == "WITHDRAWN":
        return
    from backend.core.control_journal import record_intent

    record_intent(current.pk, "PILOT_WITHDRAW", study=str(study_id))
    erase_enrollment(member)


def erase_account(owner_id):
    capacity_lock()
    for member in PilotEnrollment.objects.filter(owner_id=owner_id, state="ACTIVE"):
        erase_enrollment(member)
    for study in PilotStudy.objects.filter(owner_id=owner_id, deleted_at=None):
        for member in PilotEnrollment.objects.filter(study=study, state="ACTIVE"):
            erase_enrollment(member)
        PilotDecision.objects.filter(report__study=study).delete()
        PilotStudy.objects.filter(pk=study.pk).update(
            deleted_at=timezone.now(),
            state="CLOSED",
            title="Withdrawn study",
            protocol={},
            protocol_digest="",
        )
    from backend.core.datasets import erase_account as erase_datasets

    erase_datasets(owner_id)


@transaction.atomic
def close_study(user, study_id):
    current, study, _ = study_for(user, study_id, manager=True, privacy=True)
    from backend.core.control_journal import record_intent

    record_intent(current.pk, "PILOT_CLOSE", study=str(study.pk))
    for member in PilotEnrollment.objects.filter(study=study, state="ACTIVE"):
        erase_enrollment(member)
    PilotDecision.objects.filter(report__study=study).delete()
    PilotStudy.objects.filter(pk=study.pk).update(
        deleted_at=timezone.now(),
        state="CLOSED",
        title="Closed study",
        protocol={},
        protocol_digest="",
    )


@transaction.atomic
def link_evaluation(user, study_id, evaluation_id):
    current, study, member = study_for(user, study_id)
    collecting(study)
    if not member or member.role != "PARTICIPANT":
        raise PermissionDenied("Participant membership required")
    row = ImprovementEvaluation.objects.select_related("plan").get(
        pk=evaluation_id, owner=current, invalidated_at=None
    )
    spec = row.plan.specification
    if (
        any(
            aware_time(spec[key]) != aware_time(study.protocol[value])
            for key, value in [
                ("baseline_end", "baseline_end"),
                ("followup_start", "followup_start"),
                ("followup_end", "ends_at"),
            ]
        )
        or spec.get("dataset_kind") != study.dataset_kind
        or spec.get("situation") != study.protocol["target"]
    ):
        raise ValidationError(
            "Evaluation must use this study's frozen target, scope and observation dates"
        )
    if row.plan.evaluations.filter(revision__gt=row.revision).exists():
        raise ValidationError("Link the latest evaluation revision")
    ids = [
        key
        for key, _ in spec.get("baseline_membership", [])
        + row.result.get("followup_membership", [])
        + row.result.get("practice_membership", [])
    ]
    from backend.core.evidence import as_opportunity

    memberships = (
        spec.get("baseline_membership", [])
        + row.result.get("followup_membership", [])
        + row.result.get("practice_membership", [])
    )
    assets = set(
        PilotCapture.objects.filter(session__enrollment=member, withdrawn_at=None).values_list(
            "asset_id", flat=True
        )
    )
    events = list(
        GameplayEvent.objects.filter(pk__in=ids, owner=current, deleted_at=None).select_related(
            "match", "run__asset"
        )
    )
    hashes = {str(e.pk): as_opportunity(e).content_hash for e in events}
    if (
        not ids
        or len(set(ids)) != len(events)
        or not {e.run.asset_id for e in events} <= assets
        or any(hashes.get(key) != value for key, value in memberships)
    ):
        raise ValidationError("Every evaluation source must be registered retained study evidence")
    PilotEnrollment.objects.filter(pk=member.pk).update(
        evaluation=row,
        evaluation_digest=digest({"plan": row.plan.content_hash, "result": row.result}),
    )
    bump(study)


@transaction.atomic
def expire_enrollments():
    # No owner lock is acquired after this global lock; all competing pilot writes serialize here.
    capacity_lock()
    count = 0
    for member in PilotEnrollment.objects.filter(state="ACTIVE", expires_at__lte=timezone.now()):
        erase_enrollment(member)
        count += 1
    return count
