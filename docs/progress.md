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
