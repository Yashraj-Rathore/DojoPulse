# DojoPulse repository instructions

## Single-branch delivery

The user requires `main` as the only repository branch. Work and publish on `main`;
do not create feature branches or re-enable automated dependency-update PRs unless
the user changes this preference. Keep dependency audits active and review/test
needed patches directly on `main`.

Publish ordinary commits with CI enabled, including final progress receipts. Do
not add `[skip ci]` or equivalent skip instructions to published commits. Monitor
the actual latest `main` commit's checks before reporting publication as verified;
a successful earlier commit does not establish a green check on the current tip.

## Mandatory progress tracking

The user requires a full product milestone/requirements tracker that is updated after **every
implementation**. [PRODUCT_PROGRESS.md](PRODUCT_PROGRESS.md) is the authoritative current
tracker; [docs/progress.md](docs/progress.md) is the chronological implementation log.

- Before implementing a change, read PRODUCT_PROGRESS.md and identify affected requirement IDs.
- After every implementation, fix, migration, integration, UI change or operational change,
  update the affected requirement rows, milestone status, evidence, remaining work and last-updated
  date. Refresh the current-position summary, blockers and next actions where affected.
- Add new requirements with stable IDs and acceptance criteria when scope changes. Reopen
  completed requirements when a regression is discovered. Do not silently drop unmet requirements.
- Append the implementation to docs/progress.md, referencing requirement IDs and recording
  changed files, actual validation, assumptions, blockers and next step.
- Keep architecture/ADRs and docs/decision-log.md consistent when decisions change.
- An implementation is not complete until both progress files are current. Update them in the
  same work/PR; do not defer tracking to another task or ask permission to maintain them.
- Distinguish local/synthetic correctness, real-game validation, permitted live integrations
  and deployed production readiness. Do not mark one complete based on evidence for another.
- Never invent results, approvals, credentials or completion percentages. If tests were not run,
  record that explicitly and label any cited earlier validation with its date/scope.
- Follow PRODUCT_PROGRESS.md's update protocol and preserve the chronological history.

Additional directory instructions remain applicable; read frontend/AGENTS.md before frontend work.
