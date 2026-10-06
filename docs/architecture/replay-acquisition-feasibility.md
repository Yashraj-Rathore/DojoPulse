# Browser-only replay acquisition: bounded feasibility contract

Updated 2026-10-06; Architecture 2.20.0. Decision: [ADR-027](../adr/ADR-027-browser-only-replay-acquisition-feasibility.md).
Status: offline preparation implemented; zero actual replay trials. No game/network adapter,
capture automation, acquisition queue, hosted renderer or new player UI is enabled.

## Required customer journey

Sign in, enter/confirm TEKKEN ID once, choose an available match and Analyze. The service handles
approved retrieval, compatible playback and capture. Customers need no installation, pairing,
folder selection, manual file movement/upload or in-game playback actions. The existing
[companion](recording-companion.md) and [video upload](evidence-storage.md) remain fallbacks.
Do not add a functioning-looking Analyze acquisition button until a real permitted transport exists.

Metadata, native bytes and encoded video are separate capabilities. Preserve the existing
[provider-neutral contract](match-ingestion.md); OFFICIAL, COMMUNITY_PUBLIC_API,
REVERSE_ENGINEERED and USER_UPLOAD have separate purpose-specific reviews. Official in-game
playback lineage does not make an undocumented external interface OFFICIAL. The default
unreviewed client-automation candidate is REVERSE_ENGINEERED with OFFICIAL upstream lineage.
No provider approval is supplied by this document or its CLI.

## Operator study before adapter implementation

1. Record technical and usage decisions for the exact provider/operation/version/runtime,
   permitted test purpose, account/hardware, capture/data rights and expiration. Keep LOCAL_FEASIBILITY
   separate from MANAGED_SERVICE. Review code licensing separately; no community code is reused.
2. On a supported, owned official-client test environment, establish exact in-game build and
   capture profile. Resolve the consented target TEKKEN ID to persistent identity and preserve
   match/participant/external replay assertions privately. Names and capture timestamps are insufficient.
3. Observe a recent public Online Replay, acquire it through a permitted operation, then play it
   on a compatible build. The initial lookup/download must be demonstrated separately from
   recording an already-downloaded replay. Unknown availability and unavailable history are outcomes.
4. After permitted automation is reviewed and implemented, run the full browser request without
   customer desktop steps or manual worker intervention. Record normal original-speed playback
   with no takeover/rewind; keep exact overlays/timing/profile for M07-M09 qualification separate.
5. Send the resulting bytes through approved private M06 storage/integrity/media validation.
   Verify authorized private playback, matching complete-file checksum and separate attribution
   to the existing imported UUID. Preserve source lineage; playable video does not publish events.
6. Independently inspect source evidence, actual backend receipt/state and playback. A JSON
   declaration or checksum cannot establish real gameplay, consent, permission or scientific gates.
7. Repeat a PC-client trial for a console player's public replay with explicit platform evidence.
   Record console-specific absence/expiry/incompatibility; private console local replays are excluded.
8. Before hosted admission, exercise wrong identity, expiry, patch incompatibility, duplicate retry,
   rate limit, timeout, cancellation and consent withdrawal. Measure per-match elapsed time,
   bytes, GPU/CPU/disk/network, licenses/account requirements, queue capacity and cost under
   proposed M17 budgets. Select a permitted supported Windows/runtime hosting plan separately
   from the current Linux Cloud Run media processing design. No game farm is provisioned.

The first real proof and the full managed-service study are different acceptance boundaries.
One successful replay cannot qualify console coverage, stable transport, costs or commercial use.

## Executable offline preparation

Implementation: [evidence checker](../../ingestion/acquisition.py) and
[CLI](../../tools/qualify_replay_acquisition.py). These commands are for developers/operators,
not customer onboarding. Store evidence in ignored `private_data/`; publish only redacted receipts.

```powershell
.\.venv\Scripts\python.exe -m tools.qualify_replay_acquisition private_data/replay-acquisition/plan.json --init --native-control UNAVAILABLE
.\.venv\Scripts\python.exe -m tools.qualify_replay_acquisition private_data/replay-acquisition/plan.json --evidence-dir private_data/replay-acquisition --output reports/replay-acquisition.json
```

Initialization creates zero trials and PENDING reviews. It never starts the game, discovers an
ID, downloads media, installs a recorder or activates a provider. `--native-control` records an
operator observation; it does not test or grant control. Existing files cannot be overwritten.

Private plan schema `replay-acquisition/1` is exported as `ingestion.acquisition.SCHEMA`.
Each artifact has a unique local reference, kind, relative POSIX path, SHA-256 and byte count.
Only explicit artifacts in the selected real directory are read; traversal/absolute paths,
links/reparse points, changing bytes and checksum mismatches are rejected. Inputs are bounded
to 1 MiB JSON, 64 artifacts/600 MiB total, 512 MiB video and 8 MiB non-video per file. This is a
trusted local evidence checker, not a hostile-media parser; it never decodes video. Existing M15
isolated media validation still applies. Do not point it at an unrelated personal directory.

Each trial declares real/synthetic data, public/local/unknown origin, player platform, source
and playback build, observation/known expiry, external customer actions, manual worker actions,
captured video reference, delivered checksum and cost. The eight stage checks are browser
request, persistent identity mapping, match lookup, replay acquisition, compatible playback,
automatic capture, private delivery and match attribution. Each includes status, automatic/manual/
unknown execution, bounded attempts, elapsed seconds and evidence references. Trials include
failed, expired, incompatible and absent replays, not just successful captures. Do not insert a
synthetic placeholder or label synthetic footage real to fill an evidence gap.

A submitted first-replay candidate requires all eight automatically observed stages with evidence,
real/public-origin declarations, declared matching exact builds, known platform, zero desktop/manual
worker actions, captured-video bytes matching a delivery declaration and a delivery receipt artifact.
Unknown build compatibility is not rescued by filenames or matching names. Known expiry is checked
at observation time; an unknown replay TTL is not invented. Step and total elapsed time, attempts
and video bytes must fit explicit bounds. A USER_UPLOAD provider remains fallback evidence.

These conditions qualify **submitted evidence for review**, not actual replay acquisition. Even a
fully declared pack always returns `runtime_enabled`, `current_permissions_verified`,
`real_game_semantics_verified`, `current_backend_delivery_verified` and `release_approval` as false;
scientific gates remain NOT_RUN. It performs no ORM writes and contains no game/provider transport.
No production setting consumes its report as an activation approval.

Managed-service gaps also retain purpose-specific technical/usage review evidence and expiry,
console-through-PC candidate, fault-control evidence, rate policy and measured/budgeted costs.
Review artifacts must be separately inspected for authenticity and exact operation/runtime scope.
The report exposes counts/gaps and a canonical content hash, omitting trial identifiers, source
paths, artifact contents and raw player IDs. Private evidence may contain identifiers or permission
records; retain it under the approved private study policy, not git.

## Actual current evidence and next action

The [dated research](../research/native-tekken-replay-access-2026-10-06.md) establishes metadata
access and an in-client recording lead. Neither supplies a qualified end-to-end transport.
Computer Use initialization succeeded, but app enumeration failed because the native pipe was
absent (`os error 2`). No game window, current build, ID resolution, console replay, capture,
private delivery or automated recovery was observed. No EULA exception/usage approval exists.
The linked source investigation also records the official video-policy review; no managed
acquisition grant is established by fan-video conditions.

The initialized current plan has zero trials; its report is NOT_RUN with review, native-control,
console, rate, cost and all fault-control gaps. [Local qualification](../experiment-results/m22-replay-acquisition.md)
records software checks separately. The next dependent work is explicit technical/usage review
and restoring supported native game control, then the bounded actual replay trial. Both remain
required before implementing a live client adapter or presenting available recordings from ID alone.
