"""Evidence-governed local releases. No live game access or automatic fact approval."""

import json
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from analysis.contracts import digest
from backend.core.consents import require_processing
from backend.core.models import (
    AnalysisPublication,
    AnalysisRun,
    DefinitionVersion,
    DrillAssignment,
    ExecutionSlot,
    GameBuild,
    GameplayEvent,
    ImprovementEvaluation,
    KnowledgeEvidence,
    KnowledgeProposal,
    KnowledgeReanalysis,
    KnowledgeReview,
    Match,
    MatchContribution,
    Profile,
    ReplayAsset,
    RunDispatch,
    UploadSession,
)
from backend.core.ownership import lock_owner
from backend.core.security import capacity_lock

# Enabling real publication requires a code/ADR/release review, not an environment switch.
REAL_PUBLICATION_APPROVED = False
TARGET = "tekken8.jin-vs-jin.blocked-uf4/v1"
SEMANTICS = "jin-standing-blocked-uf4/1"
KINDS = ("build", "move", "situation", "metric", "knowledge", "drill", "compatibility")
KEY = re.compile(r"^[A-Za-z0-9_.:/-]{1,160}$")
FIELDS = {
    "build": ({"game_build", "platform", "overlays"}, set()),
    "move": (
        {"game_build", "move", "startup_frames", "on_block_frames", "reach_test", "timing_test"},
        set(),
    ),
    "situation": (
        {
            "game_build",
            "supported_semantics",
            "trigger",
            "required_observations",
            "unknown_rules",
            "exclusions",
        },
        set(),
    ),
    "metric": (
        {"game_build", "supported_semantics", "numerator", "denominator", "unknown_policy"},
        set(),
    ),
    "knowledge": (
        {"game_build", "situation_definition", "metric_definition", "move_versions"},
        set(),
    ),
    "drill": (
        {
            "game_build",
            "situation_definition",
            "metric_definition",
            "knowledge_revision",
            "title",
            "repetitions",
            "setup",
            "native_practice",
        },
        set(),
    ),
    "compatibility": (
        {"game_build", "from_knowledge", "to_knowledge", "disposition", "rationale"},
        set(),
    ),
}
for _kind, (_required, _optional) in FIELDS.items():
    if _kind != "build":
        _required.add("build_definition")


def actor(user):
    current = lock_owner(user.pk)
    if not live_user(current.pk) or not current.is_staff:
        raise PermissionDenied("Active operator access required")
    require_processing(current)
    if not settings.DEBUG or settings.RESTORE_QUARANTINE:
        raise PermissionDenied("Knowledge review is local only; hosted qualification is pending")
    capacity_lock()  # Shared reviews and erasure serialize without locking other accounts.
    return current


def live_user(user_id):
    return (
        get_user_model().objects.filter(pk=user_id, is_active=True).exists()
        and not Profile.objects.filter(user_id=user_id)
        .filter(Q(deleted_at__isnull=False) | Q(processing_withdrawn_at__isnull=False))
        .exists()
    )


def valid_key(value):
    if not isinstance(value, str) or not KEY.fullmatch(value):
        raise ValidationError("Use a bounded version/reference code")
    return value


def dependencies(kind, payload):
    fields = {
        "knowledge": [("situation_definition", "situation"), ("metric_definition", "metric")],
        "drill": [
            ("situation_definition", "situation"),
            ("metric_definition", "metric"),
            ("knowledge_revision", "knowledge"),
        ],
        "compatibility": [("from_knowledge", "knowledge"), ("to_knowledge", "knowledge")],
    }.get(kind, [])
    result = [(payload[field], expected) for field, expected in fields]
    if kind != "build":
        result.append((payload["build_definition"], "build"))
    if kind == "knowledge":
        result += [(key, "move") for key in payload["move_versions"]]
    return result


def validate_payload(kind, build, payload):
    if kind not in KINDS or not isinstance(payload, dict):
        raise ValidationError("Unsupported knowledge artifact")
    required, optional = FIELDS[kind]
    if not required.issubset(payload) or set(payload) - required - optional:
        raise ValidationError(f"{kind} fields must be: {', '.join(sorted(required))}")
    # Explicit canonical build plus its captured version/platform, never a date-based guess.
    if (
        not isinstance(payload["game_build"], str)
        or not payload["game_build"]
        or len(payload["game_build"]) > 80
    ):
        raise ValidationError("An exact captured build label is required")
    expected_build = f"tekken8/{build.platform}/{payload['game_build']}"
    if build.key.startswith("tekken8/") and build.key != expected_build:
        raise ValidationError("Captured version/platform differs from the canonical build key")
    if kind == "build" and (
        payload["platform"] != build.platform
        or not isinstance(payload["overlays"], list)
        or not payload["overlays"]
    ):
        raise ValidationError("Build confirmation needs the exact platform and visible overlays")
    if kind == "move":
        valid_key(payload["move"])
        if (
            type(payload["startup_frames"]) is not int
            or not 1 <= payload["startup_frames"] <= 200
            or type(payload["on_block_frames"]) is not int
            or not -200 <= payload["on_block_frames"] <= 200
        ):
            raise ValidationError(
                "Reviewed integer frame facts are required; unknown facts cannot publish"
            )
        valid_key(payload["reach_test"])
        valid_key(payload["timing_test"])
    if kind in {"situation", "metric"} and payload["supported_semantics"] != SEMANTICS:
        raise ValidationError("Only the bounded Jin standing block-punish semantics are supported")
    if kind == "situation":
        from analysis.rules import REQUIRED

        if (
            payload["trigger"] != "opponent-jin-uf4-blocked"
            or not isinstance(payload["required_observations"], list)
            or any(not isinstance(x, str) for x in payload["required_observations"])
            or set(payload["required_observations"]) != set(REQUIRED)
            or not isinstance(payload["unknown_rules"], list)
            or not isinstance(payload["exclusions"], list)
            or not payload["unknown_rules"]
            or not payload["exclusions"]
        ):
            raise ValidationError("Mandatory observability/unknown/exclusion rules are required")
    if kind == "metric" and (
        payload["numerator"],
        payload["denominator"],
        payload["unknown_policy"],
    ) != ("eligible-successes", "eligible-known-outcomes", "exclude-and-report"):
        raise ValidationError("Unsupported metric semantics")
    if kind == "knowledge" and (
        not isinstance(payload["move_versions"], list)
        or not 1 <= len(payload["move_versions"]) <= 10
        or any(not isinstance(x, str) for x in payload["move_versions"])
        or len(set(payload["move_versions"])) != len(payload["move_versions"])
    ):
        raise ValidationError("Distinct reviewed move versions are required")
    if kind == "drill":
        if (
            type(payload["repetitions"]) is not int
            or not 1 <= payload["repetitions"] <= 200
            or not isinstance(payload["setup"], dict)
            or not isinstance(payload["native_practice"], dict)
            or not payload["setup"]
            or not payload["native_practice"]
            or not isinstance(payload["title"], str)
            or not 1 <= len(payload["title"]) <= 120
        ):
            raise ValidationError("A bounded drill needs its title, native setup and repetitions")
    if kind == "compatibility":
        if payload["from_knowledge"] == payload["to_knowledge"] or payload["disposition"] not in {
            "SAME_MEASUREMENT",
            "REANALYSIS_REQUIRED",
            "INCOMPATIBLE",
        }:
            raise ValidationError(
                "Distinct versions and an explicit compatibility disposition are required"
            )
        valid_key(payload["rationale"])
    for key, expected in dependencies(kind, payload):
        valid_key(key)
        if not DefinitionVersion.objects.filter(pk=key, kind=expected).exists():
            raise ValidationError("A referenced definition is missing or has the wrong kind")
    if len(json.dumps(payload, allow_nan=False).encode()) > 32768:
        raise ValidationError("Knowledge payload exceeds 32 KiB")


def source_snapshot(asset, build, version, dataset_kind):
    if (
        asset.deleted_at
        or not live_user(asset.owner_id)
        or not asset.retain_until
        or asset.retain_until <= timezone.now()
    ):
        raise ValidationError("Knowledge evidence is unavailable or expired")
    if UploadSession.objects.filter(asset=asset).exclude(state="COMPLETE").exists():
        raise ValidationError("An unfinished upload cannot be review evidence")
    if (
        asset.metadata.get("game_build"),
        asset.metadata.get("platform"),
        asset.metadata.get("dataset_kind"),
    ) != (version, build.platform, dataset_kind):
        raise ValidationError("Evidence must explicitly match build, platform and dataset scope")
    run = (
        asset.analysisrun_set.filter(status__in=["REVIEW_REQUIRED", "PARTIAL", "COMPLETED"])
        .order_by("-created_at")
        .first()
    )
    media = run.result.get("source", {}) if run else {}
    duration = media.get("duration_seconds")
    if (
        not re.fullmatch(r"[a-f0-9]{64}", asset.source_sha256)
        or media.get("source_sha256") != asset.source_sha256
        or not isinstance(duration, (int, float))
        or not 0 < duration <= 600
    ):
        raise ValidationError(
            "Successful bounded media validation with a matching hash is required"
        )
    return {
        "source_sha256": asset.source_sha256,
        "generation": asset.storage_generation,
        "metadata_hash": digest(asset.metadata),
        "duration_seconds": duration,
        "retain_until": asset.retain_until.isoformat() if asset.retain_until else None,
    }


def proposal_material(proposal):
    return {
        "key": proposal.key,
        "kind": proposal.kind,
        "build": proposal.game_build_id,
        "scope": proposal.dataset_kind,
        "payload": proposal.payload,
        "provenance": proposal.provenance,
        "reviewers": [proposal.reviewer_one_id, proposal.reviewer_two_id],
        "sources": sorted([(str(s.asset_id), s.snapshot) for s in proposal.sources.all()]),
        "dependencies": proposal.provenance.get("dependency_hashes", {}),
    }


def intact(proposal):
    if proposal.state not in {"OPEN", "PUBLISHED", "RETIRED"} or not all(
        live_user(i)
        for i in (proposal.owner_id, proposal.reviewer_one_id, proposal.reviewer_two_id)
    ):
        return False
    if digest(proposal_material(proposal)) != proposal.content_hash:
        return False
    sources = list(proposal.sources.select_related("asset"))
    if not sources:
        return False
    try:
        for source in sources:
            if (
                source_snapshot(
                    source.asset,
                    proposal.game_build,
                    proposal.payload["game_build"],
                    proposal.dataset_kind,
                )
                != source.snapshot
            ):
                return False
    except ValidationError:
        return False
    return True


def effective(definition, dataset_kind, owner_id=None, *, historical=False, seen=None):
    """Legacy definitions are synthetic fixtures only; immutable APPROVED is not a grant."""
    if definition.status != "APPROVED":
        return False
    proposal = (
        KnowledgeProposal.objects.filter(published=definition).select_related("game_build").first()
    )
    if not proposal:
        return dataset_kind == "synthetic"
    if (
        proposal.dataset_kind != dataset_kind
        or (owner_id is not None and proposal.owner_id != owner_id)
        or not settings.DEBUG
        or settings.RESTORE_QUARANTINE
    ):
        return False
    if dataset_kind == "real" and not REAL_PUBLICATION_APPROVED:
        return False
    if proposal.state not in (
        {"PUBLISHED", "RETIRED"} if historical else {"PUBLISHED"}
    ) or not intact(proposal):
        return False
    expected_payload = {**proposal.payload, "synthetic_only": dataset_kind == "synthetic"}
    if (
        definition.payload != expected_payload
        or definition.game_build_id != proposal.game_build_id
        or definition.kind != proposal.kind
        or definition.key != proposal.key
    ):
        return False
    if definition.content_hash != digest(
        {
            "key": definition.key,
            "kind": definition.kind,
            "status": definition.status,
            "game_build": definition.game_build_id,
            "payload": definition.payload,
        }
    ):
        return False
    seen = set() if seen is None else seen
    if definition.pk in seen:
        return False
    seen = seen | {definition.pk}
    for key, expected in dependencies(definition.kind, definition.payload):
        dep = DefinitionVersion.objects.filter(pk=key, kind=expected).first()
        if (
            not dep
            or dep.content_hash != proposal.provenance["dependency_hashes"].get(key)
            or not effective(dep, dataset_kind, proposal.owner_id, historical=historical, seen=seen)
        ):
            return False
    return True


def require_definition(key, dataset_kind, owner_id, *, kind=None, historical=False):
    capacity_lock()
    definition = DefinitionVersion.objects.get(pk=key)
    if (kind and definition.kind != kind) or not effective(
        definition, dataset_kind, owner_id, historical=historical
    ):
        raise ValidationError(
            "Definition is unreviewed, withdrawn, expired, incompatible or outside this workspace/scope"
        )
    return definition


def visible_drills(owner):
    result = []
    for definition in DefinitionVersion.objects.filter(kind="drill"):
        proposal = KnowledgeProposal.objects.filter(published=definition).first()
        if proposal and proposal.owner_id != owner.pk:
            continue
        scope = "synthetic" if definition.payload.get("synthetic_only") else "real"
        result.append(
            {
                "key": definition.key,
                "payload": definition.payload,
                "status": "APPROVED"
                if effective(definition, scope, owner.pk)
                else ("UNAVAILABLE" if definition.status == "APPROVED" else definition.status),
            }
        )
    return result


@transaction.atomic
def propose(
    user,
    *,
    key,
    kind,
    build_key,
    dataset_kind,
    payload,
    provenance,
    asset_ids,
    reviewer_one,
    reviewer_two,
    request_id,
):
    current = actor(user)
    valid_key(key)
    if dataset_kind not in {"synthetic", "real"}:
        raise ValidationError("Use an explicit real or synthetic scope")
    if (
        set(provenance) != {"reference", "rights", "share_with_reviewers", "publish_game_facts"}
        or provenance["rights"] not in {"OWNED_RECORDING", "PERMITTED_FACTS"}
        or provenance["share_with_reviewers"] is not True
        or provenance["publish_game_facts"] is not True
    ):
        raise ValidationError(
            "Explicit source rights, full-source reviewer sharing and public game-fact permission are required"
        )
    valid_key(provenance["reference"])
    if (
        current.pk in {reviewer_one, reviewer_two}
        or reviewer_one == reviewer_two
        or not all(
            get_user_model().objects.filter(pk=i, is_staff=True).exists() and live_user(i)
            for i in (reviewer_one, reviewer_two)
        )
    ):
        raise ValidationError("Assign two active independent operators, distinct from the author")
    build = GameBuild.objects.get(pk=build_key, game_id="tekken8")
    validate_payload(kind, build, payload)
    if not 1 <= len(asset_ids) <= 10 or len(set(asset_ids)) != len(asset_ids):
        raise ValidationError("Select 1-10 distinct owned sources")
    assets = list(ReplayAsset.objects.filter(owner=current, pk__in=asset_ids))
    if len(assets) != len(asset_ids):
        raise PermissionDenied("Evidence must belong to the author")
    snapshots = [
        (asset, source_snapshot(asset, build, payload["game_build"], dataset_kind))
        for asset in assets
    ]
    provenance = {
        **provenance,
        "dependency_hashes": {
            key: DefinitionVersion.objects.get(pk=key).content_hash
            for key, _ in dependencies(kind, payload)
        },
    }
    proposal = KnowledgeProposal(
        owner=current,
        key=key,
        kind=kind,
        game_build=build,
        dataset_kind=dataset_kind,
        payload=payload,
        provenance=provenance,
        reviewer_one_id=reviewer_one,
        reviewer_two_id=reviewer_two,
        request_id=request_id,
    )
    material = {
        "key": key,
        "kind": kind,
        "build": build.pk,
        "scope": dataset_kind,
        "payload": payload,
        "provenance": provenance,
        "reviewers": [reviewer_one, reviewer_two],
        "sources": sorted([(str(a.pk), s) for a, s in snapshots]),
        "dependencies": provenance["dependency_hashes"],
    }
    proposal.content_hash = digest(material)
    prior = KnowledgeProposal.objects.filter(owner=current, request_id=request_id).first()
    if prior:
        if prior.content_hash != proposal.content_hash or not intact(prior):
            raise ValidationError("Request ID belongs to different or withdrawn evidence")
        return prior
    if DefinitionVersion.objects.filter(pk=key).exists():
        raise ValidationError("Create a new version key; draft definitions cannot be toggled")
    proposal.save()
    KnowledgeEvidence.objects.bulk_create(
        [KnowledgeEvidence(proposal=proposal, asset=a, snapshot=s) for a, s in snapshots]
    )
    return proposal


def accessible(user, proposal_id, *, author=False):
    current = actor(user)
    proposal = KnowledgeProposal.objects.select_related("game_build").get(pk=proposal_id)
    if (author and proposal.owner_id != current.pk) or current.pk not in {
        proposal.owner_id,
        proposal.reviewer_one_id,
        proposal.reviewer_two_id,
    }:
        raise PermissionDenied("This proposal is not shared with you")
    return proposal


@transaction.atomic
def review(user, proposal_id, *, proposal_hash, decision, note, confirm_reviewed, request_id):
    proposal = accessible(user, proposal_id)
    if (
        user.pk not in {proposal.reviewer_one_id, proposal.reviewer_two_id}
        or proposal.state != "OPEN"
        or not intact(proposal)
    ):
        raise PermissionDenied("Assigned independent review of intact open evidence is required")
    if (
        proposal_hash != proposal.content_hash
        or decision not in {"APPROVE", "REJECT"}
        or not confirm_reviewed
        or not isinstance(note, str)
        or not 1 <= len(note.strip()) <= 2000
    ):
        raise ValidationError(
            "Review the sealed payload and sources, then record a decision and note"
        )
    prior = proposal.reviews.filter(owner=user).first()
    if prior:
        if (prior.decision, prior.note, prior.request_id) != (decision, note.strip(), request_id):
            raise ValidationError("Review already sealed; corrections need a new proposal")
        return prior
    return KnowledgeReview.objects.create(
        owner=user,
        proposal=proposal,
        decision=decision,
        note=note.strip(),
        proposal_hash=proposal_hash,
        request_id=request_id,
    )


@transaction.atomic
def publish(user, proposal_id):
    proposal = accessible(user, proposal_id, author=True)
    if proposal.state == "PUBLISHED" and effective(
        proposal.published, proposal.dataset_kind, user.pk
    ):
        return proposal.published
    if proposal.state != "OPEN" or not intact(proposal):
        raise ValidationError("Proposal is unavailable or changed; create a new version")
    if proposal.dataset_kind == "real" and not REAL_PUBLICATION_APPROVED:
        raise ValidationError(
            "Real publication requires current-build, expert, rights and release approval; this local module cannot grant it"
        )
    reviews = list(proposal.reviews.all())
    if {
        r.owner_id
        for r in reviews
        if r.decision == "APPROVE" and r.proposal_hash == proposal.content_hash
    } != {proposal.reviewer_one_id, proposal.reviewer_two_id} or len(reviews) != 2:
        raise ValidationError("Two independent approvals of this exact evidence are required")
    for key, expected in dependencies(proposal.kind, proposal.payload):
        dep = require_definition(key, proposal.dataset_kind, user.pk, kind=expected)
        if dep.content_hash != proposal.provenance["dependency_hashes"][key] or (
            proposal.kind != "compatibility"
            and (
                dep.game_build_id != proposal.game_build_id
                or dep.payload.get("game_build") != proposal.payload["game_build"]
            )
        ):
            raise ValidationError("Dependency/build evidence changed or differs")
    if proposal.kind == "drill":
        knowledge = DefinitionVersion.objects.get(pk=proposal.payload["knowledge_revision"])
        if any(
            knowledge.payload[field] != proposal.payload[field]
            for field in ("situation_definition", "metric_definition")
        ):
            raise ValidationError("Drill measurement differs from its knowledge revision")
    if proposal.kind == "compatibility":
        target = DefinitionVersion.objects.get(pk=proposal.payload["to_knowledge"])
        if (
            target.game_build_id != proposal.game_build_id
            or target.payload["game_build"] != proposal.payload["game_build"]
        ):
            raise ValidationError("Compatibility target must match its explicit build")
        if KnowledgeProposal.objects.filter(
            kind="compatibility",
            state="PUBLISHED",
            payload__from_knowledge=proposal.payload["from_knowledge"],
            payload__to_knowledge=proposal.payload["to_knowledge"],
        ).exists():
            raise ValidationError("Retire the previous mapping before replacing this pair")
    definition = DefinitionVersion.objects.create(
        key=proposal.key,
        kind=proposal.kind,
        game_build=proposal.game_build,
        status="APPROVED",
        payload={**proposal.payload, "synthetic_only": proposal.dataset_kind == "synthetic"},
    )
    proposal.published, proposal.state = definition, "PUBLISHED"
    # Sealed digest describes the candidate, not its later grant lifecycle.
    proposal.save(update_fields=["published", "state"])
    return definition


def event_knowledge(event):
    return event.measurement.get("knowledge_revision", event.match.knowledge_revision)


def event_available(event):
    if not event.measurement and event.match.dataset_kind == "synthetic":
        return True
    for key in (event_knowledge(event), event.situation, event.metric):
        definition = DefinitionVersion.objects.filter(pk=key).first()
        if (
            definition
            and KnowledgeProposal.objects.filter(published=definition).exists()
            and not effective(definition, event.match.dataset_kind, event.owner_id, historical=True)
        ):
            return False
    return True


def revoke(proposal, reason, *, erase=False, retire=False):
    proposal.state, proposal.reason = ("RETIRED" if retire else "WITHDRAWN"), reason
    fields = ["state", "reason"]
    if erase:
        proposal.payload, proposal.provenance = {}, {}
        fields += ["payload", "provenance"]
        proposal.reviews.update(note="")
        proposal.sources.all().delete()
    proposal.save(update_fields=fields)
    if retire:
        return
    # Withdraw dependent releases transitively; a frozen historical evaluation is invalidated,
    # never silently recomputed with new definitions or mixed builds.
    keys = {proposal.published_id} if proposal.published_id else set()
    while keys:
        dependents = [
            p
            for p in KnowledgeProposal.objects.filter(state__in=["PUBLISHED", "RETIRED"])
            if keys.intersection(p.provenance.get("dependency_hashes", {}))
        ]
        if not dependents:
            break
        for dependent in dependents:
            dependent.state, dependent.reason = "WITHDRAWN", "DEPENDENCY_WITHDRAWN"
            dependent.save(update_fields=["state", "reason"])
            keys.add(dependent.published_id)
    if keys:
        assignments = DrillAssignment.objects.filter(drill_id__in=keys)
        ImprovementEvaluation.objects.filter(
            plan__assignment__in=assignments, invalidated_at=None
        ).update(invalidated_at=timezone.now())
        assignments.update(status="WITHDRAWN")
        events = list(
            GameplayEvent.objects.filter(
                Q(situation__in=keys)
                | Q(metric__in=keys)
                | Q(measurement__knowledge_revision__in=list(keys))
                | Q(measurement={}, match__knowledge_revision__in=keys)
            )
        )
        if events:
            from backend.core.loops import invalidate_for_events

            invalidate_for_events([str(e.pk) for e in events])
            GameplayEvent.objects.filter(pk__in=[e.pk for e in events]).update(
                deleted_at=timezone.now()
            )
            MatchContribution.objects.filter(match_id__in=[e.match_id for e in events]).delete()
        runs = KnowledgeReanalysis.objects.filter(
            Q(target_id__in=keys) | Q(mapping_id__in=keys)
        ).values_list("run_id", flat=True)
        AnalysisRun.objects.filter(pk__in=runs).exclude(status="CANCELLED").update(
            status="CANCELLED", fence=F("fence") + 1, lease_until=None
        )
        RunDispatch.objects.filter(run_id__in=runs).update(status="CANCELLED", lease_until=None)
        ExecutionSlot.objects.filter(run_id__in=runs, released_at=None).update(
            stop_requested_at=timezone.now()
        )


@transaction.atomic
def lifecycle(user, proposal_id, action):
    proposal = accessible(user, proposal_id, author=True)
    if action not in {"RETIRE", "WITHDRAW"}:
        raise ValidationError("Unknown release operation")
    if action == "RETIRE" and proposal.state not in {"PUBLISHED", "RETIRED"}:
        raise ValidationError("Only a published version can retire")
    revoke(
        proposal,
        "AUTHOR_RETIRED" if action == "RETIRE" else "AUTHOR_WITHDRAWN",
        retire=action == "RETIRE",
    )
    return proposal


def invalidate_asset(asset_id):
    capacity_lock()
    for proposal in KnowledgeProposal.objects.filter(sources__asset_id=asset_id).exclude(
        state="WITHDRAWN"
    ):
        revoke(proposal, "SOURCE_WITHDRAWN", erase=True)


def erase_account(owner_id):
    capacity_lock()
    for proposal in KnowledgeProposal.objects.filter(
        Q(owner_id=owner_id) | Q(reviewer_one_id=owner_id) | Q(reviewer_two_id=owner_id)
    ):
        revoke(proposal, "ACCOUNT_WITHDRAWN", erase=True)
    KnowledgeReview.objects.filter(owner_id=owner_id).update(note="")


def restore_revoke():
    capacity_lock()
    for proposal in KnowledgeProposal.objects.all():
        revoke(proposal, "RESTORE_QUARANTINE", erase=True)


def reanalysis_candidate(owner, match, mapping):
    if (
        not match.asset_id
        or match.deleted_at
        or match.metadata_state == "REVIEW_REQUIRED"
        or match.asset.deleted_at
        or (match.asset.retain_until and match.asset.retain_until <= timezone.now())
    ):
        return "UNAVAILABLE", None
    if not effective(mapping, match.dataset_kind, owner.pk):
        return "MAPPING_UNAVAILABLE", None
    publication = AnalysisPublication.objects.filter(match=match).first()
    events = list(
        GameplayEvent.objects.filter(
            match=match, run_id=publication.run_id if publication else None
        )
    )
    versions = {event_knowledge(e) for e in events} if events else {match.knowledge_revision}
    if versions != {mapping.payload["from_knowledge"]}:
        return "OTHER_REVISION", None
    if mapping.payload["disposition"] != "REANALYSIS_REQUIRED":
        return mapping.payload["disposition"], None
    target = DefinitionVersion.objects.get(pk=mapping.payload["to_knowledge"])
    if (
        match.game_build != target.payload["game_build"]
        or match.asset.metadata.get("platform") != target.game_build.platform
    ):
        return "CAPTURE_BUILD_INCOMPATIBLE", None
    snapshot = {
        "source_sha256": match.asset.source_sha256,
        "asset_id": str(match.asset_id),
        "game_build": match.game_build,
        "metadata_revision": match.metadata_revision,
        "from_knowledge": mapping.payload["from_knowledge"],
        "target_hash": target.content_hash,
        "mapping_hash": mapping.content_hash,
        "publication_revision": publication.revision if publication else 0,
        "publication_run": str(publication.run_id) if publication else None,
    }
    return "READY", snapshot


@transaction.atomic
def impact(user, mapping_key):
    current = actor(user)
    mapping = require_definition(mapping_key, "synthetic", current.pk, kind="compatibility")
    matches = Match.objects.filter(owner=current, deleted_at=None).select_related("asset")[:500]
    return {
        "mapping": mapping.key,
        "matches": [
            {
                "id": str(m.pk),
                "game_build": m.game_build,
                "dataset_kind": m.dataset_kind,
                "state": reanalysis_candidate(current, m, mapping)[0],
            }
            for m in matches
        ],
        "limit": 500,
        "note": "Original build and frozen plans remain unchanged. Cross-build captures need a new compatible baseline.",
    }


@transaction.atomic
def reanalyse(user, *, match_id, mapping_key, request_id):
    current = actor(user)
    match = Match.objects.select_related("asset").get(pk=match_id, owner=current)
    mapping = require_definition(mapping_key, match.dataset_kind, current.pk, kind="compatibility")
    state, snapshot = reanalysis_candidate(current, match, mapping)
    prior = KnowledgeReanalysis.objects.filter(owner=current, request_id=request_id).first()
    if prior:
        if (
            prior.match_id != match.pk
            or prior.mapping_id != mapping.pk
            or prior.snapshot != snapshot
            or prior.run.status == "CANCELLED"
        ):
            raise ValidationError(
                "Request ID belongs to a different, changed or cancelled reanalysis"
            )
        return prior
    if state != "READY":
        raise ValidationError(f"Reanalysis is gated: {state}")
    if AnalysisRun.objects.filter(
        owner=current, asset=match.asset, status__in=["QUEUED", "PROCESSING"]
    ).exists():
        raise ValidationError("This capture already has active analysis")
    from backend.core.jobs import enqueue_run
    from backend.core.security import admit_run, validate_admission

    validate_admission(current)
    admit_run(current)
    run = enqueue_run(
        owner=current,
        asset=match.asset,
        request_key=f"knowledge:{request_id}",
        pipeline_version=f"knowledge/{mapping.content_hash[:32]}",
    )
    return KnowledgeReanalysis.objects.create(
        owner=current,
        match=match,
        mapping=mapping,
        target_id=mapping.payload["to_knowledge"],
        run=run,
        snapshot=snapshot,
        request_id=request_id,
    )


def publication_measurement(run, match):
    """Canonical reviewer import calls this before creating facts, including delayed jobs."""
    reanalysis = KnowledgeReanalysis.objects.filter(run=run).first()
    key = reanalysis.target_id if reanalysis else match.knowledge_revision
    managed = KnowledgeProposal.objects.filter(published_id=key).exists()
    if not managed and match.dataset_kind == "synthetic":
        return {"knowledge_revision": key, "situation": TARGET, "metric": "punish-success/v1"}
    knowledge = require_definition(key, match.dataset_kind, match.owner_id, kind="knowledge")
    if knowledge.payload[
        "game_build"
    ] != match.game_build or knowledge.game_build.platform != run.asset.metadata.get("platform"):
        raise ValidationError("Published knowledge differs from the capture build/platform")
    if reanalysis:
        if not AnalysisPublication.objects.filter(match=match, run=run).exists():
            state, snapshot = reanalysis_candidate(match.owner, match, reanalysis.mapping)
            if state != "READY" or snapshot != reanalysis.snapshot:
                raise ValidationError(
                    "Reanalysis evidence or selected publication changed; request again"
                )
    return {
        "knowledge_revision": key,
        "knowledge_hash": knowledge.content_hash,
        "situation": knowledge.payload["situation_definition"],
        "metric": knowledge.payload["metric_definition"],
    }
