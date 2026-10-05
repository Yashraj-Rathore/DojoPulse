# M12 local comparison qualification

Date: 2026-10-05. Dataset: independently reviewed synthetic fixtures.

Scope: scheduled follow-up/retention, exact provenance, complete current collections,
append-only owned missing/recorded/skipped-session ledgers, immutable result revisions,
currentness projections, private reproducible reports, baseline-only planning diagnostics,
erasure/restore/migration and guided UI. This is software evidence only.

Local qualification:

- Existing loop/practice: 26 PostgreSQL passes in 42.87s.
- Full pre-final-refinement suite: 468 passes, seven separate Docker skips and one stale
  concurrency mock-location failure in 477.65s (476 JUnit cases). The engine moved from
  loops to comparisons; the original deletion-race assertion is retained with its actual
  engine hook. This run is not claimed as a completely green full suite.
- Final affected PostgreSQL/training/concurrency: **50 passes in 177.71s**, zero skips,
  errors or failures, after source/currentness/manifest and hook refinements. Includes
  source/decoder/platform drift, expiry, unfavorable omission, missing-session resolution,
  immutable phases/retention references, request retries, ownership/CSRF, safe reproducible
  reports, export/account erasure, guarded rollback and actual two-thread serialization.
- **47 Edge browser journeys in 45.9s**; final four M12 cases in 8.6s after source-expiry UI
  refinement. A 390px provenance/hash view was inspected without horizontal overflow.
- Final production Next build, ESLint/TypeScript, Ruff/format (218 files), mypy (27 modules),
  Django/schema check, local migration 0020, contract loader and documentation links pass.
- Native PostgreSQL guarded fresh forward/reverse/forward, actual dump/restore,
  controls-before-reads and repeat replay pass through migration 0020; session receipt erasure,
  result invalidation, report/diagnosis/upload erasure and cancelled restored assignments
  asserted. Actual production RPO/RTO remains NOT_MEASURED.

Qualification findings remain recorded: first focused run 45 passes/two fixture errors
(nonexistent Match.platform and duplicated played keys); next 20 passes/one stale platform
fixture mutation. Corrected to actual asset metadata. Initial native seed lacked the new
result's required baseline membership; corrected fixture and final rehearsal passed.
No product gate or assertion was removed to make those checks pass.

Main publication and actual Linux/full-suite, Chromium, Docker/max-profile, Terraform,
audit and application-container CI are pending. No Docker execution is claimed locally.

Real prospective cohort, source/decoder bias, session independence, effect/retention,
powered broader study, expert/player usability and G5/G6 remain NOT_RUN. Local fallback
cannot supply trusted decoder identity; actual isolated decoding pins it. No endpoint,
dependency, provider, recognizer or hosted release activation.
