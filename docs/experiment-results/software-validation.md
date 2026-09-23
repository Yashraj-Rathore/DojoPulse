# Local software validation — 2026-09-18

Decision: continue to real-data collection and human observability review.
Do not release automatic gameplay judgments, call the draft drill reviewed, or enable
external uploads. No real Tekken experiment has run.

## What was executed

Windows, Python 3.12.2, PostgreSQL 17 on an isolated loopback cluster, Node 22.14,
Next.js 16.3.5 and FFmpeg/FFprobe 8.1.2. Dependency versions are pinned in requirements.lock
and frontend/package-lock.json. Docker's daemon was unavailable; no container build or
Cloud Run/Storage integration test was executed.

- PostgreSQL-backed pytest suite: **64 passed**. Includes real concurrent job claims and
  evaluation-versus-deletion transactions, full synthetic API loop, ingestion → worker →
  retention purge, source/membership invariants, immutable historical knowledge, reanalysis,
  verified practice, CSRF/ownership, decoder limits, template regression and every result status.
- Ruff lint/format and mypy for the typed analysis/tooling package pass.
- Django system check and migration-drift check pass. PostgreSQL migrations and draft loading run.
- Next.js production build, ESLint and TypeScript pass.
- Playwright: **2 passed** using installed headless Edge. Tests use mocked API responses for
  the capture/drill gates and uncertainty/unknown rendering; these do not validate gameplay
  or replace Django API integration tests. The full-page screenshot was visually inspected.
- GitHub Actions is configured for PostgreSQL, FFmpeg, Python checks, Next build and Chromium
  smoke tests. Remote GitHub CI has not run. No deployment was performed.

The local test XML is reports/pytest.xml (ignored runtime artifact).
UI screenshot: frontend/test-results/workspace.png (ignored runtime artifact).

## Complete synthetic loop

The API test uses deliberately fabricated **synthetic-only** evidence: 50 baseline outcomes
in 5 sessions (5 successes), 40 reviewed practice attempts, and 50 later outcomes in 5 sessions
(45 successes). Definitions are synthetic test fixtures in the disposable test database;
the real draft definitions remain unapproved. The test expects an observational improvement,
then verifies identical reevaluation is idempotent and deleting the practice source invalidates
the result and removes its verified exposure. Other tests cover deterioration, unchanged,
inconclusive, insufficient and incompatible cases.

This is a software invariant check. The rates are not a player's performance, a pilot result,
detector precision, a training effect, or evidence that Jin's move can be reliably observed.

## Measured synthetic media benchmark

One generated black 1920×1080 H.264 SDR 60 fps clip, duration 0.5 seconds, analyzed three times.
Each run produces REVIEW_REQUIRED and zero gameplay opportunities.

| Measurement | Actual result |
|---|---:|
| Captures processed / unique sources / reprocessing | 3 / 1 / 2 |
| Failed jobs | 0 |
| Median wall processing time | 2.843 seconds |
| Total sampled decoder CPU time | 0.609375 seconds |
| Maximum sampled decoder RSS | 222,605,312 bytes (212.29 MiB) |
| Source bytes per clip | 4,395 |
| Derived bytes per analysis | 259,530 |
| Total derived bytes stored | 778,590 |
| Human review seconds | 0 — no gameplay review occurred |
| Cloud transfer/cost, reviewer hourly rate | unknown / not measured |
| Cost per completed loop/comparable evaluation | unknown |

Machine load and warm/cold starts affect timing; only three runs were taken.
The first run took about 7.99 seconds, so the median is not a latency guarantee.
CPU/RSS are watchdog samples, not a full profiler or hard isolation proof.
A tiny black fixture has low entropy and is not representative of a 10-minute game capture.
Do not extrapolate memory, storage, throughput or cloud cost linearly from this clip.
The maximum accepted profile and malicious decoder cases still need an actual sandbox rehearsal.

Sanitized machine-readable summary: software-benchmark.json.
Private clip: private_data/fixtures/synthetic.mp4; local detailed reports: reports/capture-*.json.

## Bugs found and corrected

Canonical JSON normalization now prevents duplicate evaluation revisions after PostgreSQL
round trips. Practice IDs/hashes are part of result lineage. Coverage checks include unknown
eligibility as well as unknown outcomes. Partial-capture evidence selection is rejected.
Owner-first write locks serialize deletion and publication; tested concurrency cannot leave a
newly published conclusion valid after its source is deleted. Immutable model inserts cannot
overwrite an existing version key through a fresh Python instance.

## Experiments awaiting real evidence

| Gate | Result | Decision |
|---|---|---|
| G1 human observability | NOT_RUN | acquire consented profile captures and independent reviewers |
| G2 end-to-end deterministic detection | NOT_RUN | no calibration or released Tekken templates |
| G3 capture friction | NOT_RUN | run unaided capture sessions |
| G4 verified practice | NOT_RUN | expert review the single draft; collect recorded trials |
| G5 natural opportunity frequency | NOT_RUN | collect complete prospective ranked histories |
| G6 comparable/useful closed loop | NOT_RUN | execute frozen plans and native/usual-workflow comparison |

The [pilot protocol](../pilot-protocol.md) specifies data, denominators, thresholds and stop rules.

## Provider-neutral architecture extension

The subsequent ingestion-contract change adds 27 offline synthetic checks. The complete
PostgreSQL-backed suite now passes **91 tests** (27.09 seconds on this run). Ruff lint/format,
mypy across 20 modules, Django system/migration checks and relative documentation links pass.
No frontend or database schema changed in that extension. No live provider integration,
commercial clearance or native replay decoding was established by the contract tests.
See [match ingestion](../architecture/match-ingestion.md) and
[source investigation](../research/tekken-match-sources.md) for the exact implementation boundary.

## Local relational match import — 2026-09-19

The full PostgreSQL suite passes **112 tests** in **42.12 seconds**, adding 21 persistence,
lifecycle, concurrency and migration checks. The 0002-to-current upgrade preserves existing
match/event rows and frozen evaluation specifications and hashes, and backfills upload sources.
Two synthetic adapters exercise identical DTOs without provider branches in gameplay analysis.
Test coverage includes idempotency, source corrections, stale workers, rollback without cursor
advancement, unknown mappings, denied real/network-provider data, cross-owner access, deleted
identity suppression, account purge, and expiration without losing metadata.

Ruff lint/format, mypy (21 source modules), Django system checks and migration drift pass.
Migrations 0003/0004 were applied to the isolated workspace PostgreSQL database. No live provider
requests, private endpoint code, native decoder, frontend changes or real gameplay validation
were part of this implementation. Local synthetic retry tests do not validate live rate limits.

## Identity and history product flow — 2026-09-19

The latest full PostgreSQL suite passes **124 tests in 27.97 seconds**. Twelve added API/worker
tests cover the actual session-authenticated link/queue/worker/history path, expiring/tampered
candidate confirmations, consent, owner isolation, disabled providers, CSRF, pagination,
revocation/deletion, schema quarantine, delayed retries and coverage/result uncertainty.

Frontend ESLint, TypeScript and the Next.js production build pass. **Five headless Edge browser
tests pass in 8.4 seconds**, including the three new identity/history flows. Browser tests use
mock HTTP responses; actual persistence and worker integration are tested separately in Python.
Desktop and revised mobile screenshots were visually inspected; the mobile history uses cards
so evidence status and expiration are visible without horizontal scrolling.

Ruff lint/format, mypy (21 modules), Django system and migration-drift checks pass. This change
requires no new migration. EWGF's public contract was rechecked, but live authenticated schema,
usage clearance and effective operational behavior remain unverified. No provider request was
made from the implemented application; all imported test matches are synthetic.

## Imported-match recording attribution — 2026-09-23

The full PostgreSQL suite passes **145 tests in 28.17 seconds**. Twenty-one attachment tests
cover exact identity/time/build/mode attribution, consent/owner gates, stale metadata, request
idempotency, duplicate bytes, independent publication requirements, real-knowledge approval
gates, historical hash/knowledge preservation, reprocessing, target deletion during streaming,
account deletion/late workers and retention. A generated 1080p60 H.264 clip runs through the
actual FFmpeg worker, attribution command service and purge lifecycle. It is synthetic media.

**Seven headless Edge tests pass in 9.3 seconds**, including attachment/removal on mobile,
required consent and retained form errors after a stale metadata response. Browser tests mock
HTTP; the Python suite tests actual persistence. The attachment form screenshot was inspected.
ESLint, production build, TypeScript, Ruff lint/format, mypy (21 modules), Django system and
migration-drift checks pass. Migration 0005 was applied to the isolated local database.
After limiting attachment reprocessing controls to supported attribution states, the 33 focused
match API/attachment tests passed in 5.91 seconds. Documentation links and diff whitespace pass.

These results establish local workflow behavior, not human attribution accuracy, real-game
recognition, safe hostile-media processing, hosted upload readiness or live provider access.
G1–G6 remain NOT_RUN. See [ADR-014](../adr/ADR-014-recording-attribution.md).

## M13 local player experience — 2026-09-23

**163 Python tests passed in 42.65s** against PostgreSQL. Eighteen new API tests cover preferences,
owner/CSRF filtering, UTC dates/pagination, corrections, feedback and notice idempotency, follow-up
window transitions, export redaction, password-confirmed account deletion, cleanup failure/retry,
and valid/invalid single-range media requests. Migration 0006 was applied locally; schema drift
and Django system checks pass. Ruff lint/format and mypy (21 modules) pass.

**11 headless Edge tests passed in 14.3s**. Four new journeys cover setup/preferences/feedback/export,
mobile keyboard evidence inspection and correction requests, account deletion/sign-out and the
synthetic training sequence through an insufficient-exposure result. Dates exercise UTC and
America/Toronto; mobile overflow/reduced-motion/skip-link focus are checked. Desktop/mobile
screenshots inspected. ESLint, TypeScript and production build pass. Browser HTTP is mocked;
actual API/database/media behavior is independently covered in Python. This is not a real user,
assistive-technology, media-decoder compatibility or gameplay-quality study.

The full M13 release exit remains open for real providers/accounts, measurement/review readiness,
participant usability, screen readers and actual device/browser qualification. No external
notification, provider request, hosted deployment or real gameplay gate was activated.
