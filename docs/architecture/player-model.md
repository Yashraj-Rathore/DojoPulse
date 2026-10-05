# Player statistics, diagnosis and priorities

Architecture 2.13.0; local M10 engineering contract, 2026-10-05.
[ADR-021](../adr/ADR-021-evidence-backed-player-diagnosis.md) records the policy.

Binary outcome uses Beta(1 + successes, 1 + failures), with observed k/n and 95% credible
interval. Unknown outcomes are excluded from n and separately shown. Eligible outcome coverage
is known outcomes / all known-eligible opportunities. Unknown eligibility is separately reported.
This coverage is NOT detector recall; only external labels establish recall.

Categorical actions use declared Dirichlet pseudocounts and mutually exclusive first actions.
No neural embedding, arbitrary skill score, or rank-derived competence label. Context starts
with player, own/opponent character, situation and compatible build. Side/resources are recorded
but not multiplied into sparse buckets before data supports them.

Independent-event credible intervals are descriptive. Match-transfer inference uses paired
period/session blocks, enough independent sessions and a prespecified meaningful difference.
Current estimates are projections from selected contributions. Reanalysis replaces contributions.

## Current diagnosis projection

`GET /api/player-model` is session-authenticated, private/no-store and serialized against
owner/account consent changes and shared knowledge/dataset withdrawal. It reads canonical
current publications directly. `MatchContribution` caches do not authorize diagnosis.
Only ranked observations with reviewed chronology/context, retained current source references
and an effective knowledge/dataset grant enter cards. Practice and metadata-only matches
cannot become gameplay observations. Withdrawn/unavailable rows are disclosed separately.

Default scope is real data and the last 90 UTC dates. Allowed filters: date_from/date_to,
character/context, dataset_kind, game_build, situation, knowledge_revision,
detector_version and platform; offset/limit paginate cards, not denominators. At most
366 dates, 1,000 ranked matches, 20,000 current events, 100 measurement groups and
100 exactly matching approved drill versions per group are
computed per request. Larger scopes fail with a narrowing instruction; no silent cutoff.
Repeated/unknown parameters and outcome/eligibility/mode filters are rejected.

Groups pin situation, metric, context, build, knowledge version/hash, detector, platform
and real/synthetic scope. Version filters do not waive compatibility. Multiple profiles
remain separate and unranked; explicit selection of one profile is required to rank.
The supported semantics remain Jin versus Jin, standing reachable blocked uf4 punishment.
No new situations, characters, automatic recognizer or provider are enabled.

`diagnosis-policy/1` is an immutable code-reviewed **proposed** policy: at least 40 known
eligible outcomes and five distinct reviewed sessions; at least 90% known outcome and
eligibility coverage; independent review of every included window and at least 80% raw
label agreement; 95% descriptive Beta failure interval lower bound of at least 20%.
Session identifiers do not establish statistical independence. Thresholds need prospective
expert/user qualification before real diagnosis. Reasons explicitly distinguish insufficient
evidence, review gaps, unsupported scope, no clear pattern and real validation pending.
Real diagnosis/ranking release approval is always false in this module; no environment
switch activates it. Synthetic patterns are visibly software qualification fixtures.

## Reviewed priority assessment

A governed drill may optionally include this fictional fixture assessment:

```json
"priority_assessment": {
  "version": "priority-assessment/1",
  "value": 0.7,
  "trainability": 0.8,
  "rationale": "Synthetic relative assessment for software qualification only."
}
```

Exact fields, finite fractions in [0,1] (no booleans), version and a 5–2,000 character
rationale are validated. M07 seals these fields in the same payload/source/dependency
hash and requires its existing two independent approvals. Original drill versions are
unchanged; adding/changing assessments requires a new proposal/version. Match exact
build/platform, situation, metric, knowledge and authorized workspace/scope. Foreign
dataset measurement grants do not grant general drill access. Zero assessments or more
than one assessed matching drill means no score, with an explicit missing/ambiguity reason.

Research score = eligible-window share × reviewed relative value × certainty × reviewed
trainability. Certainty = descriptive failure interval lower bound × raw label agreement.
Eligible-window share includes eligible unknown outcomes and divides by **all reviewed
candidate windows**, including unknown eligibility and exclusions. It is not attack
occurrence per match, detector recall, damage, expected benefit or a global skill score.
Value/trainability are explicit reviewed relative judgments, not learned probabilities.
Within one compatible profile the score sorts deterministically, with at most three
ranked priorities and stable ID tie-breaking. A missing assessment never becomes 1.0.

## Cards, trends and lifecycle

The home workspace shows counts, unknowns/exclusions, both coverages, sessions,
descriptive failure uncertainty, raw review agreement, thresholds/reasons, factor values,
matching reviewed drills and policy/knowledge/assessment/evidence hashes. Up to five
timestamp examples sample failures first; complete selected evidence determines counts.
The evidence hash covers opportunity content, timing, review and measurement pins.
Private playback and full-match inspection reuse the existing owner/grant/retention checks.

Monthly gameplay summaries remain within the exact measurement profile. Recorded ranked
match wins/losses/unknowns have their own denominator and date/context/build scope.
Situation/knowledge/detector/platform filters apply only to gameplay; the UI states this.
Missing/disputed player-slot or winner mapping is an unknown result. Neither monthly view
establishes improvement or causation; the frozen baseline/practice/follow-up M12 mechanism
is unchanged. Baseline recommendation records are displayed as frozen snapshots.

No new tables or diagnosis caches are introduced. Current-publication selection prevents
revision double counting; per-source grant memoization exists only inside the locked
read. Source expiry/deletion, metadata disputes, dataset/knowledge/reviewer withdrawal,
consent withdrawal and restore erasure remove evidence/authority from subsequent reads.
Visible UI polls every ten seconds and clears stale cards on failed reads/scope changes.
Actual hosted workload/performance, expert thresholds/relative ratings, qualified reviewer
agreement, real comparability/selection bias and player usability remain unvalidated.
