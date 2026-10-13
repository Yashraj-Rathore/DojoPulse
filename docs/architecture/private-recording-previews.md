# Private recording preview contract

Architecture 2.22.0; 2026-10-13. [ADR-029](../adr/ADR-029-private-recording-preview-lifecycle.md).
M06.12 defines local/controlled engineering; M06.11 retains actual hosted acceptance.

## Owned lineage and admission

`RecordingPreview.asset` is one-to-one with an owned ReplayAsset; its current run
is one-to-one with a `recording-preview/1` AnalysisRun. Preview state is
WAITING_UPLOAD, QUEUED, READY, PURGING or PURGED. The original is never replaced.
Each attempt writes create-only artifacts beneath
`OWNER/ASSET/previews/PREVIEW/RUN/FENCE/`, preventing retry/ABA key reuse.
Manifest entries pin exact keys, byte counts, SHA-256 and GCS generations.

`POST /api/upload-sessions` with `preview_only: true` requires processing consent
and permitted MP4 bytes, but does not require a continuous-capture assertion or
Jin/Jin analysis metadata. Only optional declared game version/platform survive
metadata shaping. Canonical match claims are rejected. Integrity verification
finishes the upload before enqueueing conversion. No Match or GameplayEvent is
created by this path. It reuses ordinary owner/operator admission, upload receipts,
bounded resumable chunks, owner/global quota, consent and source-hash checks.

Maintenance preserves WAITING_UPLOAD reservation while its upload is active and
unexpired, subject to owner/processing/retention/quarantine checks. Completion under
the owner lock enqueues conversion only if WAITING_UPLOAD intent remains. Cancelling
the derivative before verification lets the original finish without restarting it;
later explicit preparation needs a fresh request and reservation.

Reserve source bytes plus 547,356,672 derivative bytes: 512 MiB video, 8 MiB report,
2 MiB timeline. Repeated requests do not duplicate jobs or reservations.
Old terminal receipts return current state without resetting a purged preview;
a new conversion uses a fresh request/run and superseded receipts cannot overwrite it.
Generic browser upload leaves platform undeclared rather than guessing Steam;
declared version/context still grants no canonical identity or gameplay facts. Snapshot
1,920 seconds per attempt and the existing maximum attempts/daily budget policy.
Actual published artifact bytes replace the maximum reservation only on fenced
success. Active execution, incomplete cleanup and write ambiguity hold storage.
Decoder CPU/RSS coverage is not inferred from coordinator measurements.

## Isolation and hostile output

The preview profile uses the pinned parser image, network none, UID/GID 10001,
read-only root, no capabilities, no new privileges, 64 PIDs, two CPUs, 3 GiB memory
including tmpfs and no swap. Only source and empty metadata are mounted read-only.
Work tmpfs is 1,152 MiB, temporary tmpfs 64 MiB; the normalizer bounds outputs and
the container deadline is 1,800 seconds. The container stays alive after completion
so tmpfs artifacts remain available for retrieval, then is removed authoritatively.

Fixed trusted Python opens exactly `preview.mp4`, `report.json`, `timeline.json`
with O_NOFOLLOW and checks descriptor regularity, link count one and bounded size.
Raw bytes stream into create-only coordinator files with independent output limits.
There is no host output mount, Docker copy/tar extraction, supplied path, arbitrary
output tree or credential/socket mount. Status is bounded to 8 KiB. Host HTTP
processes never invoke FFmpeg/ffprobe; bundle admission recomputes hashes, full PTS
vectors and timing-quality counts and rejects extra files/approval claims.

Coordinator staging and publication can temporarily hold two bounded artifact
copies. Logical owner quota is source plus final/reserved derivative; physical
staging capacity, admission/concurrency and real maximum-load acceptance remain
deployment obligations. The trusted-local escape is explicitly DEBUG and operator
only, and does not demonstrate managed isolation.

## Website and lifecycle

The workspace's **Private recordings** section lists the latest 50 owned assets.
It supports manual preview upload, preparation/retry, cancel/remove converted
playback, private video and pages of 100 original recording timing intervals.
URLs must exactly match the internal owned preview route. A read failure clears
stale media/quality, and an in-flight refresh cannot repopulate removed playback.
The original stays available to the existing separate evidence/attribution workflow.

Routes:

- `GET /api/private-recordings`: owned recording summaries, no private storage keys.
- `GET|POST|DELETE /api/assets/{UUID}/preview`: state, idempotent preparation,
  converted-artifact cancellation/removal; DELETE preserves original bytes.
- `GET /api/assets/{UUID}/preview/media`: authenticated no-store full/open/suffix
  ranges, exact byte bounds, LOCAL file size or pinned GCS generation.
- `GET /api/assets/{UUID}/preview/quality?offset=N`: bounded numeric timing positions;
  no source paths, storage keys, identifiers from a decoder report or source hash.

All reads verify ownership, source hash, current run/fence, verified upload,
processing permission, retention, account state and restore quarantine. Streaming
periodically rechecks access; previously authorized/downloaded bytes remain beyond
server revocation. Recording gaps are continuity evidence only, not identified
game frames, cut/rewind cause, moves, match attribution or coaching approval.

Cancellation fences work and denies playback before physical cleanup. An old local
publisher cannot recreate bytes after owner-serialized deletion/withdrawal; stale
attempts are fenced and erased before stop acknowledgment/retry. Reconciliation
retains slots when Docker stop cannot be confirmed. Source deletion holds parent
purge/upload quota until every child is erased. Processing withdrawal clears preview
results; training-only withdrawal does not revoke separately permitted playback.
Export contains shaped preview state/quality, never its private manifest.

Restore cancels runs/revokes previews before prefix erasure. Known active local
Docker containers must be stopped; trusted host decoder stop uncertainty blocks
release. Local preview prefixes are swept for every source, including post-backup
children missing from the database and unknown assets in the server-owned numeric
owner/UUID-asset namespace, without deleting retained originals. Inventory bounds
fail quarantine rather than silently truncating; links cannot escape the private
root. Quarantine/read guards do not replace the required operational stop of
trusted-local workers before restore. Pending
cloud write intent blocks release. Migration reversal requires confirmed PURGED
rows with no bytes, manifest or write uncertainty.

## Hosted release gates and reviewed references

ADR-030 adds [independent write recovery](preview-write-recovery.md): initialization
and session receipts, resumable create-only uploads, orphan quota mirrors,
cancellation before all-version erasure and empty-inventory confirmation. Legacy
ambiguous media POSTs without receipts stay blocked. Controlled correctness does
not qualify independent replicated durability or actual cloud operation.

GCS preview publication and managed runtime remain independently disabled, even
when ordinary source storage is qualified. Controlled create-only media insertion
uses the fixed official endpoint, ifGenerationMatch=0, bounded streamed body and
response verification of bucket/key/size/MD5/generation; reads pin that generation.
Prefix erasure enumerates all versions and rejects foreign/source object scope.
Write intent is persisted before RPC and is not refunded on an ambiguous response.

Actual hosted acceptance still needs durable intents outside restorable database
state, backup-loss/late-write erasure proof, equivalent isolated runtime, finite
in-flight write settlement, IAM/CORS, region/budget and measured representative
workload/cost. None is inferred from these contracts or local Docker tests.

Primary API references reviewed 2026-10-13: [Google objects.insert](https://docs.cloud.google.com/storage/docs/json_api/v1/objects/insert)
and [Docker container exec](https://docs.docker.com/reference/cli/docker/container/exec/).
Their documented mechanisms do not establish game-provider usage rights or
production approval. [Qualification](../experiment-results/private-recording-previews.md)
separates synthetic checks, actual owner footage, Docker and hosted evidence.
