# M07 local knowledge qualification

Date: 2026-10-03. Scope: local synthetic engineering, not real game validation.
Requirements: M07.02-M07.07, M06.02, M11.01, M12.02, M14.04-M14.06, M15.06,
M01.05/.06 and M19.02. See [contract](../architecture/knowledge-governance.md).

Implemented sealed evidence/dependency proposals, blinded independent decisions, immutable
publication, scoped effective approval, lifecycle/privacy, reviewer range playback,
unverified build registration, explicit capture platform, reviewed compatibility, bounded
canonical reanalysis and event knowledge pins. Drafts stay unchanged; real publication and
hosted review remain disabled.

Local checks on 2026-10-03: full PostgreSQL regression **369 passed, seven skipped**
(228.16s) before the final lock-order correction; the restored loader plus targeted
privacy/governance suite **30 passed** (115.06s). Final full lock-order/race qualification
is pending and will be recorded separately. No earlier pass establishes that final change.

All **30 Edge journeys passed** (33.9s), including five knowledge browser cases, retry
identity, CSRF header, independent review, dual-approval publication/withdrawal and patch
abstention/queue controls. Production Next build, lint/TypeScript, Ruff/mypy, Django/schema,
additive migration and idempotent loader passed. Inspected the generated 390px mobile
screenshot; the page stays within viewport width. Browser API fixtures are controlled,
not actual gameplay, permission or screen-reader acceptance.

Both Python-lock audits and production npm audit passed. No dependencies were added.
Existing unpatched dev lint-chain braces finding and source-access review remain tracked.
Native PostgreSQL used fresh UUID databases for forward/reverse/forward migration,
actual pg_dump/restore, repeated signed controls, pending upload purge and M07 restored
release-grant/source/note erasure. Production RPO/RTO and actual cloud erasure are unmeasured.
A rollback guard rejects existing governed history/event pins instead of changing hashes.

Development failures corrected before qualification: missing synthetic drill flags,
test-harness API/JSON normalization, Next effect lint and browser route-announcer selector.
No validation gate was weakened; the existing loader-idempotency test is preserved.
Final audit added withdrawn active-view tombstones and deterministic PostgreSQL worker
claim versus foreign-reviewer withdrawal ordering. All loop/job/publication writes acquire
owner then shared capacity before domain rows. The deterministic race then exposed a
deferred foreign-key COMMIT conflict with the exclusive owner lock. PostgreSQL owners now
use FOR NO KEY UPDATE; both forced race tests passed (2 in 7.93s). Final full suite/recovery
are running. Synthetic account setup uses a fast test-only hasher, with production password
configuration unchanged. Actual latest main publication/CI is pending;
Docker max-profile execution is unavailable locally and must be qualified in its CI job.

Acceptance: approval/rejection/retry identity; assigned-only access/blind review/CSRF;
scope separation/hash tampering; foreign/unvalidated/expired/wrong-platform sources;
retirement/withdrawal; account/consent/source/restore erasure; streamed revocation;
cross-build abstention/stale publication; full synthetic reanalysis/prior hashes/frozen
plans; concurrent PostgreSQL publication/deletion; guarded rollback and native recovery.

Next: permitted exact-build captures and actual independent Tekken experts, with reviewed
rights before a real release decision. All G1-G6 remain NOT_RUN. Provider rights/keys,
actual hosting and M07 factual approval are not established by synthetic receipts.


Final local result: **371 PostgreSQL/Python tests passed, seven Docker/max-profile tests
skipped** in 170.50s after all code corrections. reports/m07-python-final.xml substantiates
the result. Final native recovery also passed after the lock changes. Static/schema/diff
checks pass; prior 30 Edge/build/TypeScript/lint and both-lock/production npm audits remain
current for unchanged frontend/dependencies. M07.07 local engineering acceptance is met;
real/hosted release remains gated. Push and actual latest-tip CI are pending, including
separate actual Docker isolation and application-container qualification.


## Verified publication

Commit **dcda2bdb52fa34ca6ea9adc374bcb8ba79c44276** was pushed directly to main.
All six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37141940752)
passed first attempt at **2026-10-03 17:53:53 UTC**. Artifact/log evidence:

| Check | Actual result |
|---|---|
| PostgreSQL/Python | 371 passed, seven Docker tests skipped separately; 97.291s JUnit, zero failures/errors |
| Docker isolation/max profile | All seven passed, no skips; 140.787s JUnit |
| Frontend | 30 Chromium journeys passed, 34.2s; production build/lint/typecheck passed |
| Deployment contracts | Three mocked Terraform tests passed; actual provisioning unapproved |
| Native recovery | Fresh PostgreSQL migration forward/reverse/forward, dump/restore, repeat controls and source/grant/note/pending-upload erasure passed |
| Dependencies | Both Python locks and production npm audits passed |
| Application containers | Unprivileged API quarantine and standalone web startup passed |

Downloaded JUnit under reports/m07-ci-37141940752 and CI logs substantiate counts;
GitHub API confirms attempt 1 and the exact main head. Only main exists. No gates were
weakened or rerun. Real game/hosting/provider/scientific approval remains absent.
This final documentation receipt retains ordinary CI; monitor its actual latest main
checks before handoff. No code changed after the qualified implementation.
