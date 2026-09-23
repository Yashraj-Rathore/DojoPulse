# Minimum data model

| Concept | Representation / decision |
|---|---|
| User / PlayerProfile | Django User and one owned profile; no automatic opponent accounts |
| Game / GameBuild / Character | stable keys, platform and release provenance; nullable unconfirmed media build |
| Move / MoveVersion / FrameData | stable move identity plus immutable version payload; frame data embedded in the version, not an empty table |
| KnowledgeRevision | immutable snapshot with provenance, hash and verification state |
| ReplayAsset / ReplaySegment | private source identity and time/mode ranges; no public paths |
| Match / Participant / Round | played-at with certainty, stable participants; rounds optional until segmented |
| AnalysisRun / AnalysisPublication | durable run and one current publication per match |
| ObservationArtifact | hash/path manifest for dense observations |
| GameplayEvent / Opportunity | sparse event; opportunity is a typed extension with eligibility/outcome |
| SituationDefinition / MetricDefinition | versioned contract records, required evidence and comparability |
| MatchContribution / PlayerStatistic | one active contribution per match/metric; statistic is computed, not independent truth |
| DetectedWeakness / Recommendation | one evidence-backed candidate and assignment recommendation; no ML score |
| DrillVersion / Assignment / Session / Attempt | immutable drill; actual exposure and review provenance |
| EvaluationPlan / ImprovementEvaluation | immutable plan and revisioned result with frozen membership |

Database constraints cover FK ownership paths where possible, unique source opportunity keys,
success implies eligible, nonnegative time/counts, one active contribution and unique evaluation
revision. Service transactions enforce same-owner nested references, membership freezing,
same-definition comparisons, chronology, practice provenance and deletion invalidation.
Model saves validate immutable fields; bulk SQL is trusted internal code and must not bypass
these commands. PostgreSQL is authoritative; SQLite is only a portable unit-test fallback.

No table per raw video frame. No generic EAV schema. No all-game universal simulator.

## Provider-neutral extension (local relational cutover implemented)

PlayerGameIdentity links an owner to a namespaced public game ID with explicit aliases,
provenance and claim/verification state. MatchSource is the versioned provider policy;
MatchSourceRecord preserves source-scoped IDs and revisioned metadata assertions. ReplaySource
links a canonical match to optional video, native payload or structured-event representations,
each with its own availability, build compatibility and retention. Provider cursors and
coverage gaps belong to durable sync state, not the match or player-statistic table.

Migrations 0003/0004 make Match.asset optional and backfill USER_UPLOAD ReplaySource rows.
The FK remains a compatibility pointer for the existing video analysis path. Historical event
rows and frozen evaluation memberships are preserved. PlayerGameIdentity, MatchSourceRecord,
ReplaySource and MatchSync are relational; identity alias bindings remain a future extension.
Metadata-only records cannot enter the punish denominator. Full schema, ownership/uniqueness
invariants and migration order: [match ingestion](match-ingestion.md).

Migration 0005 adds recording attribution state and hashed review provenance to ReplaySource.
New imported-match recordings stay PENDING_REVIEW until media validation and explicit operator
attribution. Approval selects Match.asset without creating another Match. GameplayEvent source
hashes follow AnalysisRun.asset, never a replacement recording selected later on the match.
Deleting a recording withdraws its events/contributions and retains imported metadata; frozen
historical context and knowledge facts remain immutable. See [ADR-014](../adr/ADR-014-recording-attribution.md).
