# ADR-018 - Resumable private evidence uploads

Date: 2026-10-03. Status: accepted for local and controlled-client engineering.

M06 needs a complete transfer lifecycle before real hosting qualification. Add an
owner-scoped UploadSession beside ReplayAsset, without introducing provider details
into Match, GameplayEvent, reviewed attribution or player-model contracts. Reserve
expected bytes and upload capacity before any transfer. Keep the request UUID,
claim digest, actual offset, expiry, verification lease/fence and retry state durable.

Use bounded local chunks and the official GCS JSON resumable-upload contract.
GCS sessions are bearer capabilities: expose them only to their authenticated owner,
never logs, exports, signed control journals or browser persistent storage. Validate
fixed host/bucket/object URLs and use a create-only generation precondition. A lost
initialization receipt never triggers a second upstream session. Record the upstream
capability deadline before initialization; retain returned capabilities even when
account deletion races with the response.

Completion requests queue verification. A background worker checks owner, consent,
claim revision, object identity, exact bytes, SHA-256 and MD5, pinning the GCS content
generation. Only then create canonical upload provenance or pending recording
attribution and one AnalysisRun. Integrity verification does not establish valid
media, a real match, attribution or gameplay. Existing isolated parsing and
independent attribution/gameplay reviews remain necessary.

Cancellation, expiry, withdrawal, match/account deletion and restore fence pending
sessions. Failed physical cleanup holds bytes and capacity. Cancel a known capability
before sweeping every object generation under its exact asset prefix. When recovery
has only a nonsecret deadline, keep erasure incomplete and quarantine closed until
the capability has expired and a subsequent prefix sweep succeeds. Never infer
successful erasure from a missing URI or one earlier empty object listing.

Playback remains authenticated and private. GCS reads pin generation, require exact
single-range headers and byte bounds, close upstream streams, and periodically
check revocation. Expired evidence cannot start, continue or publish analysis or
enter newly computed practice/comparisons.

The browser hashes small blocks, transfers bounded chunks, rechecks observed offsets,
and supports pause, resume, refresh recovery and cancellation. The accepted capture
profile requires one continuous uncut recording; the checkbox is a declaration,
not automatic segmentation/rewind detection.

GCS_STORAGE_QUALIFIED and external uploads remain false in code. Local uploads stay
staff-only. Actual IAM/CORS/session/range/late-finalization/version erasure, equivalent
hosted parser isolation, independent durable controls, ingress/temp quotas and real
capture attribution are release gates. No cloud resources or live provider session
were created. See [contract](../architecture/evidence-storage.md) and
[qualification](../experiment-results/m06-storage.md).
