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
