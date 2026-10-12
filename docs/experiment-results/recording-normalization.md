# Source-preserving recording normalization qualification

Date: 2026-10-12. Architecture 2.21.0; ADR-028/D043. Requirements M06.01/.05/.09/.10/.11,
M22.07/.13, M15.04 and M19.02. Scope: trusted local operator media engineering; no hosted
normalization, automatic acquisition, canonical publication or scientific approval.

## Implemented scope

Versioned policy, provider-independent normalization/timing primitives and private CLI create
a new H.264 preview, hashed full source/derivative timestamp map and provenance/quality report.
Source snapshot/checksum, file-only protocols, two threads, bounded process/output size,
create-only destination and owned failure cleanup preserve the original. Every decoded frame
is compared; AAC packet payloads/counts/timestamps and color declarations are verified.
All semantic/scientific approval flags remain false. Strict worker admission was not relaxed.

41 focused tests passed in 43.48s; two Windows symlink-creation tests skipped because the
host lacks that OS privilege. This includes existing five media tests plus 38 new normalization
cases. Actual synthetic HEVC/H.264, full-range color, shifted nonzero PTS, missing-frame gaps
and AAC conversions preserve frames/timestamps, while altered source, count, time, audio,
color, unsupported media, oversize, timeout/partial-output cleanup and private error handling
fail safely. Linux CI must separately execute actual file/ancestor symlink checks.

Full local PostgreSQL regression: 619 passed/11 skipped in 1075.44s (seven real Docker tests
not enabled, four Windows file/ancestor link privilege skips). Final focused tests additionally
cover the final CLI/report changes; no subsequent backend behavior changed. Static checks,
262 formatted Python files, mypy over 40 files, Django checks and no migration drift pass.
No schema/HTTP/worker/storage/UI route changes were made for normalization.

## Actual owner footage

The selected official Steam export is the private capture alias `capture-2026-10-12-01`;
see [initial inspection](../research/replay-capture-evidence-2026-10-12.md). It was normalized
under the same versioned policy. Raw paths, participant/account identifiers, video, checksums,
preview PNGs and full private reports are excluded from public git.

| Actual check | Result |
|---|---|
| Source | HEVC, 240,556,903 bytes, 1920 x 1080, 158.516667 seconds |
| Derivative | H.264, 496,940,978 bytes, same dimensions/duration; below 512 MiB limit |
| Decoded frames | 9,363 before and after; no duplication, interpolation or dropping |
| Presentation timestamps | Every timestamp preserved; maximum measured error 0 microseconds |
| AAC | Packet count/payloads preserved; maximum PTS/DTS/duration error 0 microseconds |
| Color | Full-range BT.709 declarations preserved |
| Timing quality | 68 gaps above 25 ms, maximum 333,332 microseconds; 1,403 total intervals outside the declared 1 ms period/25 ms gap policy, including those 68 gaps |
| Timeline/quality provenance | Complete vectors hashed; all unknown intervals preserved; original checksum unchanged |
| Encoding observations | 265.20 seconds wall, 356.66 observed CPU seconds, 304,640,000-byte observed peak RSS; complete normalization 433.92 seconds |
| Visual sampling | Output PNGs at 65/110 seconds viewed; changing game scenes and HUD/input/frame/status overlays remain visible; not a complete semantic/continuity audit |
| Approval | PREVIEW_READY only; strict timing/average-rate profile still fails; canonical/scientific/precise-gameplay approval false |

The first whole-video invocation failed safely and removed partial outputs. The old CLI
returned a general redacted error, so its exact failing check was not retained; do not infer
the cause. Added allowlisted error diagnostics and an explicit bounded 900-second local
encoder ceiling. The measured retry completed, with source and derivative full scans,
unchanged source and zero measured timing error. This is local performance evidence on one
owner clip, not an SLA, representative capacity/cost study or all-input guarantee.

The video remains outside the provisional Jin/Jin target. Re-encoding is lossy; matching frame
counts/timestamps does not claim pixel equality or verify moves, cuts, pauses, takeover,
match completion, exact build attribution or detector calibration. No M06 backend admission
or authenticated website preview was performed. M06.11 tracks that remaining delivery scope.
M22.13 remains BLOCKED; this manual owner export is not a browser-only ID acquisition trial.

## Security patch and publication

The current production audit found new Next.js advisories in locked 16.3.6. Applied verified
same-minor Next/eslint-config-next 16.3.8 and retained existing reviewed transitive patches.
Production npm and both Python lock audits return zero known findings. Five existing braces
development findings remain tracked in the [security runbook](../operations/security-runbook.md).
Read frontend instructions/version-matched guides; lint, production build, typing and all 57
Edge browser checks passed (1.3m). No product UX changed and no scanner suppression used.

Implementation is prepared on main; publication/exact-tip CI pending. The prior Oct 6 seven-job
CI remains dated evidence for prior code. Ordinary CI, including Linux/PostgreSQL, Docker,
Windows, browser, audit, container and Terraform checks, must verify the new published tip.
