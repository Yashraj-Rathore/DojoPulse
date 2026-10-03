# M06 storage qualification

Date: 2026-10-03. Architecture 2.10.0, ADR-018 / D030, migration 0016.
Scope: local synthetic engineering and controlled official GCS client contracts.
Actual GCS, hosted release and real-game capture/attribution: NOT_RUN.

Delivered durable owner-scoped upload sessions and expected-byte reservations,
bounded exact-offset LOCAL chunks, official GCS create-only initialization and
observed progress, background full-byte SHA-256/MD5/size/generation verification,
private range playback, resumable/pause/refresh/cancel UI, target-match/account/
consent/expiry cleanup and conservative post-backup capability-expiry erasure.
Canonical Match/source/run creation happens only after byte verification; imported
recordings still require attribution review and independent gameplay publication.
Neither a checksum nor a continuous-capture checkbox establishes real gameplay.

Local checks:

- Full PostgreSQL checkpoint: 336 tests passed in 97.64s; seven Docker isolation
  checks skipped locally because no qualified image was configured. Initial full
  regression found three missing Accept-Ranges headers on 416 responses; fixed
  without weakening assertions. Final four schema-drift/crashed-verifier cases
  passed with the 34-test upload collection in 12.69s. That selected run reported
  two database-teardown warnings. Final complete run: **340 passed, seven skipped
  in 92.29s**, with no teardown warnings; XML retained at reports/m06-pytest.xml.
- 25 Edge browser journeys passed in 25.7s, including actual browser incremental
  SHA-256/MD5, lost response, confirmed offset resume, refresh with the same receipt,
  delayed verification, cleanup failure/404 receipt clearing and GCS requests with
  app credentials omitted. Mocked GCS browser transfer is not actual CORS evidence.
- Frontend lint, production build and TypeScript passed. The 390px mobile recording
  form/integrity-progress screenshot was visually inspected; no overflow. Earlier
  browser failures were ambiguous form/Next-announcer selectors and a test-file
  BOM encoding issue; corrected without dropping cases.
- Native PostgreSQL 17 applied migration 0016. Two disposable loopback databases
  passed migration forward/reverse/forward, actual pg_dump/pg_restore, signed controls
  before reads, pending-upload erasure/checksum clearing and repeat replay. Source
  database was never restored or deleted; production RPO/RTO remains NOT_MEASURED.
- Django system/schema checks, draft contract load, Ruff check/format (184 files),
  mypy (23 source files) and diff whitespace checks passed at the recorded checkpoint.
- Both pinned Python locks: no known vulnerabilities. Production npm audit:
  zero vulnerabilities. Full dev npm audit separately has five high findings through
  unpatched braces GHSA-vfj7-8cjw-p6xm in the trusted lint glob chain; upstream patch
  is tracked in M15.04/security runbook. No suppressed advisory, forced downgrade,
  production-audit weakening or dependency-update branch was introduced.

The new upload tests include real PostgreSQL competing admission/repeated chunks
and cancellation during verification; stale verifier completion; cross-owner/CSRF;
size/type/consent/claim rejection; duplicate/incomplete/conflicting chunks; checksum
failure without canonical publication; quotas held through failed purge; expiry,
withdrawal and account/target-match deletion; imported metadata revision changes;
provider retries/shape drift; crash budget; fixed upstream URL and cancellation
contracts; generation/range byte bounds/stream closure; restore of unknown session
deadlines; and reversal requiring physical erasure. Existing canonical/provider,
account/pilot/operations/range tests continue to apply.

Official documentation was reviewed for JSON initialization, length/checksum metadata,
256 KiB chunk multiples, 308/probed offsets, one-week expiry, cancellation 499,
content generations and Range behavior; links are in the storage contract. Controlled
clients assert our interpretation. Actual Location/CORS/expiry/late-finalization,
private bucket IAM/version/soft-delete/erasure, independent durable journal and hosted
isolation/load still require dated staging qualification and a reviewed code change.
GCS_STORAGE_QUALIFIED, external uploads and managed media remain false in code.
No live cloud session, object, credential, signed URL or billable service was created.

Publication: ordinary commit on main and exact-head CI monitoring pending. Remote
main was inspected at c5b553ad34f734b974d0a121caeb67b2f15696c1 and only main exists;
no remote rewrite or new Next config payload was found. Previous source-access review
remains open. M06.08 satisfies the defined engineering scope; M06 release remains
PARTIAL, with all real provider/scientific/hosting gates preserved.


## Published implementation CI

[Run 37135033487](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37135033487)
completed SUCCESS at **2026-10-03 16:00:27 UTC**, first attempt, exact main head
**0588ce4cb66a6a8dfff252a2115b684ff0e38afb**. All six jobs passed:
Python/PostgreSQL, media sandbox, frontend, application containers, dependencies
and deployment contracts. Logs and downloaded JUnit corroborate **340 Python tests
in 66.36s**, seven skips separately exercised by **seven Docker isolation/max-profile
tests in 142.07s**; **25 Chromium journeys in 28.2s**; three Terraform mocked tests;
native PostgreSQL container-client migration/dump/restore/pending-upload erasure;
production build/static/schema, both Python locks and production npm audits, and
unprivileged API quarantine/standalone web startup. No retried or weakened gate.

Final review added an owner-locked current-state/consent check after a slow upload
status probe. Controlled cancellation during that probe cannot return the earlier
session capability. **35 focused upload tests passed locally in 9.37s**, Ruff
check/format and diff checks passed. This follow-up and qualification receipt are
published on main with ordinary CI; final handoff requires the actual latest tip's
six checks. The 340-test receipt above belongs to 0588ce4, not the follow-up.
Actual hosted/scientific/privacy/provider gates and the development lint advisory
remain open. No GCS session or external deployment was activated.


## Final code qualification

[Run 37135447719](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37135447719)
completed SUCCESS at **2026-10-03 16:07:03 UTC**, first attempt, exact main head
**1d56929bdc7a5169048128c9e4c069c3220c350a**. All six check runs also independently
report completed success. Final code counts: **341 PostgreSQL/Python tests in
66.30s**, seven skipped cases separately exercised by **seven Docker tests in
130.41s**, **25 Chromium journeys in 25.0s**, three Terraform mock tests, native
recovery/pending-upload erasure and existing dependency/build/static/schema/
unprivileged startup gates. Main is the sole remote branch and the workspace is
clean. No retries, skipped workflow or weakened acceptance assertions.

This final documentation receipt changes only tracker/log/evidence, publishes with
ordinary CI, and requires monitoring its actual latest main checks before handoff.
The qualified code above is unchanged by that receipt. Actual GCS/scientific/hosted
release remains unqualified and the unpatched development lint finding stays open.
