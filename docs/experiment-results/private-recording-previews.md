# Private recording previews qualification

Date: 2026-10-13. Requirements: M06.01/.02/.05-.07/.11/.12, M13.03/.06,
M15.01/.06, M16.02/.05, M17.02/.03, M19.02. Architecture 2.22.0 / ADR-029 / D044.

## Evidence so far

- Focused PostgreSQL: 24 private-preview cases passed in 43.36 seconds. Covers
  ownership/ranges, source/derivative quota, request identity, stale attempt cleanup,
  cross-pipeline/non-promotion, withdrawal/cancel/delete/expiry, restore prefix sweep,
  ambiguous write retention, rollback guard, controlled GCS body/response contract,
  forged bundle rejection, bounded binary retrieval and actual generated HEVC/VFR.
- Local Edge: three new playback cases passed in 12.8 seconds, including 390px timing
  positions, revoked reads and stable retry/removal. Mobile screenshot visually checked;
  mock metadata/URL is UI evidence, not proof of decoded owner video.
- Local lint, Next 16.3.8 production build, TypeScript, Ruff and mypy 42 files pass;
  Django/schema drift checks pass. Python lock audits and production npm audit pass
  on this date. Known development lint advisories remain separately tracked.

Initial tests exposed a missing PostgreSQL test transaction and missing browser
authentication fixture; both corrected. Additional stale-write fencing and UI
refresh suppression were implemented and rechecked. Earlier Oct 12 normalization
CI remains separately dated; it does not qualify this new module.

Broad local PostgreSQL run: 645 passed, 15 platform/Docker skips in 867.25 seconds
(660 collected cases). This run preceded the final shape/unknown-asset sweep additions;
the final focused rerun supplies that separate coverage. Running both against the same
temporary test database initially caused cleanup collisions; the rerun is sequential.
All 60 Edge checks pass (1.4m); final preview/upload fixture/layout checks also pass
seven cases in 26.5 seconds. Native PostgreSQL dump/restore, migration roundtrip,
quarantine/repeated control replay and explicit private-preview/pending-upload erasure
pass, including the updated bounded namespace sweep. Actual production RPO/RTO unmeasured.
Current npm audit confirms five high development-only findings; production audit zero.

Owner backend trial completed in 334.719 seconds: verified resumable transfer followed
by trusted-local conversion and private API delivery in an isolated validation account/
database. PREVIEW_READY retains 9,363 frames, 68 large gaps, 1,403 irregular intervals,
158.516667 seconds and max gap 333.332ms. Original/source copy hashes match; actual
derived artifacts total 497,481,471 bytes. Private range delivers 4,096 bytes/206,
foreign account gets 404, first timing page exposes 100 of 1,403 intervals. Zero
Match/GameplayEvent rows and all gameplay/canonical/scientific approval remain false.

Actual owner derivative decodes at 1920x1080, 158.516667 seconds, readyState 4/no
media error in Edge's website player (7.6s check, three bounded range requests).
Its UI authentication/range route is mocked; actual backend ownership/range semantics
were checked separately above. Private rendered screenshot inspected, retained outside
git. Initial ad hoc browser fixtures omitted unrelated history/model fields; reusing
the existing complete fixtures corrected those harness errors.

Final focused PostgreSQL: 26 passed in 41.07s after sequential rerun. Real Docker CI and ordinary main/exact-tip publication remain
underway; no hosted or current-commit CI success claimed before completion.

## Evidence boundaries

Synthetic bundle-shape tests deliberately use non-video bytes; the separate actual
generated HEVC/VFR case executes FFmpeg and verifies source preservation, 29 frames,
one gap, private ranges and empty canonical contribution. Four new Docker cases
exercise the actual preview profile, full binary retrieval, malformed input and
revocation; local Docker daemon is absent, so these need actual Linux CI execution.

The original owner capture is `capture-2026-10-12-01`; its private source, credentials,
paths, identities, checksums, outputs and screenshots are excluded from git. Its
earlier trusted-local normalization preserved 9,363 timestamps/AAC and all 68 large
gaps / 1,403 irregular intervals. The current trial uses an isolated validation
database/account and explicitly trusted-local decoder; it cannot establish the
owner's product-account binding, hosted isolation, automatic acquisition, match
attribution, uninterrupted normal-speed replay or scientific gate approval.

M06.11 remains PARTIAL for actual hosted qualification; M06.12 local/controlled
acceptance awaits completed evidence. G1-G6 remain NOT_RUN, M22.13 browser ID-to-private
video remains BLOCKED, no live GCS/cloud preview/game provider has been enabled.

## Initial publication failures and corrected local checks

Initial source a586914 / run38421395882 failed Linux mypy's inferred file-handle
Popen overload and one asynchronous cancellation locator (59/60 Chromium passed).
Corrected with integer descriptors and a specific completion-status wait; no checks
or resource/revocation limits disabled. Review also fixed finished-request resurrection:
old receipts stay idempotent; fresh attempts get new IDs/runs after terminal conversion.
Added backend/browser regression cases. Final local27 PostgreSQL/37.42s and explicit
Linux/Windows mypy42 pass; corrected full source CI is still required. Earlier counts
above retain their dated/tree scope. M06.12 remains in qualification.

Corrected final local preview/upload browser suite:8 passed in30.0s; lint/TypeScript pass. No browser/backend assertion removed.
