# Progress

This file is the chronological implementation log. For the authoritative current milestone and
requirements checklist, read [PRODUCT_PROGRESS.md](../PRODUCT_PROGRESS.md). Both files must be
updated after every implementation, as required by [AGENTS.md](../AGENTS.md).

## Phase 0-1 — 2026-09-18

Completed: inventoried sole original architecture, read original and conversation review,
reconciled must-change items, created V2 domain/pipeline/evaluation/security/experiment documents.
Files: docs/architecture*, docs/experiment-results, decision log and forthcoming ADRs.
Tests: none run yet; documentation phase. No application or gameplay results claimed.
Validated: Python 3.12, Node 22, FFmpeg/FFprobe present. Docker CLI exists; daemon initially absent.
Unvalidated: all gameplay/capture/transfer hypotheses, current in-game move facts and drill review.
Next: contracts, dataset tooling and local deterministic pipeline; keep automatic claims gated.

## Phases 2–10 — local implementation

Completed: candidate scoring and provisional Jin mirror block-punish target; frozen draft
situation/capture/knowledge/drill contracts; independent annotation schema and split validation;
bounded FFmpeg/OpenCV CLI; outcome-specific perception metrics and cost harness; Django/DRF
domain, PostgreSQL migrations, fenced worker, private media, deletion lineage, frozen plans,
session-aware comparison and verified practice import.
Files: contracts/, datasets/, game_data/, analysis/, tools/, backend/, tests/.
Tests: first 42 pure/media tests passed. First integrated PostgreSQL run: 52 passed, 1 failed;
failure revealed tuple/list JSON normalization creating duplicate evaluation revisions. Fixed
with canonical-content comparison; regression rerun pending. Ruff and mypy passed after formatting.
Validated: isolated PostgreSQL 17 runs on loopback port 55432; migrations and draft contract
loading succeed. Existing PostgreSQL service was not modified. Real FFmpeg synthetic input is
probed/extracted and correctly produces no gameplay claims.
Unvalidated: all six real-game experiment gates; current capture overlays, move facts, frequency,
drill correctness, transfer, economics and hostile-media container isolation.
Blockers: no real footage/reviewers; Docker Desktop daemon unavailable. Hosted/external ingestion
remains disabled. One drill exists as a draft, with no fabricated expert approval.
Next: integrated loop, security regressions, frontend smoke checks, CI, operational README and
prospective pilot handoff. Statistical bounds now include a finite-sample uncertainty envelope
to prevent a misleading zero-width session bootstrap when every session has the same rate.

## Phases 11–14 — local prototype and pilot handoff

Completed: thin Next.js capture/review/practice/evaluation UI; measured practice summaries;
explicit unknown/uncertainty displays; local asynchronous worker and retention command;
CI with PostgreSQL/FFmpeg and browser checks; offline parser Docker candidate; development
README; prospective native/usual-workflow comparator and all six experiment result templates.
Files: frontend/, .github/workflows/ci.yml, infrastructure/, README.md, docs/pilot-protocol.md,
docs/experiment-results/, backend/core/ownership.py and expanded service/security tests.

Validation: 64 PostgreSQL-backed Python tests pass, including a complete synthetic API loop,
actual multipart ingestion/FFmpeg worker/purge, concurrent claims and deletion versus publication.
Ruff lint/format, mypy (16 analysis/tool modules), Django checks/migration drift pass. Next.js
production build, ESLint, TypeScript and 2 headless Edge smoke tests pass; screenshot inspected.
The latest immutable-insert hardening received a final regression run recorded in results.

Measured synthetic benchmark: 3 runs / 1 unique 0.5-second black clip, median 2.843 seconds,
peak sampled decoder RSS 222,605,312 bytes, zero failures. Costs remain null without actual
rates/invoices. See software-validation.md for denominators, limits and reproducible commands.

Assumptions validated: local services run with PostgreSQL; software distinguishes unknown from
failure; practice provenance, frozen evidence, version compatibility and deletion lineage are
enforced by the tested service boundary. No gameplay assumption was validated by these tests.

Phase 12 hosted deployment: intentionally NOT EXECUTED. External ingestion remains disabled.
The Docker daemon was unavailable; parser isolation, actual cloud resumable cancellation,
maximum-profile resource behavior and restore/deletion integrations remain untested.
No paid resources, real user accounts or external communications were created.

Remaining blockers: real game footage and consent, exact in-game build/overlay verification,
expert drill/knowledge review, independent annotators and a prospective cohort. G1–G6 remain
NOT_RUN. Exactly one draft drill exists; it is not described as expert-reviewed.
Next authorized step: use the pilot protocol to collect/review the initial 20 captures, then
make a documented continue/narrow/stop decision before expanding recognition or hosting.

## Provider-neutral match ingestion — 2026-09-18

Completed: researched official replay update behavior, Wavu public metadata flow/API, current
EWGF public API and pinned archived backend. Verified one documented Wavu response's field
types; retained only the schema. No private game endpoints, authenticated EWGF calls, game
credentials, native payloads or provider communications were used.

Architecture 2.1 adds PlayerGameIdentity, versioned MatchSource policy, MatchSourceRecord and
ReplaySource design, identity selection/ownership distinction, source-scoped IDs, raw/canonical
build handling, replay expiry, immutable provenance, quotas, retries, cursors and coverage gaps.
The canonical event/player model remains provider-independent. Metadata supports history and
results, but cannot establish punish opportunities. Upload remains the gameplay-evidence fallback.

Files: docs/research/tekken-match-sources.md, docs/architecture/match-ingestion.md, ADR-013,
contracts/match-sources-v1.json, ingestion/ typed protocols/policy/offline normalizer,
synthetic fixture and tests/test_ingestion_contracts.py; V2/context/model/security/pipeline docs
and README linked to the addition.

Validation: 27 new contract tests pass; full PostgreSQL-backed suite: 91 passed in 27.09s.
Ruff lint/format, mypy (20 modules), Django system/migration-drift checks and documentation
link validation pass. No schema migration or frontend change was required for this design.
Validated assumptions: metadata/payload distinction; large integer IDs preserved; legacy
Polaris-to-TEKKEN-ID DTO mapping; reviewed permissions cannot be inferred from access class.

Open: commercial/provider usage clearance, permitted name resolver, authenticated EWGF schema,
coverage/SLAs, native replay format/decoder and automatic import lifecycle integration.
The architecture explicitly stages the mandatory Match.asset removal and upload provenance
backfill; no DB cutover or live identity/sync API is claimed in this design change. All network
providers ship disabled. Next: approve a concrete public-provider operation/purpose, obtain
permitted live fixtures, implement/test the staged relational cutover, then enable history import.

## Local match-import implementation — 2026-09-19

Completed the next authorized steps: migrations 0003/0004 add PlayerGameIdentity,
MatchSourceRecord, ReplaySource and MatchSync; Match.asset/build/session/context/knowledge can
be absent, and existing uploads receive USER_UPLOAD source links. New uploads dual-write those
links. Metadata imports preserve unmapped raw codes and create no gameplay events or fake media.

Two in-memory adapters and `import_synthetic_matches` exercise explicit identity selection,
owner isolation, idempotent refresh, provider-scoped IDs, revisioned corrections, atomic page
checkpoints, coverage gaps, fenced leases, bounded retries and replay availability changes.
Corrections cannot rewrite reviewed gameplay facts; dependent active conclusions are invalidated.
Metadata deletion removes assertions and revokes local identity sync; account deletion removes
identity/sync state. No provider credentials or live transport were introduced.

Validation: 112 PostgreSQL-backed tests passed in 42.12s. The upgrade rehearsal starts at 0002,
creates historical upload/event/frozen-plan records, applies the current migrations and verifies
preservation plus the source backfill. Concurrency tests cover one winning sync claim and
deletion versus page commit. Ruff, mypy (21 modules), Django checks and migration drift pass.
The isolated local database has migrations 0003/0004 applied. Frontend code was unchanged.

Next: review a documented provider's operation/purpose and permitted live schema; then add the
player-link/sync/history API and UI. Native payload decoding, verified identity ownership,
cross-provider merge review and video-to-imported-match attribution remain future work.
Real gameplay gates G1–G6 remain NOT_RUN.

## Player linking and match-history UI/API — 2026-09-19

Implemented explicit candidate lookup/selection, signed owner-bound five-minute confirmations,
processing consent, linked identities, queued discovery, private paginated history, sync status,
revocation and metadata deletion. History shows source revision, unknown mappings, incomplete
coverage and replay availability independently of gameplay evidence. Small screens use stacked
match cards. A correction awaiting review returns an unknown result; all committed page gaps
remain in the conservative coverage summary.

`process_match_syncs` processes bounded pages outside HTTP. Resolution, queuing and processing
require local DEBUG, LOCAL_MATCH_IMPORTS and staff status. Two fictional fixture providers are
available; EWGF and Wavu are displayed as unavailable. No provider transports, account keys,
subscriptions or private endpoint access were implemented. Existing capture workflow remains
the available evidence fallback; video-to-imported-match attribution is still pending.

EWGF's public documentation was rechecked, including its request/error contract. Substantive
terms text and expandable match-response fields were not available from extraction; the browser
tool had no available browser. The activation review records usage rights, private credential
setup and permitted current-schema fixtures as unresolved. No provider was contacted.
See [review](research/ewgf-activation-review-2026-09-19.md) and README for the concrete next inputs.

Validation: **124 Python tests passed in 27.97s**, including 12 new API/worker checks.
**5 headless Edge browser tests passed in 8.4s**; desktop and revised mobile screenshots inspected.
Frontend ESLint, TypeScript and Next.js production build pass. Ruff lint/format, mypy (21 modules),
Django system/migration-drift checks pass. No additional DB migration was required.
The workspace PostgreSQL cluster was restarted after it had stopped between sessions.
The UI defaults to disabled demo imports until the documented local flag and worker are enabled.
G1–G6 remain NOT_RUN; no real gameplay or provider availability claim follows from these tests.

## Comprehensive product tracker — 2026-09-19

Requirement: M01.05. Created [PRODUCT_PROGRESS.md](../PRODUCT_PROGRESS.md) as the authoritative
current-status checklist: 21 milestones and 136 uniquely identified requirement rows, including
12 conditional wider-platform capabilities. It covers the local prototype, permitted real
ingestion, validated knowledge/detection/practice/comparison, complete player UX, account/privacy
lifecycle, security, hosting, operations/economics, pilot, beta, supported launch and later breadth.

Current status is explicit: M01–M03 complete within local scope; no validated real-game product,
live provider or hosted release. G1–G6 remain NOT_RUN. Each remaining requirement has acceptance
criteria or concrete missing input. Existing software validation is referenced with its date,
not presented as a new test run. No overall percentage or unsupported completion claim added.

Files: PRODUCT_PROGRESS.md, root AGENTS.md, README.md, docs/progress.md and docs/decision-log.md.
AGENTS.md requires reading/updating affected requirement IDs after every implementation, updating
the current snapshot and next work, and appending an evidence-based work-log entry in the same
change. README and this log link to the tracker; historical entries are preserved.

Validation: checked all 21 milestone sections, uniqueness of 136 requirement IDs, allowed status
values, agreement between completed milestone summaries and their rows, relative documentation
links, and git diff whitespace. All pass. No application tests added or re-run for this
documentation-only change. Product/scientific assumptions and external blockers are unchanged.
Next: use requirement IDs to scope the next implementation; obtain permitted provider inputs
and consented real evidence while continuing independent product/security work.

## Reviewed recording attachment to imported matches — 2026-09-23

Requirements: M06.03, M06.06, M06.07, M13.03; related invariants M02.05 and partial M05.07.
Implemented a local owner/staff-gated multipart attachment API, mobile form, private review
link, reprocessing and recording removal. Migration 0005 stores ReplaySource attribution
claims/digests and review provenance. Uploads preserve the canonical match and source assertions,
pin the byte hash, validate IDs/slot/time/build/mode/session/dataset against known facts, and
queue the existing media worker. Request UUIDs provide idempotency; duplicate bytes, multiple
active attachments and stale metadata are rejected. An interrupted/deleted target cannot leave
an uncommitted recording behind.

The new `review_recording` command requires successful media validation, a matching source hash,
explicit visual review and exact-build knowledge. Real evidence additionally requires approved
knowledge and a verified build. Attribution approval selects the optional Match.asset; it does
not publish gameplay events. Existing independent annotation review remains necessary.
Event source hashes now follow their original AnalysisRun.asset. Replacement recordings cannot
rewrite historical gameplay/knowledge facts or frozen memberships. Deletion/expiration withdraws
the recording and dependent evidence while preserving imported match metadata. Account deletion
covers pending attachments and fences late workers. The media worker rejects changed source bytes.

Files: backend/core/{recordings,recording_api,match_api,evidence,storage,models}.py, API routes,
management commands review_recording/process_runs, migration 0005, frontend attachment/history
components and styles, attachment and browser tests, README, ADR-014, architecture/data/pipeline/
ingestion documentation, decision D021 and this tracker. Architecture is now 2.3.0.

Validation: **145 Python tests passed in 28.17s**, including 21 new attachment checks and a real
FFmpeg run on generated synthetic media. **7 headless Edge tests passed in 9.3s**, including
consent, attachment/removal, preserved history and stale-metadata error display. Browser tests
mock HTTP; Python separately tests actual API/database/worker behavior. Mobile form screenshot
inspected. Frontend build/lint/types, Ruff lint/format, mypy (21 modules), Django system and
migration-drift checks pass. Migration 0005 applied to the isolated local PostgreSQL database.
The stopped local database was restarted; a run stalled before startup was cancelled and rerun.
The first browser run found an ambiguous test alert locator; scoping it to the form fixed it.
After the final history-action gate adjustment, all 33 focused match API/attachment tests passed
in 5.91s. Ruff checks, documentation links, unique tracker IDs and git diff whitespace also pass.

Assumptions/limits: one supported Jin/Jin recording, trusted local operators, human attribution,
synthetic correctness only. Hosted upload/isolation, real capture/attribution accuracy, knowledge
approval, provider usage rights/credentials/schema and all G1–G6 gates remain unresolved.
No live or undocumented provider transport was added. M06.03 is PARTIAL at product scope despite
the completed local implementation. Cross-provider deduplication remains future work.
Next: integrated evidence timeline/accessibility (M13.03–M13.07), and parser isolation rehearsal
(M15.02) when the container runtime is available; continue obtaining consented real evidence.
