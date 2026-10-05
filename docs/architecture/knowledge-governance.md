# Local knowledge governance

Architecture 2.11.0 / 2026-10-03. [Decision](../adr/ADR-019-reviewed-knowledge-releases.md).

Use `/knowledge` from an active local operator account. Register an exact build/version
and platform as UNVERIFIED, upload supported continuous footage with explicit platform,
and complete media validation. Existing recordings without platform evidence remain private
but cannot support a governed release. Never infer capture build/platform from a research
date, provider's current patch or newest knowledge. Canonical build keys and labels must agree.

Prepare and independently review these versions in order:

1. Build: captured version, platform and visible overlays.
2. Move: stable move code, integer startup/on-block facts, offline reach/timing fixture
   references. Unknown facts remain drafts; templates intentionally contain nulls.
3. Situation: existing Jin standing blocked-uf4 semantics, mandatory observations,
   trigger and explicit unknown/exclusion rules.
4. Metric: eligible successes / eligible known outcomes; unknowns excluded and reported.
5. Knowledge: exact build confirmation and situation/metric/move dependencies.
6. Drill: matching measurement, title, bounded repetitions, native practice/setup.
7. Compatibility: source/target knowledge, disposition and reviewed offline change rationale.

Candidates bind 1-10 owned validated sources of at most ten minutes, matching version,
platform/scope, with an unexpired retention deadline. The author permits two assigned
reviewers to view each whole recording and declares permission to publish game facts
without personal material or proprietary imported tables. Evidence/notes are private;
references are bounded offline codes, never URLs fetched by the service. Payloads are
bounded to 32 KiB and checked by kind. Two active independent staff reviewers attest to
the exact sealed digest. Local roles do not certify expertise, rights or in-game truth.

`KnowledgeProposal`, `KnowledgeEvidence` and immutable `KnowledgeReview` preserve the trail.
Publication creates a new immutable `DefinitionVersion`; the associated proposal is the
revocable grant. Draft flags never change. Dependency hashes/builds and drill-to-knowledge
alignment are rechecked. Synthetic versions remain synthetic and author-workspace scoped.
Legacy approvals are accepted only for synthetic fixtures; ungoverned real publication is
rejected. Catalogs, assignments, practice, plans/evaluation, recording attribution and
annotation import check current grants instead of trusting APPROVED alone.

Session/CSRF/rate-limited endpoints: `GET/POST /api/knowledge`, `POST /api/knowledge/builds`,
proposal `review/publish/retire/withdraw` commands and private source range playback.
Other decisions stay sealed until a reviewer's own submission. Playback rechecks grants
while streaming and returns no public storage paths/capabilities. Exports contain owned
proposals, own reviews/reanalysis receipts, excluding other reviewers' notes/identifiers.

Retirement stops new use while historical measurements retain their exact valid definitions.
Withdrawal invalidates downstream releases/conclusions and fences queued work.
The affected gameplay rows are withdrawn from active views while their historical values
and frozen memberships remain stored. Worker claims, gameplay publication and plan writes
take owner then shared-capacity locks before domain rows, matching cross-account reviewer
revocation; no second owner's lock is acquired after the shared lock.
PostgreSQL owner locks use FOR NO KEY UPDATE: owner writes remain serialized while
foreign-key checks on another account's shared records can complete at commit. Services
never rewrite user primary keys; account deletion remains a serialized tombstone.
Account/consent/source erasure removes private candidate JSON, notes and source grants; permitted
published facts and nonprivate hashes remain for audit. Expiration blocks use before the
purge worker runs. Restore quarantine erases grants/notes, including withdrawals newer than
the backup. Re-consent cannot reactivate them: prepare a new version/review.

Preview `/api/knowledge/reanalysis?mapping_key=...` before an explicit POST with owned match,
mapping key and stable request UUID. At most 500 matches are previewed; jobs use existing
account/admission/resource limits. REANALYSIS_REQUIRED permits a canonical AnalysisRun only
for the target's captured build/platform. SAME_MEASUREMENT records a decision without
extending frozen comparisons; INCOMPATIBLE abstains. A patch difference cannot be repaired
by relabeling a recording. Original metadata, selected-publication revision and source/
definition hashes are pinned and rechecked at reviewed replacement. Interrupted requests
preserve UUIDs; changed/cancelled work rejects reuse. Workers validate media, not gameplay.

`GameplayEvent.measurement` pins analysis knowledge/situation/metric. `as_opportunity` keeps
older hashes when a new run is selected. Match build/knowledge remains capture history.
Reviewed annotation import atomically replaces active contributions; prior events and
frozen evaluation memberships remain. Rules still cover one target with mandatory unknowns.

Real activation needs reviewed current-build footage, actual independent experts, source
rights, frame/reach/timing evidence and a documented release decision. Hosting needs
qualified private reviewer authorization, storage, isolation and recovery. No provider,
undocumented endpoint, detector, real study, expert approval or deployment is enabled.
M07.02/.03/.05 release gates remain open.

M08 adds an [explicit source-specific dataset measurement grant](dataset-operations.md).
An owned retained source may import only its exact independently reviewed current
snapshot batch through the canonical operator publisher, with snapshot/definition hash
pins. This does not make another workspace's synthetic definitions or drills generally
available; dataset withdrawal invalidates derived active events and evaluations.

M10 permits an optional `priority_assessment` on a **new** governed drill version.
Its exact version, bounded relative value/trainability and rationale are sealed and reviewed
by the same independent reviewers alongside the drill's sources/dependencies. Existing versions
are not rewritten; missing or ambiguous assessments have no default weight. See the
[player-model contract](player-model.md) and [ADR-021](../adr/ADR-021-evidence-backed-player-diagnosis.md).
