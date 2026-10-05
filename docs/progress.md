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
