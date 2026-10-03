# M06: private uploads and evidence storage

Architecture 2.10.0, ADR-018 / D030, 2026-10-03. Local and controlled-client scope.
External uploads and real GCS use remain disabled; this is not staging approval.

## Owner-scoped lifecycle

UploadSession owns a unique (owner, request_id), a one-to-one ReplayAsset, optional
imported Match, claim digest, expected SHA-256/MD5, actual offset and one-hour expiry.
ReplayAsset reserves expected bytes immediately (maximum 512 MiB). Initializing,
uploading, verifying and purging sessions share the four global/one owner upload
slots with legacy multipart admissions. Assets awaiting physical purge remain in
storage quotas; failed cleanup does not release their reservation.

States are INITIALIZING -> UPLOADING -> VERIFYING -> COMPLETE, or PURGING -> CANCELLED.
The database persists initialization before the remote RPC. Repeating an identical
request returns the same receipt; changing file/details rejects it. No ambiguous
upstream initialization is reissued. Returned capabilities are retained even when
revocation races with the response. A lost capability retains its pre-recorded
seven-day-plus-ten-minute deadline; browser transfer access still expires at one hour.

API (authenticated session/CSRF, existing account rate limits, private no-store):

| Request | Purpose |
|---|---|
| POST /api/upload-sessions | Validate continuous MP4 declaration/consent/claim; reserve bytes; initialize once |
| GET /api/upload-sessions/{id} | Read owner-scoped state and actual observed offset |
| PUT /api/upload-sessions/{id}/chunk | LOCAL only, octet stream <=8 MiB, exact Content-Length and Upload-Offset; conflicting retry rejected |
| POST /api/upload-sessions/{id}/complete | Require all expected bytes; queue background verification |
| DELETE /api/upload-sessions/{id} | Cancel incomplete upload and attempt private physical cleanup |
| GET /api/assets/{id}/media | Completed evidence only; authenticated single-range playback |

No filename becomes an object key. Keys are generated owner/asset/source.mp4.
Input metadata is serializer allowlisted; imported claims bind player/opponent,
slot, original play time, build, purpose, characters, dataset kind and revision.
Only trusted operators can submit files. No native replay or undocumented Tekken
transport is enabled. Legacy multipart APIs remain available under their existing
bounded operator-only admission controls; the UI now uses resumable transfer.

## Verification and canonical publication

`process_uploads` sweeps ready/expired/revoked sessions; `process_runs` polling and
`purge_expired` also invoke reconciliation. Waiting transfers cannot consume the
ready-work scan. Failed purges receive a delay so other owners can advance.
Verification uses an owner-locked lease/fence with a 180-second absolute deadline,
three bounded transient attempts and backoff. Stale verifiers cannot publish or
erase newer completed evidence. Cancellation/deletion/withdrawal wins atomically.

For GCS, metadata must match the exact bucket/key, size, video/mp4 type, identity
encoding, expected MD5 and session ID. Pin its numeric generation, download within
byte/time bounds and hash actual bytes. LOCAL hashes the private file in small blocks.
Both require exact length/SHA-256/MD5. MD5 is the transport integrity checksum, not
an authorization or collision-resistant evidence identity; SHA-256 remains canonical.

Successful verification creates one upload Match/source/run, or a ReplaySource in
PENDING_REVIEW for an imported match. The imported UUID/history is preserved and
its Match.asset stays unselected until existing attribution review succeeds. No
GameplayEvent or approved coaching evidence is created from upload metadata.
The parser still verifies the supported 1080p60 SDR H.264 MP4 profile <=10 minutes,
and reviewed gameplay publication still requires its existing gates.

## Capability and playback boundaries

GCS uses its official JSON API: fixed storage.googleapis.com, configured bucket,
create-only ifGenerationMatch=0, fixed content length/type and validated Location.
Chunks are multiples of 256 KiB (8 MiB default) except the last. Probe the actual
committed Range after every transfer/lost response; do not assume all sent bytes
were committed. Cancellation accepts the documented JSON API 499 receipt.

Session URIs are secret bearer capabilities. They appear only in an authorized
UPLOADING response and the direct HTTPS request. Browser GCS requests omit app
cookies, authorization, CSRF and referrers; URLs are never persisted. Browser
sessionStorage holds only fingerprint, request UUID and internal session ID. After
refresh, reselect the same file/details to resume. Different input must cancel the
existing receipt first. A 404 cancellation clears only the stale browser receipt;
it grants no access to another account's upload.

Private playback supports one bounded/open/suffix byte range. GCS requests pin the
verified generation and require an exact 206 Content-Range and identity encoding.
Ignored ranges, oversized/short upstream bodies and redirects fail closed; upstream
connections close on failure/disconnect. A 180-second read limit and periodic owner,
quarantine, deletion and retention checks stop continued streaming. No public or
signed playback URL is returned. Actual browser CORS/Range behavior awaits staging.

## Erasure, restore and operation

Cancel pending upstream sessions before purging all versions under the exact asset
prefix. Failed cancellation/listing/deletion leaves a tombstone, reserved bytes and
PURGING state. Expiry, account/target-match deletion and processing withdrawal revoke
pending uploads. Their worker retries cleanup. Completed captures use existing asset
delete, withdrawing canonical evidence while retaining imported match metadata.

Signed asset/account controls include private storage identity, reserved bytes and
nonsecret upstream deadline. They never contain the capability URI. Restores revoke
all pending sessions/leases and consent before reads. A post-backup missing asset is
recreated as a private tombstone, or swept under orphan controls; an unknown still-live
capability cannot be acknowledged as erased. Repeated restore application is safe.
Independent current controls are required; an older DB/media snapshot is insufficient
and does not authorize releasing restore quarantine.

Run `python manage.py process_uploads` regularly for verification/cleanup, or run the
ordinary polling worker. Run `purge_expired` and existing maintenance at least hourly.
Migration 0016 preserves existing assets as LOCAL with no session deadline; reversal
refuses any session without completed physical erasure. Stop ingress/workers, back up,
inspect actual sessions/objects and review rollback before downgrading a live schema.

## Qualification still required

GCS_STORAGE_QUALIFIED=False, RESUMABLE_STORAGE_PROVIDER=LOCAL, external uploads=False
and managed media=False remain code gates, not environment switches. To change them,
review project/region/budget, private bucket IAM/public prevention/soft-delete/version
policy, upload CORS/preflight/308/probe/expiry behavior, fixed metadata/checksums,
generation ranges, delayed cancellation and all-version erasure under actual outages.
Retain dated staging receipts and an approved architecture change. Review independent
durable controls and hosted parser isolation, ingress/temp quotas, named maintenance,
account/consent/backup erasure and privacy/real capture validation before public release.

Official contracts reviewed: [resumable uploads](https://docs.cloud.google.com/storage/docs/performing-resumable-uploads),
[object insertion](https://docs.cloud.google.com/storage/docs/json_api/v1/objects/insert),
[object metadata](https://docs.cloud.google.com/storage/docs/json_api/v1/objects),
[range parameters](https://docs.cloud.google.com/storage/docs/json_api/v1/parameters)
and [data validation](https://docs.cloud.google.com/storage/docs/data-validation).
Controlled tests establish our adapter contract only; they do not prove actual Google
configuration, permitted live Tekken ingestion or real gameplay accuracy.
