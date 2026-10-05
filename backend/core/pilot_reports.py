"""Bounded, revisioned G1-G6 evidence packs. Metrics never grant gameplay release."""

from statistics import median

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from analysis.contracts import aware_time, digest
from analysis.perception_metrics import score_predictions
from backend.core.models import (
    PilotCapture,
    PilotDecision,
    PilotEnrollment,
    PilotGateReport,
    PilotSession,
    PilotTask,
)
from backend.core.pilots import bump, final_label, live_capture, study_for


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def snapshot(study):
    members = list(
        PilotEnrollment.objects.filter(
            study=study, state="ACTIVE", expires_at__gt=timezone.now(), owner__is_active=True
        )
        .exclude(owner__profile__processing_withdrawn_at__isnull=False)
        .select_related("evaluation__plan")
    )
    participants = [m for m in members if m.role == "PARTICIPANT"]
    sessions = list(PilotSession.objects.filter(enrollment__in=participants).order_by("pk"))
    captures = list(
        PilotCapture.objects.filter(session__in=sessions)
        .select_related("asset", "session__enrollment__owner")
        .order_by("pk")
    )
    captures = [c for c in captures if live_capture(c)]
    tasks = list(
        PilotTask.objects.filter(capture__in=captures)
        .select_related("capture__session__enrollment")
        .prefetch_related("pilotreview_set")
        .order_by("pk")
    )
    active = {m.pk for m in members}
    labeled = [
        (t, *final_label(t))
        for t in tasks
        if {t.reviewer_one_id, t.reviewer_two_id, t.adjudicator_id} <= active
    ]
    manifest = {
        "protocol": study.protocol_digest,
        "members": [
            [
                str(m.pk),
                str(m.pseudonym),
                m.role,
                m.split,
                m.comparison_order,
                m.consent_digest,
                m.evaluation_digest,
            ]
            for m in sorted(members, key=lambda m: str(m.pk))
        ],
        "sessions": [
            [
                str(s.pk),
                str(s.enrollment_id),
                s.phase,
                s.state,
                s.played_at.isoformat(),
                s.playable_seconds,
                s.unaided,
                s.setup_seconds,
                s.useful,
                s.insight_seconds,
            ]
            for s in sessions
        ],
        "sources": [
            [str(c.pk), c.source_sha256, c.game_build, c.duration_seconds] for c in captures
        ],
        "tasks": [
            [
                str(t.pk),
                t.kind,
                t.start_us,
                t.end_us,
                str(t.reviewer_one_id),
                str(t.reviewer_two_id),
                str(t.adjudicator_id),
                t.prediction,
                [
                    [str(r.reviewer_id), r.label_digest, r.seconds]
                    for r in sorted(t.pilotreview_set.all(), key=lambda r: str(r.reviewer_id))
                ],
            ]
            for t in tasks
        ],
    }
    return participants, sessions, captures, tasks, labeled, digest(manifest)


def metrics(study):
    participants, sessions, captures, tasks, labeled, data_hash = snapshot(study)
    resolved = [(t, label) for t, state, label in labeled if state in {"AGREED", "ADJUDICATED"}]
    targets = [(t, label) for t, label in resolved if t.kind == "TARGET"]
    target_count = sum(t.kind == "TARGET" for t in tasks)
    visible = sum(label["visibility"] == "RESOLVABLE" for _, label in targets)
    unobservable = sum(label["visibility"] == "UNOBSERVABLE" for _, label in targets)
    qc = {t.capture_id: label for t, label in resolved if t.kind == "QC"}
    g1 = {
        "captures": len(captures),
        "target_windows": target_count,
        "resolvable": visible,
        "resolvable_rate": ratio(visible, target_count),
        "unobservable_rate": ratio(unobservable, target_count),
        "qc_captures": len(qc),
    }
    g1_ok = (
        len(captures) >= 20
        and target_count > 0
        and len(qc) == len(captures)
        and visible / target_count >= 0.9
    )
    heldout = [
        (t, label) for t, label in targets if t.capture.session.enrollment.split == "held-out"
    ]
    truth, predictions = [], []
    for task, label in heldout:
        base = {"source_id": str(task.capture_id), "id": str(task.pk), "start_us": task.start_us}
        truth.append({**base, "eligibility": label["eligibility"], "outcome": label["outcome"]})
        if task.prediction:
            predictions.append(
                {
                    **base,
                    **{key: task.prediction[key] for key in ("start_us", "eligibility", "outcome")},
                }
            )
    g2 = score_predictions(truth, predictions)
    g2["negative_controls"] = sum(label["eligibility"] == "INELIGIBLE" for _, label in heldout)
    g2["unreviewed_windows"] = sum(
        t.kind == "TARGET" and t.capture.session.enrollment.split == "held-out" for t in tasks
    ) - len(heldout)
    g2["accepted_predictions"] = sum(
        p["eligibility"] == "ELIGIBLE" and p["outcome"] != "UNKNOWN" for p in predictions
    )
    g2["detector_versions"] = sorted(
        {t.prediction["detector_version"] for t, _ in heldout if t.prediction}
    )
    g2_ok = len(g2["detector_versions"]) == 1 and (
        g2["accepted_predictions"] >= 300
        and g2["negative_controls"] > 0
        and g2["unreviewed_windows"] == 0
        and all(
            item["precision"] is not None
            and item["precision"] >= 0.98
            and item["one_sided_precision_lower_95"] >= 0.95
            and item["recall"] is not None
            and item["recall"] >= 0.60
            for key, item in g2["slices"].items()
            if key in {"SUCCESS", "FAILURE"}
        )
    )
    # First attempted baseline capture per player. Missing/invalid attempts stay in the denominator.
    first = {}
    for session in sorted(sessions, key=lambda s: (s.played_at, str(s.pk))):
        if session.phase == "BASELINE":
            first.setdefault(session.enrollment_id, session)
    valid_sessions = {
        c.session_id
        for c in captures
        if qc.get(c.pk, {}).get("profile_valid") is True and qc[c.pk]["visibility"] == "RESOLVABLE"
    }
    unaided = [first[m.pk] for m in participants if m.pk in first and first[m.pk].unaided]
    valid = sum(s.state == "CAPTURED" and s.pk in valid_sessions for s in unaided)
    setup = [s.setup_seconds for s in unaided if s.setup_seconds is not None]
    g3 = {
        "participants": len(participants),
        "attempted": len(first),
        "unaided": len(unaided),
        "valid": valid,
        "valid_rate": ratio(valid, len(participants)),
        "setup_known": len(setup),
        "median_setup_seconds": median(setup) if setup else None,
    }
    g3_ok = (
        len(participants) >= 15
        and len(unaided) == len(participants)
        and len(setup) == len(participants)
        and valid / len(participants) >= 0.8
        and median(setup) <= 600
    )
    trial_rows = []
    for member in participants:
        member_tasks = [
            t for t in tasks if t.kind == "TRIAL" and t.capture.session.enrollment_id == member.pk
        ]
        member_labels = [
            (t, label)
            for t, label in resolved
            if t.kind == "TRIAL" and t.capture.session.enrollment_id == member.pk
        ]
        known = [
            (t, label)
            for t, label in member_labels
            if label["eligibility"] == "ELIGIBLE" and label["outcome"] != "UNKNOWN"
        ]
        correct = sum(
            bool(t.prediction)
            and t.prediction["eligibility"] == label["eligibility"]
            and t.prediction["outcome"] == label["outcome"]
            and abs(t.prediction["start_us"] - t.start_us) <= 16667
            for t, label in known
        )
        accepted = sum(
            bool(t.prediction)
            and t.prediction["eligibility"] == "ELIGIBLE"
            and t.prediction["outcome"] != "UNKNOWN"
            for t in member_tasks
        )
        trial_rows.append(
            {
                "participant": str(member.pseudonym),
                "trials": len(member_tasks),
                "reviewed": len(member_labels),
                "known_truth": len(known),
                "accepted_predictions": accepted,
                "coverage": ratio(accepted, len(member_tasks)),
                "agreement": ratio(correct, accepted),
            }
        )
    qualified = [
        row
        for row in trial_rows
        if row["trials"] >= 40
        and row["reviewed"] == row["trials"]
        and row["coverage"] >= 0.9
        and row["agreement"] >= 0.95
    ]
    g4 = {"players": trial_rows, "qualifying_players": len(qualified)}
    g4_ok = len(qualified) >= 10
    exposures = []
    for member in participants:
        periods = {}
        for phase, lower, upper in [
            ("BASELINE", "started_at", "baseline_end"),
            ("FOLLOWUP", "followup_start", "ends_at"),
        ]:
            eligible = [
                (t, label)
                for t, label in targets
                if t.capture.session.enrollment_id == member.pk
                and t.capture.session.phase == phase
                and aware_time(study.protocol[lower])
                <= t.capture.session.played_at
                <= aware_time(study.protocol[upper])
                and label["eligibility"] == "ELIGIBLE"
                and label["outcome"] != "UNKNOWN"
            ]
            periods[phase] = {
                "known": len(eligible),
                "sessions": len({t.capture.session_id for t, _ in eligible}),
            }
        exposures.append(
            {
                "participant": str(member.pseudonym),
                "periods": periods,
                "sufficient": all(
                    p["known"] >= 40 and p["sessions"] >= 5 for p in periods.values()
                ),
            }
        )
    sufficient = sum(row["sufficient"] for row in exposures)
    ended = timezone.now() >= aware_time(study.protocol["ends_at"])
    g5 = {
        "histories": len(participants),
        "sufficient": sufficient,
        "sufficient_rate": ratio(sufficient, len(participants)),
        "window_ended": ended,
        "playable_seconds": sum(s.playable_seconds for s in sessions)
        if sessions and all(s.playable_seconds is not None for s in sessions)
        else None,
        "measured_playable_seconds": sum(s.playable_seconds or 0 for s in sessions),
        "unmeasured_playable_sessions": sum(s.playable_seconds is None for s in sessions),
        "session_states": {
            key: sum(s.state == key for s in sessions)
            for key in ("CAPTURED", "MISSING", "ZERO_OPPORTUNITIES", "INVALID")
        },
        "players": exposures,
    }
    g5_ok = ended and len(participants) >= 20 and sufficient / len(participants) >= 0.6
    reviewed_sessions = [
        s for s in sessions if s.pk in valid_sessions and s.phase in {"BASELINE", "FOLLOWUP"}
    ]
    reviewed_minutes = (
        sum(s.playable_seconds for s in reviewed_sessions) / 60
        if reviewed_sessions and all(s.playable_seconds is not None for s in reviewed_sessions)
        else None
    )
    g5["reviewed_playable_minutes"] = reviewed_minutes
    reviewed_ids = {s.pk for s in reviewed_sessions}
    g5["observed_eligible_opportunities"] = sum(
        label["eligibility"] == "ELIGIBLE"
        for t, label in targets
        if t.capture.session_id in reviewed_ids
    )
    g5["opportunities_per_reviewed_minute"] = (
        g5["observed_eligible_opportunities"] / reviewed_minutes
        if reviewed_minutes and len(targets) == target_count
        else None
    )
    comparable = 0
    linked = 0
    for member in participants:
        evaluation = member.evaluation
        if (
            evaluation
            and not evaluation.invalidated_at
            and member.evaluation_digest
            == digest({"plan": evaluation.plan.content_hash, "result": evaluation.result})
            and not evaluation.plan.evaluations.filter(revision__gt=evaluation.revision).exists()
        ):
            linked += 1
            comparable += evaluation.result.get("status") in {
                "OBSERVED_IMPROVEMENT",
                "OBSERVED_DETERIORATION",
                "NO_MEANINGFUL_CHANGE",
                "INCONCLUSIVE",
            }
    comparisons = []
    for member in participants:
        ratings = {}
        for phase in ("FOLLOWUP", "NATIVE", "USUAL"):
            rows = [
                s
                for s in sessions
                if s.enrollment_id == member.pk and s.phase == phase and s.useful is not None
            ]
            # One predeclared observation per mode; duplicates or missing ratings cannot prove utility.
            ratings[phase] = (
                rows[0]
                if len(rows) == 1
                and rows[0].useful is not None
                and (rows[0].useful is False or rows[0].insight_seconds is not None)
                else None
            )
        first_phase = {
            "STRUCTURED_FIRST": "FOLLOWUP",
            "NATIVE_FIRST": "NATIVE",
            "USUAL_FIRST": "USUAL",
        }.get(member.comparison_order)
        if (
            all(ratings.values())
            and first_phase
            and all(ratings[first_phase].played_at <= value.played_at for value in ratings.values())
        ):
            follow = ratings["FOLLOWUP"]
            comparisons.append(
                {
                    "participant": str(member.pseudonym),
                    "added_utility": bool(follow.useful)
                    and all(
                        not ratings[phase].useful
                        or follow.insight_seconds < ratings[phase].insight_seconds
                        for phase in ("NATIVE", "USUAL")
                    ),
                }
            )
    g6 = {
        "participants": len(participants),
        "linked_evaluations": linked,
        "comparable": comparable,
        "comparable_rate": ratio(comparable, len(participants)),
        "complete_comparisons": len(comparisons),
        "added_utility": sum(c["added_utility"] for c in comparisons),
        "comparisons": comparisons,
        "allocations": {
            key: sum(m.comparison_order == key for m in participants)
            for key in ("UNASSIGNED", "STRUCTURED_FIRST", "NATIVE_FIRST", "USUAL_FIRST")
        },
        "interpretation": "Descriptive only. No positive-change or causal claim is required for comparability.",
    }
    g6_ok = (
        ended
        and len(participants) >= 20
        and comparable / len(participants) >= 0.6
        and len(comparisons) == len(participants)
        and sum(value >= 5 for key, value in g6["allocations"].items() if key != "UNASSIGNED") >= 2
        and sum(c["added_utility"] for c in comparisons) / len(participants) >= 0.6
    )
    common = {
        "dataset_digest": data_hash,
        "dataset_kind": study.dataset_kind,
        "protocol_digest": study.protocol_digest,
        "scope": "SOFTWARE_REHEARSAL" if study.dataset_kind == "synthetic" else "REVIEW_REQUIRED",
        "scientific_gate": "NOT_RUN",
        "release_approval": False,
        "source_manifest": [
            {
                "capture_id": str(c.pk),
                "session_id": str(c.session_id),
                "source_sha256": c.source_sha256,
                "game_build": c.game_build,
                "participant": str(c.session.enrollment.pseudonym),
                "split": c.session.enrollment.split,
            }
            for c in captures
        ],
        "independent_review_seconds": sum(
            r.seconds for t in tasks for r in t.pilotreview_set.all()
        ),
        "review_states": {
            key: sum(state == key for _, state, _ in labeled)
            for key in ("PENDING", "AGREED", "DISAGREEMENT", "ADJUDICATED")
        },
        "notes": "Candidate metrics on a frozen local dataset. Approved real protocol, sampling review and independent expert decision remain separate. No labels are published automatically.",
    }
    rows = {
        key: {
            **common,
            "gate": key,
            "metrics": value,
            "candidate_criteria_met": bool(ok),
            "proposed_action": "CONTINUE" if ok else "WAIT",
        }
        for key, value, ok in [
            ("G1", g1, g1_ok),
            ("G2", g2, g2_ok),
            ("G3", g3, g3_ok),
            ("G4", g4, g4_ok),
            ("G5", g5, g5_ok),
            ("G6", g6, g6_ok),
        ]
    }
    if g1["unobservable_rate"] is not None and g1["unobservable_rate"] > 0.2:
        rows["G1"]["proposed_action"] = "NARROW"
    if any(row["trials"] >= 40 and row["coverage"] < 0.8 for row in trial_rows):
        rows["G4"]["proposed_action"] = "STOP"
    if len(participants) >= 15 and g3["valid_rate"] < 0.5:
        rows["G3"]["proposed_action"] = "NARROW"
    if ended and len(participants) >= 20 and g5["sufficient_rate"] < 0.3:
        rows["G5"]["proposed_action"] = "NARROW"
    if (
        ended
        and len(participants) >= 20
        and (
            g6["comparable_rate"] < 0.3
            or len(comparisons) == len(participants)
            and g6["added_utility"] == 0
        )
    ):
        rows["G6"]["proposed_action"] = "STOP"
    return rows


@transaction.atomic
def generate(user, study_id):
    _, study, _ = study_for(user, study_id, manager=True)
    if study.state != "FROZEN":
        raise ValidationError("Freeze source inputs before generating evidence reports")
    data_rows = metrics(study)
    existing = list(PilotGateReport.objects.filter(study=study, revision=study.revision))
    if any(r.invalidated_at or r.content_hash != digest(data_rows[r.gate]) for r in existing):
        bump(study)
        study.refresh_from_db()
    reports = []
    for gate, data in data_rows.items():
        row, _ = PilotGateReport.objects.get_or_create(
            study=study,
            gate=gate,
            revision=study.revision,
            defaults={"data": data, "content_hash": digest(data)},
        )
        if row.invalidated_at or row.content_hash != digest(data):
            raise ValidationError(
                "Evidence changed without a new study revision; regenerate after reviewed invalidation"
            )
        reports.append(row)
    return reports


@transaction.atomic
def decide(user, study_id, report_id, action, reason, reference):
    _, study, member = study_for(user, study_id)
    if not member or member.role != "EXPERT":
        raise PermissionDenied("Independent consenting expert required")
    report = PilotGateReport.objects.get(
        pk=report_id, study=study, revision=study.revision, invalidated_at=None
    )
    if metrics(study)[report.gate] != report.data:
        raise ValidationError("Report evidence is stale")
    if action == "CONTINUE" and not report.data["candidate_criteria_met"]:
        raise ValidationError(
            "Continue requires sufficient candidate evidence; no waiver by button"
        )
    row, _ = PilotDecision.objects.get_or_create(
        report=report,
        defaults={"actor": member, "action": action, "reason": reason, "reference": reference},
    )
    if (row.actor_id, row.action, row.reason, row.reference) != (
        member.pk,
        action,
        reason,
        reference,
    ):
        raise ValidationError("Gate decision is immutable")
    return row


@transaction.atomic
def annotations(user, study_id):
    _, study, _ = study_for(user, study_id, manager=True)
    return annotation_batches(study)


def annotation_batches(study):
    """Internal builder. Callers hold capacity lock and independently check access."""
    if study.state != "FROZEN":
        raise ValidationError("Freeze the study before exporting labels")
    from analysis.annotations import validate_annotations
    from backend.core.models import Match

    batches = []
    _, _, captures, tasks, _, _ = snapshot(study)
    for capture in captures:
        selected = [t for t in tasks if t.capture_id == capture.pk and t.kind != "QC"]
        if not selected:
            continue
        match = Match.objects.get(asset_id=capture.asset_id, deleted_at=None)
        examples = []
        for task in selected:
            state, label = final_label(task)
            if not label:
                raise ValidationError(
                    "Every exported target/trial needs complete independent review"
                )
            reviews = list(task.pilotreview_set.select_related("reviewer"))
            pair = [r for r in reviews if r.reviewer_id != task.adjudicator_id]
            third = next((r for r in reviews if r.reviewer_id == task.adjudicator_id), None)
            examples.append(
                {
                    "id": str(task.pk),
                    "start_us": task.start_us,
                    "end_us": task.end_us,
                    "situation": study.protocol["target"],
                    "characters": ["jin", "jin"],
                    "eligibility": label["eligibility"],
                    "outcome": label["outcome"],
                    "conditions": label["conditions"],
                    "evidence": [
                        f"source-sha256:{capture.source_sha256}@{task.start_us}-{task.end_us}"
                    ],
                    "reviews": [
                        {
                            "reviewer": str(r.reviewer.pseudonym),
                            "eligibility": r.label["eligibility"],
                            "outcome": r.label["outcome"],
                            "confidence": {
                                "RESOLVABLE": "high",
                                "UNCERTAIN": "low",
                                "UNOBSERVABLE": "unobservable",
                            }[r.label["visibility"]],
                            "seconds": r.seconds,
                        }
                        for r in pair
                    ],
                    "adjudication": {
                        "reviewer": str(third.reviewer.pseudonym),
                        "reason": "Independent structured-label disagreement resolved",
                        "seconds": third.seconds,
                    }
                    if state == "ADJUDICATED"
                    else None,
                }
            )
        batch = {
            "schema_version": "annotation/1",
            "source_id": str(capture.asset_id),
            "source_sha256": capture.source_sha256,
            "dataset_kind": study.dataset_kind,
            "game_build": capture.game_build,
            "session_id": match.session_id,
            "source_kind": match.mode,
            "played_at": match.played_at.isoformat(),
            "examples": examples,
        }
        validate_annotations(
            batch,
            capture.source_sha256,
            situation=study.protocol["target"] if study.protocol.get("dataset_id") else None,
        )
        batches.append(batch)
    return {
        "scope": "SOFTWARE_REHEARSAL" if study.dataset_kind == "synthetic" else "REVIEW_REQUIRED",
        "automatic_publication": False,
        "batches": batches,
    }
