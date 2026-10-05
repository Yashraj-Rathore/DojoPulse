# M08 local dataset qualification

2026-10-05. Architecture 2.12.0. Scope: local synthetic engineering,
not a real golden dataset, Tekken frame facts, recognition approval or hosted release.

Requirements M08.01-M08.07, M07.05, M09.04, M12.02, M14.04/.05,
M15.01/.06, M16.05, M18.07, M01.05/.06 and M19.02.
[Contract](../architecture/dataset-operations.md), [ADR-020](../adr/ADR-020-versioned-dataset-operations.md).

Implemented governed collection/study pins, dataset-wide keyed split/source assignments,
freeze/blinding, independent timing/adjudication, content-hashed snapshots and coverage/
session/timing/prediction QA. Portable validation preserves legacy file manifests and
never claims current byte/permission verification. Exact-source canonical operator
import pins measurement/snapshot hashes; withdrawal erases private receipts and removes
active derived contributions without rewriting original captures. Local UI, account
export, guarded migration 0018 and native restore erasure are included.

Final local qualification:

- Full PostgreSQL suite: **394 passed, seven separately gated Docker tests skipped**,
  274.99s. JUnit reports/m08-python-final.xml records 401 cases, zero failures/errors.
  All 23 M08 tests are included: definition/scope pins, blind freeze, sparse/negative/
  adverse categories, independent timing/adjudication, null timing, original split/source
  assignments after withdrawal, unchanged generation/platform, retired history, revoked
  grants, exact owned canonical import, guarded rollback and PostgreSQL concurrent
  import-versus-foreign-reviewer withdrawal. The race finishes with no live contribution.
- All **35 Edge journeys** passed in 34.8s after the Strict Mode fragment fix. Production
  build, TypeScript and ESLint pass. Inspected 390px mobile screenshot shows category/
  uncertainty warnings, readable receipt hashes and visible keyboard focus without overflow.
- Ruff/format/mypy, Django/schema checks and local documentation links pass. Both pinned
  Python-lock audits and production npm audit find no known vulnerabilities.
- Final native PostgreSQL rehearsal passes fresh forward/reverse/forward through 0018,
  actual pg_dump/restore, repeat signed control replay and private dataset/pending-upload/
  knowledge erasure. It asserts closed erased collection grants, empty invalidated
  snapshot JSON and removed keyed partitions. The seed tests private storage erasure,
  not an approved dataset. Verified-empty local M08 tables were also safely round-tripped
  to synchronize the completed additive schema; no existing dataset history was removed.
- M08.07 is locally DONE. Direct main publication and actual latest-tip six-job CI pending;
  remote still verified sole main at 7b1fd81 before publication. Docker/max-profile,
  Terraform and application-container qualification will run in CI, not Windows locally.

No gate was weakened. Real permission/protocol/participants, representative source and
success/failure/negative/uncertain labels, qualified reviewers/adjudicator, independent
held-out and frame accuracy evidence, external retained-copy erasure, hosted scale and
G1-G6 remain unrun. Known dev lint advisory and source-access review remain tracked;
no dependency/provider/release flag was changed.
