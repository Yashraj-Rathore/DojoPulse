# M16 engineering qualification — 2026-10-02

Scope: local PostgreSQL 17, synthetic recovery, injected Google clients and
deployment preparation. No Google credentials/resources, real game captures,
permitted live provider, hosted upload or production acceptance.

Implemented requirement coverage: M16.01–M16.06 foundations; M14.05 restore
controls; M15.06 dispatcher/storage/worker failure injection; M19.02 CI expansion.
All M16 rows remain PARTIAL until their hosted acceptance criteria pass.

Actual checks to date:

- Full local Python/PostgreSQL suite: **253 passed, seven opt-in Docker tests
  skipped, 72.64 s** before the final signed-checkpoint addition. Final full-suite
  revalidation is pending; do not substitute this count for a later result.
- Ruff check/format, mypy (23 files), Django check and migration-drift checks passed;
  migration 0009 applied locally.
- Native pg_dump/pg_restore rehearsal passed migration forward/reverse/forward,
  post-backup account/asset/match deletion and withdrawal, repeat replay and 503
  quarantine checks. Production recovery objectives remain NOT_MEASURED.
- Terraform 1.15.7 with signed Google provider 7.46.1: fmt/validate and **three
  mocked plans passed**. Cross-platform provider checksums recorded. No real plan
  or apply was executed.
- Next 16.3.6 lint, production standalone build and typecheck passed; **14 Edge
  journeys passed in 22.1 s**. Fixtures mock API responses; one background provider
  fetch logged ECONNREFUSED while the Django server was absent.
- Optional pinned cloud dependency audit: no known vulnerabilities reported.
- Local Docker daemon was unavailable in this turn; fresh sandbox/container
  evidence awaits remote CI. M14's seven Docker checks remain historical evidence
  from 2026-10-02 verification, not a new M16 result.

Fault checks cover transactional outbox rollback, retry exhaustion, duplicate
worker/task entry, ambiguous launch without resubmission, retained physical
capacity, terminal stop observations, lease/deadline/fence guards, authenticated
payload shaping, bounded generation-pinned downloads, all-version purge,
arbitrary resumable URL rejection, failed journal writes and tampered/missing
control records. They use controlled clients, not an observed Google response.

Remaining hosted acceptance:

- Region, project/account, cost/privacy decision, billing alerts and RPO/RTO.
- Equivalent qualified media sandbox; independent hard stop/deadline and identity
  review. Nested Docker in Cloud Run is unsupported.
- Current replicated controls and checkpoint freshness, stable-key recovery,
  maximum journal scale and actual backup/retained-copy deletion policy.
- Cloud IAM/TLS/SQL/secrets/health and same-origin web routing; OIDC, operation
  receipts, cancellation, ambiguous-runtime inventory and outage tests with staging.
- Hosted ingress, resumable cancellation/late finalization, owner playback/range
  tests, GCS generations/version erasure and total memory at maximum media profile.
- Applicable source-integrity, privacy/security, provider and scientific release
  decisions. No approval or credential was fabricated.

Final local revalidation after signed checkpoint hardening: **254 passed, seven
Docker checks skipped, 67.22 s**; mypy passed again. The 22 M16 tests independently
passed after hardening, and native PostgreSQL recovery/replay passed again. Remote
publication and fresh Linux container/sandbox receipts remain pending.

Final execution-stop review added a managed-worker regression: publishing a report
does not release its hosting execution slot. The complete local suite then passed
**255 tests, seven Docker skips, 59.59 s**. Native recovery, static/system/migration
checks and documentation links passed on the final command/configuration changes.
