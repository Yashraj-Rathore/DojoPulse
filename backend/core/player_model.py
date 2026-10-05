"""Bounded live projections over canonical publications; no provider or detector dependency."""

from collections import Counter, defaultdict
from dataclasses import asdict

from django.core.exceptions import ValidationError

from analysis.contracts import digest
from analysis.player_model import POLICY, diagnose, priority_assessment, rank_cards
from backend.core.evidence import as_opportunity
from backend.core.knowledge import SEMANTICS, TARGET, effective, event_available, event_knowledge
from backend.core.models import AnalysisPublication, DefinitionVersion, Match
from backend.core.search import current_events, filter_matches

MAX_MATCHES = 1000
MAX_EVENTS = 20000
MAX_GROUPS = 100


def scope_of(event):
    return {
        "situation": event.situation,
        "metric": event.metric,
        "context": event.match.context,
        "game_build": event.match.game_build,
        "knowledge_revision": event_knowledge(event),
        "knowledge_hash": event.measurement.get("knowledge_hash"),
        "detector_version": event.detector_version,
        "platform": event.run.asset.metadata.get("platform") or "unknown",
        "dataset_kind": event.match.dataset_kind,
    }


def review_status(event):
    reviews = event.review.get("reviews", [])
    if len(reviews) != 2 or any(not isinstance(r, dict) for r in reviews):
        return False, False
    reviewers = {r.get("reviewer") for r in reviews}
    if len(reviewers) != 2 or not all(reviewers):
        return False, False
    judgments = {(r.get("eligibility"), r.get("outcome")) for r in reviews}
    final = (event.eligibility, event.outcome)
    adjudication = event.review.get("adjudication")
    needs_third = (
        len(judgments) > 1
        or final not in judgments
        or (
            event.outcome != "UNKNOWN"
            and any(r.get("confidence") == "unobservable" for r in reviews)
        )
    )
    if needs_third and (
        not isinstance(adjudication, dict)
        or not adjudication.get("reviewer")
        or adjudication["reviewer"] in reviewers
    ):
        return False, False
    return bool(event.verified), len(judgments) == 1


def supported_scope(scope):
    if scope["context"] != "jin/jin":
        return False
    situation = DefinitionVersion.objects.filter(pk=scope["situation"], kind="situation").first()
    metric = DefinitionVersion.objects.filter(pk=scope["metric"], kind="metric").first()
    return bool(
        (
            situation
            and situation.payload.get("supported_semantics") == SEMANTICS
            and metric
            and metric.payload.get("numerator") == "eligible-successes"
            and metric.payload.get("denominator") == "eligible-known-outcomes"
        )
        or (
            scope["dataset_kind"] == "synthetic"
            and scope["situation"] == TARGET
            and scope["metric"] == "punish-success/v1"
        )
    )


def matching_drills(owner, scope):
    result = []
    candidates = DefinitionVersion.objects.filter(
        kind="drill",
        status="APPROVED",
        payload__game_build=scope["game_build"],
        payload__situation_definition=scope["situation"],
        payload__metric_definition=scope["metric"],
        payload__knowledge_revision=scope["knowledge_revision"],
    ).select_related("game_build")
    if candidates.count() > 100:
        raise ValidationError(
            "More than 100 matching drill versions; ask the operator to retire superseded assessments"
        )
    for drill in candidates:
        payload = drill.payload
        if drill.game_build_id and drill.game_build.platform != scope["platform"]:
            continue
        if any(
            payload.get(field) != scope[target]
            for field, target in (
                ("situation_definition", "situation"),
                ("metric_definition", "metric"),
                ("knowledge_revision", "knowledge_revision"),
                ("game_build", "game_build"),
            )
        ) or not effective(drill, scope["dataset_kind"], owner.pk):
            continue
        assessment = payload.get("priority_assessment")
        if assessment is not None:
            try:
                assessment = priority_assessment(assessment)
            except ValueError:
                continue  # Malformed legacy fixtures are never an assessment authority.
        result.append(
            {
                "key": drill.key,
                "content_hash": drill.content_hash,
                "title": payload.get("title", "Reviewed drill"),
                "assessment": assessment,
            }
        )
    return sorted(result, key=lambda d: d["key"])


def result_counts(matches):
    counts = Counter()
    for match in matches:
        players = [p for p in match.participants.all() if p.is_player]
        result = "UNKNOWN"
        if (
            len(players) == 1
            and match.winner_slot in (1, 2)
            and match.metadata_state != "REVIEW_REQUIRED"
        ):
            result = "WIN" if match.winner_slot == players[0].slot else "LOSS"
        counts[result] += 1
    known = counts["WIN"] + counts["LOSS"]
    return {
        "matches": len(matches),
        "wins": counts["WIN"],
        "losses": counts["LOSS"],
        "unknown": counts["UNKNOWN"],
        "known_results": known,
        "win_rate": counts["WIN"] / known if known else None,
    }


def projection(owner, values):
    matches = filter_matches(
        Match.objects.filter(owner=owner, deleted_at=None, mode="ranked"), values
    )
    for field in ("dataset_kind", "context", "game_build"):
        if field in values:
            matches = matches.filter(**{field: values[field]})
    if matches.count() > MAX_MATCHES:
        raise ValidationError("Scope exceeds 1000 ranked matches; narrow the dates or context")
    captures = list(matches.prefetch_related("participants").order_by("played_at", "id"))
    query = current_events(owner).filter(match__in=matches).select_related("match", "run__asset")
    for field in ("situation", "detector_version"):
        if field in values:
            query = query.filter(**{field: values[field]})
    if query.count() > MAX_EVENTS:
        raise ValidationError("Scope exceeds 20000 current events; narrow the dates or context")
    groups, scopes, availability = defaultdict(list), {}, {}
    unavailable = Counter()
    for event in query.order_by("match__played_at", "match_id", "start_us", "id"):
        scope = scope_of(event)
        if any(
            scope[field] != values[field]
            for field in ("knowledge_revision", "platform")
            if field in values
        ):
            continue
        if not event.match.chronology_verified or not all(
            (
                event.match.session_id,
                event.match.context,
                event.match.game_build,
                event_knowledge(event),
            )
        ):
            unavailable["CHRONOLOGY_OR_CONTEXT"] += 1
            continue
        grant = (
            event.owner_id,
            event.run.asset_id,
            digest(event.measurement),
            event.situation,
            event.metric,
            event_knowledge(event),
        )
        if grant not in availability:
            availability[grant] = event_available(event)
        observation = as_opportunity(event, knowledge_available=availability[grant])
        if observation.deleted:
            unavailable["WITHDRAWN_EXPIRED_OR_DISPUTED"] += 1
            continue
        key = digest(scope)
        if key not in groups and len(groups) >= MAX_GROUPS:
            raise ValidationError("Scope exceeds 100 measurement groups; choose a context/version")
        groups[key].append((event, observation))
        scopes[key] = scope
    cards = []
    for key, pairs in groups.items():
        scope = scopes[key]
        reviews = [review_status(e) for e, _ in pairs]
        reviewed = sum(complete for complete, _ in reviews)
        agreement = (
            sum(agree for complete, agree in reviews if complete) / reviewed if reviewed else None
        )
        drills = matching_drills(owner, scope)
        assessed = [d for d in drills if d["assessment"] is not None]
        selected = assessed[0] if len(assessed) == 1 else None
        card = diagnose(
            [o for _, o in pairs],
            independent_reviews=reviewed,
            review_agreement=agreement,
            assessment=selected["assessment"] if selected else None,
            supported=supported_scope(scope),
        )
        if len(assessed) > 1:
            card["reasons"].append("AMBIGUOUS_PRIORITY_ASSESSMENT")
        periods = defaultdict(list)
        for event, opportunity in pairs:
            periods[event.match.played_at.strftime("%Y-%m")].append(opportunity)
        from analysis.statistics import summarize

        samples = sorted(
            pairs, key=lambda p: (p[0].outcome != "FAILURE", p[0].match.played_at, p[0].start_us)
        )[:5]
        card.update(
            {
                "id": key,
                "scope": scope,
                "drills": drills,
                "assessment_drill": selected,
                "evidence_hash": digest(
                    sorted(
                        (
                            o.id,
                            digest(
                                {
                                    "opportunity_hash": o.content_hash,
                                    "start_us": e.start_us,
                                    "end_us": e.end_us,
                                    "review": e.review,
                                    "measurement": e.measurement,
                                }
                            ),
                        )
                        for e, o in pairs
                    )
                ),
                "evidence_total": len(pairs),
                "evidence_sample_limit": 5,
                "evidence": [
                    {
                        "id": str(e.pk),
                        "match_id": str(e.match_id),
                        "asset_id": str(e.run.asset_id),
                        "start_us": e.start_us,
                        "end_us": e.end_us,
                        "outcome": e.outcome,
                        "played_at": e.match.played_at.isoformat(),
                    }
                    for e, _ in samples
                ],
                "trends": [
                    {"period": period, "summary": summarize(rows)}
                    for period, rows in sorted(periods.items())
                ],
            }
        )
        cards.append(card)
    if len(cards) > MAX_GROUPS:
        raise ValidationError("Scope exceeds 100 measurement groups; choose a context/version")
    profiles = {
        tuple(
            c["scope"][field]
            for field in (
                "context",
                "game_build",
                "knowledge_revision",
                "knowledge_hash",
                "detector_version",
                "platform",
                "dataset_kind",
            )
        )
        for c in cards
    }
    if len(profiles) > 1:
        cards.sort(key=lambda c: c["id"])
        for card in cards:
            card["priority_rank"] = None
            card["reasons"].append("SELECT_ONE_COMPATIBLE_MEASUREMENT_SCOPE")
    else:
        cards = rank_cards(cards)
    history_periods = defaultdict(list)
    for match in captures:
        history_periods[match.played_at.strftime("%Y-%m")].append(match)
    publication_count = AnalysisPublication.objects.filter(match__in=matches).count()
    return {
        "contract": "player-model/1",
        "policy": asdict(POLICY),
        "policy_hash": digest(asdict(POLICY)),
        "release_approved": False,
        "ranking_state": "MIXED_MEASUREMENT_SCOPES"
        if len(profiles) > 1
        else "SINGLE_MEASUREMENT_SCOPE",
        "filters": {k: str(v) for k, v in values.items()},
        "cards": cards[values["offset"] : values["offset"] + values["limit"]],
        "card_total": len(cards),
        "next_offset": values["offset"] + values["limit"]
        if values["offset"] + values["limit"] < len(cards)
        else None,
        "unavailable_events": dict(unavailable),
        "capture_inventory": {
            "ranked_matches": len(captures),
            "with_publication": publication_count,
            "without_publication": len(captures) - publication_count,
        },
        "history": {
            "summary": result_counts(captures),
            "trends": [
                {"period": period, **result_counts(rows)}
                for period, rows in sorted(history_periods.items())
            ],
        },
        "history_note": "Results describe recorded ranked matches in the date/context/build scope; situation, knowledge, detector and platform filters apply only to gameplay cards.",
        "frequency_note": "Frequency is the eligible share of reviewed candidate windows, not occurrence per match or detector recall.",
    }
