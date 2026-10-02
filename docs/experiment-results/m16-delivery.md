# M16 engineering qualification — 2026-10-02

Scope: local PostgreSQL 17, synthetic recovery, injected Google clients and
deployment preparation. No Google credentials/resources, real game captures,
permitted live provider, hosted upload or production acceptance.

Implemented requirement coverage: M16.01–M16.06 foundations; M14.05 restore
controls; M15.06 dispatcher/storage/worker failure injection; M19.02 CI expansion.
All M16 rows remain PARTIAL until their hosted acceptance criteria pass.

Actual checks to date:

- Final local Python/PostgreSQL suite: **255 passed, seven opt-in Docker skips,
  59.59 s**. Remote PostgreSQL suite: **255 passed, seven skips, 37.41 s**. The
  seven skipped sandbox checks executed in their separate remote Docker job.
- Ruff check/format, mypy (23 files), Django check and migration-drift checks passed;
  migration 0009 applied locally.
- Native pg_dump/pg_restore rehearsal passed migration forward/reverse/forward,
  post-backup account/asset/match deletion and withdrawal, repeat replay and 503
  quarantine checks. Production recovery objectives remain NOT_MEASURED.
- Terraform 1.15.7 locally / 1.16.5 remotely with signed Google provider 7.46.1:
  fmt/validate and **three mocked plans passed**. Cross-platform checksums
  recorded. No real plan or apply was executed.
- Next 16.3.6 lint, production standalone build and typecheck passed; **14 Edge
  journeys passed in 22.1 s**; **14 remote Chromium journeys passed in 15.6 s**.
  Fixtures mock API responses; one background provider
  fetch logged ECONNREFUSED while the Django server was absent.
- Optional pinned cloud dependency audit: no known vulnerabilities reported.
- Local Docker daemon was unavailable. Remote Linux checks freshly passed **seven
  sandbox tests in 148.54 s**, including the maximum capture profile, and built
  both API/web images. Startup checks verified nonroot users, API quarantine/503
  and standalone web HTTP. This is container evidence, not Cloud Run acceptance.

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

Publication: `bbf270411ce6c47e1c5609017bf1c49aa3de38a5` pushed to main.
[CI run 37023337650](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37023337650),
attempt one, completed SUCCESS 2026-10-02 15:00:14 UTC; all six jobs passed.
Both Python locks reported no known vulnerabilities; npm reported zero. The
containerized PostgreSQL 17 client rehearsal passed actual synthetic dump/restore,
migration forward/reverse/forward, controls before reads and repeated replay.
No CI fix/retry or weakened gate was needed. Progress/docs publication receipts
use `[skip ci]` only when code/dependencies/workflow remain unchanged from this run.
