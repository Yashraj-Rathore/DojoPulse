# M22 recording sync qualification

Date: 2026-10-06. Architecture 2.19.0. Scope: coherent local developer-preview engineering
qualified on source 7635a3c161d8614b91dcb75e1035ee6b524617db. All seven
[CI jobs](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37488902056) passed,
completed 15:47:52 UTC. Final ordinary receipt retains exact latest-tip monitoring. No supported game/recorder, signed installation,
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
| Windows credential/file behavior | Actual current-user DPAPI roundtrip/encrypted-at-rest/tamper rejection, writer-excluding share mode and controlled linked-root rejection pass. Dedicated Windows CI: 17 pass/no skips (1.358s); platform-specific Linux skip is exercised here. Signed delivery/broader real device compatibility is separate |
| New browser flows | Three Edge tests pass: pairing/code privacy/revocation/mobile, attribution without re-upload, remote deletion/original disclosure |
| Full browser regression | Local final 57 Edge pass (1.1m), narrow mobile screenshot inspected/no overflow. Exact-source CI 57 Chromium pass (58.5s) |
| Static/build | Ruff checks/248 formatted Python files, mypy 35, Django check/schema, production Next build/lint/types and final typecheck pass; seven-job CI YAML valid; 312 local Markdown links and 157 unique valid requirement rows checked |
| Full PostgreSQL/native restore | Exact source: 557 PostgreSQL/Python pass (580.176s), eight skips (seven Docker plus one Windows-specific check exercised by separate jobs). Native dump/restore, guarded forward/reverse/forward, restored device invalidation, manual-copy suppression retention and pending upload erasure pass; migrations 0022/0023 applied locally. Actual hosted RPO/RTO not measured |
| Source publication/CI | Corrected source 7635a3c [run 37488902056](https://github.com/Yashraj-Rathore/DojoPulse/actions/runs/37488902056): all seven jobs successful, watcher exit 0. XML/logs downloaded and checked; remote source head/only-main inventory match. Final ordinary receipt requires actual latest-tip monitoring |

Initial full local backend run: 553 pass/one mocked same-transaction revocation failure/
seven separate Docker skips (773.65s); corrected the interleaving test, then final affected
and exact-source complete CI pass. This earlier run is not described as a full pass.

Initial scoped SQLite failures identified auth withdrawal error shaping and pytest local
parser settings; fixed before 88 PostgreSQL pass. A new same-transaction mocked revocation
test was corrected to interleave revocation between authentication and service admission,
matching the actual boundary; the corrected case passes in the final affected suite. A final pause-during-local-inspection fence and redirect credential isolation are also tested. Windows symlink privilege is unavailable locally; that local check is skipped explicitly, but the controlled linked-root case passes in actual Windows CI. Broader real reparse/device acceptance remains a delivery gate.

## Remaining acceptance

Actual Windows install/update/uninstall/signing and recorder compatibility, independent
desktop/privacy/security review, device resource/network behavior, real supported footage,
approved hosted storage/admission and resource budgets remain M22.07–08. Automatic in-game
replay recording remains M22.09; direct native acquisition/rendering remains X01 unverified.
Live ID metadata still needs M04/M05 usage/credential/schema review. Manual upload is retained.

Run instructions and exact limits: [source helper](../../companion/README.md).
Design: [companion contract](../architecture/recording-companion.md).

The source adds a Windows CI job exercising protected state, exclusive file access and
offline transfer controls. Actual Windows regression is green; signed installation/real
recorder qualification remains separate. The source is qualified above; the final ordinary
receipt is also monitored on its exact latest main SHA before handoff.

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
corrected-source all-seven CI is green, with no release gate bypassed.

Downloaded source artifacts verify 557 backend passes/eight separately exercised platform
and Docker skips, 17 Windows/no skips and seven actual Docker/max-profile/no skips
(123.229s). Completed logs verify 57 Chromium (58.5s), three Terraform mock contracts,
both Python lock audits and zero production npm findings, static/build/type/schema/
contracts, unprivileged application startup and HTTP asset bytes, and guarded native
recovery. The first source 60d55ac failed Linux typing and the sharp/source-map-js audit;
7635a3c corrects both and passes. M22.02-06/.10 DONE means local engineering only;
M22 remains PARTIAL. Next: M22.07-08 Windows distribution, real recorder/device/privacy
and resource/hosted acceptance; provider/gameplay gates are retained.
