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

## M13 player experience — implementation checkpoint, 2026-09-23

Scope: all M13.01–M13.08 local engineering, plus supporting M14.04/M14.05 services.
Added persistent onboarding/timezone/notice preferences, owner-scoped timeline and match filters,
private byte-range playback, guided baseline/practice/follow-up navigation, feedback/correction
queue, in-app notices/dismissals, whitelisted JSON export and password-confirmed account deletion.
Deletion tombstones every asset before file cleanup so a failed purge can resume safely.
Frontend integration and synthetic browser checks are being verified; real providers, hosted
accounts, reviewer operations and real-player/screen-reader/device studies remain unvalidated.
Migration 0006 applied locally; first 17 new backend API/security/playback checks pass (13.83s).
Final regression results and remaining acceptance criteria will be recorded below before push.

## M13 player experience — implementation verified, 2026-09-23

All M13.01–M13.08 local engineering is integrated: persistent supported-scope onboarding,
searchable owner-scoped match history and current-event timeline, source-window player and byte
ranges, complete-match selection, provenance/correction states, coherent baseline/drill/frozen-plan/
practice/follow-up navigation, local account export/deletion, help and correction queue, in-app
notices and preferences. M13.05 and M13.08 meet the declared local acceptance scope; the milestone
remains PARTIAL because its real-player exit depends on permitted providers, production accounts,
review/measurement readiness, real usability, screen readers and device/browser qualification.

Privacy controls do not expose source paths, upload tokens, raw provider assertions or other
people's identity snapshots in exports. Password/confirmation/CSRF protect account deletion;
login identity is pseudonymized, all assets tombstoned before file IO, late workers fenced, and
feedback/receipts removed. Failed purges remain retryable for every asset. Correction feedback
cannot rewrite an event. Onboarding/notice preferences do not grant training consent. Notices
remain in-app, bounded to latest 100 records/category; no external messages were sent.

Files: experience_api/search/media_response, Profile/Feedback/NoticeReceipt and migration 0006,
API/history/overview/admin/storage integration; workspace tools, evidence browser, training journey,
shared client/time formatter, history/attachment/page/styles; API and browser tests. Added the
player-experience architecture contract, updated README/data/privacy docs, decisions D022/D023,
Architecture 2.4.0 and this tracker. The existing validated foundation was committed separately
as db2b6b1 because the remote initially contained only the architecture skeleton.

Validation: **163 PostgreSQL-backed Python tests passed in 42.65s**; **11 headless Edge browser
tests passed in 14.3s**. Eighteen new API tests include consent separation, owner/CSRF boundaries,
UTC filters/pagination, disputed evidence, idempotent feedback/notices, plan-window transitions,
export exclusions, account deletion failure/retry and range playback. Four new browser journeys
cover onboarding/preferences/notices/feedback/export, mobile keyboard/timeline/corrections,
confirmed deletion/sign-out, and synthetic baseline -> frozen plan -> practice -> honest comparison.
Browser tests mock HTTP; actual persistence/media serving are tested in Python. Desktop/mobile
screenshots inspected; UTC and America/Toronto rendering checked. ESLint, production build,
TypeScript, Ruff lint/format, mypy (21 modules), Django system/migration-drift checks pass.
Migration 0006 applied locally. Export now checks API success before creating a downloaded JSON
file, avoiding silent download of an error response. No secrets/media/dependencies staged.

Remaining: no real provider access, signup/recovery service, automatic detector, approved real
drill, hosted deployment or completed user study. G1–G6 remain NOT_RUN. Next: real-device and
screen-reader/participant qualification and M15.02 parser isolation once its runtime is available;
continue provider, expert and consented-data preparation. User authorized publication to main;
push/remote CI outcome is recorded separately after execution.

## M13 publication and first remote CI — 2026-09-23

Published foundation `db2b6b1` and M13 `13209e1` to `origin/main` under the user's explicit push
instruction. `git ls-remote` verified main matched the implementation SHA; the implementation
working tree was clean. [GitHub run 35877396459](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/35877396459)
reports successful frontend (Linux Chromium, 1m28s) and Python/PostgreSQL (1m52s) jobs. The workflow
aggregate was still finalizing when this receipt was written; job-level success is the evidence
recorded here. This establishes remote software checks, not hosted application/staging qualification.
M19.02/M19 are therefore PARTIAL. Documentation-only publication receipt follows the implementation
commit; it does not change the tested code. M13's real-player release dependencies remain open.

## M15 local security, privacy and reliability implementation — 2026-09-29

Requirements: M15.01–M15.07; CI configuration also affects M19.02. User requested the whole
milestone. Implemented the available local module and kept its external release exit explicit.
Architecture is now 2.5.0; decision D024 records the trust/admission boundaries.

Changed backend settings/API/upload handlers and added `security.py`, `parsers.py`, migration
0007 and `security_maintenance`: atomic PostgreSQL request budgets, fixed-code audit logging,
private API responses, bounded JSON/form bodies, pre-multipart upload reservations, source
storage accounting including unpurged tombstones, queue/daily/active-job limits and reservation
revocation on account deletion. Match-sync admission is bounded too. Jobs, recordings and
annotation publication enforce nested ownership; cancellation is limited to pending/active
jobs. Fenced run completion now publishes source hashes transactionally, and the coordinator
independently hashes source bytes before trusting decoder reports.

Added `backend/core/parser.py` and `tools/sandbox_capture.py`; updated the Dockerfile and
introduced `requirements-analysis.lock`. The default worker requires an immutable Docker
image ID and fails closed. The parser has no network, application credentials, Docker socket
or host output mount; kernel resource limits, ephemeral tmpfs, process cancellation and an
explicit PID-1 lifetime handler are tested. Only shaped FAILED/REVIEW_REQUIRED reports return;
no gameplay opportunities are accepted. Trusted local fixture mode remains explicitly gated.
Offline `ingestion/boundary.py` validates reviewed target/DNS/response boundaries without
performing any HTTP request or enabling a real provider.

Added three security/provider/sandbox test modules, expanded CI with sandbox/advisory jobs,
added Dependabot configuration, SECURITY.md, a threat model, incident runbook and
[dated qualification receipt](experiment-results/m15-security.md). Updated setup/environment
instructions and deployment architecture. No frontend source change or external deployment.

Actual validation: **209 Python/PostgreSQL tests passed in 52.61s**; the ordinary run skipped
seven explicit Docker tests, which were run separately: **seven passed in 153.86s** on local
Docker 24.0.6/cgroup v1. The exact 600-second/512-MiB synthetic file decoded in 60.80s,
with 58.45 decoder CPU seconds and sampled peak decoder RSS 239,579,136 bytes; oversized input,
malformed input, scratch/PID/memory exhaustion and lifetime/cancellation cleanup were exercised.
Ruff lint/format, mypy (23 modules), Django system/migration-drift checks passed; migration
0007 applied to the existing loopback cluster. `pip check` passed after editable metadata refresh.

The first audit found two DRF 3.16.1 advisories; upgraded the lockfile/project constraint and
local environment to 3.17.2. Final pinned Python audit and npm production audit reported no
known advisories. Installed pip-audit only as a development checking tool. Frontend checks
remain the earlier 2026-09-23 evidence; new CI jobs have not run remotely. Initial test failures
were resolved (legacy gate expectations, trusted local fixture settings, cgroup layout/network
inventory assumptions, preserved hash-error code and bounded-body response handling).

Operational changes: started Docker Desktop hidden and recovered the existing workspace
PostgreSQL cluster after its prior unclean shutdown; no cluster recreation, credentials,
accounts, provider access or paid/cloud resources. Test fixtures and local XML/JSON receipts
remain ignored. No commit/push was performed for this task.

Remaining: worst-complexity/exploit media corpus, independent security/privacy review and
named response ownership, production ingress/temp quotas and kill deadline, managed IAM/secrets,
OS image vulnerability review, restore suppression and actual permitted-provider failure injection.
The in-container deadline is not a guarantee against compromised code disabling its handler.
M15.02 moves BLOCKED → PARTIAL; M15.03/.07 move NOT_STARTED → PARTIAL. M15 stays PARTIAL
because its exit concerns an externally exposed workload. Next: independent review and
deployment-specific qualification, alongside the existing permitted-provider and real-data gates.

## M15 publication preflight and remote reconciliation — 2026-09-29

User explicitly authorized pushing M15. Committed the implementation as `516b519`.
Fetch showed remote `301ed0b` replacing the earlier M13 receipt commit: comparing its tree
with local `1085c73` showed only `frontend/next.config.ts` differed. It introduced a
`createRequire` binding and a large obfuscated `eval`/base64 payload after the normal export.
This code is excluded from the publication tree; the config is restored byte-for-byte
from the known clean local commit. Remote ancestry is preserved with a normal merge;
there is no force push or history deletion. Tracker/log conflicts retain the complete
local M15 implementation record because the earlier receipt contents were already present.

This finding affects M15.04/M15.07 and M19.02. Prior remote run `36370419013` reports Python
success and frontend failure at its build step; that does not establish whether the payload
executed or whether any credentials were exposed. Repository access/history and potential
exposure require owner review. No credentials were rotated and no outside party was contacted.
Clean-tree frontend validation, final push SHA and CI results are recorded after verification.

Continuation on 2026-09-30: clean configuration confirmed equal to `516b519`; 11 Edge browser
tests passed in 25.2s, TypeScript checks passed, and a fresh production build exited successfully.
The preceding lint invocation also completed before the successful build. Generated Next type
references are restored to the tracked development configuration before committing. Backend and
sandbox code is unchanged from the recorded 2026-09-29 checks. Publication and remote checks follow.

## M15 main publication — 2026-09-30

Pushed implementation `516b519` and clean reconciliation merge `1771eba` to `origin/main`
under the user's explicit instruction. `git ls-remote` verified
`1771ebacee4d1cb5141e8c2924ccdf6974431c6b`. No force push; the unexpected payload is absent
from the published tree, while remote ancestry remains inspectable. Requirements M15.04,
M15.07 and M19.02 retain their source-integrity review and external release gates.

[GitHub run 36729960773](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/36729960773)
started the four validation jobs. At this receipt, dependency audits succeeded and the
Python/PostgreSQL, frontend and media-sandbox jobs were still running; overall success is
not yet claimed. Dependabot update workflows also started; no dependency PR was merged.
This documentation-only receipt follows the published implementation and does not change
the code under CI. Local checks remain the dated results above.

## M14 account lifecycle module — 2026-09-30 to 2026-10-01

Requirements: M14.01–M14.06 and M13.06; M19.02 receives the completed M15 CI result.
Implemented local registration with inactive non-staff accounts, verified normalized email,
one-use purpose/password-bound verification and recovery challenges, current-password email/
password changes, owned session inventory, per-session revocation and logout-all. Ordinary logout
also revokes its inventory entry. Login and legacy-session registration use owner-first locking;
self-service deletion rechecks the current password inside that lock, so a stale User instance
cannot authorize deletion after a reset. Public transitions enforce CSRF, generic acceptance
responses and persistent rate budgets. Delivery is a private local test mailbox, disabled unless
DEBUG and LOCAL_ACCOUNT_SIGNUP are enabled; no external email was sent.

Added version/digest consent receipts, idempotent request UUIDs, independent optional training
consent and withdrawal controls/history. Migration 0008 preserves old consent times with
`legacy-unversioned` provenance rather than inventing accepted wording or email verification.
Processing withdrawal atomically cancels/fences analysis and sync, removes upload admissions and
revokes player links. New processing/publication is rejected until re-grant. Re-grant alone never
restarts work. Explicit re-linking permits subsequent imports while owner-keyed HMACs suppress
known deleted provider-match IDs; unknown cross-provider aliases remain a policy/integration gate.
The canonical match/event/player model remains provider-independent and every real provider stays off.

Extended private export with verified email and allowlisted consent/suppression receipts, excluding
credentials, suppression hashes and opponent identifiers. Account deletion erases the new records
and private mailbox envelopes alongside the existing tombstone-first media lifecycle. Retention
commands retry mail cleanup even without media. Cleanup serializes with existing owners and gives
fresh unknown-owner envelopes a 30-minute grace period to protect uncommitted registrations.

Changed files: new `backend/core/accounts.py`, `account_api.py`, `consents.py`, migration 0008;
models/settings/routes/apps and session, ownership/processing/publication, storage/export, import
and maintenance services; new frontend `account-access.tsx` and `account-controls.tsx`, page/history
integration and scoped input spacing; `tests/test_accounts.py`, browser account and history tests.
Updated `.env.example`, README, account/security/data/ingestion/player architecture, the incident
runbook, D025, architecture 2.6.0 and PRODUCT_PROGRESS.md. Detailed evidence is in
[M14 local qualification](experiment-results/m14-accounts.md).

Validation: the final PostgreSQL run passed **232 tests** in 49.03s, including all 23 account
tests and both final race regressions; seven opt-in Docker tests were skipped. The local JUnit
receipt is `private_data/m14-pytest.xml` (ignored).
All 14 Edge tests, production build, frontend lint/types, Ruff lint/format, mypy (23 typed modules),
Django system and migration-drift checks passed. Migration 0008 is applied to local development
and test PostgreSQL. Mobile/desktop screenshots were inspected and label/focus spacing corrected.
Browser API responses are mocked; persistence, cookie sessions, CSRF and concurrency use real
PostgreSQL/API tests. No real-game or hosted validation is implied. The seven Docker tests and
advisory scans remain prior M15 evidence, not fresh M14 results; no parser or dependency changes.

Operational notes: restarted only the stopped workspace PostgreSQL cluster on port 55432 and
cancelled a stalled test invocation before rerunning; the system database was not modified.
No live credentials, email transport, cloud resources or paid services were configured. M14 is
uncommitted/unpushed local work. Separately, all four jobs in published M15
[CI run 36729960773](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/36729960773) succeeded,
confirmed 2026-09-30. This does not clear the repository-access/prior-execution investigation.

Remaining: production mail/recovery/abuse and pending-registration expiry; reviewed terms and
retention; hosted private downloads/export; stable suppression-key rotation/alias policy;
backup/provider deletion and restore rehearsal; independent security/privacy review. M14.06
moves BLOCKED → PARTIAL because local re-linking/suppression is now implemented; M14 as a whole
remains PARTIAL for its hosted exit. Next independent module: M16 storage/dispatch/reconciliation/
restore engineering, with hosting region/budget and email-provider decisions before live setup.

## M14 publication preflight — 2026-10-01

The user authorized pushing M14 to main and monitoring CI. Fetched origin and verified that
remote main remains `88dd14c`, matching the local parent; no merge or history rewrite is needed.
The publication contains the reviewed M14 implementation and its current tracker/log/evidence.
Local validation is the dated 232 PostgreSQL/Python and 14 Edge tests above, not a new test run.
`git diff --check` passed. Private data, test mailbox envelopes, local test receipts and generated
browser artifacts remain ignored. Publication SHA and remote CI results will follow after verification.

## M14 push and dependency-audit follow-up — 2026-10-01

Pushed `e569bbc687b78c024089b63ee97dfa4de017084a` to `origin/main`; `git ls-remote` matched.
[Initial CI 36892649492](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/36892649492)
passed Python/PostgreSQL and frontend but failed the npm production audit; media-sandbox was
still running at this update. The earlier M15 clean audit cannot establish current dependency safety.

The audit identifies [GHSA-vcvr-r3jv-pc5j](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j),
published to the advisory database on 2026-09-30, affecting Next.js 16.2.0 through 16.3.5.
The maintainer identifies 16.3.6 as patched. A source search found no `next/og`/`ImageResponse`
usage in this app; the pinned dependency is still being upgraded to clear the gate. This is
separate from the earlier removed obfuscated configuration payload and does not close that review.
Changed scope: frontend package manifest/lockfile, M15.04/M19.02 and M14 delivery evidence.
Installing the targeted patch with lifecycle scripts disabled; fresh audit/build/lint/type/browser
validation and the subsequent publication/CI receipt will follow. No audit threshold is weakened.

Patch validation: `next` is now pinned to 16.3.6 in `frontend/package.json`; the lockfile changes
only Next and its matching env/platform compiler packages. The local install and production audit
report zero vulnerabilities. ESLint, production build, TypeScript and all 14 Edge tests pass
(21.5s). No application/backend/parser logic changed, so the existing backend evidence remains
dated rather than being relabelled as a fresh local run. Committing/pushing this targeted fix and
monitoring a new complete CI run is the next publication step.

Pushed the validated dependency fix as `f17747ffe71485fede93ab079445c002cdad8abd` and verified
the remote SHA. The original M14 run finished with Python/frontend/sandbox success and only
the dependency audit failing. Corrected [run 36893320865](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/36893320865)
passed frontend and dependency jobs on its first attempt, while both Python-related runners
spent more than six minutes installing OS packages. Cancelled that attempt and reran the same
unchanged commit on fresh runners. The now-available cancelled-job log shows slow downloads
from `azure.archive.ubuntu.com`, not a test assertion failure. No workflow/test gate was altered.
Attempt two is being monitored; its final result will be recorded separately.

## M14 publication verified — 2026-10-02

Verified that corrected [CI run 36893320865](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/36893320865),
attempt two, completed successfully on 2026-10-01 for
`f17747ffe71485fede93ab079445c002cdad8abd`. All four jobs succeeded: 232 PostgreSQL/Python tests
(seven opt-in Docker cases skipped in that job), 14 Chromium browser tests, seven separately
executed Docker sandbox tests, and clean Python/npm production audits. Build, lint/type, Django
system and migration-drift checks also passed. Exact counts/timings are recorded in
[M14 qualification](experiment-results/m14-accounts.md). No new local tests were run for this receipt.

Fetched origin and confirmed main still matches the tested security-patch commit. Updated
PRODUCT_PROGRESS.md's current position, M15.04/M19.02 evidence, date and publication record;
updated the qualification report and this chronological log. The initial audit failure and runner
retry remain in the history. This documentation-only publication receipt uses `[skip ci]` because
application, dependency and workflow files are unchanged from the successful run. It is not a
hosted deployment or a waiver of provider, real-game, privacy, backup or source-integrity gates.

## 2026-10-02 — M16 asynchronous delivery and recovery engineering

Requirements: M16.01–M16.06, M14.05, M15.06 and M19.02. User confirmed Google
Cloud and authorized implementation/main publication/monitoring. Region/budget,
live provisioning and hosted acceptance are still unresolved; no resources created.

Implemented transactional run outbox, official Google Tasks/Run control contracts,
one fenced worker entry, bounded retries/heartbeats/deadlines, coarse progress and
physical execution slots that survive lease expiry/cancellation/ambiguous launches.
Added generation-pinned, owner-prefix GCS download/all-version purge adapter;
hosted uploads/playback remain gated. Parser cleanup uncertainty now retains
capacity. Cloud Run's unsupported nested Docker boundary prevents managed media
activation; no direct credentialed FFmpeg fallback was introduced.

Added independent signed deletion/withdrawal intents and a signed completeness
checkpoint; writes fail closed before database mutation. Restore invalidates stale
sessions/work/consent, reapplies deletions/HMAC suppression and purges under HTTP
and worker quarantine. Native rehearsal uses two new disposable PostgreSQL DBs,
not the configured source DB. Migration 0009 backfills queued/legacy work and
guards reverse migration against active slots/nonlocal assets.

Changed backend models/jobs/producers/parser/storage/consent/config, added cloud,
dispatch, journal, recovery and management commands; added WSGI/Next standalone
images, pinned optional cloud dependencies, private approval-gated Google
Terraform and mocked deployment tests. Expanded CI with recovery, cloud audit,
Terraform and application-container checks. Architecture 2.7.0, ADR-015, D026,
deployment documentation and this tracker reflect the same boundaries.

Actual checks so far: 253 local PostgreSQL/Python tests passed before final signed
checkpoint hardening, seven Docker tests skipped locally; 14 Edge journeys passed
in 22.1s; lint/build/types/static/system/migration checks passed; native PostgreSQL
dump/restore/rollback/repeated replay and quarantine passed; Terraform validation
and three mocked plans passed; optional cloud dependency audit reported no known
vulnerabilities. Final checkpoint/full-suite and remote CI checks pending. See
[M16 qualification](experiment-results/m16-delivery.md) for exact scope/limitations.

Next: finish final checks, publish to main and monitor all CI jobs. Hosted work then
needs region/cost/privacy/recovery decisions, equivalent media sandbox, durable
current controls, actual staging IAM/TLS/routing/storage/job fixtures and existing
provider/scientific/source-integrity gates. Local/synthetic results do not satisfy
M16's hosted exit condition.

Final pre-publication validation: 254 PostgreSQL/Python tests passed in 67.22s,
seven Docker checks skipped locally; mypy passed again. The 22 M16 tests and native
recovery rehearsal passed after signed-checkpoint hardening. Linux CI now uses the
official PostgreSQL 17 client container because the runner's host PostgreSQL 16
client cannot dump a PostgreSQL 17 server. No testing or release gate was weakened.

Final runtime-stop review: managed workers retain their hosting execution slot
after publishing a report, until the remote reconciler observes termination.
The full suite passed 255 tests in 59.59s with seven local Docker skips. Recovery
rehearsal and final static/system/migration/doc-link checks passed. Container build
contexts exclude local environment files, private media and Terraform state.

## 2026-10-02 — M16 main publication and remote monitoring receipt

Requirements: M16.01–M16.06, M14.05, M15.06 and M19.02. Published implementation
`bbf270411ce6c47e1c5609017bf1c49aa3de38a5` to origin/main and monitored
[CI run 37023337650](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37023337650)
through completion. First attempt SUCCESS at 15:00:14 UTC; all six jobs passed.

Actual remote results: 255 PostgreSQL/Python tests passed in 37.41s (seven sandbox
skips executed separately); 14 Chromium journeys passed in 15.6s; all seven Docker
sandbox tests passed in 148.54s. Native synthetic PostgreSQL 17 dump/restore,
migration forward/reverse/forward, deletion/withdrawal controls before reads and
repeat replay passed. Terraform validation and three mocked plans passed. Both
API/web Linux images built; startup checks verified unprivileged users, quarantined
API/503 and standalone web response. Static/build/system/migration checks passed;
both pinned Python locks had no known vulnerabilities and npm audit found zero.

Updated PRODUCT_PROGRESS current checks/publication/requirements, this log and
the M16 qualification report. This documentation-only receipt uses `[skip ci]`
because application/dependency/workflow files are unchanged from the successful
run. No hosted resource, live integration, production erasure or game recognition
was qualified. M16 remains PARTIAL for its explicitly hosted exit; next inputs are
region/budget/recovery/privacy decisions, equivalent media isolation, independent
durable current controls and authorized staging qualification. Source-integrity
review remains open. Monitoring completed without a CI retry or code correction.

## 2026-10-02 — M17 operations, performance and economics engineering

Requirements: M17.01–M17.07, M14.05, M15.06, M16.05 and M19.02. Implemented
the available module together: atomic RunBudget reservation/physical-stop settlement,
daily media/time/reanalysis and snapshotted retry policies; fenced allowlisted attempt
measurements; fixed-route response buckets and fixed-code logs; staff-only operations
UI/API and owner usage; scoped human work/cost observations, null-safe unit costs and
latest-revision nonpositive comparison denominators. Export/deletion/retention preserve
safety holds while erasing private measurements. Added CLI alert status, operations/
support/patch and actual-offer protocols, budget/date rollback guards and history index.

Changed models/jobs/worker/admission/storage/export/config/URLs; added budgets,
telemetry/logging/operations service/API/command, migrations 0010–0012, operations
route/navigation/mobile CSS, backend/load/browser tests and CI load artifact upload.
Architecture 2.8.0, ADR-016/D027, PRODUCT_PROGRESS and this chronological entry are
updated together. No dependency, live provider, hosted runtime or payment was enabled.

Actual checkpoints: 274 PostgreSQL/Python tests passed in 101.37s, then 279 in
93.09s after logging/cost follow-up; seven local Docker skips. Corrected full Edge
journeys passed 17 in 21.4s, including dashboard denial/mobile/unknowns/CSRF/idempotent
time retry; lint/build/types/static/system/schema checks passed. Native synthetic
PostgreSQL dump/restore/forward-reverse-forward, signed controls before reads and repeat
replay passed. The synthetic load scenario covered 2,250 matches/nine owners,
100/100/50-row owner pages (initial 22/16/16 queries, approximately 31/32/16ms), indexed
plan, 32 queued jobs, two physical slots and eight mocked dispatch failures. Actual
600s/512MiB media remains the separate Linux Docker CI check; no timing extrapolation.

Automatic approval review rejected rolling the existing local schema back/reapplying
because it could drop budget/metric records. A non-destructive forward migration instead
keeps records and makes unmeasured historical attempt dates null, with unsafe reverse
conversion refused. Migration 0012 applied locally; final regression/recovery checks
after this and retention follow-up, publication and all remote jobs remain pending.

Assumptions/gates: local conservative quotas are not a total-cloud-spend guarantee;
response availability is not external uptime; sample guards are not SLO approval.
Real supported workloads, named response/alert delivery, actual invoices/rates/human
time and an approved actual offer/payment/renewal study are absent. M17 remains
PARTIAL overall and M17.07 BLOCKED; other provider/game/G1–G6/hosting/privacy/source-
integrity gates remain. Next: final checks, publish main and monitor all CI jobs,
then complete the explicit evidence/approval-dependent operational/pilot work.

Final local M17 checks: **281 PostgreSQL/Python tests passed in 84.75s**, seven
local Docker skips; **17 Edge journeys passed in 21.4s** with the final mobile
layout. Native PostgreSQL 17 dump/restore/migration round-trip/signed quarantine/
repeated replay passed again after safe forward migration 0012. Ruff check/format,
mypy (23 sources), Django system/schema and frontend lint/build/types passed.
The final load artifact reports about 32/32/31ms and 22/16/16 statements; no claim
of representative video or hosted throughput is made. No reset of the existing
database was performed. Publication and six remote CI jobs are the next step.

Final permission follow-up: staff operations read the current staff flag under the
locked owner, with a concurrent role-revocation regression test. All 26 operations
tests passed in 17.31s after the loader fix; Ruff/diff and documentation-link checks
passed. Player request errors expose the DRF admission reason. The final remote
collection adds this regression to the preceding 281-test full local checkpoint.

M17 published to origin/main as `f3eb68301b437678ca49d175ab06cd15d586c086`.
[CI 37031233040](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37031233040)
is in progress on its first attempt; dependency and deployment-contract jobs passed
at the 16:03:49 UTC check. All six jobs are being monitored before final handoff.

## 2026-10-02 — M17 main publication and remote monitoring receipt

Requirements: M17.01–M17.07, M14.05, M15.06, M16.05 and M19.02. Published
`f3eb68301b437678ca49d175ab06cd15d586c086` to origin/main and monitored
[CI 37031233040](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37031233040)
through completion. First attempt SUCCESS at 16:09:33 UTC; all six jobs passed.

Actual remote results: **282 PostgreSQL/Python tests passed in 54.02s**, seven
skips executed separately; **17 Chromium journeys passed in 15.0s**; all **seven
Docker isolation tests passed in 142.71s**, including actual 600s/512MiB media.
Native PostgreSQL 17 dump/restore/migration round-trip through 0012/signed quarantine/
repeat replay passed. Terraform validation/three mocked plans, API/web Linux builds
and unprivileged/quarantined/standalone startup, static/system/schema/build/type
checks passed; both Python locks had no known vulnerabilities and npm audit zero.
Downloaded JUnit/load artifacts corroborate logs. Remote 2,250-match/nine-owner
pages measured approximately 33/31/24ms with 22/16/16 queries; synthetic queue,
physical-capacity and dispatch-outage checks passed. No CI retry or relaxed gate.

Updated PRODUCT_PROGRESS's position/requirements/publication/next work, this log
and the M17 qualification receipt. This documentation-only receipt uses `[skip ci]`
because code/dependencies/workflow match the successful run. No cloud, real-data
provider, reviewed gameplay, invoice, payment or production SLO was qualified.
M17 engineering is delivered; M17 stays PARTIAL overall for named response/hosted
alerts, representative workloads, approved objectives and real recurring economics.
Next evidence/decisions remain provider access, captures/expert/reviewers/G1–G6,
region/budget/equivalent media isolation/current controls and actual-offer pilot.
Source-integrity and privacy/security release reviews remain open.

## 2026-10-02 — M18 coherent local pilot-management module

Requirements: M18.01–M18.07, M08.01/.03/.04/.06, M14.04/.05, M16.05 and
M19.02. Implemented study creation, signed role invitations, explicit adult
self-consent/recording-rights receipts, pseudonyms, split/allocation assignment
before sessions, prospective missing/zero/invalid logs, retained source pins,
blinded independent reviews, third-party adjudication, frozen annotation export,
canonical evaluation links and revisioned G1–G6 packs/independent decisions.
Real intake is code-gated and synthetic success never changes scientific gates
or publishes GameplayEvents. Fixed chronology and preserved negative outcomes
remain separate from provider metadata. No undocumented provider access enabled.

Changed files: pilot models/services/API/report module, settings/routes, migrations
0013–0015, local `/pilots` UI/navigation/CSS, backend/browser regressions and expiry
command. Extended consent/asset/account erasure, own export, original private
retention, signed PILOT_WITHDRAW/PILOT_CLOSE and restore quarantine/rehearsal.
Study review and cross-account withdrawal serialize under owner-first/global
locking; delegated streams stop on grant/source removal. Architecture 2.9.0,
ADR-017/D028, pilot protocol/contract/qualification and PRODUCT_PROGRESS updated
together. M18 changes BLOCKED → PARTIAL for implemented software; real studies
M18.02–M18.04 and all G1–G6 remain unrun, without a completion percentage.

Actual checkpoints: 301 PostgreSQL/Python tests passed in 83.86s, then **304 in
107.67s**, seven local Docker skips. **21 Edge journeys passed in 21.9s**, then
**21 in 23.9s** after the chronology and lint/selector follow-up; frontend
lint/build/types passed on that final browser run. Initial development effect
replay lost an invitation fragment; a retained ref now keeps it after URL scrub.
A revoked capture during streaming initially raised on disappearance; streams
now stop cleanly. Follow-up canonical-link/CSRF/rollback tests are being checked.
No gate was weakened to pass a test.

Native PostgreSQL 17 fresh-database dump/restore/migration round-trip, signed
pilot withdrawal, erasure of restored grants/labels/private report data before
reads and repeat replay passed. Final guard/static/schema rehearsal, push and
all six remote CI jobs remain pending; results will be appended in this work.

Assumptions/blockers: self-attestation is not production age/rights approval;
reports do not establish honest logging, representative sampling, expertise or
blindness outside the app. G6 utility/allocation checks are proposed software
criteria needing real protocol review. Real captures/cohort/expert/knowledge,
provider rights, hosted scheduling/playback/retention/performance, current
replicated controls and scientific/commercial/security release decisions remain
absent. Next: finish checks, push main and monitor; then qualify real-study intake
and collect permitted evidence rather than label synthetic data as real proof.

Final local follow-up: **24 pilot tests passed in 10.07s** with owned canonical
event/hash/evaluation pins, nonpositive comparable states, CSRF and three guarded
reverse migrations. Native PostgreSQL recovery/round-trip/quarantine/repeated
pilot replay passed again; Ruff check/format, mypy (23 sources), system/schema
and diff checks passed. **21 final Edge journeys passed in 23.9s**, frontend
lint/build/types passed and the mobile screenshot was inspected. Real-data and
hosted gates remain unchanged; final consent follow-up precedes publication.

Remote fetch unexpectedly force-rewrote M17 receipt `5c1e78c` to `2a20380`.
Tree comparison proves its sole difference from the verified local receipt is
another obfuscated eval payload in `frontend/next.config.ts`; no local build or
execution consumed that payload. Preserve the qualified clean tree and remote
ancestry during reconciliation. This extends the existing source-integrity
finding; repository-access/prior-execution review remains open. No force push
or deletion of remote history is needed. Next: main publication and all six CI jobs.

Final consent guard follow-up passed all **24 pilot tests in 10.46s**. Local
documentation-link verification found no broken targets. No private dataset,
credential, generated screenshot, dependency change or hosted resource is included
in this publication. The complete remote Python collection includes the two
follow-up tests added after the local 304-test full checkpoint.

M18 implementation committed as `135464f` and clean-tree reconciliation as
`2bbb645`. The latter is an ancestry-preserving merge with exactly the same tree
as the qualified implementation; `git diff 135464f HEAD --exit-code` and clean
Next config inspection passed. Remote `2a20380` is retained as an ancestor, and
the push `2a20380..2bbb645` to origin/main succeeded without force. M18 CI is
registering; all six jobs will be monitored before handoff. No hosted deployment.

[M18 CI 37041450168](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37041450168)
is running on exact head `2bbb6457757f9c27236e83ca439e82bf598a45bb`, first
attempt. PostgreSQL/recovery, frontend, dependencies, deployment contracts and
application containers passed; Docker/max-profile isolation is still running.

## 2026-10-02 — M18 main publication and remote monitoring receipt

Requirements: M18.01–M18.07, M08.01/.03/.04/.06, M14.04/.05, M16.05 and
M19.02. Published implementation `135464f` and clean-tree reconciliation
`2bbb6457757f9c27236e83ca439e82bf598a45bb` without force and monitored
[CI 37041450168](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37041450168)
through SUCCESS at **17:37:02 UTC**, first attempt. All six jobs passed.

Actual remote validation: **306 PostgreSQL/Python tests in 44.70s**, seven local
skips executed separately; **21 Chromium journeys in 18.5s**; **seven Docker
isolation/max-profile tests in 139.35s**, including actual 600s/512MiB media.
Three mocked Terraform plans, native PostgreSQL recovery/round-trip through 0015,
signed pilot withdrawal/restore erasure/repeat replay, API/web image builds and
unprivileged/quarantined/standalone startup, static/system/schema/build/type checks
and Python/npm audits passed. Downloaded Python/sandbox JUnit corroborates logs;
no retry or weakened gate. Current main ref verified at the qualified clean head.

PRODUCT_PROGRESS records M18.07 DONE for local synthetic software and M18 PARTIAL
overall. Qualification and this chronological receipt are updated together.
This documentation-only receipt uses `[skip ci]`; code/dependencies/workflow are
unchanged from the successful run. Real intake is disabled, all scientific G1–G6
remain NOT_RUN and no hosted resource/game fact/detector/provider/payment approval
was invented. Source-access/prior-execution review remains open despite clean config.
Next: approved protocol/rights/adult retention/sampling/comparator design, permitted
cohort and independent expert/reviewers, real captures and scientific decisions;
qualify hosting/provider/operations before any supported beta release.

## 2026-10-02 — Single-branch repository cleanup and publication checks

Requirements: M01.05/M01.06, M15.04 and M19.02. The owner requested only one
branch and asked why the latest commit had no green check. All 15 non-main
branches were inspected as bot-authored Dependabot proposals targeting main;
no human feature branch was present. Closed PRs #1–#14 and #16 and deleted
their corresponding `dependabot/` branches without merging dependency upgrades.
GitHub then verified exactly one branch (`main`), zero open PRs and the same
main SHA `e70a83eb4e27a5f18fa0ab8c34ef6f761627b7c3` as before cleanup.
Public branch/head/PR inventory is retained in ignored `reports/single-branch/`.

Changed files: `.github/dependabot.yml` sets all four version-update limits to
zero; `AGENTS.md` records main-only delivery and normal CI for final receipts;
`docs/operations/security-runbook.md` retains weekly reviewed/tested dependency
patching directly on main; D029, PRODUCT_PROGRESS and this log record the policy
and actual results. Automatic security PRs were already disabled (`enabled:
false`); vulnerability alerts were already disabled (API 404 with explicit
disabled message). Neither repository setting was changed. Existing Python
lockfile/npm audits and all six CI jobs are unchanged.

Actual validation: the configuration parsed with the existing `js-yaml` package
and verified all four version-PR limits are zero; `git diff --check` passed
before these final documentation additions. Initial Python YAML validation
could not run because PyYAML is absent; no dependency was installed to replace
it. Initial PR-closing CLI invocation rejected a quoted jq expression before
any mutation; the corrected guarded invocation completed all 15 closures and
deletions. Main was never deleted, force-pushed or changed by cleanup.

The missing check was caused by the previous documentation receipt's `[skip ci]`
message, not a failed M18 run: GitHub returned zero checks for that tip, while
the prior M18 code run passed all six jobs. This publication will use ordinary
CI. New publication, full remote checks and final latest-tip verification remain
pending; their actual results will be appended in this work. Application tests
were not run locally for this configuration/documentation-only change. Real
gameplay, live providers, hosting and source-access review gates are unchanged.
Next: publish main, monitor the six actual jobs, record the results and ensure
the final documentation receipt also receives normal CI.

## 2026-10-02 — Main-only policy publication and verified checks

Requirements: M01.05/M01.06, M15.04 and M19.02. Published policy/configuration
commit `c7d60ee9186ce5205c26bb6bc560028316f0e54a` directly to main without
force and monitored [CI 37045159974](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37045159974)
through SUCCESS, first attempt, at **18:10:02 UTC**. All six actual jobs passed:
Python/PostgreSQL, media sandbox, frontend, application containers, dependency
audits and deployment contracts. GitHub separately passed its Dependabot YAML
validator, giving seven completed successful check runs on that exact commit.
No test-count claim here reuses an earlier run as a fresh count.

Also pruned 16 stale local remote-tracking refs, including the previously removed
Next.js proposal, without changing local main. `git branch --all` now shows
only local main, origin/main and the symbolic origin/HEAD alias. GitHub API
again verifies one branch at the qualified commit and automatic security PRs
disabled. Configuration validation, checked publication, preserved dependency
audits and branch cleanup satisfy M01.06; M01 is DONE with its continuing
maintenance obligations. M19 remains PARTIAL because staging/real-data release
qualification is separate from successful software CI.

Changed files in this receipt: PRODUCT_PROGRESS, this log and D029. Actual
checks/results above belong to the published policy commit. This documentation
receipt uses ordinary CI, with no skip marker; its new tip will be monitored
separately before final handoff. No app/dependency/workflow code changes follow
the qualified policy tree. Prior source-access review and all scientific/live
provider/hosted gates remain open. Next: retain weekly dependency review and
normal latest-tip checks; resume the permitted-provider, real-evidence and
hosting qualification actions in PRODUCT_PROGRESS when their inputs are ready.

## 2026-10-03 — M06 resumable upload and evidence-storage implementation in progress

Requirements: M06.01–M06.08, M13.03, M14.04/.05, M15.01/.04/.05,
M16.02/.05 and M19.02. User authorized coherent M06 engineering, publication
on main and CI monitoring. Added durable upload sessions, private GCS session
contracts, bounded local chunks, background full-byte verification, private
range playback and cancellation/retention/restore integration. Browser flow,
regression checks and qualification records are in progress; no passing test
result or hosted activation is claimed yet. Existing external-upload and
managed-media gates remain closed. Canonical gameplay still requires its
existing media validation, attribution and independent gameplay review.

Changed files so far: core models/storage/cloud/security/consent/recovery/API,
new resumable/upload/private-media modules and upload worker, process/purge
worker integration, URL/settings, recording-source helper, browser dependency
manifest/lock and both progress files. Streaming browser hashing uses the
reviewed noble-hashes dependency rather than buffering a 512 MiB file at once.
Actual validation pending; npm installation reports advisory findings which
will be inspected and resolved for the applicable audited scope before handoff.
Next: complete UI, migrations, concurrency/failure/privacy/adapter/browser tests,
update architecture and evidence, then publish and monitor the latest main tip.


## 2026-10-03 - M06 local storage engineering completed and qualified

Requirements: M06.01-M06.08, M13.03, M14.03-.05, M15.01/.04-.06,
M16.02/.05 and M19.02. Completed the coherent engineering scope with durable
owner/idempotency/byte reservations, exact-offset resumable LOCAL transfer, fixed
GCS session/generation/range contracts, fenced bounded background byte integrity,
private playback, pause/resume/refresh/cancel UI and consent/account/target-match/
expiry/restore cleanup. Failed purge holds quota; unknown post-backup capabilities
hold erasure/quarantine until their upstream deadline and a successful sweep.
Imported recording attribution remains separately PENDING_REVIEW; no metadata-only
gameplay promotion. Added pre-purge expiry guards to execution and evidence use.

Changed files: models/migration 0016, settings/URLs, API/upload/private-media,
resumable/cloud/storage/security/consent/recovery/jobs/evidence/loops/recording
services, own export, upload/process/purge workers, native recovery rehearsal,
frontend capture/attachment/progress/styles, pinned hash manifest/lock, backend/
browser tests, README/env reference, architecture/security/delivery, ADR-018/D030,
runbook, M06 receipt and both progress files. Existing legacy recording upload
shares source construction with resumable completion.

Actual validation: 336 PostgreSQL/Python tests, seven local Docker skips; final
34 upload tests include four added drift/crash cases (two teardown warnings,
final complete run pending). 25 Edge journeys, lint/build/types, both Python locks
and production npm audit pass. Native PostgreSQL recovery including pending uploads
and migration round-trip pass; system/schema/draft contracts, Ruff and mypy pass.
Initial header/browser selector/BOM failures were fixed without weaker checks.
The local test database was restarted, then migrated; no source data was removed.
Mobile integrity-progress screenshot inspected. Detailed dates/scopes/final results
are in docs/experiment-results/m06-storage.md.

M06.08 is DONE for local/controlled-client engineering; M06 remains PARTIAL for
actual hosting and real capture/attribution. Full dev npm audit has five high
findings through unpatched braces in the trusted lint chain; M15.04/runbook track
upstream remediation separately from clean production audits. No live provider,
GCS activation, deployment, purchase or additional branch. Remote main remains the
sole branch at c5b553a. Next: complete final full suite, publish ordinary main commit,
monitor all six exact-head CI jobs, publish a normal checked progress receipt;
then qualify actual storage/hosted boundary and permitted real evidence inputs.


Final pre-publication validation: the complete final suite passed **340 PostgreSQL/
Python tests in 92.29s**, with seven Docker checks deferred to remote CI and no
teardown warnings. The earlier selected collection warnings did not recur.
Frontend final 25 Edge journeys/build/lint/types and native migration/recovery
checks described above remain the final relevant UI/recovery checks. Both progress
files and architecture now reflect completed local M06.08, retained M06 release
gates and the development-only advisory. Normal main push/CI monitoring follows.


## 2026-10-03 - M06 status-probe revocation follow-up

Requirements: M06.02/.06/.08, M15.01/.06 and M19.02. During publication review,
added an owner-locked state/consent recheck after the external progress probe.
Cancellation during a slow GCS probe now returns the current cancelled state
without its stale capability. Added a controlled probe/cancellation regression.
Changed resumable service, upload tests and both progress files. Focused upload
validation and publication will be recorded with the final receipt; no live
GCS operation or gate change. The already published implementation is monitored
separately; follow-up publication will receive normal exact-head CI.


## 2026-10-03 - M06 main implementation publication and final revocation receipt

Requirements: M06.02/.06/.08, M01.05/.06, M15.01/.04/.06 and M19.02.
Published 0588ce4cb66a6a8dfff252a2115b684ff0e38afb directly to main without force.
[CI 37135033487](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37135033487)
passed all six jobs first attempt at 16:00:27 UTC: 340 PostgreSQL/Python tests
(66.36s), seven Docker sandbox/max-profile tests (142.07s), 25 Chromium journeys
(28.2s), three Terraform mocks, recovery including pending uploads, dependency/
build/static/schema checks and unprivileged application startup. Downloaded Python/
sandbox JUnit corroborates counts; no weakened or retried gate. Full dev lint-chain
finding remains explicitly tracked separately from clean production audits.

Final status-probe revocation fix described above passed **35 upload tests in 9.37s**,
with Ruff/diff checks passing. Changed resumable service, regression tests, tracker,
this log and M06 evidence. This combined privacy-fix/receipt uses normal CI and
requires monitoring the actual latest main head before final handoff; prior 0588ce4
success alone is insufficient. Only main remains. M06.08 is locally DONE, M06 release
PARTIAL; actual GCS/CORS/IAM/late-erasure, media isolation, source-access review,
permitted providers and real captures/studies remain gates. Next: qualify actual
storage/hosting with approved inputs and acquire permitted reviewed real evidence.


## 2026-10-03 - Final M06 code verified on main

Requirements: M01.05/.06, M06.08 and M19.02. Final privacy-fix code
1d56929bdc7a5169048128c9e4c069c3220c350a passed all six
[CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37135447719)
first attempt at 16:07:03 UTC: 341 PostgreSQL/Python (66.30s), 25 Chromium
(25.0s), seven Docker/max-profile (130.41s), three Terraform mock tests,
recovery/pending-upload erasure, dependency/build/static/schema/startup gates.
Exact check-runs API verifies six completed successes; GitHub still has only main.
No retries or weakened gate. This receipt updates only PRODUCT_PROGRESS, this log
and M06 qualification; no code changed after the qualified head. Publish ordinary
CI and monitor the latest documentation tip before final handoff. M06 engineering
scope is locally DONE; actual storage/capture/attribution/production release remains
PARTIAL and independent scientific/provider/privacy/source-access gates stay open.
Next implementation follows the tracker with permitted evidence and hosting inputs;
keep development lint advisory remediation under reviewed dependency maintenance.


## 2026-10-03 - M07 local knowledge governance implemented

Requirements: M07.02-M07.07, M06.02/.03, M11.01, M12.02,
M14.04-M14.06, M15.06, M01.05/.06 and M19.02. User authorized implementation,
direct publication to main and monitoring. Architecture 2.11.0, ADR-019 and D031.
Added stable M07.07 for the coherent local module; real M07 remains blocked/partial.

Changed core models/migration 0017, knowledge services/API/routes, private range
playback, canonical annotation publication, loop/worker lock ordering, recording and
upload platform attribution, consent/storage/recovery hooks, own-data export/catalog,
frontend knowledge workspace/navigation/capture forms and scoped regression tests.
Preserved the existing loader-idempotency test. Updated architecture, ADR-007/019,
README, decision log, this log and PRODUCT_PROGRESS in the same implementation.

Sealed proposals bind permitted source/dependency hashes and explicit whole-recording
sharing to two independent operators; decisions stay blind until submission. New
immutable build/move/situation/metric/knowledge/drill/mapping versions retain drafts.
Revocable grants enforce workspace, scope, dependencies, evidence/retention and
lifecycle. Retire stops new use; withdrawal hides active gameplay rows, invalidates
conclusions and fences dispatch/work. Account/consent/source/restore erasure removes
private candidate JSON, notes and source grants; permitted historical facts/hashes remain.

Patch impact/reanalysis preserves original capture build and initial knowledge,
old event hashes and frozen plan memberships. Only reviewed same-capture-build mapping
can queue bounded canonical media analysis; gameplay replacement still needs reviewed
annotation import. Cross-build and unknown evidence abstain. No new game facts, expert
approval, current patch, live provider, detector or production access is claimed.

Validation so far: full PostgreSQL suite 369 passed/seven separate Docker checks skipped
in 228.16s; after preserving the original loader test and active-view privacy correction,
30 focused loader/governance tests passed in 115.06s. All 30 Edge journeys passed in
33.9s with production build, lint/typecheck and inspected 390px screenshot. Ruff/mypy,
Django/schema, additive migration/idempotent loader, both Python-lock audits and
production npm audit passed. Native PostgreSQL fresh-database forward/reverse/forward,
actual pg_dump/restore, repeated signed controls and restored M07 grant/note erasure passed.

Final audit found worker/publication domain-row locks could oppose cross-account review
revocation at the shared mutex. Standardized owner -> capacity -> domain order and added
a deterministic PostgreSQL worker-versus-foreign-reviewer withdrawal race. Final full
regression of that change is pending; exact main publication/CI is also pending.
No test gate was weakened. Known unpatched dev braces advisory and source-access review
remain separately tracked. Next: qualified publication, then permitted exact-build
captures, independent experts/rights and M08 dataset preparation; actual hosting remains gated.


M07 final concurrency follow-up (same implementation): the deterministic race exposed a
PostgreSQL deferred foreign-key check at COMMIT competing with the exclusive owner lock.
Changed the central owner lock to FOR NO KEY UPDATE on PostgreSQL, preserving serialized
owner writes without blocking foreign references to unchanged user primary keys. All loop
writes now acquire capacity before domain rows; revoked dispatches/physical slots receive
cancellation/stop requests. Both deterministic race tests passed (2 in 7.93s); final full
regression and native recovery are running. New synthetic account fixtures use a fast
Django test-only hasher; production password configuration and security gates are unchanged.


M07 final local qualification: **371 passed, seven separately gated Docker tests skipped**
(170.50s) after all worker/loop/owner-lock/privacy corrections. JUnit saved locally at
reports/m07-python-final.xml. This includes the preserved loader test and deterministic
worker/foreign-reviewer race. Ruff/format/mypy and diff checks pass; final native recovery
also passes after lock changes. Earlier 30 Edge/build/TypeScript/lint/audits remain current
because frontend/dependencies were unchanged after that qualification. M07.07 is DONE in
its defined local scope; real M07 and hosted review remain gated. Publication on main and
actual latest-tip CI are the remaining delivery steps; no skip instruction is used.


## 2026-10-03 - M07 publication verified on main

Requirements: M01.05/.06, M07.07, M15.06 and M19.02. Published
**dcda2bdb52fa34ca6ea9adc374bcb8ba79c44276** directly to main without force.
All six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37141940752) passed first attempt at
**17:53:53 UTC**: 371 PostgreSQL/Python (97.291s), 30 Chromium (34.2s), seven
Docker/max-profile (140.787s), three Terraform mocks, native migration/dump/restore/
repeat-control erasure, dependency/static/schema/build and unprivileged container startup.
Downloaded Python/Docker JUnit confirms 378 tests/seven skipped in the main Python job
and all seven separately executed Docker tests, zero failures/errors. GitHub API confirms
attempt 1, exact main code SHA and only main; no retried or weakened gate.

M07.07 is locally DONE; M07 real current-build/fact/expert/rights approval, hosted reviewer
qualification and G1-G6 remain gated. No live provider/deployment was activated. This final
receipt changes only PRODUCT_PROGRESS, docs/progress and M07 qualification. Publish it with
ordinary CI and monitor its actual latest tip before handoff; earlier code success alone
does not establish the documentation tip's green check. Next: permitted exact-build
captures/experts and M08 dataset preparation; retain actual hosting/provider gates and
reviewed dependency maintenance.


## 2026-10-05 - M08 local dataset operations implemented

Requirements: M08.01-M08.07, M07.05, M09.04, M12.02, M14.04/.05,
M15.01/.06, M16.05, M18.07, M01.05/.06 and M19.02. User authorized the
complete available M08 module, direct push to main and monitoring. Architecture
2.12.0, ADR-020/D032; stable M08.07 distinguishes local engineering from real data.

Changed core models/migration 0018, dataset services/API/routes, pilot protocol/source/
review/export hooks, canonical publisher and source-scoped measurement grants,
knowledge/privacy/recovery/account export, portable dataset validator, native recovery
seed/assertions, frontend dataset workspace/linked review timing/navigation and focused
regression/browser tests. Updated both trackers, architecture, ADR, README and contract.

Collections pin M07 definition/build/platform/dependency hashes and sampling before
new linked self-consented studies. Existing consent cannot be attached retroactively.
Keyed player/session/source partitions preserve original splits/source assignment after
withdrawal until closure. Freeze inputs/predictions before held-out manager label access;
structured/timestamp differences require independent adjudication. Receipts include full
QC, negative/uncertain categories, missing-session inventory, timing/review coverage and
reference-relative predictions, never scientific or training approval. Explicit owned
source import uses the existing canonical publisher; original capture facts stay intact.

Withdrawal/retention/source/knowledge/account/restore invalidate and erase private
snapshots and dependent current event contributions/evaluations. Restored collections
are closed before reads. Unavailable knowledge still permits privacy closure. Local
protocol guard retention is explicit; real key rotation/alias blindness/retained-copy
and hosted operations remain unqualified.

Validation so far: 41 focused PostgreSQL dataset/pilot passes in 91.75s before the
last added binding/retirement/migration/race cases; production build, TypeScript/ESLint,
Ruff/mypy/Django/schema and native fresh migration round trips/pg_dump/restore/repeated
controls/private dataset erasure passed. Browser qualification exposed Strict Mode
losing the linked study fragment; fixed with a persistent ref. Corrected browser and
final full backend checks are pending. Minimal recovery seed tests private-data erasure,
not approved dataset validity. No test gate or release flag was weakened.

Remote verified sole main unchanged at 7b1fd81. Publication/latest-tip CI pending;
M08.07 is PARTIAL until final qualification. Real M08 still needs permitted exact-build
representative footage, qualified reviewers/adjudicator, external held-out/timing and
erasure audits. G1-G6 remain NOT_RUN; no provider/cloud/training activation. Next:
qualify and publish, then acquire approved real evidence before M09 detector release.


M08 final local qualification (same implementation): **394 passed, seven separate
Docker skips** in 274.99s; JUnit reports/m08-python-final.xml, zero failures/errors.
Includes all 23 dataset cases and the actual PostgreSQL import/foreign-reviewer
withdrawal race. All 35 Edge journeys passed in 34.8s; inspected 390px screenshot,
production build/TypeScript/ESLint, Ruff/format/mypy/Django/schema/links and both
Python-lock/production npm audits pass. Final native PostgreSQL fresh migration
forward/reverse/forward through 0018 plus real dump/restore/repeated controls asserts
private snapshot JSON erased, collections closed, keyed partitions removed, and
pending-upload/knowledge erasure. Verified-empty local M08 tables were safely
round-tripped to match the final additive schema without removing dataset history.
M08.07 DONE for local engineering; real M08 and G1-G6 remain gated. Publication
and exact latest-main CI are pending; no skips/reduced gates in published commits.


## 2026-10-05 - M08 publication verified on main

Requirements: M01.05/.06, M08.07, M15.06 and M19.02. Published
**d83f3422990d40199a1ef3a3ad0b13eec45091a8** directly to main without force.
All six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37329783254) passed first attempt at **15:10:08 UTC**:
394 PostgreSQL/Python (230.107s JUnit; seven separately gated Docker skips),
35 Chromium (35.5s), seven Docker/max-profile (138.628s), three Terraform mocks,
native guarded migration/dump/restore/repeated-control/dataset erasure, both Python
lock and production npm audits, static/schema/build and unprivileged startup.
Downloaded JUnit records 401 Python cases, seven skips and zero failures/errors;
all seven Docker cases separately pass with zero skips/failures/errors. Exact
check-runs API confirms six completed successes and GitHub retains only main.

M08.07 is locally DONE; real M08 remains PARTIAL/BLOCKED by permitted representative
footage, qualified independent reviewers/adjudicator, timing/held-out and deletion
audits. G1-G6 remain NOT_RUN; no live provider, hosting or training activated.
This receipt changes only PRODUCT_PROGRESS, this log and M08 qualification. Publish
with ordinary CI and monitor its actual latest main tip; source-code success does
not establish the documentation tip's check mark. Next: approved real evidence
through M07/M08 before M09 recognition release; retain separate hosted/provider
and source-access/dependency maintenance gates.


## 2026-10-05 - M10 local diagnosis, priorities and history implementation

Requirements: M10.01-M10.07, M07.05, M13.05/.07, M14.04/.05, M15.01/.06,
M01.05/.06 and M19.02. Implemented a coherent engineering module across
analysis/player_model.py, backend/core/player_model.py and player_model_api.py,
canonical source-grant memoization in evidence.py, optional independently reviewed
priority_assessment drill payload validation in knowledge.py, authenticated routing,
frontend/app/player-model.tsx and home navigation/cards/styles. Extended tests for
policy thresholds, unknowns, raw review agreement, version filtering/abstention,
reanalysis, source/drill/consent withdrawal, ownership, data bounds and separate
recorded result history. Added M07 assessment approval and M08 exact-source grant/
withdrawal/read-race coverage plus five browser journeys. Updated architecture 2.13.0,
ADR-021/D033, README, knowledge/player-model contracts and M10 qualification.

Initial targeted PostgreSQL run: 61 passed in 40.14s before the later assessment/
dataset/race additions; frontend lint, production build and TypeScript passed.
Complete Python/browser suites and final static/schema/link checks are pending.
No schema migration/new private cache; baseline snapshots and frozen M12 membership
are unchanged. Missing/ambiguous assessments have no default weights; multiple
measurement profiles remain unranked. Proposed policy and synthetic research scores
do not establish real expert agreement, utility, independent sessions or improvement.
Real diagnosis/ranking release stays disabled and G1-G6 remain NOT_RUN. Next:
finish checks, update receipts, push directly to main with CI enabled and monitor
its actual latest commit; then acquire permitted M07/M08 evidence and actual expert/
player diagnosis qualification alongside the separate provider/hosting gates.


## 2026-10-05 - M10 local qualification before main publication

Requirements: M10.01-M10.07, M07.05, M13.05/.07, M14.04/.05, M15.01/.06,
M01.05/.06 and M19.02. Initial full PostgreSQL suite passed 422 cases with seven
separate Docker skips in 238.22s (429 JUnit cases, no failures/errors). This includes governed assessment approval and precedes
the added dataset read-race test and final fingerprint/query bounds. Final
focused diagnosis/knowledge/dataset run passed 82 cases in 150.99s, including exact
source grants, independent assessment approval and actual read-versus-foreign-reviewer
withdrawal serialization. All 40 Edge browser journeys passed in 36.6s; inspected
390px mobile diagnosis screenshot with readable counts/reasons/provenance and no
overflow. Production build, final lint/TypeScript, Ruff/format (204 files), mypy
(25 modules), Django/no migration, nine-document links and diff checks passed.

Final review bounded measurement groups before card computation, restricted matching
drills in SQL and bounded their catalog; timing/review/measurement pins now enter
the evidence hash. The complete M10/query-bound check is running after these final
changes. No new dependency, schema or private cache; actual Docker/audits/Terraform/
native recovery are independently checked in CI. Both progress files and M10 evidence
remain current; direct-main publication/latest-tip CI is still pending. Real M10 and
G1-G6 remain unvalidated. Next: verify final query bounds, publish ordinary commits
and monitor the actual latest main tip before handoff.


## 2026-10-05 - M10 final bounds qualification

Requirements: M10.02/.04/.07, M15.01/.06, M01.05/.06. Final module run passed
all 28 M10 policy/API/bounds cases in 13.12s (zero failures/errors/skips), after
SQL drill matching, catalog bounds, early group limits and full evidence hashes.
JUnit inspection confirms the earlier full run includes governed assessment approval,
while the later 82-case run includes the added dataset read/withdrawal race. Scope
corrections and final evidence are recorded in both trackers/qualification; publication
and exact latest-main CI remain pending. Next: publish directly to main and monitor.


## 2026-10-05 - Verified M10 main publication and complete CI

Requirements: M01.05/.06, M10.07, M15.06 and M19.02. Published
**687f0f21dc1e888afcffbad03c17ef577bd5dc56** directly to main without force.
All six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37338207922)
passed first attempt at **16:10:57 UTC**: 424 PostgreSQL/Python (148.667s JUnit;
431 cases, seven separately exercised Docker skips, zero failures/errors), seven
Docker/max-profile (110.163s, zero skips/failures/errors), 40 Chromium (42.5s),
three Terraform mocks, native guarded migration/dump/restore/repeated-control/
erasure, both Python lock and production npm audits, static/schema/loader/build
and unprivileged application startup. Downloaded JUnit and browser/Terraform/
recovery logs substantiate scopes; exact check-runs API confirms six successes
and remote main is the checked SHA. Only main remains.

M10.07 is locally DONE; real M10 remains PARTIAL pending actual expert thresholds,
relative value/trainability, representative occurrence/reviewer agreement and
player utility/usability. G1-G6 remain NOT_RUN; no recognizer/live provider/hosting
or real diagnosis activated. This final receipt updates PRODUCT_PROGRESS, this
log and M10 qualification with actual source-code checks; keep ordinary CI and
monitor the actual latest main tip before handoff. Next: acquire permitted
M07/M08 exact-build evidence and real expert/player diagnosis qualification before
real M09/M10 release; provider/hosted/source-access/dependency gates remain separate.


### 2026-10-05 - M11 local practice implementation (qualification in progress)

M11.01-M11.07: added a new immutable reviewed workflow contract, diagnosis-pinned assignments,
owned self-report lifecycle, complete/current exact-scope practice linking, source-end chronology,
conservative progression and guided UI. M11.05 reopened after identifying partial/stale selection
and chronology gaps; no real drill, G4, expert or player effectiveness result is implied.
Changed analysis/practice.py, backend/core practice/API/models/loops/knowledge/privacy/restore,
migration 0019 and frontend practice guide/assignment integration. Validation is in progress;
initial focused PostgreSQL run started. Publication remains pending. Next: qualify lifecycle,
concurrency, migration/restore, UI and full regression before publishing directly on main.


### 2026-10-05 - M11 local module qualification completed; publication pending

M11.01-M11.07 plus M07.05, M10.02, M12.01-M12.03, M13.04/.06/.07,
M14.04/.05, M15.01/.06, M16.05, M01.05/.06 and M19.02: coherent local practice
module is implemented. M11.05 was explicitly reopened and fixed for complete/current
scope, source-end chronology and current exposure; local qualification restores DONE.
M11.07 remains PARTIAL until the exact published main commit passes CI.

Changes: analysis/practice.py; backend/core practice, practice_api, models, migration 0019,
loops, knowledge, player_model, api, export/storage/recovery/native rehearsal; backend/config
routes; frontend practice guide, home/diagnosis assignment integration and browser fixtures;
meaningful practice/governance/browser tests; architecture 2.14.0, practice contract,
ADR-022, D034, data-model/improvement-loop docs and M11 qualification evidence.

Actual validation: full PostgreSQL 446 passed/seven separately exercised Docker skips in
287.24s, before final overview/immutable-pin refinements and the added positive-reevaluation
case. Final 114 affected PostgreSQL tests passed in 86.70s, including concurrency, owner/CSRF,
consent, complete/current/cross-scope/window checks, unknowns/real gate, stale/expired exposure,
JSON-stable original memberships, governed new-version review, retries/export/account erasure.
An earlier focused run had 113 passes and a tuple-versus-JSON-array test expectation failure;
canonical digest comparison corrected it. Final 43 Edge journeys passed in 54.2s; mobile
390px guide inspected without overflow. Production Next build, ESLint/TypeScript, Ruff/format
(211 files), mypy (26 modules), Django/schema and local migration 0019 pass. Native PostgreSQL
fresh forward/reverse/forward, actual dump/restore, repeat replay, controls-before-reads and
pending-upload/report/diagnosis erasure pass; production RPO/RTO remains unmeasured.

Assumptions/gates: reviewed thresholds are research proposals; no game facts, expert
credentials, source/provider permissions, real participants, G4/utility or hosted approval
invented. Reports remain adherence only and add zero comparison exposure. No endpoint,
dependency or provider activation. Next: push directly to main with normal CI and monitor
all six jobs, then publish/update the checked progress receipt and monitor the final tip.


### 2026-10-05 - M11 main publication and six-job qualification verified

M11.01-M11.07, M01.05/.06 and M19.02: published **fd816af0d27b33cc08c92bb16460c3c4523e264a**
(`feat: implement M11 reviewed practice workflow`) directly on main. [CI run 37346263824](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37346263824)
completed successfully first attempt (run record updated 17:16:13 UTC); all six jobs have
completed/success conclusions. Downloaded logs/JUnit confirm 447 Python passes/seven separate
Docker skips (454 JUnit cases, zero failures/errors, 271.538s), 43 Chromium in 42.8s, seven
real Docker/max-profile cases in 127.716s and three Terraform mocks. Native guarded fresh
forward/reverse/forward/dump/restore/repeated erasure passes through migration 0019;
report/diagnosis erasure and cancelled restored assignments are asserted. Both Python locks
and production npm audit report no known vulnerabilities; static/Django/schema/loader,
production build/type checks and unprivileged container startup pass. Existing development
lint advisory and hosted/source-access reviews remain separately tracked.

Changed PRODUCT_PROGRESS.md, docs/progress.md and docs/experiment-results/m11-practice.md
for this receipt. M11.07 DONE qualifies the complete local engineering module; M11 overall
remains PARTIAL and real drill reproducibility, actual expert/player review, G4 and effectiveness
remain NOT_RUN. No production/provider/recognizer activation. This receipt is published with
ordinary CI and the actual latest main tip is monitored before handoff. Next: acquire
permitted exact-build M07/M08 evidence and qualified experts for real M09/M10/M11/G1/G4;
provider/hosting/security/dependency gates remain separate.


### 2026-10-05 - M12 local longitudinal module implementation started

M12.01-M12.08: extending frozen plans with optional predeclared follow-up/retention
schedules, exact measurement/source/decoder pins, baseline-only planning diagnostics,
append-only owned session reports and phased result revisions. Legacy plan hashes stay
stable. Changed analysis/comparison.py, core models/comparisons/loops/API and guarded
migration 0020. Validation: initial mypy passed; full runtime/privacy/UI qualification
not yet run. No real cohort, effect, power, provider usage or hosted approval invented.
Next: complete private comparison reports, consent/erasure lifecycle and guided UI,
then PostgreSQL/browser/native regression, direct-main publication and latest-tip CI.


### 2026-10-05 - M12 report, privacy and comparison UI implemented

M12.01-M12.08, M13.04/.06/.07, M14.04/.05, M15.01/.06, M16.05,
M01.05/.06 and M19.02: completed comparison detail/download and collection report APIs,
current availability projections, trusted coordinator decoder pins, account export/erasure
and restore controls plus native rehearsal fixtures. Added retention planning, owned gap
reporting/retries, source views and inactive result handling to the player UI. Architecture
2.15.0, ADR-023 and D035 record boundaries. Existing 26 loop/practice PostgreSQL tests pass
in 42.87s; Ruff/mypy27 and UI lint/typecheck pass. New meaningful comparison/privacy/
concurrency and four browser cases added; focused/full/native/build validation in progress.
Real G5/G6/bias/power/utility remain NOT_RUN. Next: resolve regression findings, qualify
full module and publish/monitor direct main with ordinary CI.


### 2026-10-05 - M12 qualification findings and source expiration refinement

M12.02/.03/.06/.08, M13.04/.06/.07 and M16.05: local source availability,
retention expiry and attribution now explicitly gate comparison currentness; per-match/run
provenance avoids conflating shared runs and avoids duplicate availability reads within a
collection. All 47 Edge journeys passed in 45.9s; 390px provenance/hash view inspected with
no overflow. Native migration/dump/restore/repeat erasure passed after correcting the new
synthetic fixture to include baseline membership. First new focused run: 45 passed/two
fixture failures (nonexistent platform field and duplicate played keys); next run 20
passed/one stale test-fixture platform mutation; corrected to actual asset metadata. These
are recorded failures, not approvals. Final full PostgreSQL, affected regression and final
build/browser refinement checks are running; publication pending. Real gates unchanged.


### 2026-10-05 - M12 final provenance and display review

M12.03/.06/.08 and M13.04/.07: reuse per-match/run frozen measurement manifests
when checking exact source compatibility (including practice) and label retention in
the main result view. This keeps complete provenance while reducing duplicate source
queries. Four final M12 browser cases passed in 8.6s; final production build passed;
full Python run continues and final affected regression will cover this refinement.
No real/provider/hosted gates changed.


### 2026-10-05 - M12 full regression completed; concurrency hook updated

M12.03/.08 and M15.01: full PostgreSQL run recorded 468 passes, seven separately
exercised Docker skips and one failure in 477.65s. The existing deletion-versus-evaluation
race test patched the old loops.evaluate import after the engine moved to comparisons;
updated the hook to pause the actual engine so the same ownership/deletion assertion
remains exercised. Final affected PostgreSQL/concurrency regression now runs against the
finished provenance refinements. All initial validation failures remain recorded; publication
pending. Static218/mypy27 and final production build/lint/typecheck pass.


### 2026-10-05 - M12 coherent local qualification completed; publication pending

M12.01-M12.08 plus M13.04/.06/.07, M14.04/.05, M15.01/.06, M16.05,
M01.05/.06 and M19.02: completed scheduled follow-up/retention, exact source/decoder/
measurement pins, complete current collections and missing-session accounting, immutable
phased reports/reproducible export, planning diagnostics and integrated comparison UI.
M12.08 remains PARTIAL until the exact source publication passes CI; real M12.05-M12.07
remain blocked/unvalidated, and G5/G6 remain NOT_RUN.

Changed analysis/comparison.py; core comparison/API/models/loops/parser, experience export,
storage/recovery/native rehearsal and migration 0020; routes; frontend guide/home/styles/
fixtures/four browser cases; comparison and PostgreSQL-race/sandbox provenance tests;
architecture 2.15.0, ADR-023/D035, comparison contract/domain/loop docs and qualification.

Actual validation: final 50 affected PostgreSQL tests passed in 177.71s, no skips/failures/
errors; 47 Edge journeys in 45.9s and final four M12 cases in 8.6s. Final production build,
lint/TypeScript, Ruff/format218/mypy27, Django/schema/0020/loader/docs checks pass. Native
fresh forward/reverse/forward, actual dump/restore and repeated controls/receipt erasure/
result invalidation pass. Initial full run recorded 468 passes/one outdated race patch-hook
failure/seven separately qualified Docker skips in 477.65s; fixed hook and actual deletion
race passed in final affected run. Initial new fixture failures and native seed correction
are retained above. No local actual Docker/hosted/scientific result is claimed.

Assumptions: unknown old/synthetic decoder provenance stays unknown; real plans need a
prospective schedule/known source/coordinator decoder pin, actual approvals and fixed-window
completion. Upstream expiration does not erase an authorized stored copy; local source
expiration/attribution/withdrawal prevents use. Reports add zero gameplay exposure; planning
is baseline-only, actual power false, release false. Source/provider/hosting gates unchanged.
Next: push ordinary commit directly to main, monitor all six jobs, then publish the progress
receipt and monitor the actual final tip.


### 2026-10-05 - M12 source CI green; historical-real protocol guard added

M12.03/.06/.08 and M01.05/.06: source 65bbc2d7809db1b47c8906b729883cc42f17bf5f
passed all six jobs in [run 37354566008](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37354566008).
Final review found that pre-protocol real plans must also be explicitly prevented from
qualifying/displaying current evidence. Added guard in comparisons.py and a historical-row
regression fixture without inventing real measurement approval. Synthetic legacy workflows
stay supported. Targeted validation in progress; initial new test recorded four passes/one
missing model import failure in 19.33s, now corrected. Publication/latest-tip qualification
remains pending; real G5/G6 unchanged. Next: finish targeted checks and publish/monitor.


### 2026-10-05 - M12 downloaded source evidence and guard qualification

M12.03/.06/.08, M01.05/.06 and M19.02: source run 37354566008, updated
18:20:57 UTC, first attempt all six completed/success. Downloaded JUnit/logs verify
469 PostgreSQL passes/seven separate Docker skips (476 cases, zero errors/failures,
245.350s), 47 Chromium in 45.2s, seven actual Docker/max-profile in 142.794s,
three Terraform mocks, native guarded 0020 forward/reverse/forward/dump/restore/erasure,
clean lock/production audits, static/build/schema/loader and unprivileged startup.

The final historical-real guard passed five targeted PostgreSQL/legacy workflow cases in
19.43s; Ruff/format218/mypy27 pass. Its second initial fixture run recorded four passes/
one cached-related-row assertion in 21.27s; refreshing the simulated historical row matches
actual private API database reads. No safety assertion or product gate was weakened.
Changed comparison guard/test, contract, PRODUCT_PROGRESS.md, this log and M12 evidence.
M12.08 remains PARTIAL pending exact final guard publication CI. Real M12/G5/G6 unchanged.
Next: push guard on main, monitor all six, then publish qualified receipt with normal CI.


### 2026-10-05 - M12 historical-real guard pushed on main; exact CI running

M12.03/.06/.08 and M01.05/.06: published 8f2f57b8e31991165fe9f701450a5e8a27e609ff
(`fix: require prospective protocols for historical real comparisons`) directly on main.
[Run 37355869813](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37355869813)
uses ordinary CI; two jobs have passed at this update and remaining jobs are running.
Earlier six-job success belongs to 65bbc2d, not this new tip. M12.08 remains PARTIAL until
this exact source revision completes qualification. Progress receipt will retain CI and
actual latest-tip monitoring. No new provider/hosting/scientific approval.


### 2026-10-05 - M12 final code six-job qualification verified; receipt publication pending

M12.03/.06/.08, M01.05/.06 and M19.02: published final code
8f2f57b8e31991165fe9f701450a5e8a27e609ff passed all six jobs first attempt in
[run 37355869813](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37355869813).
All six completed/success states were observed; gh run watch --exit-status returned 0.
Python job completed its full suite, native 0020 recovery rehearsal and artifact upload
at 18:34:53 UTC. This timestamp is the observed job completion, not an invented run
updatedAt. Other five jobs completed successfully; real local M12.08 acceptance is DONE.
M12 overall remains PARTIAL; actual cohort, source bias, retention/power and G5/G6 are unrun.

Automatic approval review rejected the final guard CI log/artifact download and run-metadata
requests because its usage limit was reached. The rejection explicitly says review could
not be completed and is not a finding that the actions are unsafe. No approval bypass was
attempted. Final guard artifact counts/timings have not been inspected or claimed; the earlier
65bbc2d downloaded artifacts retain their own dated 469 PostgreSQL/47 Chromium/seven Docker/
three Terraform scope. The five targeted guard tests remain local evidence (19.43s).

Changed PRODUCT_PROGRESS.md, this log and M12 evidence for the final receipt, locally only.
Receipt commit/push and a fresh remote-head/branch recheck remain pending review availability;
there is no claim of a published receipt or its CI. Resume with ordinary main-only commit,
push and monitor the actual latest tip. Next recommended engineering module: M09 detector/
artifact governance, explicit unknown/confidence handling, reproducible benchmark reporting
and reviewed fallback; release recognition only with permitted representative real labels.
No actual provider, production, powered study or recognition activation.

### 2026-10-05 - M12 final artifact receipt recovered during authorized M09 implementation

M12.03/.06/.08, M01.05/.06 and M19.02: automatic review is available again. Read-only final
8f2f57b run 37355869813 artifacts were downloaded: 477 cases, **470 PostgreSQL passes and seven
separate Docker skips**, zero failures/errors, 429.660s; separate Docker job seven actual passes,
141.479s. Earlier unavailable-download statements retain their historical scope. Final M12
receipt will be included in the authorized M09 publication, with CI on the exact new tip.

### 2026-10-05 - M09 coherent local recognition engineering implemented, qualification running

M09.01-M09.08, M08.05/.06, M14.04/.05, M15.01/.06, M16.05, M18.07, M01.02/.05/.06 and M19.02:
fixed engine and immutable measurement/code/template/config manifests, bounded nullable/ordinal
observations/evidence spans, explicit UNKNOWN/unverified candidates, all-held-out-source benchmark
receipts, independent exact-report approvals, latest passing activation, one active version,
replacement/rollback/stop/drift controls, staff UI/API and portable owner reproduction. Existing
M08/M18 blinded review remains canonical fallback; no candidate event publication. Privacy/export,
withdrawal/expiry/reviewer revocation and restore erasure include new guarded migration 0021.
Architecture 2.16.0, ADR-024 and D036 record the boundary.

Changed analysis/recognition.py, tools/analyze_capture.py and tools/recognize_observations.py;
backend/core models, recognition service/API, dataset invalidation, recovery/native rehearsal,
private export and URLs; frontend recognition route/navigation/styles/browser tests; recognition
contracts/ADR/qualification and both mandatory progress files. Local corrected initial PostgreSQL
suite: 26 passes in 130.78s after 11 ordering failures/15 passes (112.32s). Initial frontend lint
caught the installed React effect rule; callback pattern fixed. Ruff/format226/mypy29 pass;
Django/schema checks passed before the last small changes. Full PostgreSQL, final UI/browser,
native PostgreSQL 0021 recovery and source/latest-tip CI remain in progress.

Assumptions: synthetic observations are fixture claims; no real probability calibration or
independent expert approval exists. All software benchmarks are retrospective; repeated hold-out
inspection cannot qualify G2. Real registration/activation, provider access and hosting remain
closed; no training rights are implied. Next: complete local qualification, commit/push main with
ordinary CI, monitor actual final-tip checks, then acquire permitted real data and expert labels.

### 2026-10-05 - M09 UI, static and native recovery qualification

M09.05-.08, M14.04/.05, M15.01/.06 and M16.05: 51 Edge browser tests passed (54.3s), including
four M09 flows. Inspected 390px mobile screenshot; layout, focus, separate metrics, stop and
manual fallback readable. Production Next 16.3.6 build/lint/types, Ruff/format226/mypy29,
Django/schema-drift and affected documentation links passed. Native PostgreSQL 0021 guarded
empty-schema forward/reverse/forward and seeded dump/restore erased private detector manifests,
observation inputs, reports and approval rows before quarantined reads; repeated controls and
pending-upload erasure passed. Real G1/G2, calibration and hosted isolation remain unrun.
Full PostgreSQL regression suite still running; exact publication/latest-tip CI remain pending.

### 2026-10-05 - M09 local development schema applied

M09.05/.08, M01.05/.06: applied additive core.0021_recognition_lifecycle successfully to the
loopback local development PostgreSQL database; Django system check passed. Native disposable
schema/recovery qualification above remains a separate check. No live cloud/provider/real
recognition activation. Final PostgreSQL regression and exact-tip publication CI remain pending.

### 2026-10-05 - M09 full local PostgreSQL regression passed

M09.01-M09.08 and affected privacy/recovery requirements: 498 PostgreSQL/Python tests passed,
seven separate Docker skips, 648.03s, 505 JUnit cases with zero errors/failures. Includes 28
M09 cases, owner-only exact-report CLI reproduction and actual cross-account locking regression.
Final added OpenCV template bridge is checked separately because it was added after collection;
its result is not included in the 498 count. Earlier 51 Edge/static/build/schema/docs/native
0021 migration/recovery checks passed. Source/main publication and actual latest-tip CI pending.

### 2026-10-05 - M09 final template bridge qualified, source ready for main

M09.01-.08, M15.01 and M01.05/.06: separately collected final PostgreSQL/OpenCV test passed
in 9.54s. Actual synthetic template matching emitted pinned LOW-support UNKNOWN candidates;
credentialed report sanitizer discarded candidates and kept automatic opportunities empty.
Final Ruff/format226/mypy29 recheck passed. Combined local evidence is 498 full-suite passes
plus this one separate case, 51 Edge browser passes, build/lint/types/schema/docs and native
0021 migration/dump/restore/erasure. Seven real Docker tests require the dedicated CI job.
No dependency/provider/real-recognition/hosting activation. M09.08 remains PARTIAL pending
exact-source remote qualification; commit/push main and monitor actual final tip next.

### 2026-10-05 - M09 source published directly on main, exact CI pending

M09.01-.08, M01.05/.06 and M19.02: pushed source 621a16142a26105233c3c7d925faf43762cc5467
(feat: implement M09 local recognition validation module) directly to main with CI enabled.
Includes recovered final M12 qualification receipt. Earlier local 498 full + one separate
PostgreSQL/OpenCV, 51 Edge/static/build/schema/docs and native 0021 recovery remain their dated
scope. Monitor this exact source and final normal-CI qualification receipt; no earlier green
run is substituted. Real recognition/calibration/G1/G2/provider/hosting approval remains closed.

### 2026-10-05 - M09 source CI five jobs passed; runner cancellation retried

M09.01-.08, M15.01/.06 and M19.02: source 621a161 run 37371312001 first attempt completed
with five successful jobs. Downloaded backend artifact: 499 PostgreSQL passes / seven separate
Docker skips, 506 cases, zero errors/failures, 302.185s. Native recovery passed. Completed
frontend log: 51 Chromium passes in 49.5s; Terraform: three mocks passed. Audits/static/build/
application-container startup passed. Media job 111968869023 was cancelled at 20:56:38 UTC:
no assigned runner, no steps executed; annotation says hosted runner acquisition failed after
multiple attempts. The workflow is therefore not green; no actual Docker test success is claimed.
GitHub Status reports an ongoing hosted-runner assignment incident (2026-10-05, 20:39 UTC update).
Retried only that cancelled job on the same exact source; five successful results are preserved.
M09.08 remains PARTIAL pending media/source qualification and final ordinary-CI receipt checks.

### 2026-10-05 - M09 source six-job qualification verified; final receipt retains ordinary CI

M09.01-.08, M08.05/.06, M14.04/.05, M15.01/.06, M16.05, M18.07, M01.02/.05/.06 and M19.02:
source 621a16142a26105233c3c7d925faf43762cc5467 passed all six jobs in run 37371312001 on
attempt 2, completed 21:11:43 UTC. Watcher exited 0; fresh run/job metadata confirms exact SHA
and six completed/success states. Downloaded artifacts confirm 499 PostgreSQL passes / seven
separate Docker skips (506 cases, 302.185s, zero errors/failures) and **seven actual Docker/
max-profile passes** (98.111s, zero skips/errors/failures). Completed log summaries confirm
51 Chromium passes (49.5s) and three Terraform mocks. Static/schema/audits/build/standalone/
unprivileged startup and native guarded 0021 recovery passed. Five original successes were
preserved; only media was retried after GitHub cancelled it without acquiring any runner or
executing steps. No source/test guard was changed to get green results.

M09.08 DONE qualifies coherent local engineering only; M09 overall remains PARTIAL and actual
observation implementations, calibration, expert reference timing/labels, G1/G2, review cost/
capacity and hosted release remain required. Updated this log, PRODUCT_PROGRESS.md, M09 evidence
and D036 qualification status. Publish this final receipt on main with CI enabled and monitor
the actual final tip, with a clean local/remote/head/branch check. Scientific/provider/hosting
activation and repository access-review/development-advisory work remain open.

### 2026-10-05 - Real capture discovery and G1 assessment implementation, validation in progress

M07.02-M07.05, M08.02-M08.05/M08.08, M09.02-M09.04 and M01.02: user authorized the
first real recognition loop, then confirmed no capture paths/reviewers and requested YouTube
or direct-game discovery. Public primary documentation and bounded local Steam/process/video
inventory were reviewed. Tekken 8 is installed; no qualifying captures or exact in-game build
were verified. Wavu documents metadata; a local recorder project uses in-client replay playback.
The discovered Commons 2022 trailer is edited, outside the profile and has an unreviewed external
licence claim. No video downloaded, game launched, contact sent or private endpoint called.

Added analysis/observability.py, tools/assess_observability.py, owned live-checked snapshot API
route and dataset UI/download. Report preserves all unresolved ranked TARGET windows, separates
TRIAL/practice and target-absent controls, validates session/task membership, shows category/QC/
timing/session gaps and source concentration, and compares exact proposed threshold boundaries.
Reports contain aggregate counts/pins without source/reviewer identities or labels; G1 remains
NOT_RUN and release approval false even for perfect/real-labelled receipts. Immutable dataset
QA, M09 policies and canonical pipeline unchanged; no new database table/migration.

Added tests/test_observability.py and browser coverage; capture/runbook, research, ADR-025,
architecture 2.17.0, README, dataset contract, D037 and tracker synchronized. Actual checks so
far: 19 new PostgreSQL/offline/API/privacy/threshold tests passed in 123.18s; Ruff passes and
mypy checks 31 sources. Existing dataset/recognition compatibility, final frontend/static/build/
browser/schema checks and publication remain pending. Actual footage, rights/protocol approval,
exact-build expert facts, qualified independent labels, G1/G2 and real observation calibration
remain blocked. Next: finish local checks, then acquire original permitted in-client recordings
with verified overlays and independently review before developing/releasing real recognition.

### 2026-10-05 - M08.08 local tooling qualified; real acquisition remains incomplete

M08.02-M08.05/M08.08, M07.02 and M09.02-M09.04: 19 initial new tests passed (123.18s)
plus one final private annotation-error case (13.38s); 53 existing dataset/recognition tests
passed (291.77s). First full Edge suite had 51 passes and one new-test synchronization timeout:
expiry was toggled before the prior refresh finished, correctly removing the report/button.
Fixed the test sequence; six dataset Edge cases passed (9.9s). All application changes remain
covered by passing scoped checks; full remote CI pending. Inspected mobile screenshot and
overflow/keyboard checks pass. ESLint/typecheck/Next production build, Ruff/format/mypy 31,
Django/migration consistency, 170 local links and diff checks pass. Optional DRF OpenAPI
generation unavailable due to missing inflection; not recorded as successful, no dependency
added. Restricted npm wrapper stalled; permission-enabled checks passed and stale wrapper stopped.

Added docs/experiment-results/g1-preparation.md; tracker M08.08 DONE is local tooling only.
M07/M08 actual evidence, M09 real observation implementation and G1/G2 remain incomplete.
No footage/reviewer approval claimed. Qualifying capture count remains zero; game UI control is
unavailable here, even though installation was found. Next: publish main with enabled CI and
monitor exact tip; obtain permitted originals and independent exact-build facts/labels before
real recognition. Both progress files and D037/current architecture reflect this boundary.

### 2026-10-05 - G1 preparation source published; exact CI pending

M08.08, M01.05/.06 and M19.02: committed/pushed e6743424fabc82a867e84dfc473d9399a3b95ccc
directly to main with ordinary CI (17 files, including both progress files). Remote branch
inventory before publication contains only main; local tree was clean after commit. Actual
source run 37380495040 is in progress; no source-wide remote success claimed yet. Earlier
local checks retain the exact scoped results above. Real footage/expertise and G1/G2 still
missing. Monitor all six source jobs, then publish a normal-CI qualification receipt and
verify the actual final tip. No feature branch or paid/cloud/provider activation.

### 2026-10-05 - G1 preparation source fully qualified; final receipt keeps CI enabled

M08.08, M08.02-M08.05, M07.02, M09.02-M09.04, M01.02/.05/.06 and M19.02:
source e6743424fabc82a867e84dfc473d9399a3b95ccc passed all six jobs in run 37380495040,
first attempt, completed 22:19:16 UTC. Exact SHA/all six success states and watcher exit 0
verified. Downloaded backend XML: 526 cases, 519 passes/seven separately gated Docker skips,
zero errors/failures, 550.267s. Downloaded sandbox XML: seven actual Docker/max-profile
passes, zero skips/errors/failures, 142.471s. Completed logs: 52 Chromium passes (47.8s)
and three Terraform mocks; audits/static/format/types/build/container/unprivileged startup
and guarded native PostgreSQL migration/dump/restore/erasure passed. Remote main still exactly
e674342 before preparing this receipt. No CI retry or source/test guard change required.

Updated PRODUCT_PROGRESS.md current checks/publication/M08.08/M19.02/next position, this log,
G1 software qualification and D037. Local M08.08 DONE does not complete actual M07/M08/M09:
zero qualifying real captures, no verified in-game build/overlays/experts/independent labels;
G1/G2 remain NOT_RUN. Publish this ordinary-CI tracking receipt, monitor its actual latest main
SHA, then confirm local/remote/head/branch consistency and clean tree. No skip instructions,
feature branches, game control, external collection, private transport or hosted release.

### 2026-10-05 - Original DojoPulse visual system, local checks complete

M13.01/.04/.07/.09, M16.02, M19.02 and M01.05/.06: owner prioritized UI improvement
before real capture work and requested MetaPunish inspiration without an exact copy. Read
root/frontend instructions and installed Next CSS/image guides. Inspected public reference
HTML/CSS and original hero (connected browser unavailable); none of those assets/copy/code
are distributed. Built-in imagegen created an original fictional martial artist/dojo;
inspected PNG then format-only compressed to 169,594-byte WebP. Three Barlow fonts/OFL
licences are self-hosted. Exact prompt/origins recorded in docs/design/visual-system.md.

Changed globals.css, layout.tsx, page.tsx, training-journey.tsx, new fonts/public art/icon,
new browser entry tests, Dockerfile.web and actual container HTTP/byte smoke checks.
Graphite/ember surfaces, condensed headings, truthful scope/validation, responsive entry
and training overview lead into existing tools. Authenticated training tools precede account/
privacy controls; section links, token scrubbing, consent, unknowns and all scientific/
provider gates remain. No backend/migration/dependency change or external feature activation.

Actual checks: ESLint/types/Next production build pass; 54 complete Edge tests pass in 57.9s.
Inspected desktop/mobile visitor and training previews plus mobile dataset view. Fixed narrow
heading sentence spacing; direct CLI runs two entry tests successfully (7.7s). A prior npm
filter invocation selected no tests because Windows dropped --grep; not counted as a pass.
Visitor 320/390/768/1440px and player 390px overflow, image loading, hash navigation, disabled
gates and skip-link keyboard checks pass. Selected body/muted/button/border/focus contrast
ratios 17.02/8.50/8.96/3.11/11.57; not a whole-page accessibility audit. Local backend/Docker/
Terraform not rerun for this UI-only implementation; full exact-source remote CI remains.

Added M13.09 stable acceptance and local DONE; overall M13 stays PARTIAL. Updated both
progress files, player-experience contract, UI receipt and D038. Native screen-reader,
real-device/participant usefulness, real captures/G1-G6 and hosted/provider approval remain
open. Remote/local main still 20f74cc and only main exists. Next: publish ordinary main
commit, monitor exact source including container assets, then normal final receipt/latest-tip
checks. Return to permitted exact-build capture/reviewer work after this UI delivery.

### 2026-10-05 - UI source published with enabled CI

M13.09, M16.02, M19.02 and M01.05/.06: source ec5e10217918b1bb3245bdd65dc5d99f08201ace
committed/pushed directly to main after fresh remote-head verification. Exactly 20 intended
files changed; local tree clean after commit. Only main exists locally/remotely. Additional
133 local Markdown links, parsed workflow/six-job and public packaging assertions pass.
Python PyYAML was unavailable; the already installed js-yaml validated the workflow instead;
no dependency installed. Exact-source CI pending, no source-wide remote success claimed.
Next: monitor all six jobs including real standalone asset HTTP comparisons, record scoped
qualification and publish an ordinary final progress receipt with actual latest-tip checks.

### 2026-10-05 - UI source fully qualified; final receipt keeps CI enabled

M13.01/.04/.07/.09, M16.02, M19.02 and M01.05/.06: source ec5e10217918b1bb3245bdd65dc5d99f08201ace
passed all six jobs in run 37385253136 first attempt, completed 23:04:25 UTC. Exact SHA/all
six success states and watcher exit 0 verified. Backend artifact: 526 cases, 519 passes/seven
separately gated Docker skips, zero errors/failures, 550.314s. Actual sandbox artifact: seven
Docker/max-profile passes, zero skips/errors/failures, 90.925s. Completed logs verify 54
Chromium passes (39.4s), three Terraform, actual unprivileged standalone hero/icon HTTP byte
comparisons, production build, audits/static and guarded native migration/dump/restore/erasure.
An initial local CI-log extraction hit Windows CP1252 output encoding; UTF-8 retry succeeded;
no source/job/test rerun or guard change was needed. Fresh remote source head equals local
source and only main exists.

Updated PRODUCT_PROGRESS.md, this log, UI receipt and D038. M13.09 DONE means local visual
engineering; overall M13/real usability/accessibility/devices and G1-G6 remain incomplete.
Publish this ordinary final tracking receipt, monitor its actual latest main SHA and confirm
clean local/remote/head/branch state. Original art/fonts and prompts are in the design notes;
no copied reference assets, private endpoint, cloud provisioning, gameplay/data activation
or real-player claim. After UI delivery, resume permitted exact-build footage and independent
review using the existing preparation tools.

### 2026-10-06 - Selected ID search and private recording-companion architecture

M22.01–M22.09, M04.01, M05.01/.03 and M01.02/.05: owner delegated the choice of an
ID-to-playback approach. Choose reviewed per-ID metadata plus opt-in Windows recording sync.
EWGF is the first metadata candidate because its documented operation is player-scoped;
Wavu remains a metadata alternative. Rechecked public EWGF API/terms, Wavu API and community
recorder documentation. No substantive usage terms or authenticated schema fixtures obtained,
and no documented video-download service established. Provider activation remains blocked.

Added ADR-026 and architecture/recording-companion.md; updated architecture-v2.md to 2.18.0,
match-ingestion.md, player-experience.md, decision-log.md (D039), PRODUCT_PROGRESS.md and this
log. M22.01 is DONE for design only; M22.02–M22.08 are NOT_STARTED and M22.09 BLOCKED pending
separate in-client replay automation review. Initial sync still requires creation/export of
a completed recording; its goal is removing repeated manual upload. Public ID lookup never
authorizes another owner's private recordings. Reuse M06 resumable media and attribution;
no companion path may directly publish canonical gameplay or coach from metadata alone.

Actual checks: final 176 local Markdown links across all eight changed documents passed;
nine unique M22 requirement IDs/statuses, architecture-version consistency, decision reference
and personal-profile-ID exclusion passed. git diff --check passed. Runtime/backend/browser/
Docker tests were not rerun for this documentation-only decision; earlier software qualification
remains separately dated 2026-10-05. No credentials, subscription, contact, copied recorder code,
game automation, private endpoint, footage acquisition, hosted deployment or publication.

Next: M22.02 owner/device pairing and revocation, then a completed-file sync vertical slice
through existing local evidence services (M22.03–M22.06), with meaningful controlled privacy,
interruption/retry/deletion checks. In parallel obtain usage evidence, privately configured key
and permitted identity/schema fixtures for M04/M05, plus exact-build footage and independent
review for M07/M08. Real Windows/hosting and in-client capture remain separate qualifications;
G1–G6 and native replay X01 are unchanged. The supplied player's identifiers are not committed.

### 2026-10-06 - Direct Tekken replay API and native-payload research

X01, M22.01/.09, M05.10 and M01.02/.05: owner requested deeper direct-API research before
building the selected companion. Searched public documentation/repository inventories and
inspected pinned EWGF WavuService/Battle/PolarisProxyService, Cathesilta recorder and GamesDat
Tekken watcher/test exclusions. Read Wavu/EWGF public descriptions, a YouTube-index project,
official replay/patch behavior and the EULA linked for the Steam game. No game backend call,
login, credential, payload/video acquisition, external contact or third-party code execution.

Added research/native-tekken-replay-access-2026-10-06.md. Updated the older source report with
a dated follow-up link, ADR-026, recording-companion.md, match-ingestion.md, D040, tracker and
this log. Existing earlier 2026-10-06 design changes remain uncommitted on main; no branches
created or publication claimed. Direct game replay-list access exists; externally obtained
playable bytes, actual format/input/event decoding and a supported renderer remain UNVERIFIED,
not proven impossible. GamesDat's support badge is an untested broad file watcher, not a
decoder. The community recorder captures in-client playback, and the inspected EWGF paths
process metadata/profile/leaderboard data. No inference is made about every private code path.

Final local validation: 189 local links across all ten changed Markdown documents passed;
requirement IDs/statuses, pinned evidence/provider classes, whitespace and personal-profile-ID
exclusion passed; git diff --check passed. Runtime/backend/browser/Docker tests not run:
this is public-source research and documentation only. No scientific or real-game qualification
added; G1–G6 remain NOT_RUN. M22 remains PARTIAL/design only, M22.09/X01 and live M04/M05
gates remain blocked. The report distinguishes technical feasibility, permitted usage and
version-dependent rendering, rather than converting search absence into impossibility.

Next for direct acquisition: obtain an allowed operation/usage contract and identity-to-payload
fixtures, then supported-runtime/format/expiry/rendering evidence before any game request/client
implementation. ADR-026 remains a staged fallback, not the sole possible architecture; the
canonical Match/ReplaySource/GameplayEvent/player-model pipeline remains provider-independent.

## 2026-10-06 - M22 local recording companion implementation

Requirements: M22.02-06/.10; M06.02/.03/.06, M14.03-05, M15.01/.06, M16.05,
M13.03/.06, M01.05/.06 and M19.02. Owner authorized implementation, main publication
and monitoring. Implemented `companion/` Windows source GUI/DPAPI/selected-folder sync;
`backend/core/companion.py` and `companion_api.py`, guarded migration 0022, device/upload
URLs and defaults; M06 unassigned-byte verification/parser/private media integration,
consent/account/deletion/restore fences and allowlisted export/native recovery fixture;
`frontend/app/recording-sync.tsx`, reused attribution form and home entry; controlled backend/
helper/browser fixtures, README and architecture/D041. Existing research/ADR-026 plan
is included in this work. No user gameplay IDs or credentials added to repository.

Focused initial SQLite run found authentication denial and local-parser test settings issues
(29 passes/three failures); corrected. PostgreSQL focused 88 pass in 36.33s, including
generated finalized 1080p60 MP4 -> helper -> resumable -> worker/media -> private range with no
Match or GameplayEvent. Actual Windows DPAPI and writer-excluding share behavior pass.
Three new Edge checks pass (9.2s); production build/lint/types and mypy 35 pass. Full browser
57 pass (1.1m), then shared fixture routes updated to avoid unmocked local proxy requests.
Initial full backend was stopped for a new-test import/export-route correction; final suite
and native migration/recovery/static/links/publication are ongoing, recorded in the receipt.

No real recorder/game capture, usage permission, installed/signable distribution, automatic
replay recording, native game request, live EWGF key/activation, G1-G6, hosting or player
benefit is established. Next: finish exact local/CI qualification, then M22.07-08 real
Windows packaging/privacy/resource acceptance, preserving independent provider/native gates.

### Final local qualification before main publication

Final affected PostgreSQL suite: **93 passed / one OS symlink-privilege skip in 24.84s**.
The earlier full run completed 553 pass/one same-transaction mocked revocation test failure/
seven separate Docker skips (773.65s); corrected the test to revoke between authentication
and service admission, then final affected suite passes. This is not represented as a final
full-regression pass. Final source CI is authoritative for the complete final tree.
Added pause-during-inspection admission fence, redirect credential isolation, linked-root
checks (local Windows privilege unavailable), invalid-auth rate budget and a dedicated
Windows CI job. Local pure Windows helper checks: 16 pass/one privilege skip in 0.84s.
Final 57 Edge pass (1.1m), mobile screenshot inspected, production build/lint/types and
final typecheck pass. Ruff/248 formatted files, mypy 35, Django check/no schema drift,
seven-job CI YAML, 312 Markdown links/157 unique requirement statuses pass. Native
PostgreSQL dump/restore and guarded forward/reverse/forward, repeated controls, restored
device invalidation and pending upload erasure pass; local migration 0022 and draft loader
run. No hosted recovery objectives measured. Source commit/push/latest-tip monitoring next.

### Manual-upload deduplication repair before publication

M22.04/.05/.10, M06.06, M14.05 and M16.05: found that an already manual-uploaded
copy could be skipped without a durable server suppression receipt. Added an explicit
RecordingReceipt.suppressed field and guarded migration 0023. Existing reserved or verified
manual copies (including removed verified assets) now receive an owner-keyed tombstone,
without granting a device access to the manual upload. Local receipt expiry/new pairing
cannot revive it. Added manual deletion/new-device and irreversible-history coverage, plus
actual native restore suppression fixture. Final affected 94 PostgreSQL pass/one OS symlink
privilege skip in 38.89s; 0023 applied, schema/static/format/mypy pass. Focused guard/native
restore and main publication/CI next. No external release boundary changed.

Final suppression guard test passes (one PostgreSQL check, 6.81s), and updated native
0022/0023 migration/recovery rehearsal passes, retaining the suppressed receipt while
revoking restored devices and erasing pending uploads. Main publication/CI remains next.

### 2026-10-06 - Initial publication and cross-platform/security correction

M22.03/.07/.10, M15.04/.06, M01.05/.06 and M19.02: published 2679bc3 and
60d55ac directly to main with ordinary CI. First run 37487810089 passed Windows companion,
frontend, media sandbox, Terraform and application containers. Linux mypy rejected
Windows-only attributes because os.name is not a recognized typing platform guard;
changed companion/{credentials,sync,__main__}.py to sys.platform guards, retaining
runtime denial on unsupported systems. mypy --platform linux and --platform win32
both pass all 35 source files; Ruff/format pass. Actual Windows CI JUnit confirms
17 passes/no skips, including the controlled linked-root case. Local final helper
plus synthetic real-MP4 transfer checks: 17 passes/one unavailable symlink privilege
in 15.91s; this does not represent game/recorder or signed delivery qualification.

The production npm audit found sharp GHSA-wq5f-xc86-pv6w and source-map-js
GHSA-68fv-2mgg-jv7q. Checked the primary advisories; updated frontend/package-lock.json
compatibly to sharp 0.35.5 (including matching native/libvips packages) and
source-map-js 1.2.2. Production audit now reports zero findings; five existing development
findings remain separately tracked, with no audit suppression or forced major upgrade.
Next build/lint/types and sharp 0.35.5 native PNG encoding pass; corrected source
publication and all-seven exact-tip CI must succeed before M22.10 local qualification.
Updated PRODUCT_PROGRESS.md and M22 receipt; architecture/provider/real/hosted gates unchanged.

Advisories: [sharp](https://github.com/advisories/GHSA-wq5f-xc86-pv6w),
[source-map-js](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).

### 2026-10-06 - Corrected M22 source qualification and final receipt

M22.02-07/.10, M06.02/.03/.06, M13.03/.06, M14.03-05, M15.01/.04/.06,
M16.05, M01.05/.06 and M19.02: corrected source
7635a3c161d8614b91dcb75e1035ee6b524617db passed all seven jobs on
[run 37488902056](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37488902056),
completed 15:47:52 UTC; watcher exit 0. Downloaded backend, Windows and media JUnit and
completed job logs verify **557 PostgreSQL/Python passes (580.176s)**, eight Linux skips
(seven Docker plus one actual Windows test, exercised by dedicated jobs), **17 actual
Windows passes/no skips (1.358s)**, **57 Chromium passes (58.5s)**, **seven actual
Docker/max-profile passes/no skips (123.229s)** and three Terraform mock contracts.
Production npm and both Python lock audits, Ruff/248 formatted files/mypy35, Django
check/schema/migrations/contracts, build/lint/types, unprivileged application startup/
HTTP asset checks and native guarded 0022/0023 migration/dump/restore all pass. Restore
revokes devices, preserves manual-copy suppression and erases pending uploads; actual
production RPO/RTO remains NOT_MEASURED. Local final image dependency encode and explicit
Linux/Windows typing also pass. Initial source failures remain above, rather than claiming
the first publication was green. Fresh remote source matches local and only main exists.

Updated PRODUCT_PROGRESS.md, this log, experiment-results/m22-recording-sync.md, current
architecture-v2/recording-companion/player-experience wording and D041 evidence. M22.02-06/.10 DONE applies
to the coherent local engineering module only. Overall M22 remains PARTIAL: installer/
signing/update/uninstall, real supported recorder/device fixtures, independent desktop/
privacy/security review, measured resources and hosted admission are M22.07-08. Live
M04/M05, automatic replay creation M22.09, native X01 and real G1-G6 are unchanged. The
helper needs existing owner-created recordings; no automatic game capture is implied.

Publish this final receipt with ordinary CI, monitor its actual latest main SHA and verify
clean matching local/remote head plus only main before handoff. No runtime code changed
for this receipt; documentation links/requirements/whitespace are checked before commit.
Next implementation is Windows delivery/recorder/privacy/resource qualification, alongside
permitted provider fixtures and exact-build footage/independent review. No provider key,
private endpoint, signed distribution purchase, game control or live cloud deployment added.

Final receipt checks: 311 local Markdown links across root/companion/docs, all 157
milestone plus 12 optional stable IDs/status/table cells and architecture 2.19.0
consistency pass; git diff --check passes. Runtime tests not rerun for documentation
changes locally; the final receipt keeps ordinary full CI on its exact SHA.
