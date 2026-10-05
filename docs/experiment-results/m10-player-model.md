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

Publication/latest-main CI remains pending. Earlier 61 targeted cases passed in 40.14s;
their scope is superseded by the later focused evidence, not a second full-suite receipt.

Qualifies local engineering only. Proposed thresholds, candidate-window frequency, relative
value/trainability, session independence, expert agreement, real event comparability,
selection/retention bias, user usefulness/accessibility and hosted performance are unvalidated.
Real diagnosis/ranking is code-gated with release_approved=false. No current-build Tekken
facts, reviewer expertise, credentials, consented real participants or successful scientific
gates are inferred from fixture approvals or test counts.
