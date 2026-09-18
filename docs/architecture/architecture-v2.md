# Architecture V2 — one measurable improvement loop

Version: 2.0.0. Decision date: 2026-09-18. Status: local engineering approved;
gameplay feasibility and external pilot NOT validated. Source: historical
[V1](../architecture.md) and the complete adversarial review in the project conversation.
[Reconciliation](review-reconciliation.md) identifies the controlling decisions.

## Product and release boundary

Observe one meaningful situation, freeze baseline evidence, prescribe one drill,
measure recorded practice, collect later real matches, compare the same situation,
and choose the next action. Improvement, deterioration, no meaningful change,
insufficient exposure, incompatibility, and inconclusive evidence are legitimate results.
No claims of causality from an observational before/after comparison.

The first experimental target is Jin defending against Jin's uf+4, with one reviewed
standing punish response. This is a provisional experimental selection, NOT a validated
current-build move catalog. Natural frequency, current move properties, reach, capture
behavior, and the drill require actual footage and expert review. They remain release gates.
No default game build is assigned to uploaded media. See [candidate study](candidate-situations.md).

## Preserved foundations

Python; Django/DRF modular monolith; PostgreSQL; private media; independently executed
batch processing; stable participants; revisioned analysis; immutable game knowledge;
observation/event/conclusion separation; deterministic rules with unknown states;
counts and statistical uncertainty; internal drill schema with optional adapters.
No LLM, neural player embedding, broker, vector store, warehouse, or native game integration.

## Implementation boundary

One shared `analysis` Python package owns typed evidence, rules, statistical summaries,
and comparison logic. `tools` provides local CLI entrypoints. `backend` owns persistence,
authorization, lifecycle commands and REST. `frontend` supplies only the improvement loop.
Knowledge and contracts are versioned JSON under `game_data` and `contracts`.
Dense observations remain files/artifacts; sparse opportunities are relational records.

Local CLI and synthetic fixtures establish software behavior, never Tekken accuracy.
Uncalibrated template detections are candidate observations and cannot establish a miss.
Human-reviewed sidecars are accepted only through an explicit operator workflow and retain
source hash, reviewers, review time, disagreement and adjudication. A client cannot self-label
an attempt as verified. External uploads remain disabled until hosting/isolation gates pass.

## Measurement and evidence

Situation, metric, capture and timing definitions are frozen. An EvaluationPlan pins
baseline membership, practice requirement, follow-up policy and compatible versions.
Each ImprovementEvaluation freezes its follow-up membership and a new revision is append-only.
Changing any definition requires a new plan; changing selected evidence requires a new result
revision. Reprocessing replaces active match contributions, never adds a second copy.
Deletion invalidates dependent evaluations and recomputes projections.

Known eligible but unobserved outcomes are not failures. Unknown eligibility is not in the
eligible denominator. Both are reported. Detection recall, outcome coverage and sample
uncertainty are distinct. No positive conclusion is published if versions, chronology,
context or measurement evidence are incompatible. Descriptive independent-trial intervals
are labeled; session-clustered intervals control longitudinal conclusions when supported.

## Retention and comparator

For the consented local study retain source through the 30-day follow-up plus 7-day audit,
with a proposed maximum 60 days from capture and explicit extension consent if needed.
If evidence expires or consent is withdrawn, invalidate dependent claims as appropriate.
Research/model-training consent is separate and off by default. Native replay tips and
the player's usual practice are the predeclared comparison workflows.

## Continuation gates

G1 human observability; G2 end-to-end automatic precision/recall; G3 capture adoption;
G4 verified practice measurement; G5 natural occurrence; G6 comparable complete loop.
All real-game gates begin NOT_RUN. Infrastructure work may continue while these are blocked,
but no automatic gameplay release, hosted pilot or validated drill is implied by passing
synthetic tests. See [experiments](experiment-plan.md) and [results](../experiment-results/README.md).

## Changes from V1

Replace the broad M1–M7 feature staircase with a narrow vertical loop. Reduce 30 situations
to one. Bring practice and evaluation into initial domain work. Extend study retention.
Add explicit evaluation membership and compatibility. Gate current game facts and move
recognition on evidence. Keep the useful deployment foundation; do not deploy it yet.

See [data](data-model.md), [events](event-model.md), [pipeline](video-pipeline.md),
[evaluation](evaluation-model.md), [security](security-privacy.md), and [deployment](deployment.md).
