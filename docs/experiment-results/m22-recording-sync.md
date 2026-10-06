# M22 recording sync qualification

Date: 2026-10-06. Architecture 2.19.0. Scope: local developer preview; final
local checks recorded below; source 60d55ac published; first CI has two failures, corrections under qualification. No supported game/recorder, signed installation,
provider permission, cloud deployment, gameplay recognition or G1–G6 approval.

## Delivered behavior

- Browser session/CSRF pairs a short-lived one-use code; Windows redeems a narrow
  30-day revocable device credential. Owner/device scopes do not authorize account,
  arbitrary upload, history or other-device media access.
- Source GUI starts paused and admits only opted-in completed supported files from
  one nonrecursive folder. Windows share-read locks exclude live writers; reparse/
  root checks, finalized MP4 boxes, bounded media profile and consistent hash prevent
  stability-only admission. No memory/game hooks or replay API access.
- DPAPI stores selected folder, owner/device identity and durable transfer receipts.
  Response loss/restart resumes server-confirmed bytes; quotas, serial chunks,
  Retry-After, backoff, failure caps and terminal byte suppression are explicit.
- M06 integrity/isolated media processing/private playback remain authoritative.
  A synced file first has no invented Match/time/players. Browser confirmation attaches
  existing bytes to the imported UUID under the existing visual review boundary.
- Device revocation, sync/processing withdrawal, recovery/logout-all and restore stop
  late device work. Deletion cannot automatically recreate the same byte copy or
  remotely erase the original PC file. Export excludes credentials and private paths.

## Checks recorded so far

| Check | Actual result |
|---|---|
| Focused PostgreSQL/transfer/attribution suite | Final affected suite 94 passed / one symlink-privilege skip, 38.89s. Initial focused 88 pass retained as dated earlier scope |
| Actual controlled MP4 | Generated black 1080p60 H.264/0.2s, local FFprobe → helper → real PostgreSQL uploads → existing local worker/parser → authenticated byte-range playback; no Match/events. This is synthetic media, not Tekken footage |
| Windows credential/file behavior | Actual current-user DPAPI roundtrip/encrypted-at-rest/tamper rejection and writer-excluding share mode pass locally; Linux CI must skip this Windows-only check |
| New browser flows | Three Edge tests pass: pairing/code privacy/revocation/mobile, attribution without re-upload, remote deletion/original disclosure |
| Full browser regression | Final 57 Edge pass (1.1m) with all recording endpoints mocked; narrow mobile screenshot inspected; no horizontal overflow |
| Static/build | Ruff checks/248 formatted Python files, mypy 35, Django check/schema, production Next build/lint/types and final typecheck pass; seven-job CI YAML valid; 312 local Markdown links and 157 unique valid requirement rows checked |
| Full PostgreSQL/native restore | Initial full 553 pass / one same-transaction mock test failure / seven separate Docker skips (773.65s); corrected interleaving case and final changes pass in affected 93 suite. First source Linux job stopped at platform typing before backend tests; corrected-source complete CI pending. Native dump/restore, guarded forward/reverse/forward, restored device invalidation and pending upload erasure pass; migrations 0022/0023 applied locally |
| Exact latest-main publication/CI | Source 60d55ac [run 37487810089](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37487810089): five jobs passed, Linux typing and production audit failed. Corrected source qualification pending |

Initial scoped SQLite failures identified auth withdrawal error shaping and pytest local
parser settings; fixed before 88 PostgreSQL pass. A new same-transaction mocked revocation
test was corrected to interleave revocation between authentication and service admission,
matching the actual boundary; the corrected case passes in the final affected suite. A final pause-during-local-inspection fence and redirect credential isolation are also tested. Windows symlink privilege is unavailable locally; that check is skipped explicitly, with actual reparse qualification retained as a delivery gate.

## Remaining acceptance

Actual Windows install/update/uninstall/signing and recorder compatibility, independent
desktop/privacy/security review, device resource/network behavior, real supported footage,
approved hosted storage/admission and resource budgets remain M22.07–08. Automatic in-game
replay recording remains M22.09; direct native acquisition/rendering remains X01 unverified.
Live ID metadata still needs M04/M05 usage/credential/schema review. Manual upload is retained.

Run instructions and exact limits: [source helper](../../companion/README.md).
Design: [companion contract](../architecture/recording-companion.md).

The source adds a Windows CI job exercising protected state, exclusive file access and
offline transfer controls. This is regression coverage, not signed installation/real recorder
qualification. Latest main SHA and all seven CI results will be recorded after publication.

A pre-publication manual-copy deduplication repair retains an explicit suppressed server
receipt even when the helper encounters a file first uploaded manually. Existing reserved
or verified manual copies never grant device access to the manual session. Guarded 0023
prevents removal of suppression history; a new-device/deletion regression and native restore
fixture cover the boundary. Updated native dump/restore, migration forward/reverse/forward, device revocation and manual suppression retention pass.

Initial Windows CI artifact confirms **17 passes, zero skips/failures/errors (1.324s)**,
including protected state, writer exclusion and controlled linked-root rejection. Linux
platform typing is corrected using sys.platform guards; explicit Linux/Windows mypy each
passes 35 files. Local final helper/controlled-media suite: 17 pass/one OS privilege skip
(15.91s). Compatible sharp 0.35.5/native libvips and source-map-js 1.2.2 patches clear the
production audit; existing five development audit findings remain tracked. Production build/lint/types and native sharp PNG encoding pass;
corrected-source all-seven CI remains pending; no release gate was bypassed.
