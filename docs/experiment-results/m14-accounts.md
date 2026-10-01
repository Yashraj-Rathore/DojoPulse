# M14 local account qualification

Implementation dates: 2026-09-30 through 2026-10-01. Requirements: M14.01–M14.06,
M13.06; remote M15 result receipt also updates M19.02. Architecture 2.6.0 / D025.

## Scope and observed results

- PostgreSQL 17 on the workspace-only loopback port 55432; Python 3.12/Django 5.2.
  The final 2026-10-01 regression run passed **232 tests** in 49.03s, with seven opt-in Docker
  tests skipped. This includes all **23 account tests**, the locked-password deletion check and
  mailbox-cleanup race regression. Ignored local receipt: `private_data/m14-pytest.xml`.
- New account tests exercise inactive/non-staff signup, normalized email, one-use/expired/
  wrong-purpose/password-invalidated challenges, generic replies, anonymous CSRF, public and
  per-owner limits, real cookie-session revocation, reset/password/email changes, disabled
  account handling, consent idempotency/withdrawal, stale worker publication, upload admission,
  explicit re-linking/suppression, private export, mail purge failure/retry, legacy consent
  migration and PostgreSQL concurrent verification with one winner. Additional regressions check
  deletion with a stale pre-reset User instance and cleanup during an uncommitted registration.
- **14 Edge browser tests passed** on 2026-10-01 (19.8s), covering the existing workspace
  journeys plus registration policy confirmation, generic recovery, reset-link fragment removal,
  explicit submit, session revocation, consent confirmation, email change and explicit re-linking.
  API responses in these browser tests are mocked; real persistence is tested by PostgreSQL tests.
- Next.js production build, ESLint and TypeScript passed on 2026-10-01. Ruff check/format and
  mypy passed (23 typed analysis/tool/provider modules; backend is tested, not claimed fully typed).
- Django system checks and migration drift checks passed; migration 0008 is applied to local
  development PostgreSQL. Its schema was also applied to the test database and its legacy
  backfill behavior checked. It does not mark legacy emails verified or fabricate policy versions.
- Mobile recovery and desktop account-control screenshots were inspected. A focused-input
  outline initially touched its label; scoped spacing was adjusted and browser/build checks
  rerun. Screenshots are ignored local artifacts at `frontend/test-results/m14-*.png`.

The prior M15 GitHub run [36729960773](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/36729960773)
finished successfully in all four jobs (Python/PostgreSQL, frontend, media-sandbox, dependencies),
confirmed 2026-09-30. This is evidence for published M15 commit `1771eba`, not for unpushed M14.
The seven local Docker tests and advisory scans recorded in the [M15 report](m15-security.md)
were not rerun for this account-only change. No dependencies or parser implementation changed.

## Interpretation and limits

These results establish local software behavior only. Registration/email challenges require DEBUG
and the opt-in local flag. Delivery writes a private test mailbox; no external email was sent.
No provider endpoint was enabled, no real player was enrolled, no cloud resources/credentials were
provisioned and no production/legal policy acceptance was invented. Browser checks are not a
manual assistive-technology study, cross-browser qualification or hosted end-to-end test.

Local PostgreSQL had stopped between sessions and was restarted through the project script;
the stalled test invocation was cancelled, then rerun successfully. The system database was not
altered. Earlier tests caught a missing explicit restart path for cancelled imports; fixing it
retains capacity checks, fences and deleted-source suppression. Two browser assertions were
updated for the added re-link field and scoped status notices; product failures were not hidden.

Remaining gates: production mail/recovery/abuse and pending-registration expiry, reviewed terms
and retention, privileged-auth policy, hosted media/export authorization, suppression-key rotation
and alias policy, managed backups/restore/provider erasure, independent security/privacy review,
repository access and possible prior execution of the removed remote config payload. M14 stays
PARTIAL for its hosted exit condition; available local engineering is implemented.

## Publication follow-up — 2026-10-01

M14 `e569bbc` was pushed to main. The initial remote dependency job caught
[GHSA-vcvr-r3jv-pc5j](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j) in Next.js 16.3.5;
Python/PostgreSQL and frontend jobs passed. The targeted fix pins Next.js to patched 16.3.6.
Fresh local npm install/production audits report zero vulnerabilities, build/lint/type checks pass,
and 14 Edge tests pass in 21.5s. This dependency change supersedes the earlier statement that no
dependency changed during the core M14 implementation. The new remote run remains pending;
this local receipt does not yet claim an entirely green publication pipeline.
