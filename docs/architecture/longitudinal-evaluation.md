# Longitudinal evaluation contract

M12 is a local research module. Software qualification does not establish real player
benefit, causal efficacy, retention or statistical power. G5/G6 remain NOT_RUN.

## Frozen protocol

New scheduled plans keep the original EvaluationSpec and add `comparison-protocol/1`.
The plan hash covers both; unscheduled legacy hashes continue to cover only the original
specification. An owned request UUID and canonical input hash make creation retries safe.
A plan remains one per assignment; retention cannot be retrofitted after seeing results.

`comparison-schedule/1` declares 5–100 expected independent follow-up sessions and an
optional retention start/end/count. Retention starts strictly after follow-up ends. All
collection ends within 366 days of baseline cutoff. Real plans require the schedule,
prospective follow-up, known source representation and a coordinator-pinned isolated
decoder image. Existing gameplay/knowledge/consent approvals still apply; this contract
grants none. Real evaluation waits until its fixed window ends; synthetic fixtures can
exercise historical windows. This is not an efficacy stop-rule override.

The baseline manifest pins canonical opportunity hashes, independent review hashes,
exact context/build/knowledge hash/detector/platform and source fingerprints. Source
fingerprints use ReplaySource provider namespace/access class/representation/parser,
AnalysisRun pipeline, validated dimensions and decoder image identity. The coordinator
adds decoder identity after sanitizing untrusted output; reports cannot supply it.
Local fallback/old records retain unknown decoder provenance. No private endpoint or
live provider is activated. Metadata alone cannot invent a gameplay opportunity.
Source or decoder changes require a new reviewed plan; there is no implicit equivalence
between providers or pooled builds. Actual cross-source bias validation remains open.

## Complete collection and session ledger

Scheduled evaluation uses every current owned ranked target opportunity in the frozen
context/dataset/window, including unfavorable, unknown and excluded outcomes. Explicit
membership must equal that collection. Each selected capture is complete. Recorded
matches without current target publication (including removed/expired evidence) are gaps;
they are never assumed to have zero opportunities. Local source expiration, unavailable
bytes or withdrawn attribution also prevent use. Upstream expiration alone does not erase
a permitted already-stored copy; its local retention/authorization remains authoritative. Missing sources, unreviewed evidence,
cross-scope changes or inadequate planned/known session counts prevent positive findings.
Unsubmitted matches cannot be detected; prospective real play logs/selection audits are
still required. Session codes are canonical recording identities, not independently
validated real-world sessionization.

Owned ComparisonSession receipts append revisions for a plan/phase/canonical session code.
RECORDED links bounded owned, chronology-reviewed ranked matches with that exact code and
context. MISSING reports played-but-unrecorded sessions; SKIPPED reports planned non-play.
Self-reports add zero numerator, denominator or practice exposure. A later RECORDED receipt
can resolve MISSING once current reviewed sources arrive. Expected session counts remain
frozen. Retries use UUID/input hashes; code and phase identify the revision chain.
Deleting a receipt clears private fields across its chain and tombstones it; retries cannot
resurrect it. Dependent phase comparisons are invalidated. Account deletion erases receipts;
restore quarantine erases all receipts and invalidates comparisons before reads. Original
immutable result hashes/memberships remain historical audit facts, not usable evidence.

Owner → shared capacity → plan locks serialize evaluation, collection reports, retries,
withdrawal and publication reads. Bounds: 1000 recorded matches/2000 opportunities per
phase, 200 session keys per phase, 3000 receipts and 200 result revisions per plan. Larger
studies need a reviewed protocol/backend change rather than silent truncation.

## Results, retention and currentness

Each phase appends a globally numbered ImprovementEvaluation revision with original
baseline, current follow-up/practice memberships, source/review manifest, collection
receipt hashes, specification/plan hashes, diagnostics and all six legitimate outcomes.
An identical phase/result returns its prior revision. Earlier results are never rewritten.
Reviewed practice stays inside the original baseline-to-initial-follow-up interval;
retention cannot add late practice to reinterpret the original intervention.

Retention compares its declared later window against the same baseline. It pins the latest
available initial result hash and its follow-up evidence. `OBSERVED_CHANGE_PERSISTS` requires
both valid phase results to show observed improvement. This does not test a causal effect
or assert significant change between follow-up and retention. Without a usable initial
result, retention explicitly reports `INITIAL_COMPARISON_UNAVAILABLE`. There is no adaptive
window selection or automatic difficulty/threshold change.

Private current reports/overview recheck consent, grants, source availability, publication,
opportunity/review/decoder hashes, complete collection and initial retention reference.
Changes mark old results unavailable; active UI counts/intervals are hidden. Re-evaluation
appends a new revision. Downloadable `comparison-report/1` includes safe provenance,
spec/protocol, collection and historical revisions, a canonical report hash and explicit
availability. It exports no raw media, storage paths, opponent external IDs or reviewer
labels. An unavailable historical result is clearly labeled in the export. Time/UUID
normalization makes unchanged reload/download hashes reproducible.

## Adequacy and uncertainty

Existing session-cluster bootstrap with conservative finite-sample Beta envelope remains
the decision engine; raw counts, unknowns, exclusions, coverage, independent session
counts, descriptive intervals and next actions remain visible when current. Five sessions
and forty outcomes are exploratory floors, not validated power or causal approval.

Baseline-only diagnostics show per-session known-outcome range, dominance and rate variance.
With at least ten nondegenerate baseline sessions, an illustrative normal approximation
uses n = ceil(2 × sample variance × (z(.975) + z(.8))² / meaningful-change²), bounded at
1000. Assumptions: independent session-rate samples, equal variance and a normal approximation.
Sparse/constant variance leaves planning unknown; no post-hoc power is reported. Actual
independence, variance, effect size, missingness/selection bias, retention and powered study
design need qualified real evidence and prospective review. The UI/export always labels
planning only and `actual_power_validated=false`; release approval stays false.

Migration 0020 preserves legacy hashes and default FOLLOWUP phases. Fresh empty reverse is
supported; populated scheduled/session/retention history blocks destructive rollback and
requires reviewed forward repair. Native PostgreSQL rehearsal covers forward/reverse/forward,
dump/restore, repeated controls and receipt erasure/result invalidation.
