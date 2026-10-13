# ADR-029: private recording previews with explicit timing limits

Date: 2026-10-13. Architecture: 2.22.0. Decision: accepted for local/controlled
engineering (M06.12); actual hosted delivery (M06.11) remains unqualified.

## Context

The owner-provided Steam export can be converted without changing its recorded
timestamps, but HEVC and uneven frame spacing prevent admission to the strict
analysis profile. The trusted-local CLI does not provide authenticated website
playback, job ownership, lifecycle cleanup or storage accounting.

## Decision

Add `RecordingPreview` as a child of an owned `ReplayAsset`, with a distinct
`recording-preview/1` AnalysisRun. Bind the source hash, immutable attempt prefix,
lease/fence, derivative hashes, object generations, policy/timeline and quality.
Reserve source and maximum derivative bytes before accepting playback uploads.
Release reservations only after confirmed erasure and stopped execution; ambiguous
writes retain quota and block restore release. Keep the original bytes immutable.

Run normalization in a separate pinned, offline, unprivileged Docker profile.
Retrieve exactly three bounded regular files by trusted descriptor-based reads;
never expose a writable host output mount or extract an untrusted archive. The
HTTP process validates bounded JSON/hashes/timestamps without decoding media.
The explicit DEBUG/local operator escape remains trusted-local only.

Expose same-owner, no-store, authenticated range playback and paginated recording
timing intervals. Recheck revocation during streaming. Cancellation, withdrawal,
expiry, deletion and quarantine deny new access immediately; already authorized
or buffered bytes cannot be recalled. Windows open-file cleanup can be deferred,
with quota retained until maintenance confirms erasure.

`PREVIEW_READY` always carries empty gameplay opportunities and false gameplay,
canonical and scientific approval. It cannot satisfy attribution, detector,
dataset, practice or player-model publication gates. Playback-only upload does not
invent a Match, opponent, player identity, played time or continuous-capture claim.

## Consequences and release limits

The player can add one permitted MP4, watch its converted private preview and see
recording gaps. This is a fallback; browser ID-to-available-replay acquisition
remains the primary target, independently blocked on technical and usage evidence.
No private game endpoint, replay downloader, game control or cloud resource is enabled.

GCS derivative writes and cloud preview runtime have independent false qualification
gates. Official create-only/generation-pinned adapter contracts are controlled
tests, not deployed evidence. Hosted release requires equivalent media isolation,
bounded execution and staging, durable write intents that survive backup loss,
late-write/version erasure proof, IAM/CORS and real capacity/cost acceptance. A
logical reservation does not prove a physical hosting disk or billing limit.

Migration 0024 refuses rollback while preview rows retain bytes, manifests or
uncertain writes. Restore revokes results, confirms known local execution stop and
sweeps asset preview prefixes, including artifacts absent from a restored backup;
uncertain cloud writes keep quarantine. Local tests do not establish hosted safety.

See the [lifecycle contract](../architecture/private-recording-previews.md) and
[qualification receipt](../experiment-results/private-recording-previews.md).
