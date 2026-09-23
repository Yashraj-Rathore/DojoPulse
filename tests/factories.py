from dataclasses import replace

from analysis.contracts import Eligibility, EvaluationSpec, Opportunity, Outcome


def event(index=0, *, followup=False, success=True, session=None, **overrides):
    return Opportunity(
        id=f"{'f' if followup else 'b'}{index}",
        played_key=f"{'f' if followup else 'b'}{index}",
        source_sha256="a" * 64,
        session_id=session or f"{'f' if followup else 'b'}s{index // 10}",
        played_at="2026-09-21T12:00:00Z" if followup else "2026-09-01T12:00:00Z",
        mode="ranked",
        situation="situation/1",
        metric="metric/1",
        game_build="synthetic-build",
        knowledge_revision="synthetic-knowledge/1",
        detector_version="synthetic-detector/1",
        context="jin/jin",
        eligibility=Eligibility.ELIGIBLE,
        outcome=Outcome.SUCCESS if success else Outcome.FAILURE,
        evidence=("span/1",),
        verified=True,
        dataset_kind="synthetic",
        **overrides,
    )


def plan_for(baseline, **overrides):
    base = EvaluationSpec(
        situation="situation/1",
        metric="metric/1",
        context="jin/jin",
        baseline_membership=tuple((e.id, e.content_hash) for e in baseline),
        compatible_builds=("synthetic-build",),
        compatible_detectors=("synthetic-detector/1",),
        compatible_knowledge=("synthetic-knowledge/1",),
        baseline_end="2026-09-10T00:00:00Z",
        followup_start="2026-09-20T00:00:00Z",
        followup_end="2026-10-20T00:00:00Z",
        dataset_kind="synthetic",
        measurement_approved=True,
    )
    return replace(base, **overrides)


def conditions(**overrides):
    from analysis.rules import REQUIRED

    return {
        **dict.fromkeys(REQUIRED, True),
        "uncertainty_us": 1000,
        "punish_confirmed": False,
        "failure_confirmed": False,
        **overrides,
    }
