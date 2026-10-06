# ID search and private recording sync

Updated 2026-10-06; Architecture 2.19.0. Status: local developer preview implemented (M22.02-06),
coherent local engineering qualified on source 7635a3c (all seven CI jobs). No live provider transport, signed installer, hosted admission or game
automation is enabled. [Run the source helper](../../companion/README.md).
Decision: [ADR-026](../adr/ADR-026-id-search-and-private-recording-companion.md).

Follow-up [native-access investigation](../research/native-tekken-replay-access-2026-10-06.md)
keeps external playable-payload retrieval UNVERIFIED, not impossible. This is a staged fallback;
a subsequently permitted and validated native source can supply evidence through the same
canonical pipeline. Public-source research does not activate any private game operation.

## Selected product journey

1. Enter a TEKKEN ID and explicitly confirm an approved provider's matching profile.
2. Import recent metadata through the existing provider-neutral match pipeline. Show source,
   coverage, freshness and unknowns; name lookup remains unavailable without a permitted resolver.
3. For an owned match, Play opens an accessible, validated recording if one is linked. Otherwise
   show that a recording is needed. A public ID alone never reveals anyone's private media.
4. Optionally install and pair the Windows companion, choose a recording folder and opt into
   automatic sync. Supported completed recordings enter the existing private upload path.
5. Match attribution and gameplay review proceed separately. A playable recording is not a
   verified measurement; automatic upload cannot publish GameplayEvent or coaching judgments.

Initial folder sync requires the player to record/export an MP4. It does not promise that
typing an arbitrary ID retrieves footage, captures an old match or starts Tekken. The later
replay-recording stage is conditional on a permitted and validated in-client approach.

## Provider choice and release boundaries

Prefer EWGF's documented per-ID battle operation for the first metadata evaluation, subject
to [the existing activation requirements](../research/ewgf-activation-review-2026-09-19.md).
Public documentation rechecked 2026-10-06 still describes bearer authentication, free last-50
battles with a 24-hour delay and 100 requests/hour, and Pro last-100 without that delay with
1,000 requests/hour. These are dated descriptions, not a provisioned tier, coverage guarantee
or commercial permission. No authenticated fixture or key was obtained. The terms page yielded
no substantive usage text in this review; approval remains unresolved.
[Published API](https://ewgf.gg/api-docs), [terms location](https://ewgf.gg/terms).

Wavu remains a reviewed candidate for metadata, with no documented video download. Do not
scan a global feed per ID/keystroke or silently fall back to an undocumented route on outage.
Server credentials stay out of the browser and companion. Global credential quota, bounded
responses, schema checks, Retry-After, capped retries and source/version provenance follow
the [ingestion contract](match-ingestion.md).

Companion recordings remain USER_UPLOAD with a dated capture-tool assertion and, where
verified, OFFICIAL in-client playback lineage. This does not make an external Tekken API
OFFICIAL. Native payload retrieval/decoding remains X01; in-client automation needs its own
operation review. Manual upload remains available, including on consoles.

## First implementation: completed-file sync

Use existing M06/M14/M15/M16 services rather than a second media or domain pipeline. No new
broker, cloud game farm, raw frame store or measurement rules are required.

| Boundary | Required behavior before release |
|---|---|
| Pairing | Short-lived one-use owner-authorized pairing; scoped revocable device credential in OS-protected storage, never account passwords or provider keys. HTTPS pinned configured service origin; no arbitrary destination or upload URLs accepted. Bound credential lifetime/rate and treat device possession separately from game-account control. |
| Local access | Explicit folder selection and permission; default sync off with visible start/pause/stop and queue. No recursive disk scan, Steam private database parsing, game-process access or automatic selection of unrelated media. Reject links/reparse escapes and files outside the selected root. |
| Admission | Only supported completed MP4s within M06 limits. Stability checks alone do not prove completion; use a readable finalized container and a consistent hashed byte snapshot, recheck changes before/during transfer, and let the server's integrity/media validation remain authoritative. Unsupported or unfinished files stay local. |
| Durable transfer | Persist a private local receipt with owner/device, random retry key, source hash/size, destination upload ID and confirmed offset. Use bounded concurrent uploads, shared owner quotas, exponential backoff, Retry-After, pause/cancel and restart recovery. Identical bytes are idempotent per owner; hashes do not prove match identity. |
| Attribution | IDs, participants/slots, played time, exact build and mode are assertions to verify. File creation/export time is not match time; filenames and a linked TEKKEN ID are not sufficient. Create pending evidence or an upload-only record when no reviewed imported-match link exists. Preserve canonical UUID and historical revisions. |
| Privacy | New sync consent is explicit. Recheck server consent, owner and target lifecycle on every transfer operation; invalid credentials stop the queue. Revocation/deletion fences late chunks and retries using existing cleanup rules. Remote deletion cannot promise erasure of the user's original local recording; local receipts cannot resurrect removed evidence. |
| Diagnostics | Bounded redacted logs and visible failures; exclude tokens, full local paths, raw profiles and opponent identifiers. Cap local receipt/cache retention and disk/byte/network use; expose unmetered cost as unknown until measured. |

A proposed device receipt is an upload retry record, not PlayerGameIdentity or proof of ownership.
Device registration and pairing introduce new authorization boundaries and must be tested before
external sync is enabled. The current browser/session-CSRF interface is not silently repurposed
as a permanent device API. Backend admission and hosted storage gates apply equally to a helper.

## Conditional next stage: replay playback and recording

The [community example](https://github.com/Cathesilta/tekken8_oneshot_replays) depends on in-game
download and a local recorder. Before adopting any approach, review permitted operations and
source/code licensing separately; qualify the current runtime, capture hardware, overlays,
normal uninterrupted playback, cancellation and storage limits. Do not infer exact payload
schema or supported standalone decoding from that README. No code was copied or executed.

Native replay existence and runtime compatibility are independent. Official patches can make
older downloaded replays unplayable and delete online replay data. Mark an unavailable replay
honestly and retain accessible permitted recorded video under its own retention policy; do not
invent a universal TTL or promise to regenerate all historical matches.
[Official version-specific impact](https://www.bandainamcoent.com/news/tekken-8-patch-notes-v3-00-02).

Qualification requires actual supported-build playback/capture evidence and usage review.
M22's initial sync does not depend on this stage. It never authorizes private endpoints,
anti-cheat bypass, memory hooks, unattended account use or collection of other users' recordings.

## Implementation order and acceptance

M22.01 records this choice. Pairing/revocation and completed-file sync (M22.02-M22.06)
are implemented and qualified against the existing local evidence services with controlled
fixtures; M22.10 records the coherent local module and source CI evidence.
Then qualify real Windows packaging/device privacy/capture compatibility and resource behavior
(M22.07-M22.08). Live EWGF activation is parallel M04/M05 work and not a prerequisite for
upload-only recordings. Evaluate in-client automatic replay capture separately (M22.09).

Meaningful checks must cover cross-owner pairing/upload isolation; expired/reused/revoked
tokens; selected-root escapes and a growing/changed file; interrupted/restarted transfers;
duplicate sync; quota/rate failures; withdrawal/deletion during retry; incorrect attribution;
and preservation of the metadata-only/event boundary. Controlled fixtures do not establish
real replay availability, hosted readiness, game knowledge, G1-G6 or player benefit.

## Implemented local boundaries (2026-10-06)

The source helper and browser controls reuse M06 reservations, integrity, isolated parser,
private ranges and deletion. Synced bytes first exist as ReplayAsset/UploadSession with
unattributed capture-tool provenance; no Match/played_at is invented. After media validation,
the browser can submit the existing attribution claim against an imported UUID using the
same operator review. No byte re-upload or automatic GameplayEvent publication occurs.

RecordingDevice credentials are SHA-256 hashes on the server and DPAPI protected per-user
on Windows; only the dedicated device upload operations accept them. DevicePairing is
one-use/ten-minute, device lifetime 30 days, and browser pairing controls retain session/CSRF.
Every transfer rechecks owner, device, consent and target under the owner lock. Withdrawal,
account recovery/logout-all and restore revoke devices; pending bytes use M06 fenced purge.
RecordingReceipt stores an owner-keyed byte suppression digest, surviving deletion; duplicate
bytes on another device return only DUPLICATE/REMOVED, never another device's capability.

HTTPS origins are explicitly configured; local development allows only loopback port 8000.
No redirects, cookies, environment proxies, arbitrary upload URLs or GCS capabilities enter
the source helper. Local admission is off by default, operator-only, DEBUG-only and LOCAL
storage-only; a deployment flag cannot activate an external service.

See [source helper limits/controls](../../companion/README.md) and
[qualification receipt](../experiment-results/m22-recording-sync.md). M22.07-08 still require
real supported recorder/device and hosted/installer/update/privacy/resource acceptance.

Manual copies encountered by sync also create an explicit owner-keyed suppressed receipt,
without granting device access to the manual session. Verified removed manual assets are
recognized by their existing hash. Guarded migrations 0022/0023 preserve device and byte
suppression history; restore revokes credentials while retaining suppression.
