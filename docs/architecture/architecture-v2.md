# Architecture V2 — one measurable improvement loop

Version: 2.14.0. Decision date: 2026-10-05. Status: local engineering approved;
gameplay feasibility and external pilot NOT validated. Source: historical
[V1](../architecture.md) and the complete adversarial review in the project conversation.
[Reconciliation](review-reconciliation.md) identifies the controlling decisions.

The [M15 security boundary](security.md) adds isolated media execution, durable admission,
provider response guards and incident procedures. Live providers and external deployment
remain gated; local qualification is documented separately from production acceptance.

The [M14 account lifecycle](accounts-consent.md) adds local verification/recovery, session
revocation, versioned consent receipts, work cancellation on withdrawal and explicit re-linking
with known-match suppression. Hosted email, reviewed policy and backup/provider erasure remain gates.

The [M16 delivery/recovery contract](hosted-delivery.md) adds transactional dispatch,
retained physical capacity, bounded heartbeats and independently signed restore controls.
Google Cloud remains selected; managed media execution awaits a qualified isolation profile.

The [M17 operations/economics contract](operations-economics.md) adds durable media/time
budgets, fenced measurements, staff monitoring, retention and explicit cost coverage.
Service objectives remain proposals; real costs, representative load, hosted alerts and
actual recurring willingness to pay still require evidence and approval.

The [M18 pilot tools](pilot-tools.md) add self-consent, pseudonyms, prospective
session logs, independent blinded review, source-linked evaluations and revisioned
G1–G6 packs. Withdrawal/restore erasure and expert decisions are separate from
canonical publication. Real intake is code-gated; synthetic success leaves all
scientific gates NOT_RUN and confers no gameplay or production approval.

The [M06 evidence-storage contract](evidence-storage.md) adds durable resumable
uploads, background full-byte integrity verification, private range playback and
cancellation/expiry/restore cleanup. LOCAL operator flows and controlled GCS adapters
are implemented; actual GCS and external uploads remain gated. Canonical metadata,
reviewed attribution and gameplay publication stay provider-independent.

The [M07 knowledge contract](knowledge-governance.md) adds evidence-pinned independent
review, new immutable releases, scoped revocable approval and explicit patch reanalysis.
Events pin analysis knowledge; capture builds and frozen comparisons stay unchanged.
Real game facts, expert approval and hosted reviewer access remain release gates.

The [M11 practice contract](practice-workflow.md) adds independently reviewed native
workflows, diagnosis-pinned assignment, separate adherence reports, complete current practice
links and conservative evidence-based next action. Real reproducibility, G4 and utility
remain open; no difficulty escalation, experiment rewrite or causal claim is inferred.

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

DojoPulse's [provider-neutral ingestion architecture](match-ingestion.md) adds player identity
resolution, permitted match discovery and metadata-only import design. OFFICIAL,
COMMUNITY_PUBLIC_API, REVERSE_ENGINEERED and USER_UPLOAD sources have separate operation and
usage gates. Match identity is independent of a video; evidence sufficiency is independent of
successful metadata ingestion. Match.asset is now optional; migrations backfill upload provenance
while preserving existing match/event/evaluation facts. Local synthetic imports are implemented;
network adapters and native replay decoding remain disabled. See [research](../research/tekken-match-sources.md)
and [ADR-013](../adr/ADR-013-provider-neutral-match-ingestion.md).

The local UI now supports explicit player selection, consent, queued metadata sync, source-aware
history and deletion. A separate PostgreSQL-backed match worker processes only synthetic
adapters under DEBUG/LOCAL_MATCH_IMPORTS/staff gates. The
[EWGF activation review](../research/ewgf-activation-review-2026-09-19.md) leaves live access
disabled pending usage rights, private credential setup and permitted current-schema fixtures.

Local staff can attach a recording to an imported match, validate the media, and explicitly
review player/time/build/mode attribution before publishing independently reviewed gameplay.
The match UUID and source assertions remain intact. Deleting the recording withdraws its
evidence while retaining imported history. Event source identity follows its original run,
so replacement recordings cannot rewrite frozen evidence. See
[ADR-014](../adr/ADR-014-recording-attribution.md). Hosted uploads and real-game validation remain gated.

M13's local player experience includes persisted onboarding, searchable history and current
evidence, private timeline playback, guided training plans, feedback/corrections, in-app
notices/preferences, JSON export and password-confirmed deletion. The
[player-experience contract](player-experience.md) defines limits and remaining release tests.
No email delivery, provider activation or automatic gameplay approval is implied. Real
onboarding and usability still depend on the earlier data/access/account gates.

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

The [M08 dataset module](dataset-operations.md) reuses consented pilot review with
exact M07 measurement pins, collection-wide split/source guards, immutable revocable
snapshots, timing/coverage QA and explicit owned-source canonical import. Real golden
data, independent frame/held-out accuracy and actual provider/hosting remain unqualified.

The [M10 player model](player-model.md) projects version-specific reviewed diagnosis,
explicit independently reviewed research priorities, timestamp cards and separate recorded
result/gameplay histories. Proposed policy thresholds and relative assessments still require
real expert/player qualification; no real diagnosis release is implied by local tests.
