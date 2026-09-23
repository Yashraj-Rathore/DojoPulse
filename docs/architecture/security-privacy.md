# Security and privacy

External uploads are disabled in the initial local build. Authenticated metadata APIs use
owner-scoped querysets AND nested-reference validation. Staff review is distinct from ownership.
Session cookies are HttpOnly with CSRF; deployment requires HTTPS and secure cookie settings.
Source media and signed upload credentials never appear in logs, public static directories or Git.

Deletion tombstones first, prevents publication, cancels open upload sessions and checks for late
finalized objects until cancellation/expiry resolves. Remove raw/proxy/annotation/artifact copies,
events and active contributions, invalidate evaluations and purge private dataset derivatives.
Hosted deletion cannot be claimed implemented solely because a fake-storage test passes.

Decoder isolation requires patched allowlisted tools, no arbitrary flags, no remote protocols,
bounded CPU/memory/wall time, read-only container root and isolated scratch storage. Processing
credentials cannot provide unnecessary cross-owner media access. Local resource tests do not
prove hostile-file safety. See deployment gates before enabling network ingestion.

Service processing consent and optional model training consent are independent. No model
training occurs in this implementation. Gameplay may identify opponents; no anonymous-data claim.
Study source retention: through evaluation + audit, max 60 days unless renewed consent. Deletion
wins over reproducibility. Restore must reapply tombstones before exposing records.

Implemented local boundary: loopback operator uploads, source/derived-directory deletion,
fenced job cancellation, tombstones, consent distinction and retention command. Asset deletion
also invalidates evidence-backed recommendations and practice-dependent evaluations.
Write transactions lock the owner first, then narrower rows, so deletion cannot race past
publication of a new conclusion. PostgreSQL concurrency tests exercise that ordering.
Manually copied exports, external annotation folders, backups and cloud objects still require
an operator inventory/provider adapter; they are not silently covered by local asset deletion.

Provider ingestion additionally requires operation/purpose-specific usage review and expiring
technical approval. Public IDs do not prove account ownership. Network/provider credentials
remain server-side, with shared quotas and allowlisted destinations. Revoking an identity must
stop/fence syncs and handle source snapshots even when no video exists. These lifecycle additions
are implemented for the local [metadata-import cutover](match-ingestion.md), not hosted services.
Candidate confirmations use signed owner-bound tokens with a five-minute lifetime. The local
API enforces session/CSRF protection and owner filters; history responses are private/no-store.
The demo flag requires DEBUG and staff status and cannot enable any live provider. Revoking an
identity fences queued jobs; schema failures are quarantined without advancing a checkpoint.

M13 adds owner-scoped preferences, feedback/corrections, in-app notice receipts and a bounded
allowlisted JSON export. Account deletion requires current password, exact confirmation and CSRF.
It pseudonymizes login fields and tombstones all assets before filesystem IO; purge failures
remain retriable even for assets not yet visited. New feedback and receipts are erased.
Authenticated range playback preserves private/no-store headers and never accepts arbitrary paths.
See [player experience](player-experience.md) for export exclusions and local-only limits.
