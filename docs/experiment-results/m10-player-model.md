# M10 local diagnosis and priorities qualification

Date: 2026-10-05. Architecture 2.13.0. Dataset scope: synthetic software fixtures.
Real expert/player diagnosis and utility validation: NOT_RUN. G1-G6: NOT_RUN.

Requirements: M10.01-M10.07, M07.05, M13.05/.07, M14.04/.05,
M15.01/.06, M01.05/.06 and M19.02.

Implemented the coherent local M10 engineering module: current canonical projection,
exact context/version/platform/scope buckets, versioned proposed sample/coverage/review
thresholds, independent-review diagnosis states, explicit governed drill value/trainability
assessments, transparent bounded research ranking, private timestamp/count/uncertainty cards,
separate recorded-result and monthly gameplay histories, scope filters, current-grant
withdrawal serialization, reanalysis deduplication and failed-read UI clearing. No migration,
new private data cache or provider/recognizer/hosted activation is introduced.

Actual local validation:

- Initial full PostgreSQL suite: 422 passed, seven separately exercised Docker skips,
  238.22s; JUnit records 429 cases, zero failures/errors. This run includes governed assessment approval but preceded the later
  dataset read-race test and final query/fingerprint refinements.
- Final focused PostgreSQL run: 82 passed, 150.99s; covers diagnosis, governed assessment
  approvals/revocation, M08 canonical grant removal and actual read/foreign-reviewer
  withdrawal serialization. Final query-bound refinement: all 28 M10 cases passed in 13.12s; zero failures/errors/skips.
- Full browser suite: 40 passed in local Edge, 36.6s, including five new diagnosis journeys.
  Inspected the 390px mobile screenshot; no overflow and hash/unknown/score explanations
  remain readable. This is browser software qualification, not real-device/screen-reader
  or participant usability acceptance.
- Production Next build, final ESLint/TypeScript, Ruff/format (204 files), mypy (25
  modules), Django checks/no pending migration, nine documents' local links and diff
  whitespace checks passed. No dependency changes; current audits and actual Docker,
  Terraform, container startup and native recovery are independently exercised in CI.

Implementation main publication and all six CI jobs are verified below; this final progress receipt retains ordinary CI and its actual latest-main checks are monitored before handoff. Earlier 61 targeted cases passed in 40.14s;
their scope is superseded by the later focused evidence, not a second full-suite receipt.

Qualifies local engineering only. Proposed thresholds, candidate-window frequency, relative
value/trainability, session independence, expert agreement, real event comparability,
selection/retention bias, user usefulness/accessibility and hosted performance are unvalidated.
Real diagnosis/ranking is code-gated with release_approved=false. No current-build Tekken
facts, reviewer expertise, credentials, consented real participants or successful scientific
gates are inferred from fixture approvals or test counts.


## Verified main implementation

Published **687f0f21dc1e888afcffbad03c17ef577bd5dc56** directly to main without force.
All six [CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37338207922)
passed first attempt at **2026-10-05 16:10:57 UTC**:

- 424 PostgreSQL/Python passes; seven Docker cases separately skipped here. Downloaded
  JUnit: 431 cases, seven skips, zero failures/errors, 148.667s.
- Seven Docker/max-profile passes; zero skips/failures/errors, 110.163s JUnit.
- 40 Chromium browser journeys, 42.5s; three Terraform mock tests, zero failures.
- Native synthetic PostgreSQL forward/reverse/forward guarded migration, real dump/restore,
  control replay before reads, repeated replay and pending-upload erasure passed. Existing
  dataset/knowledge restore erasure remains exercised; production RPO/RTO is NOT_MEASURED.
- Both Python lock and production npm audits, Ruff/format/mypy, Django/schema/loader,
  frontend lint/typecheck/build and unprivileged API-quarantine/web startup passed.

Exact check-runs API confirms six completed successes and branch API confirms main is
this code SHA before the final receipt. Only main remains; final receipt uses no CI skip.
M10.07 is DONE for local engineering; M10.03-.06 and the milestone remain PARTIAL for
actual expert/utility/comparability and release qualification. Real G1-G6 remain NOT_RUN.
No live provider, actual recognizer, cloud deployment, training or real diagnosis enabled.
