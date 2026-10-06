# M22 browser-only replay acquisition preparation

Date: 2026-10-06. Architecture 2.20.0. Scope: offline feasibility evidence tooling and
browser-only product priority; **not an implemented acquisition transport or real replay proof**.

Requirements: M22.01/.09/.11-.14, M13.10, M01.05 and M19.02.
Decision: [ADR-027](../adr/ADR-027-browser-only-replay-acquisition-feasibility.md).
Contract: [bounded procedure](../architecture/replay-acquisition-feasibility.md).

## Actual acquisition result

The computer-use skill and guidance were read. Importing `@oai/sky` succeeded, but
`sky.list_apps()` returned `Computer Use native pipe is unavailable: failed to connect
native pipe: The system cannot find the file specified. (os error 2)`.
No game window selected, game started, inputs sent, endpoint called, recorder installed,
public/private replay acquired or gameplay recording created. Exact installed build and PC
playback of a console player's public replay remain unverified. No usage acceptance obtained.

Public source/EULA/official v3.02.01 replay-invalidation notes rechecked. The community
recorder's already-downloaded-replay prerequisite remains a distinct acquisition gap; source
availability/game ownership establishes no managed-service grant. This research does not
close M04/M05, M22.09/.13-.14 or X01. No provider was contacted or activated.

Initialized private `private_data/replay-acquisition/plan.json` and ran the real CLI against
that empty evidence directory, with native control UNAVAILABLE. Report
`reports/replay-acquisition-final.json`, assessed **2026-10-06 16:38:21.361782 UTC**:

- Plan hash: `2622ae0c749258c40f70f25e1c087295549fc9a74b0bd98e4b0d730b425300e9`.
- Report hash: `bbb7f09e13267560dbfb1109940a9ea217931bb995c9725ad318681f337bb5da`.
- **Zero artifacts, trials, real/synthetic trials, first-replay candidates and console candidates**.
- First-replay evidence NOT_RUN; technical/usage review, native control, console, rate and
  cost gaps present; all eight fault-control checks NOT_RUN.
- Runtime, current permissions, real game semantics, media profile, current backend delivery
  and release approval all false; scientific gates NOT_RUN.

The initialized plan/report contain no personal player ID or game credentials and remain
ignored local artifacts. No synthetic attempt is presented as actual Tekken progress.

## Local software checks

Initial focused test collection found a decorator syntax typo; corrected before qualification.
Initial 54 acquisition/ingestion checks pass in 1.40s. Expanded provider-boundary run passes
82 in 1.51s, then linked-ancestor evidence protection/non-promotion checks were added and
the final affected suite rerun: **82 passed / one local Windows symlink-creation privilege skip in 1.45s**. Linux source CI will exercise the latter; no actual-game tests ran.

Meaningful controlled cases cover manual/already-downloaded-only capture, synthetic/unknown
platform/origin, future/expired observations, incompatible builds, captured/delivered hash
mismatch, missing lookup evidence, total timeout/retry ceilings, failed/absent denominators,
review purpose/expiry, USER_UPLOAD fallback, traversal/checksum corruption/non-finite JSON,
non-promoting complete declarations, redacted output and create-only CLI files. Linux CI will
cover actual symlink/root-ancestor rejection where local Windows lacks creation privileges.
Fixture bytes are intentionally synthetic and do not validate a playable video or real backend.

Ruff full repository check and 253-file formatting pass; explicit Linux/Windows mypy each
passes 37 source files. No runtime schema/API/frontend/dependency changes were made.
Current controlled qualification preserves the existing provider operation gates and contains
no network/game/ORM mutation. Document/link/tracker validation and main publication checks
are recorded below; prior runtime qualification remains dated in
[the recording-sync receipt](m22-recording-sync.md).

## Remaining work

M22.11 is the accepted design; M22.12 is the preparation tooling only. Complete technical
and usage review and restore supported native game control, then demonstrate M22.13 with
actual evidence. M22.14 requires console-through-PC, licensed/permitted managed runtime,
fault controls and measured limits/cost before hosted operation. M13.10 remains blocked.
Only then implement an actual adapter and browser acquisition queue/progress/retries.
The qualified companion/manual upload remain fallbacks, not required customer setup.

Local documentation validation passes: 336 local Markdown links, 174 unique requirement IDs
(162 milestone requirements plus 12 optional), status/table cells and Architecture 2.20.0
consistency; git diff --check passes. Main source publication/ordinary exact-tip CI next.
